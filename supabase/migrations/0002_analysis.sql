-- Key/value store for derived analyses (e.g. per-match importance), kept
-- separate from snapshots. value is JSONB; one row per analysis key.
CREATE TABLE IF NOT EXISTS analysis (
    key   TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    ts    TEXT
);
