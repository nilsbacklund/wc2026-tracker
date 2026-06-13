"""Live scores from ESPN's unofficial scoreboard API.

Free, no key, browser-CORS-enabled, genuinely live (verified 2026-06-13).
Unofficial: shapes can change without notice, so parsing is defensive and
team names that don't resolve are skipped rather than crashing the poll loop.

status.type.state: "pre" | "in" | "post"; period + displayClock give the
minute. We normalize to our match status vocabulary.
"""
import httpx

from .. import names

SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
)


def fetch_scoreboard(date=None, timeout=15.0):
    """Fetch raw events. `date` as YYYYMMDD restricts to one day."""
    params = {"dates": date} if date else None
    with httpx.Client(timeout=timeout) as client:
        r = client.get(SCOREBOARD_URL, params=params)
        r.raise_for_status()
        return parse_scoreboard(r.json())


def _minute(status):
    """Best-effort match minute from period + clock."""
    state = status.get("type", {}).get("state")
    if state != "in":
        return None
    # displayClock like "67'" or "90'+3'"; fall back to clock seconds.
    dc = (status.get("displayClock") or "").strip("'+ ")
    head = dc.split("'")[0].split("+")[0]
    if head.isdigit():
        return int(head)
    clock = status.get("clock")
    return int(clock // 60) if clock else None


def parse_scoreboard(payload):
    """Return a list of normalized live-match dicts:
    {espn_id, home, away, home_score, away_score, status, minute, completed}.
    Only matches where both teams resolve to canonical names are returned.
    """
    out = []
    for event in payload.get("events", []):
        comp = (event.get("competitions") or [{}])[0]
        competitors = comp.get("competitors", [])
        home = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if not home or not away:
            continue
        h = names.from_espn(home["team"]["displayName"])
        a = names.from_espn(away["team"]["displayName"])
        if h is None or a is None:
            continue
        status = comp.get("status", {})
        state = status.get("type", {}).get("state")
        norm = {"pre": "scheduled", "in": "in_play", "post": "finished"}.get(
            state, "scheduled")
        winner = h if home.get("winner") else a if away.get("winner") else None
        out.append({
            "espn_id": event.get("id"),
            "home": h,
            "away": a,
            "home_score": _int(home.get("score")),
            "away_score": _int(away.get("score")),
            "status": norm,
            "minute": _minute(status),
            "completed": bool(status.get("type", {}).get("completed")),
            "winner": winner,
            "kickoff_utc": event.get("date"),
        })
    return out


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
