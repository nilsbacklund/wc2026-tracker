"""Authoritative fixtures & results from football-data.org v4.

Free tier covers the World Cup (competition code WC, id 2000); header
X-Auth-Token; 10 calls/min; scores are delayed (fine for full-time
confirmation, not for live — ESPN handles live). Needs FOOTBALL_DATA_TOKEN.
"""
import os

import httpx

from .. import names

BASE = "https://api.football-data.org/v4"

# football-data stage -> our stage label.
STAGE_MAP = {
    "GROUP_STAGE": "group", "LAST_32": "R32", "LAST_16": "R16",
    "QUARTER_FINALS": "QF", "SEMI_FINALS": "SF",
    "THIRD_PLACE": "third_place", "FINAL": "final",
}
STATUS_MAP = {
    "SCHEDULED": "scheduled", "TIMED": "scheduled", "IN_PLAY": "in_play",
    "PAUSED": "in_play", "EXTRA_TIME": "in_play", "PENALTY_SHOOTOUT": "in_play",
    "FINISHED": "finished", "SUSPENDED": "scheduled", "POSTPONED": "scheduled",
    "CANCELLED": "scheduled", "AWARDED": "finished",
}


def _token():
    tok = os.environ.get("FOOTBALL_DATA_TOKEN")
    if not tok:
        raise RuntimeError("FOOTBALL_DATA_TOKEN not set")
    return tok


def fetch_matches(timeout=20.0):
    """All WC matches, normalized. Raises if token missing."""
    with httpx.Client(timeout=timeout,
                      headers={"X-Auth-Token": _token()}) as client:
        r = client.get(f"{BASE}/competitions/WC/matches")
        r.raise_for_status()
        return parse_matches(r.json())


def parse_matches(payload):
    out = []
    for m in payload.get("matches", []):
        home = names.from_football_data((m.get("homeTeam") or {}).get("name", ""))
        away = names.from_football_data((m.get("awayTeam") or {}).get("name", ""))
        score = m.get("score", {}) or {}
        ft = score.get("fullTime", {}) or {}
        out.append({
            "source_id": m.get("id"),
            "stage": STAGE_MAP.get(m.get("stage"), m.get("stage")),
            "group": (m.get("group") or "").replace("GROUP_", "") or None,
            "matchday": m.get("matchday"),
            "home": home,
            "away": away,
            "status": STATUS_MAP.get(m.get("status"), "scheduled"),
            "home_score": ft.get("home"),
            "away_score": ft.get("away"),
            "winner": score.get("winner"),  # HOME | AWAY | DRAW | None
            "duration": score.get("duration"),  # REGULAR | EXTRA_TIME | PENALTY_SHOOTOUT
            "kickoff_utc": m.get("utcDate"),
        })
    return out
