"""Slow, readable, per-iteration reference simulator (correctness oracle).

Deliberately independent of the vectorized engine: plain dict/loop logic,
and the knockout bracket is the ORIGINAL hardcoded block from wc2026_sim.py
rather than the slot-grammar tables, so a transcription error in either
implementation shows up as a probability mismatch.

Shares only the model constants/formulas (model.py) and the third-slot
assignment (thirds.assign — exhaustively unit-tested on all 495 subsets).
"""
from collections import defaultdict

from wc2026 import model, thirds
from wc2026.structure import (GROUPS, GROUP_LETTERS, GROUP_FIXTURES,
                              DEFAULT_ELO, HOSTS, AMERICAS)


def _eff(team):
    return float(model.effective_rating(
        DEFAULT_ELO[team], team in HOSTS, team in AMERICAS))


def _play_group(names, rng):
    pts = {t: 0 for t in names}
    gd = {t: 0 for t in names}
    gf = {t: 0 for t in names}
    results = {}
    for i, j in GROUP_FIXTURES:
        a, b = names[i], names[j]
        la, lb = model.lambdas(_eff(a), _eff(b))
        sa, sb = int(rng.poisson(la)), int(rng.poisson(lb))
        results[(a, b)] = (sa, sb)
        if sa > sb:
            pts[a] += 3
        elif sb > sa:
            pts[b] += 3
        else:
            pts[a] += 1
            pts[b] += 1
        gd[a] += sa - sb
        gd[b] += sb - sa
        gf[a] += sa
        gf[b] += sb
    return pts, gd, gf, results


def _rank(names, pts, gd, gf, results, rng):
    """Full FIFA ranking, brute force: sort by triple, then resolve exact
    ties with a head-to-head mini-table."""
    order = sorted(names, key=lambda t: (pts[t], gd[t], gf[t], rng.random()),
                   reverse=True)
    final = []
    i = 0
    while i < len(order):
        tied = [t for t in order
                if (pts[t], gd[t], gf[t]) ==
                   (pts[order[i]], gd[order[i]], gf[order[i]])]
        if len(tied) > 1:
            h2p = defaultdict(int)
            h2d = defaultdict(int)
            h2f = defaultdict(int)
            for (a, b), (sa, sb) in results.items():
                if a in tied and b in tied:
                    if sa > sb:
                        h2p[a] += 3
                    elif sb > sa:
                        h2p[b] += 3
                    else:
                        h2p[a] += 1
                        h2p[b] += 1
                    h2d[a] += sa - sb
                    h2d[b] += sb - sa
                    h2f[a] += sa
                    h2f[b] += sb
            tied.sort(key=lambda t: (h2p[t], h2d[t], h2f[t], rng.random()),
                      reverse=True)
        final.extend(tied)
        i += len(tied)
    return final


def _ko(a, b, rng):
    return a if rng.random() < float(model.ko_win_prob(_eff(a), _eff(b))) else b


def simulate_once(rng):
    """One full tournament; returns (champion, set_of_r32_teams)."""
    first, second, third = {}, {}, {}
    tpts, tgd, tgf = {}, {}, {}
    for g in GROUP_LETTERS:
        names = GROUPS[g]
        pts, gd, gf, results = _play_group(names, rng)
        order = _rank(names, pts, gd, gf, results, rng)
        first[g], second[g], third[g] = order[0], order[1], order[2]
        tpts[g], tgd[g], tgf[g] = (pts[order[2]], gd[order[2]], gf[order[2]])

    ranked = sorted(GROUP_LETTERS,
                    key=lambda g: (tpts[g], tgd[g], tgf[g], rng.random()),
                    reverse=True)
    qual = tuple(sorted(ranked[:8]))
    amap = thirds.assign(qual)
    T = lambda m: third[amap[m]]

    # Original hardcoded bracket from wc2026_sim.py (kept verbatim on purpose).
    W = {}
    W[73] = _ko(second["A"], second["B"], rng)
    W[74] = _ko(first["E"], T(74), rng)
    W[75] = _ko(first["F"], second["C"], rng)
    W[76] = _ko(first["C"], second["F"], rng)
    W[77] = _ko(first["I"], T(77), rng)
    W[78] = _ko(second["E"], second["I"], rng)
    W[79] = _ko(first["A"], T(79), rng)
    W[80] = _ko(first["L"], T(80), rng)
    W[81] = _ko(first["D"], T(81), rng)
    W[82] = _ko(first["G"], T(82), rng)
    W[83] = _ko(second["K"], second["L"], rng)
    W[84] = _ko(first["H"], second["J"], rng)
    W[85] = _ko(first["B"], T(85), rng)
    W[86] = _ko(first["J"], second["H"], rng)
    W[87] = _ko(first["K"], T(87), rng)
    W[88] = _ko(second["D"], second["G"], rng)
    r32_teams = ({first[g] for g in GROUP_LETTERS}
                 | {second[g] for g in GROUP_LETTERS}
                 | {third[amap[m]] for m in amap})
    W[89] = _ko(W[74], W[77], rng)
    W[90] = _ko(W[73], W[75], rng)
    W[91] = _ko(W[76], W[78], rng)
    W[92] = _ko(W[79], W[80], rng)
    W[93] = _ko(W[83], W[84], rng)
    W[94] = _ko(W[81], W[82], rng)
    W[95] = _ko(W[86], W[88], rng)
    W[96] = _ko(W[85], W[87], rng)
    W[97] = _ko(W[89], W[90], rng)
    W[98] = _ko(W[93], W[94], rng)
    W[99] = _ko(W[91], W[92], rng)
    W[100] = _ko(W[95], W[96], rng)
    W[101] = _ko(W[97], W[98], rng)
    W[102] = _ko(W[99], W[100], rng)
    champion = _ko(W[101], W[102], rng)
    return champion, r32_teams


def run_reference(n, seed):
    import numpy as np
    rng = np.random.default_rng(seed)
    champ = defaultdict(int)
    advance = defaultdict(int)
    for _ in range(n):
        c, r32 = simulate_once(rng)
        champ[c] += 1
        for t in r32:
            advance[t] += 1
    return ({t: 100.0 * champ[t] / n for t in champ},
            {t: 100.0 * advance[t] / n for t in advance})
