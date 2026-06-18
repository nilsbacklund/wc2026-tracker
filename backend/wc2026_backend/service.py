"""Application service: ingestion, Elo updates, simulation, snapshots.

Ties the engine, sources, and store together. Stateless functions that take
a Store so the live loop, CLI, and API all share one code path.
"""
from wc2026 import elo as elo_rule
from wc2026 import model
from wc2026 import thirds
from wc2026.simulate import default_spec, run_sims
from wc2026.structure import (AMERICAS, BRACKET, GROUP_LETTERS, HOSTS,
                              R32_MATCHES, TEAMS)

from .sources import eloratings, espn


def import_elo(store, ratings=None):
    """Import ratings (default: live eloratings.net) into the store."""
    ratings = ratings or eloratings.fetch_elo()
    store.set_elo(ratings)
    return ratings


def spec_from_store(store):
    """Build an engine spec from stored Elo (falling back to defaults)."""
    elo = store.get_elo()
    if not elo or len(elo) < len(TEAMS):
        return default_spec(elo or None)
    return default_spec(elo)


def ingest_espn(store, events=None):
    """Apply ESPN live/finished results to matches. Returns ids that changed."""
    events = events if events is not None else espn.fetch_scoreboard()
    changed = []
    for ev in events:
        match = store.match_by_teams(ev["home"], ev["away"])
        if match is None:
            continue
        row = dict(match)
        # Orient scores to the stored home/away (ESPN home may be our away).
        if ev["home"] == match["home"]:
            hs, as_ = ev["home_score"], ev["away_score"]
        else:
            hs, as_ = ev["away_score"], ev["home_score"]
        row.update(status=ev["status"], home_score=hs, away_score=as_,
                   minute=ev["minute"], kickoff_utc=ev.get("kickoff_utc")
                   or match["kickoff_utc"])
        if match["stage"] != "group" and ev["status"] == "finished" and ev["winner"]:
            row["ko_winner"] = ev["winner"]
            row["ko_decided_by"] = row.get("ko_decided_by") or "regular"
        if _row_changed(match, row):
            store.upsert_match(_to_upsert(row))
            changed.append(match["id"])
    return changed


TOURNAMENT_START = "2026-06-11"


def _date_range(start, end):
    """List of YYYYMMDD strings from start to end (inclusive), ISO dates in."""
    from datetime import date, timedelta
    d0 = date.fromisoformat(start)
    d1 = date.fromisoformat(end)
    out = []
    while d0 <= d1:
        out.append(d0.strftime("%Y%m%d"))
        d0 += timedelta(days=1)
    return out


def backfill_espn(store, start=TOURNAMENT_START, end=None):
    """Ingest every match day from `start` to `end` (default today, UTC).

    ESPN's default scoreboard only returns the current day, so a fresh deploy
    mid-tournament must walk past dates to pick up already-played results.
    Returns the combined list of changed match ids.
    """
    from datetime import datetime, timezone
    end = end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    changed = []
    for d in _date_range(start, end):
        try:
            changed.extend(ingest_espn(store, espn.fetch_scoreboard(date=d)))
        except Exception:
            continue  # a bad day shouldn't abort the whole backfill
    return changed


def _state_with(all_matches, known_ids):
    """Engine state where only matches in `known_ids` are finished; the rest
    are scheduled. Mirrors store.engine_state()'s per-match shape."""
    out = []
    for m in all_matches:
        e = {"id": m["id"], "stage": m["stage"], "group": m["grp"],
             "home": m["home"], "away": m["away"], "minute": None}
        if m["id"] in known_ids and m["home_score"] is not None:
            e["status"] = "finished"
            e["score"] = {"home": m["home_score"], "away": m["away_score"]}
            if m["stage"] != "group":
                e["ko"] = {"winner": m["ko_winner"],
                           "decided_by": m["ko_decided_by"]}
        else:
            e["status"] = "scheduled"
        out.append(e)
    return {"matches": out}


def _initial_elo(store):
    """Pre-tournament Elo: each team's rating before its first update.

    Reconstructed from elo_history (the earliest recorded 'before' per team);
    teams that haven't played keep their current rating (never updated).
    """
    ratings = dict(store.get_elo())
    earliest = {}
    for r in store.elo_history_rows():  # ascending application order
        earliest.setdefault(r["team"], r["before"])
    ratings.update(earliest)
    return ratings


