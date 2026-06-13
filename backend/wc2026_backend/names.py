"""Canonical team names and aliases for external data sources.

The engine's 48 team names (structure.TEAMS) are canonical. External sources
spell some teams differently; these maps translate to/from canonical. Verified
against live eloratings.net and ESPN data on 2026-06-13.
"""
from wc2026.structure import TEAMS

# Canonical name -> eloratings.net team name (only where it differs).
ELORATINGS_ALIASES = {
    "USA": "United States",
    "Turkiye": "Turkey",
    "Bosnia": "Bosnia and Herzegovina",
    "Curacao": "Curaçao",
}

# Canonical name -> ESPN displayName (only where it differs).
ESPN_ALIASES = {
    "USA": "United States",
    "Turkiye": "Türkiye",
    "Bosnia": "Bosnia-Herzegovina",
    "South Korea": "Korea Republic",
    "Ivory Coast": "Côte d'Ivoire",
    "DR Congo": "Congo DR",
    "Cape Verde": "Cape Verde",
    "Curacao": "Curaçao",
}

# football-data.org uses FIFA-style names; canonical -> football-data name.
FOOTBALL_DATA_ALIASES = {
    "USA": "United States",
    "Turkiye": "Türkiye",
    "Bosnia": "Bosnia and Herzegovina",
    "South Korea": "Korea Republic",
    "Ivory Coast": "Ivory Coast",
    "DR Congo": "DR Congo",
}


def _reverse(aliases):
    """Build source-name -> canonical, including identity for unaliased teams."""
    rev = {t: t for t in TEAMS}
    rev.update({src: canon for canon, src in aliases.items()})
    return rev


_ESPN_TO_CANON = _reverse(ESPN_ALIASES)
_FD_TO_CANON = _reverse(FOOTBALL_DATA_ALIASES)
_ELO_TO_CANON = _reverse(ELORATINGS_ALIASES)


def from_espn(name):
    """ESPN displayName -> canonical, or None if not a tournament team."""
    return _ESPN_TO_CANON.get(name)


def from_football_data(name):
    return _FD_TO_CANON.get(name)


def from_eloratings(name):
    return _ELO_TO_CANON.get(name)


def to_eloratings(canon):
    return ELORATINGS_ALIASES.get(canon, canon)
