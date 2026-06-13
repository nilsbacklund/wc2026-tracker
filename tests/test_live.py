"""Live polling loop: trigger classification and snapshot writing.

Uses a temp SQLite store seeded from fixtures and a flat Elo table so no
network is touched — the poller's `fetch` is injected with canned events in
the normalized ESPN parser shape (what ingest_espn consumes).
"""
import asyncio

import pytest

from wc2026.structure import TEAMS
from wc2026_backend.fixtures import seed_matches
from wc2026_backend.live import LivePoller
from wc2026_backend.store import Store
from wc2026_backend import service


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "live.sqlite")
    seed_matches(s)
    service.import_elo(s, {t: 1800.0 for t in TEAMS})
    yield s
    s.close()


def _event(home, away, hs, as_, status, minute=None, winner=None):
    return {"espn_id": "x", "home": home, "away": away,
            "home_score": hs, "away_score": as_, "status": status,
            "minute": minute, "completed": status == "finished",
            "winner": winner, "kickoff_utc": None}


def _poller(store, events):
    return LivePoller(store, fetch=lambda: events, n_sims=400)


def test_new_finished_triggers_fulltime(store):
    ev = [_event("Mexico", "South Africa", 2, 0, "finished", winner="Mexico")]
    out = asyncio.run(_poller(store, ev).poll_once())
    assert out["trigger"] == "fulltime"
    assert out["snapshot_id"] is not None
    assert store.latest_snapshot()["trigger"] == "fulltime"


def test_score_increase_triggers_goal(store):
    # Match is already in play 0-0; a poll sees it at 1-0 -> goal.
    m = store.match_by_teams("Mexico", "South Africa")
    store.upsert_match({**m, "status": "in_play",
                        "home_score": 0, "away_score": 0, "minute": 20})
    ev = [_event("Mexico", "South Africa", 1, 0, "in_play", minute=23)]
    out = asyncio.run(_poller(store, ev).poll_once())
    assert out["trigger"] == "goal"
    assert out["snapshot_id"] is not None


def test_no_change_no_snapshot(store):
    # Empty scoreboard -> nothing ingested, no snapshot.
    out = asyncio.run(_poller(store, []).poll_once())
    assert out["trigger"] is None
    assert out["snapshot_id"] is None
    assert store.latest_snapshot() is None


def test_fetch_exception_is_swallowed(store):
    def boom():
        raise RuntimeError("ESPN down")
    poller = LivePoller(store, fetch=boom, n_sims=400)
    out = asyncio.run(poller.poll_once())  # must not raise
    assert out["changed"] == []
    assert out["trigger"] is None
    assert store.latest_snapshot() is None


def test_kickoff_then_goal_priority(store):
    """A scheduled match kicking off and an in-play match scoring in the same
    cycle: goal outranks kickoff."""
    m2 = store.match_by_teams("South Korea", "Czechia")
    store.upsert_match({**m2, "status": "in_play",
                        "home_score": 0, "away_score": 0, "minute": 10})
    ev = [
        _event("Mexico", "South Africa", 0, 0, "in_play", minute=1),  # kickoff
        _event("South Korea", "Czechia", 0, 1, "in_play", minute=12),  # goal
    ]
    out = asyncio.run(_poller(store, ev).poll_once())
    assert out["trigger"] == "goal"
    goal_match = store.match_by_teams("South Korea", "Czechia")
    assert out["match_id"] == goal_match["id"]
