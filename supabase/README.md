# Supabase / Postgres backend

The backend persists to SQLite by default. Set `SUPABASE_DB_URL` to switch to a
Supabase (Postgres) backend — `get_store()` in
`backend/wc2026_backend/store_factory.py` picks the backend automatically.

## 1. Create the project

1. Create a project at https://supabase.com (free tier includes the World Cup
   window comfortably).
2. In **Project Settings → Database → Connection string**, copy the
   **URI** (`postgres://...`). Use the connection-pooler URI (port `6543`) for
   serverless/many-connection use, or the direct URI (port `5432`) otherwise.

## 2. Run the migration

Apply `migrations/0001_init.sql`. Either:

- **Supabase SQL Editor**: paste the file contents and run it, **or**
- **psql / Supabase CLI**:

  ```bash
  psql "$SUPABASE_DB_URL" -f supabase/migrations/0001_init.sql
  # or, with the Supabase CLI linked to the project:
  supabase db push
  ```

The `alter publication supabase_realtime add table snapshots;` line enables
Realtime inserts on `snapshots` so the frontend can update live; it is a no-op
on a plain Postgres without that publication and can be removed there.

## 3. Set env vars

```bash
export SUPABASE_DB_URL="postgres://postgres:<password>@<host>:6543/postgres"
```

Install the optional dependency (psycopg 3) used by the adapter:

```bash
pip install -e ".[supabase]"
```

With `SUPABASE_DB_URL` set, the app uses `SupabaseStore`; unset it to fall back
to local SQLite. No code changes needed either way.
