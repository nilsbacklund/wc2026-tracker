"""Best-8-of-12 third-place qualification and R32 slot assignment.

FIFA Annex C defines a canonical slot table for all 495 possible qualified
sets; we use a deterministic backtracking matching that satisfies the same
constraints (may differ from FIFA's canonical pick when multiple matchings
exist — fine for odds; real R32 pairings override this once groups finish).
Every 8-of-12 subset admits a valid matching (Annex C's table proves
feasibility), so the backtracking is asserted to succeed.
"""
from functools import lru_cache

import numpy as np

from .structure import GROUP_LETTERS, THIRD_SLOTS


@lru_cache(maxsize=None)
def assign(qualified):
    """Map R32 match number -> group letter of the third-placed team.

    `qualified` is a sorted tuple of 8 group letters. Deterministic:
    most-constrained slot first, candidates in alphabetical order.
    """
    qual = set(qualified)
    slots = sorted(THIRD_SLOTS, key=lambda m: (len(THIRD_SLOTS[m] & qual), m))
    assignment = {}
    used = set()

    def bt(i):
        if i == len(slots):
            return True
        m = slots[i]
        for g in sorted(THIRD_SLOTS[m] & qual - used):
            assignment[m] = g
            used.add(g)
            if bt(i + 1):
                return True
            used.discard(g)
            del assignment[m]
        return False

    if not bt(0):
        raise AssertionError(f"no valid third-place matching for {qualified}")
    return dict(assignment)


def rank_thirds(pts, gd, gf, rng):
    """Rank the 12 third-placed teams; return (12, N) array of group indices
    ordered best first. Criteria: points, GD, GF, then random (lots)."""
    n = pts.shape[1]
    jitter = rng.integers(0, 1 << 20, size=(12, n))
    key = (((pts * 2048 + (gd + 512)) * 1024 + gf) << 20) + jitter
    return np.argsort(-key, axis=0, kind="stable")


def qualified_sets(third_rank):
    """Top-8 qualified groups per iteration as a 12-bit mask array (N,)."""
    n = third_rank.shape[1]
    mask = np.zeros(n, dtype=np.int64)
    for k in range(8):
        mask |= 1 << third_rank[k]
    return mask


def slot_teams(mask, third_team, ko_matches):
    """Resolve third-place R32 slots for every iteration.

    mask: (N,) qualified-set bitmasks; third_team: (12, N) global team index
    of each group's third; ko_matches: iterable of R32 match numbers needing
    a third. Returns {match: (N,) team index array}.
    """
    n = mask.shape[0]
    out = {m: np.empty(n, dtype=np.int64) for m in ko_matches}
    for bits in np.unique(mask):
        sel = mask == bits
        qual = tuple(GROUP_LETTERS[i] for i in range(12) if bits >> i & 1)
        amap = assign(qual)
        for m in ko_matches:
            gi = GROUP_LETTERS.index(amap[m])
            out[m][sel] = third_team[gi, sel]
    return out