def rebuild_history(store, n=20000):
    """Replace the snapshot history with one snapshot per played match.

    Replays finished matches in chronological (kickoff) order: a pre-tournament
    baseline, then a snapshot after each match. Crucially, the Elo ratings
    EVOLVE through the replay — starting from the pre-tournament values and
    applying each match's K=60 update in order — so every historical point
    reflects what was actually known then (a team's rating jump shows up at the
    match that caused it, not retroactively). Each point also conditions on the
    cumulative real results. A fixed seed keeps Monte Carlo noise consistent
    between adjacent points.
    """
    all_matches = store.all_matches()
    finished = [m for m in all_matches
                if m["status"] == "finished" and m["home_score"] is not None]
    finished.sort(key=lambda m: (m["kickoff_utc"] or "", m["id"]))

    elo = _initial_elo(store)
    store.clear_snapshots()

    # Baseline: pre-tournament ratings, no results.
    res = run_sims(spec=default_spec(elo),
                   state=_state_with(all_matches, set()), n=n, seed=2026)
    store.add_snapshot(res["probs"], n, "pretournament", None)

    known = set()
    for m in finished:
        a, b = m["home"], m["away"]
        # Evolve Elo with this match's result (same rule as live updates).
        if a in elo and b in elo:
            eff_a = float(model.effective_rating(elo[a], a in HOSTS, a in AMERICAS))
            eff_b = float(model.effective_rating(elo[b], b in HOSTS, b in AMERICAS))
            elo[a], elo[b] = elo_rule.update(
                elo[a], elo[b], m["home_score"], m["away_score"],
                eff_a=eff_a, eff_b=eff_b)
        known.add(m["id"])
        res = run_sims(spec=default_spec(elo),
                       state=_state_with(all_matches, known), n=n, seed=2026)
        store.add_snapshot(res["probs"], n, "fulltime", m["id"])
    return len(finished)


def _outcome_probs(spec, home, away, stage):
    """Probabilities + representative scores for a match's outcomes.

    Group: home win / draw / away win via independent Poisson goals.
    Knockout: two outcomes via the compressed Elo win probability.
    Scores are oriented to the stored home/away.
    """
    from math import exp, factorial
    info = spec["teams"]

    def eff(team):
        return float(model.effective_rating(
            info[team]["elo"], info[team]["host"], info[team]["americas"]))

    ea, eb = eff(home), eff(away)
    if stage != "group":
        p = float(model.ko_win_prob(ea, eb))
        return [("home", p, {"home": 1, "away": 0}),
                ("away", 1 - p, {"home": 0, "away": 1})]

    la, lb = (float(x) for x in model.lambdas(ea, eb))
    pois = lambda k, lam: exp(-lam) * lam ** k / factorial(k)
    ph = pd = pa = 0.0
    for i in range(11):
        for j in range(11):
            p = pois(i, la) * pois(j, lb)
            if i > j:
                ph += p
            elif i == j:
                pd += p
            else:
                pa += p
    s = ph + pd + pa or 1.0
    return [("home", ph / s, {"home": 2, "away": 0}),
            ("draw", pd / s, {"home": 1, "away": 1}),
            ("away", pa / s, {"home": 0, "away": 2})]


def _force(state, match_id, score):
    """Copy of state with one match forced to a finished result."""
    out = []
    for m in state["matches"]:
        if m["id"] == match_id:
            m = {**m, "status": "finished", "score": score}
            if m.get("stage") and m["stage"] != "group":
                winner = m["home"] if score["home"] > score["away"] else m["away"]
                m["ko"] = {"winner": winner, "decided_by": "regular"}
        out.append(m)
    return {"matches": out}


METRICS_IMPORTANCE = ("champ", "advance")


