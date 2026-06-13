"""Backend: source parsers, ingestion, Elo application, snapshots.

Uses saved fixtures and a temp SQLite db — no network required.
"""
import json
from pathlib import Path

import pytest

from wc2026_backend.fixtures import seed_matches
from wc2026_backend.sources import espn, football_data
from wc2026_backend.store import Store
from wc2026_backend import service

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "test.sqlite")
    seed_matches(s)
    yield s
    s.close()


def test_seed_creates_104_matches(store):
    matches = store.all_matches()
    assert len(matches) == 104
    assert sum(1 for m in matches if m["stage"] == "group") == 72
    assert store.get_match(104)["stage"] == "final"


def test_espn_parser_resolves_real_names():
    payload = json.loads((FIXTURES / "espn_scoreboard.json").read_text())
    events = espn.parse_scoreboard(payload)
    by_pair = {frozenset((e["home"], e["away"])): e for e in events}
    canada = by_pair[frozenset(("Canada", "Bosnia"))]
    assert canada["status"] == "finished"
    assert {canada["home_score"], canada["away_score"]} == {1, 1}
    usa = by_pair[frozenset(("USA", "Paraguay"))]
    assert usa["home_score"] + usa["away_score"] == 5


def test_football_data_parser():
    payload = {"matches": [{
        "id": 999, "stage": "GROUP_STAGE", "group": "GROUP_F", "matchday": 1,
        "homeTeam": {"name": "Sweden"}, "awayTeam": {"name": "Japan"},
        "status": "FINISHED", "utcDate": "2026-06-14T16:00:00Z",
        "score": {"winner": "HOME", "duration": "REGULAR",
                  "fullTime": {"home": 2, "away": 1}}}]}
    rows = football_data.parse_matches(payload)
    assert rows[0]["home"] == "Sweden"
    assert rows[0]["group"] == "F"
    assert rows[0]["stage"] == "group"
    assert rows[0]["home_score"] == 2


def test_ingest_updates_standings(store):
    events = json.loads((FIXTURES / "espn_scoreboard.json").read_text())
    changed = service.ingest_espn(store, espn.parse_scoreboard(events))
    assert len(changed) == 2
    usa = store.match_by_teams("USA", "Paraguay")
    assert usa["status"] == "finished"
    assert usa["home_score"] == 4  # USA is the stored home team in group D


def test_elo_update_idempotent(store):
    service.import_elo(store, {t: 1800.0 for t in
                               __import__("wc2026").structure.TEAMS})
    events = json.loads((FIXTURES / "espn_scoreboard.json").read_text())
    service.ingest_espn(store, espn.parse_scoreboard(events))
    first = service.apply_elo_updates(store)
    assert set(first) == {7, 19}  # Canada-Bosnia, USA-Paraguay
    again = service.apply_elo_updates(store)
    assert again == []  # nothing re-applied
    # USA won 4-1, so its rating rose above the 1800 baseline.
    assert store.get_elo()["USA"] > 1800


def test_resimulate_writes_snapshot(store):
    service.import_elo(store, {t: 1800.0 for t in
                               __import__("wc2026").structure.TEAMS})
    out = service.resimulate(store, n=2000, trigger="test")
    assert out["snapshot_id"] == 1
    snap = store.latest_snapshot()
    assert snap["trigger"] == "test"
    assert abs(sum(p["champ"] for p in snap["probs"].values()) - 100) < 0.5


def test_conditioning_flows_through_service(store):
    # USA 4-1 should lift USA's advance odds well above Paraguay's.
    service.import_elo(store, {t: 1800.0 for t in
                               __import__("wc2026").structure.TEAMS})
    events = json.loads((FIXTURES / "espn_scoreboard.json").read_text())
    service.ingest_espn(store, espn.parse_scoreboard(events))
    out = service.resimulate(store, n=4000, trigger="test")
    probs = out["probs"]
    assert probs["USA"]["advance"] > probs["Paraguay"]["advance"]
