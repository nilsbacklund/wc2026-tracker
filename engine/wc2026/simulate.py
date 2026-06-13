"""Vectorized Monte Carlo tournament simulation with conditioning.

All N iterations are simulated simultaneously as numpy arrays. Real results
from `state` are constants across iterations; in-play matches sample only
their remaining minutes (time-scaled Poisson on top of the current score);
everything else is sampled in full.

Pure: takes plain data, returns probabilities. No I/O.
"""
from collections import defaultdict

import numpy as np

from . import model, standings, thirds
from .structure import (BRACKET, GROUPS, GROUP_FIXTURES, GROUP_LETTERS,
                        KO_ORDER, R32_MATCHES, THIRD_SLOTS, DEFAULT_ELO,
                        HOSTS, AMERICAS)


def default_spec(elo=None):
    """Spec from the verified structure plus an Elo table (name -> rating)."""
    elo = elo or DEFAULT_ELO
    return {
        "teams": {t: {"elo": float(elo[t]), "group": g,
                      "host": t in HOSTS, "americas": t in AMERICAS}
                  for g in GROUP_LETTERS for t in GROUPS[g]},
        "groups": {g: list(GROUPS[g]) for g in GROUP_LETTERS},
        "model": dict(model.MODEL_PARAMS),
    }


class _Tournament:
    """Index arrays derived from a spec."""

    def __init__(self, spec):
        self.groups = spec["groups"]
        self.teams = [t for g in GROUP_LETTERS for t in self.groups[g]]
        self.idx = {t: i for i, t in enumerate(self.teams)}
        info = spec["teams"]
        self.eff = model.effective_rating(
            [info[t]["elo"] for t in self.teams],
            [info[t]["host"] for t in self.teams],
            [info[t]["americas"] for t in self.teams])


def _group_fixtures(tournament, state_matches):
    """Per group: list of 6 fixtures [(i_loc, j_loc, real)] where real is
    None (scheduled) or a dict from state (finished / in_play)."""
    by_pair = {}
    for m in state_matches or []:
        if m.get("stage") == "group" and m.get("status") in ("finished", "in_play"):
            for name in (m["home"], m["away"]):
                if name not in tournament.idx:
                    raise ValueError(f"unknown team in state: {name!r}")
            by_pair[frozenset((m["home"], m["away"]))] = m

    out = {}
    matched = set()
    for g in GROUP_LETTERS:
        names = tournament.groups[g]
        fixtures = []
        for i, j in GROUP_FIXTURES:
            pair = frozenset((names[i], names[j]))
            m = by_pair.get(pair)
            if m is not None:
                matched.add(pair)
                if m["home"] == names[j]:
                    i, j = j, i  # orient local indices to the real home team
            fixtures.append((i, j, m))
        out[g] = fixtures
    unmatched = set(by_pair) - matched
    if unmatched:
        raise ValueError(f"state group matches not in any group: "
                         f"{[tuple(p) for p in unmatched]}")
    return out


def _sample_group(tournament, g, fixtures, n, rng):
    """Goal matrices (6, N) for one group, honoring real results."""
    names = tournament.groups[g]
    hg = np.empty((6, n), dtype=np.int64)
    ag = np.empty((6, n), dtype=np.int64)
    for f, (i, j, real) in enumerate(fixtures):
        ra = tournament.eff[tournament.idx[names[i]]]
        rb = tournament.eff[tournament.idx[names[j]]]
        if real is not None and real["status"] == "finished":
            hg[f] = real["score"]["home"]
            ag[f] = real["score"]["away"]
        elif real is not None and real["status"] == "in_play":
            remaining = max(0.0, model.REGULATION_MINUTES
                            - float(real.get("minute", 45)))
            la, lb = model.lambdas(ra, rb, minutes=remaining)
            hg[f] = real["score"]["home"] + rng.poisson(la, size=n)
            ag[f] = real["score"]["away"] + rng.poisson(lb, size=n)
        else:
            la, lb = model.lambdas(ra, rb)
            hg[f] = rng.poisson(la, size=n)
            ag[f] = rng.poisson(lb, size=n)
    return hg, ag


def _ko_winner(tournament, team_a, team_b, n, rng, real=None):
    """Winner team-index array for one KO match.

    real: state match dict; a recorded winner fixes the outcome, an in-play
    score conditions it (remaining-minutes Poisson, ties go to a compressed
    coin standing in for extra time + penalties).
    """
    if real is not None and (real.get("ko") or {}).get("winner"):
        return np.full(n, tournament.idx[real["ko"]["winner"]], dtype=np.int64)

    ra, rb = tournament.eff[team_a], tournament.eff[team_b]
    if real is not None and real.get("status") == "in_play":
        remaining = max(0.0, model.REGULATION_MINUTES
                        - float(real.get("minute", 45)))
        la, lb = model.lambdas(ra, rb, minutes=remaining)
        sa = real["score"]["home"] + rng.poisson(la, size=n)
        sb = real["score"]["away"] + rng.poisson(lb, size=n)
        p_et = model.ko_win_prob(ra, rb)
        win_a = np.where(sa == sb, rng.random(n) < p_et, sa > sb)
    else:
        win_a = rng.random(n) < model.ko_win_prob(ra, rb)
    return np.where(win_a, team_a, team_b)


