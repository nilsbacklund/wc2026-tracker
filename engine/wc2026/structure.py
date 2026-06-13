"""Verified 2026 World Cup tournament structure.

Group draw confirmed June 2026 (incl. March playoff winners). Bracket and
third-place slot constraints verified against the official FIFA schedule
(matches 73-104). This module holds data only — no logic.
"""

GROUPS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "B": ["Canada", "Bosnia", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["USA", "Paraguay", "Australia", "Turkiye"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

GROUP_LETTERS = sorted(GROUPS)
TEAMS = [t for g in GROUP_LETTERS for t in GROUPS[g]]

HOSTS = {"Mexico", "USA", "Canada"}
AMERICAS = {"Mexico", "USA", "Canada", "Brazil", "Argentina", "Uruguay",
            "Colombia", "Ecuador", "Paraguay", "Panama", "Haiti", "Curacao"}

# Elo ratings used until the real eloratings.net table is imported.
# Top 4 anchored (June 11, 2026): Spain 2157, Argentina 2115, France 2063,
# England 2024. Others are informed estimates.
DEFAULT_ELO = {
    "Mexico": 1850, "South Africa": 1680, "South Korea": 1790, "Czechia": 1760,
    "Canada": 1810, "Bosnia": 1740, "Qatar": 1650, "Switzerland": 1860,
    "Brazil": 2000, "Morocco": 1900, "Haiti": 1590, "Scotland": 1780,
    "USA": 1840, "Paraguay": 1790, "Australia": 1760, "Turkiye": 1840,
    "Germany": 1955, "Curacao": 1600, "Ivory Coast": 1790, "Ecuador": 1885,
    "Netherlands": 1985, "Japan": 1880, "Sweden": 1810, "Tunisia": 1750,
    "Belgium": 1925, "Egypt": 1790, "Iran": 1800, "New Zealand": 1620,
    "Spain": 2157, "Cape Verde": 1640, "Saudi Arabia": 1700, "Uruguay": 1920,
    "France": 2063, "Senegal": 1850, "Iraq": 1690, "Norway": 1905,
    "Argentina": 2115, "Algeria": 1800, "Austria": 1830, "Jordan": 1680,
    "Portugal": 2010, "DR Congo": 1700, "Uzbekistan": 1700, "Colombia": 1935,
    "England": 2024, "Croatia": 1905, "Ghana": 1740, "Panama": 1740,
}

# Knockout bracket, match number -> (slot, slot).
# Slot grammar: "1E"/"2B" = group position, "3:ABCDF" = third-placed team from
# one of those groups, "W74"/"L101" = winner/loser of an earlier match.
BRACKET = {
    # Round of 32
    73: ("2A", "2B"),       74: ("1E", "3:ABCDF"),
    75: ("1F", "2C"),       76: ("1C", "2F"),
    77: ("1I", "3:CDFGH"),  78: ("2E", "2I"),
    79: ("1A", "3:CEFHI"),  80: ("1L", "3:EHIJK"),
    81: ("1D", "3:BEFIJ"),  82: ("1G", "3:AEHIJ"),
    83: ("2K", "2L"),       84: ("1H", "2J"),
    85: ("1B", "3:EFGIJ"),  86: ("1J", "2H"),
    87: ("1K", "3:DEIJL"),  88: ("2D", "2G"),
    # Round of 16
    89: ("W74", "W77"), 90: ("W73", "W75"), 91: ("W76", "W78"), 92: ("W79", "W80"),
    93: ("W83", "W84"), 94: ("W81", "W82"), 95: ("W86", "W88"), 96: ("W85", "W87"),
    # Quarterfinals
    97: ("W89", "W90"), 98: ("W93", "W94"), 99: ("W91", "W92"), 100: ("W95", "W96"),
    # Semifinals
    101: ("W97", "W98"), 102: ("W99", "W100"),
    # Third place + final
    103: ("L101", "L102"), 104: ("W101", "W102"),
}

KO_ORDER = sorted(BRACKET)
R32_MATCHES = range(73, 89)

# Matches whose second slot takes a third-placed team, -> allowed groups.
THIRD_SLOTS = {m: set(pair[1][2:]) for m, pair in BRACKET.items()
               if pair[1].startswith("3:")}

# Stage reached by winning / appearing in a match, for probability counters.
STAGE_OF_MATCH = {**{m: "r32" for m in range(73, 89)},
                  **{m: "r16" for m in range(89, 97)},
                  **{m: "qf" for m in range(97, 101)},
                  **{m: "sf" for m in (101, 102)}}

# The six fixtures of a 4-team group, as local team indices, in a fixed
# canonical order used by the engine when a fixture list isn't supplied.
GROUP_FIXTURES = [(0, 1), (2, 3), (0, 2), (3, 1), (3, 0), (1, 2)]
