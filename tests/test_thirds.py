"""Third-place slot assignment: feasible for all 495 subsets, deterministic,
and constraint-valid."""
from itertools import combinations

from wc2026 import thirds
from wc2026.structure import GROUP_LETTERS, THIRD_SLOTS


def test_all_495_subsets_have_valid_assignment():
    for qual in combinations(GROUP_LETTERS, 8):
        amap = thirds.assign(qual)
        assert sorted(amap) == sorted(THIRD_SLOTS)
        assert sorted(amap.values()) == sorted(qual)  # each group used once
        for m, g in amap.items():
            assert g in THIRD_SLOTS[m]


def test_assignment_deterministic():
    qual = tuple("ABCDEFGH")
    assert thirds.assign(qual) == thirds.assign(tuple("ABCDEFGH"))
