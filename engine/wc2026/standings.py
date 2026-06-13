"""Group standings with FIFA tiebreakers, vectorized across iterations.

Ranking criteria (FIFA WC group stage): points, goal difference, goals for,
then head-to-head (points, GD, GF among the tied teams), then drawing of lots
(modeled as a random tiebreak; fair-play points are not tracked — documented
caveat). The fast path ranks every iteration with an integer sort key on
(points, GD, GF, random); iterations where teams are exactly tied on all
three are re-resolved in a sparse pass that applies head-to-head rules.
"""
import numpy as np

from .structure import GROUP_FIXTURES

N_TEAMS = 4
N_FIX = 6


def table_stats(home_goals, away_goals, fixtures=GROUP_FIXTURES):
    """Points/GD/GF per team from goal matrices of shape (n_fixtures, N).

    Returns pts, gd, gf with shape (4, N), int64.
    """
    n = home_goals.shape[1]
    pts = np.zeros((N_TEAMS, n), dtype=np.int64)
    gd = np.zeros((N_TEAMS, n), dtype=np.int64)
    gf = np.zeros((N_TEAMS, n), dtype=np.int64)
    for f, (i, j) in enumerate(fixtures):
        hg, ag = home_goals[f], away_goals[f]
        pts[i] += np.where(hg > ag, 3, np.where(hg == ag, 1, 0))
        pts[j] += np.where(ag > hg, 3, np.where(hg == ag, 1, 0))
        gd[i] += hg - ag
        gd[j] += ag - hg
        gf[i] += hg
        gf[j] += ag
    return pts, gd, gf


def _sort_key(pts, gd, gf, jitter):
    # gd is bounded by total goals scored in 6 matches; +512 keeps it positive.
    return (((pts * 2048 + (gd + 512)) * 1024 + gf) * 1024) + jitter


def rank_group(pts, gd, gf, home_goals, away_goals, rng,
               fixtures=GROUP_FIXTURES):
    """Rank a group's 4 teams in every iteration, best first.

    Returns order of shape (4, N): order[k] = local team index ranked k-th.
    """
    n = pts.shape[1]
    jitter = rng.integers(0, 1024, size=(N_TEAMS, n))
    key = _sort_key(pts, gd, gf, jitter)
    order = np.argsort(-key, axis=0, kind="stable")

    # Sparse head-to-head pass: only iterations where some pair of teams is
    # exactly tied on (pts, gd, gf) — there the jitter order may violate
    # head-to-head and must be recomputed.
    triple = (pts * 2048 + (gd + 512)) * 1024 + gf
    sorted_triple = np.take_along_axis(triple, order, axis=0)
    tied = (sorted_triple[:-1] == sorted_triple[1:]).any(axis=0)
    for it in np.nonzero(tied)[0]:
        order[:, it] = _rank_one_h2h(
            pts[:, it], gd[:, it], gf[:, it],
            home_goals[:, it], away_goals[:, it], rng, fixtures)
    return order


def _rank_one_h2h(pts, gd, gf, hg, ag, rng, fixtures):
    """Full FIFA ranking for a single iteration, applying head-to-head among
    exactly tied teams. Random stands in for fair play/drawing of lots."""
    groups_of_tied = {}
    for t in range(N_TEAMS):
        groups_of_tied.setdefault((pts[t], gd[t], gf[t]), []).append(t)

    ranked = []
    # Sort tie-classes by the shared (pts, gd, gf) triple, best first.
    for triple in sorted(groups_of_tied, reverse=True):
        tied = groups_of_tied[triple]
        if len(tied) == 1:
            ranked.extend(tied)
            continue
        # Head-to-head mini-table among the tied teams only.
        h2h_pts = {t: 0 for t in tied}
        h2h_gd = {t: 0 for t in tied}
        h2h_gf = {t: 0 for t in tied}
        for f, (i, j) in enumerate(fixtures):
            if i in h2h_pts and j in h2h_pts:
                if hg[f] > ag[f]:
                    h2h_pts[i] += 3
                elif hg[f] < ag[f]:
                    h2h_pts[j] += 3
                else:
                    h2h_pts[i] += 1
                    h2h_pts[j] += 1
                h2h_gd[i] += hg[f] - ag[f]
                h2h_gd[j] += ag[f] - hg[f]
                h2h_gf[i] += hg[f]
                h2h_gf[j] += ag[f]
        ranked.extend(sorted(
            tied,
            key=lambda t: (h2h_pts[t], h2h_gd[t], h2h_gf[t], rng.random()),
            reverse=True))
    return np.array(ranked, dtype=np.int64)
