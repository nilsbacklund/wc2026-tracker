"""Fetch the current World Football Elo table from eloratings.net.

World.tsv columns (no header): rank, prev_rank, team_code, current_elo, ...
en.teams.tsv: code <tab> name. We map codes -> our 48 canonical teams.
Verified live 2026-06-13: all 48 teams resolve, anchors match (ES 2157, ...).
"""
import httpx

from wc2026.structure import TEAMS
from .. import names

WORLD_URL = "https://eloratings.net/World.tsv"
TEAMS_URL = "https://eloratings.net/en.teams.tsv"


def fetch_elo(timeout=20.0):
    """Return {canonical_team: elo_int} for all 48 tournament teams.

    Raises if any team can't be resolved (so a silent source change can't
    publish odds on stale ratings)."""
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        teams_tsv = client.get(TEAMS_URL).raise_for_status().text
        world_tsv = client.get(WORLD_URL).raise_for_status().text
    return parse_elo(world_tsv, teams_tsv)


def parse_elo(world_tsv, teams_tsv):
    name_by_code = {}
    for line in teams_tsv.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            name_by_code[parts[0]] = parts[1]
    elo_by_code = {}
    for line in world_tsv.splitlines():
        parts = line.split("\t")
        if len(parts) >= 4 and parts[3].lstrip("-").isdigit():
            elo_by_code[parts[2]] = int(parts[3])

    code_by_name = {v: k for k, v in name_by_code.items()}
    out = {}
    missing = []
    for team in TEAMS:
        code = code_by_name.get(names.to_eloratings(team))
        if code is None or code not in elo_by_code:
            missing.append(team)
        else:
            out[team] = elo_by_code[code]
    if missing:
        raise ValueError(f"eloratings.net: could not resolve {missing}")
    return out