def match_importance(store, n=6000, max_matches=14):
    """Rank upcoming matches by how much their outcome moves the predictions.

    For each scheduled match with known teams, force each outcome, re-simulate,
    and measure (a) the expected shift of the whole title-odds distribution
    (total impact) and (b) each team's min/max odds across outcomes (per-team
    leverage — includes matches a team isn't playing in). Uses current ratings.
    """
    spec = spec_from_store(store)
    state = store.engine_state()
    base = run_sims(spec=spec, state=state, n=n, seed=2026)["probs"]
    teams = list(base.keys())

    upcoming = [m for m in store.all_matches()
                if m["status"] == "scheduled" and m["home"] and m["away"]]
    upcoming.sort(key=lambda m: (m["kickoff_utc"] or "", m["id"]))

    out = []
    for m in upcoming[:max_matches]:
        outs = _outcome_probs(spec, m["home"], m["away"], m["stage"])
        per_team = {t: {k: [] for k in METRICS_IMPORTANCE} for t in teams}
        total = {k: 0.0 for k in METRICS_IMPORTANCE}
        meta = []
        for label, prob, score in outs:
            probs_o = run_sims(spec=spec, state=_force(state, m["id"], score),
                               n=n, seed=2026)["probs"]
            # Capture the two participants' odds under this outcome, so the UI
            # can explain "how the scores need to end up."
            meta.append({
                "label": label, "prob": round(prob, 3), "score": score,
                "home_adv": round(probs_o[m["home"]]["advance"], 1),
                "home_champ": round(probs_o[m["home"]]["champ"], 2),
                "away_adv": round(probs_o[m["away"]]["advance"], 1),
                "away_champ": round(probs_o[m["away"]]["champ"], 2),
            })
            for k in METRICS_IMPORTANCE:
                acc = 0.0
                for t in teams:
                    v = probs_o[t][k]
                    per_team[t][k].append(v)
                    acc += abs(v - base[t][k])
                total[k] += prob * 0.5 * acc
        team_swing = {
            t: {k: {"min": round(min(per_team[t][k]), 2),
                    "max": round(max(per_team[t][k]), 2),
                    "base": round(base[t][k], 2)}
                for k in METRICS_IMPORTANCE}
            for t in teams}
        out.append({
            "id": m["id"], "home": m["home"], "away": m["away"],
            "group": m["grp"], "kickoff_utc": m["kickoff_utc"],
            "outcomes": meta,
            "total": {k: round(total[k], 2) for k in METRICS_IMPORTANCE},
            "teams": team_swing,
        })
    return {"matches": out, "n_sims": n}


def compute_and_store_importance(store, n=6000, max_matches=14):
    data = match_importance(store, n=n, max_matches=max_matches)
    store.set_analysis("importance", data)
    return data


def most_likely_bracket(store, n=20000):
    """The 'favorites advance' knockout bracket.

    Group standings come from the Monte Carlo (most likely 1st/2nd/3rd per
    group); the best-8 thirds fill the R32 third-place slots; the result is the
    16 Round-of-32 pairings. The frontend resolves the rest of the tree by
    effective Elo (so it can also flip matches to explore scenarios), so we
    also return each team's effective rating. Real R32 pairings override the
    projection once a match's teams are known.
    """
    spec = spec_from_store(store)
    res = run_sims(spec=spec, state=store.engine_state(), n=n, seed=2026,
                   with_groups=True)
    gp, probs = res["group_pos"], res["probs"]
    info = spec["teams"]

    def eff(team):
        return round(float(model.effective_rating(
            info[team]["elo"], info[team]["host"], info[team]["americas"])), 1)

    first, second, third = {}, {}, {}
    for g in GROUP_LETTERS:
        teams_g = list(gp[g])
        first[g] = max(teams_g, key=lambda tm: gp[g][tm]["p1"])
        second[g] = max((tm for tm in teams_g if tm != first[g]),
                        key=lambda tm: gp[g][tm]["p2"])
        third[g] = max((tm for tm in teams_g if tm not in (first[g], second[g])),
                       key=lambda tm: gp[g][tm]["p3"])

    # Best 8 third-placed teams: those whose 3rd-place team is likeliest to
    # advance overall. Then fill the third-place R32 slots deterministically.
    qual = sorted(GROUP_LETTERS, key=lambda g: probs[third[g]]["advance"],
                  reverse=True)[:8]
    amap = thirds.assign(tuple(sorted(qual)))

    def slot_team(slot):
        pos, gl = slot[0], slot[1]
        return {"1": first, "2": second}[pos][gl]

    known = {m["id"]: m for m in store.all_matches()}
    r32 = []
    for m in R32_MATCHES:
        real = known.get(m, {})
        if real.get("home") and real.get("away"):  # real pairing once known
            home, away = real["home"], real["away"]
        else:
            a_slot, b_slot = BRACKET[m]
            home = slot_team(a_slot)
            away = third[amap[m]] if b_slot.startswith("3:") else slot_team(b_slot)
        r32.append({"match": m, "home": home, "away": away})

    return {"r32": r32, "elo": {tm: eff(tm) for tm in info}}