def run_sims(spec=None, state=None, n=20000, seed=2026):
    """Simulate the tournament N times conditioned on `state`.

    state: {"matches": [...]} or a plain list of match dicts (see backend
    schema). Returns {"probs": {team: {advance, r16, qf, top4, final,
    champ}}, "meta": {...}} with probabilities in percent.
    """
    spec = spec or default_spec()
    t = _Tournament(spec)
    rng = np.random.default_rng(seed)
    matches = (state or {}).get("matches") if isinstance(state, dict) else state
    matches = matches or []
    ko_real = {m["id"]: m for m in matches
               if m.get("stage") != "group" and m.get("id") in BRACKET}

    # --- group stage ---
    fixtures = _group_fixtures(t, matches)
    first = np.empty((12, n), dtype=np.int64)
    second = np.empty((12, n), dtype=np.int64)
    third = np.empty((12, n), dtype=np.int64)
    tpts = np.empty((12, n), dtype=np.int64)
    tgd = np.empty((12, n), dtype=np.int64)
    tgf = np.empty((12, n), dtype=np.int64)
    for gi, g in enumerate(GROUP_LETTERS):
        hg, ag = _sample_group(t, g, fixtures[g], n, rng)
        pairs = [(i, j) for i, j, _ in fixtures[g]]
        pts, gd, gf = standings.table_stats(hg, ag, pairs)
        order = standings.rank_group(pts, gd, gf, hg, ag, rng, pairs)
        base = np.array([t.idx[name] for name in t.groups[g]])
        first[gi] = base[order[0]]
        second[gi] = base[order[1]]
        third[gi] = base[order[2]]
        cols = np.arange(n)
        tpts[gi] = pts[order[2], cols]
        tgd[gi] = gd[order[2], cols]
        tgf[gi] = gf[order[2], cols]

    # --- third-place qualification ---
    third_rank = thirds.rank_thirds(tpts, tgd, tgf, rng)
    mask = thirds.qualified_sets(third_rank)
    third_slot = thirds.slot_teams(mask, third, THIRD_SLOTS)

    # --- knockout ---
    winners, losers = {}, {}
    r32_entrants = []

    def resolve(slot):
        if slot.startswith("W"):
            return winners[int(slot[1:])]
        if slot.startswith("L"):
            return losers[int(slot[1:])]
        if slot.startswith("3:"):
            return None  # filled from third_slot by match number
        gi = GROUP_LETTERS.index(slot[1])
        return {"1": first, "2": second}[slot[0]][gi]

    for m in KO_ORDER:
        slot_a, slot_b = BRACKET[m]
        team_a = resolve(slot_a)
        team_b = third_slot[m] if slot_b.startswith("3:") else resolve(slot_b)
        real = ko_real.get(m)
        # Real pairings (known once groups finish) override simulated slots —
        # this also neutralizes any Annex-C divergence in third placement.
        if real is not None and real.get("home") and real.get("away"):
            team_a = np.full(n, t.idx[real["home"]], dtype=np.int64)
            team_b = np.full(n, t.idx[real["away"]], dtype=np.int64)
        winners[m] = _ko_winner(t, team_a, team_b, n, rng, real)
        losers[m] = np.where(winners[m] == team_a, team_b, team_a)
        if m in R32_MATCHES:
            r32_entrants.extend([team_a, team_b])

    # --- counters ---
    nt = len(t.teams)
    counts = defaultdict(lambda: np.zeros(nt, dtype=np.int64))
    for arr in r32_entrants:
        counts["advance"] += np.bincount(arr, minlength=nt)
    stage_winners = {"r16": range(73, 89), "qf": range(89, 97),
                     "top4": range(97, 101), "final": (101, 102)}
    for stage, ms in stage_winners.items():
        for m in ms:
            counts[stage] += np.bincount(winners[m], minlength=nt)
    counts["champ"] = np.bincount(winners[104], minlength=nt)

    probs = {team: {stage: round(100.0 * counts[stage][i] / n, 3)
                    for stage in ("advance", "r16", "qf", "top4", "final", "champ")}
             for i, team in enumerate(t.teams)}
    n_finished = sum(1 for m in matches if m.get("status") == "finished")
    n_live = sum(1 for m in matches if m.get("status") == "in_play")
    return {"probs": probs,
            "meta": {"n_sims": n, "seed": seed,
                     "conditioned_finished": n_finished,
                     "conditioned_in_play": n_live}}
