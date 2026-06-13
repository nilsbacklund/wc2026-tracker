"""Supabase/Postgres persistence adapter.

Drop-in replacement for store.Store backed by Postgres via psycopg 3. Mirrors
the SQLite schema/semantics exactly so callers (service.py, standings_view.py,
app.py) see identical method signatures and return shapes (note 'grp', not
'group'; snapshots return parsed 'probs').

psycopg connections are not thread-safe and FastAPI serves sync handlers from a
threadpool, so we open a short-lived connection per operation from the
connection string. At our volume (a handful of writes per match) this is simple
and correct; swap in psycopg_pool later if needed.
"""
import json
import os
import time

DEFAULT_ENV = "SUPABASE_DB_URL"


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class SupabaseStore:
    def __init__(self, dsn=None):
        self.dsn = dsn or os.environ.get(DEFAULT_ENV)
        if not self.dsn:
            raise RuntimeError(
                f"{DEFAULT_ENV} not set; cannot connect to Supabase/Postgres")
        # Lazy import so psycopg is only required when this backend is used.
        import psycopg  # noqa: F401
        self._psycopg = psycopg
        # Fail fast if the DB is unreachable / credentials are wrong.
        with self._connect():
            pass

    def _connect(self):
        return self._psycopg.connect(self.dsn, autocommit=True)

    def close(self):
        # No persistent connection is held; nothing to close.
        pass

    # --- matches ---
    def upsert_match(self, row):
        cols = ("id", "stage", "grp", "matchday", "home", "away", "kickoff_utc",
                "status", "home_score", "away_score", "minute", "ko_winner",
                "ko_decided_by")
        vals = [row.get(c) for c in cols] + [_now()]
        names = (*cols, "updated_at")
        placeholders = ",".join(["%s"] * len(names))
        updates = ",".join(f"{c}=EXCLUDED.{c}" for c in (*cols[1:], "updated_at"))
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO matches ({','.join(names)}) "
                f"VALUES ({placeholders}) "
                f"ON CONFLICT (id) DO UPDATE SET {updates}", vals)

    def all_matches(self):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM matches ORDER BY id")
            return self._rows(cur)

    def get_match(self, mid):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM matches WHERE id=%s", (mid,))
            rows = self._rows(cur)
        return rows[0] if rows else None

    def match_by_teams(self, home, away):
        """Find a match by unordered team pair (for ingestion by name)."""
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM matches WHERE (home=%s AND away=%s) "
                "OR (home=%s AND away=%s)", (home, away, away, home))
            rows = self._rows(cur)
        return rows[0] if rows else None

    # --- elo ---
    def set_elo(self, ratings):
        ts = _now()
        data = [(t, float(r), ts) for t, r in ratings.items()]
        with self._connect() as conn, conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO elo (team, rating, updated_at) VALUES (%s,%s,%s) "
                "ON CONFLICT (team) DO UPDATE SET rating=EXCLUDED.rating, "
                "updated_at=EXCLUDED.updated_at", data)

    def get_elo(self):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT team, rating FROM elo")
            return {team: float(rating) for team, rating in cur.fetchall()}

    def record_elo_change(self, team, match_id, before, after):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO elo_history (team, match_id, before, after, ts) "
                "VALUES (%s,%s,%s,%s,%s)",
                (team, match_id, before, after, _now()))

    def elo_applied_match_ids(self):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT DISTINCT match_id FROM elo_history")
            return {r[0] for r in cur.fetchall()}

    # --- snapshots ---
    def add_snapshot(self, probs, n_sims, trigger, match_id=None):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO snapshots (ts, trigger, match_id, n_sims, probs) "
                "VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (_now(), trigger, match_id, n_sims, json.dumps(probs)))
            return cur.fetchone()[0]

    def latest_snapshot(self):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM snapshots ORDER BY id DESC LIMIT 1")
            rows = self._rows(cur)
        return _snapshot_row(rows[0]) if rows else None

    def history(self, since=None):
        q = "SELECT * FROM snapshots"
        args = ()
        if since:
            q += " WHERE ts >= %s"
            args = (since,)
        q += " ORDER BY ts"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(q, args)
            rows = self._rows(cur)
        return [_snapshot_row(r) for r in rows]

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

    @staticmethod
    def _rows(cur):
        """Return cursor rows as dicts keyed by column name."""
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def _snapshot_row(d):
    d = dict(d)
    # JSONB comes back already parsed; tolerate TEXT/str just in case.
    if isinstance(d.get("probs"), str):
        d["probs"] = json.loads(d["probs"])
    return d
