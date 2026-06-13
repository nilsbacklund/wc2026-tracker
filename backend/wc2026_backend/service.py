"""Application service: ingestion, Elo updates, simulation, snapshots.

Ties the engine, sources, and store together. Stateless functions that take
a Store so the live loop, CLI, and API all share one code path.
"""
from wc2026 import elo as elo_rule
from wc2026 import model
from wc2026.simulate import default_spec, run_sims
from wc2026.structure import AMERICAS, HOSTS, TEAMS

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
