"""Golden test: the bracket tables must match the FIFA schedule as verified
and recorded in CLAUDE.md. If this fails, someone touched verified data."""
from wc2026.structure import BRACKET, GROUPS, THIRD_SLOTS

VERIFIED_R32 = {
    73: ("2A", "2B"), 74: ("1E", "3:ABCDF"), 75: ("1F", "2C"),
    76: ("1C", "2F"), 77: ("1I", "3:CDFGH"), 78: ("2E", "2I"),
    79: ("1A", "3:CEFHI"), 80: ("1L", "3:EHIJK"), 81: ("1D", "3:BEFIJ"),
    82: ("1G", "3:AEHIJ"), 83: ("2K", "2L"), 84: ("1H", "2J"),
    85: ("1B", "3:EFGIJ"), 86: ("1J", "2H"), 87: ("1K", "3:DEIJL"),
    88: ("2D", "2G"),
}
VERIFIED_R16 = {
    89: ("W74", "W77"), 90: ("W73", "W75"), 91: ("W76", "W78"),
    92: ("W79", "W80"), 93: ("W83", "W84"), 94: ("W81", "W82"),
    95: ("W86", "W88"), 96: ("W85", "W87"),
}
VERIFIED_QF = {97: ("W89", "W90"), 98: ("W93", "W94"),
               99: ("W91", "W92"), 100: ("W95", "W96")}
VERIFIED_TAIL = {101: ("W97", "W98"), 102: ("W99", "W100"),
                 103: ("L101", "L102"), 104: ("W101", "W102")}


def test_bracket_matches_verified_schedule():
    assert BRACKET == {**VERIFIED_R32, **VERIFIED_R16,
                       **VERIFIED_QF, **VERIFIED_TAIL}


def test_third_slots_derived_correctly():
    assert THIRD_SLOTS == {74: set("ABCDF"), 77: set("CDFGH"),
                           79: set("CEFHI"), 80: set("EHIJK"),
                           81: set("BEFIJ"), 82: set("AEHIJ"),
                           85: set("EFGIJ"), 87: set("DEIJL")}


def test_groups_complete():
    assert len(GROUPS) == 12
    teams = [t for g in GROUPS.values() for t in g]
    assert len(teams) == 48 == len(set(teams))
    assert "Sweden" in GROUPS["F"]