def compute_and_store_bracket(store, n=20000):
    data = most_likely_bracket(store, n=n)
    store.set_analysis("bracket", data)
    return data


def winning_path(store, team, batch=20000, min_champ=300, max_batches=40):
    """Most likely title route for `team`, conditioned on it being champion.

    Batches simulations (so even a 0.2% team accumulates enough title runs
    without huge memory) and, among the iterations where `team` wins it all,
    reports the opponent it most often beat in each knockout round.
    """
    spec = spec_from_store(store)
    state = store.engine_state()
    total_champ = total_sims = 0
    acc = None
    teams_order = None
    seed = 2026
    for _ in range(max_batches):
        res = run_sims(spec=spec, state=state, n=batch, seed=seed, path_for=team)
        seed += 1
        total_sims += batch
        p = res.get("path")
        if not p:
            break
        teams_order = p["teams"]
        total_champ += p["champ_count"]
        if acc is None:
            acc = {rk: list(v) for rk, v in p["counts"].items()}
        else:
            for rk, v in p["counts"].items():
                acc[rk] = [a + c for a, c in zip(acc[rk], v)]
        if total_champ >= min_champ:
            break

    rounds = {}
    if acc and total_champ:
        for rk, counts in acc.items():
            order = sorted(range(len(counts)), key=lambda i: counts[i], reverse=True)
            rounds[rk] = [
                {"team": teams_order[i], "share": round(100.0 * counts[i] / total_champ, 1)}
                for i in order[:3] if counts[i] > 0]
    return {"team": team, "champ_count": total_champ, "sims": total_sims,
            "rounds": rounds}


def compute_and_store_winning_paths(store, batch=20000, min_champ=300,
                                    max_batches=40):
    """Winning paths for Sweden + the current title favorites (likely focuses)."""
    base = run_sims(spec=spec_from_store(store), state=store.engine_state(),
                    n=20000)["probs"]
    favs = sorted(base, key=lambda tm: base[tm]["champ"], reverse=True)[:6]
    targets = list(dict.fromkeys(["Sweden", *favs]))
    out = {tm: winning_path(store, tm, batch=batch, min_champ=min_champ,
                            max_batches=max_batches) for tm in targets}
    store.set_analysis("winning_paths", {"teams": out})
    return out


def apply_elo_updates(store):
    """Apply Elo updates for finished matches not yet applied. Idempotent."""
    applied = store.elo_applied_match_ids()
    ratings = store.get_elo()
    if not ratings:
        ratings = import_elo(store)
    info = {t: {"host": t in HOSTS, "americas": t in AMERICAS} for t in TEAMS}
    updated = []
    for m in store.all_matches():
        if (m["id"] in applied or m["status"] != "finished"
                or m["home_score"] is None or m["away_score"] is None
                or m["home"] is None or m["away"] is None):
            continue
        a, b = m["home"], m["away"]
        ra, rb = ratings[a], ratings[b]
        eff_a = float(model.effective_rating(ra, a in HOSTS, a in AMERICAS))
        eff_b = float(model.effective_rating(rb, b in HOSTS, b in AMERICAS))
        na, nb = elo_rule.update(ra, rb, m["home_score"], m["away_score"],
                                 eff_a=eff_a, eff_b=eff_b)
        store.record_elo_change(a, m["id"], ra, na)
        store.record_elo_change(b, m["id"], rb, nb)
        ratings[a], ratings[b] = na, nb
        updated.append(m["id"])
    if updated:
        store.set_elo(ratings)
    return updated


def resimulate(store, n=20000, trigger="manual", match_id=None, seed=2026):
    """Run a conditioned simulation and persist a snapshot."""
    spec = spec_from_store(store)
    state = store.engine_state()
    result = run_sims(spec=spec, state=state, n=n, seed=seed)
    snap_id = store.add_snapshot(result["probs"], n, trigger, match_id)
    return {"snapshot_id": snap_id, **result}


def _row_changed(old, new):
    keys = ("status", "home_score", "away_score", "minute", "ko_winner")
    return any(old.get(k) != new.get(k) for k in keys)


def _to_upsert(row):
    return {k: row.get(k) for k in
            ("id", "stage", "grp", "matchday", "home", "away", "kickoff_utc",
             "status", "home_score", "away_score", "minute", "ko_winner",
             "ko_decided_by")}
