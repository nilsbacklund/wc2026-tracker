-- WC2026 Live Odds Tracker — initial Postgres/Supabase schema.
--
-- Mirrors backend/wc2026_backend/store.py's SQLite SCHEMA, with Postgres types:
--   * IDENTITY columns for autoincrement (elo_history.id, snapshots.id)
--   * JSONB for snapshots.probs (the SQLite store writes a JSON string; JSONB
--     accepts that and the adapter reads it back already-parsed)
--   * ts/updated_at kept as TEXT to match the ISO-8601 strings the code writes
--     (avoids TIMESTAMPTZ coercion surprises across backends)
--
-- matches.id is the FIFA match number (1..104), so it is a plain INTEGER PK
-- supplied by the caller, not generated.

CREATE TABLE IF NOT EXISTS matches (
    id            INTEGER PRIMARY KEY,
    stage         TEXT NOT NULL,
    grp           TEXT,
    matchday      INTEGER,
    home          TEXT,
    away          TEXT,
    kickoff_utc   TEXT,
    status        TEXT NOT NULL DEFAULT 'scheduled',
    home_score    INTEGER,
    away_score    INTEGER,
    minute        INTEGER,
    ko_winner     TEXT,
    ko_decided_by TEXT,
    updated_at    TEXT
);

CREATE TABLE IF NOT EXISTS elo (
    team       TEXT PRIMARY KEY,
    rating     DOUBLE PRECISION NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS elo_history (
    id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    team     TEXT NOT NULL,
    match_id INTEGER NOT NULL,
    before   DOUBLE PRECISION NOT NULL,
    after    DOUBLE PRECISION NOT NULL,
    ts       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshots (
    id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ts       TEXT NOT NULL,
    trigger  TEXT NOT NULL,
    match_id INTEGER,
    n_sims   INTEGER NOT NULL,
    probs    JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON snapshots (ts);

-- The frontend subscribes to new odds snapshots over Supabase Realtime.
-- Publishing inserts on `snapshots` lets the dashboard update live after a
-- re-simulation. Guarded so the migration is idempotent.
do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and tablename = 'snapshots'
  ) then
    alter publication supabase_realtime add table snapshots;
  end if;
exception
  when undefined_object then null;  -- publication absent on vanilla Postgres
end $$;

-- Supabase Realtime delivers postgres_changes only for rows the subscribing
-- role can SELECT under RLS. Snapshots are public, read-only odds, so allow
-- the anon key to read them; the backend writes via a direct DB connection
-- (SUPABASE_DB_URL), which bypasses RLS. Without this policy the browser
-- subscribes successfully but never receives INSERT events.
alter table snapshots enable row level security;
do $$
begin
  if not exists (
    select 1 from pg_policies
    where tablename = 'snapshots' and policyname = 'public read snapshots'
  ) then
    create policy "public read snapshots" on snapshots
      for select to anon using (true);
  end if;
end $$;
