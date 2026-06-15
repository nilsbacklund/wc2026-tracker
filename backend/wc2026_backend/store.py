"""Persistence layer. SQLite implementation behind a small interface so a
Supabase/Postgres adapter can replace it without touching callers.

Tables mirror the planned Supabase schema:
  matches    - the 104-match schedule + live/finished state (id = FIFA number)
  elo        - current rating per team
  elo_history- audit of rating changes, keyed by applied match (idempotency)
  snapshots  - odds snapshots (probs as JSON), Realtime-published in Supabase
"""
import json
import sqlite3
import threading
import time
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "wc2026.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY,
    stage TEXT NOT NULL,
    grp TEXT,
    matchday INTEGER,
    home TEXT,
    away TEXT,
    kickoff_utc TEXT,
    status TEXT NOT NULL DEFAULT 'scheduled',
    home_score INTEGER,
    away_score INTEGER,
    minute INTEGER,
    ko_winner TEXT,
    ko_decided_by TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS elo (
    team TEXT PRIMARY KEY,
    rating REAL NOT NULL,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS elo_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team TEXT NOT NULL,
    match_id INTEGER NOT NULL,
    before REAL NOT NULL,
    after REAL NOT NULL,
    ts TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    trigger TEXT NOT NULL,
    match_id INTEGER,
    n_sims INTEGER NOT NULL,
    probs TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON snapshots(ts);
CREATE TABLE IF NOT EXISTS analysis (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    ts TEXT
);
"""


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Store:
    def __init__(self, path=DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # FastAPI serves sync handlers from a threadpool; allow cross-thread
        # use and serialize writes with a lock. WAL keeps reads concurrent.
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._lock = threading.Lock()
        with self._lock:
            self.conn.executescript(SCHEMA)
            self.conn.commit()

    def close(self):
        self.conn.close()

    # --- matches ---
    def upsert_match(self, row):
        cols = ("id", "stage", "grp", "matchday", "home", "away", "kickoff_utc",
                "status", "home_score", "away_score", "minute", "ko_winner",
                "ko_decided_by")
        vals = {c: row.get(c) for c in cols}
        vals["updated_at"] = _now()
        placeholders = ",".join(f":{c}" for c in (*cols, "updated_at"))
        updates = ",".join(f"{c}=excluded.{c}"
                           for c in (*cols[1:], "updated_at"))
        with self._lock:
            self.conn.execute(
                f"INSERT INTO matches ({','.join((*cols,'updated_at'))}) "
                f"VALUES ({placeholders}) "
                f"ON CONFLICT(id) DO UPDATE SET {updates}", vals)
            self.conn.commit()

    def all_matches(self):
        return [dict(r) for r in
                self.conn.execute("SELECT * FROM matches ORDER BY id")]

    def get_match(self, mid):
        r = self.conn.execute("SELECT * FROM matches WHERE id=?", (mid,)).fetchone()
        return dict(r) if r else None

    def match_by_teams(self, home, away):
        """Find a match by unordered team pair (for ingestion by name)."""
        r = self.conn.execute(
            "SELECT * FROM matches WHERE (home=? AND away=?) OR (home=? AND away=?)",
            (home, away, away, home)).fetchone()
        return dict(r) if r else None

    # --- elo ---
    def set_elo(self, ratings):
        ts = _now()
        with self._lock:
            self.conn.executemany(
                "INSERT INTO elo (team, rating, updated_at) VALUES (?,?,?) "
                "ON CONFLICT(team) DO UPDATE SET rating=excluded.rating, "
                "updated_at=excluded.updated_at",
                [(t, float(r), ts) for t, r in ratings.items()])
            self.conn.commit()

    def get_elo(self):
        return {r["team"]: r["rating"]
                for r in self.conn.execute("SELECT team, rating FROM elo")}

    def record_elo_change(self, team, match_id, before, after):
        with self._lock:
            self.conn.execute(
                "INSERT INTO elo_history (team, match_id, before, after, ts) "
                "VALUES (?,?,?,?,?)", (team, match_id, before, after, _now()))
            self.conn.commit()

    def elo_applied_match_ids(self):
        return {r["match_id"] for r in
                self.conn.execute("SELECT DISTINCT match_id FROM elo_history")}

    # --- snapshots ---
    def add_snapshot(self, probs, n_sims, trigger, match_id=None):
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO snapshots (ts, trigger, match_id, n_sims, probs) "
                "VALUES (?,?,?,?,?)",
                (_now(), trigger, match_id, n_sims, json.dumps(probs)))
            self.conn.commit()
            return cur.lastrowid

    def latest_snapshot(self):
        r = self.conn.execute(
            "SELECT * FROM snapshots ORDER BY id DESC LIMIT 1").fetchone()
        return _snapshot_row(r) if r else None

    def history(self, since=None):
        q = "SELECT * FROM snapshots"
        args = ()
        if since:
            q += " WHERE ts >= ?"
            args = (since,)
        q += " ORDER BY id"  # insertion order (= match order for a rebuild)
        return [_snapshot_row(r) for r in self.conn.execute(q, args)]

    def clear_snapshots(self):
        with self._lock:
            self.conn.execute("DELETE FROM snapshots")
            self.conn.commit()

    # --- analysis (key/value) ---
    def set_analysis(self, key, value):
        with self._lock:
            self.conn.execute(
                "INSERT INTO analysis (key, value, ts) VALUES (?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
                "ts=excluded.ts", (key, json.dumps(value), _now()))
            self.conn.commit()

    def get_analysis(self, key):
        r = self.conn.execute(
            "SELECT value FROM analysis WHERE key=?", (key,)).fetchone()
        return json.loads(r["value"]) if r else None

    # --- engine bridge ---
    def engine_state(self):
        """Matches in the shape engine.run_sims expects."""
        matches = []
        for m in self.all_matches():
            entry = {
                "id": m["id"], "stage": m["stage"], "group": m["grp"],
                "home": m["home"], "away": m["away"], "status": m["status"],
                "minute": m["minute"],
            }
            if m["home_score"] is not None and m["away_score"] is not None:
                entry["score"] = {"home": m["home_score"], "away": m["away_score"]}
            if m["stage"] != "group":
                entry["ko"] = {"winner": m["ko_winner"],
                               "decided_by": m["ko_decided_by"]}
            matches.append(entry)
        return {"matches": matches}


def _snapshot_row(r):
    d = dict(r)
    d["probs"] = json.loads(d["probs"])
    return d
