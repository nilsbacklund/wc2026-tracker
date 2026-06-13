# Deploying WC2026 Live Odds Tracker

The whole app ships as **one container**: a multi-stage Docker image that builds
the React/Vite frontend and serves it from the FastAPI backend (same origin —
the backend mounts `frontend/dist` at `/`). The database is **Supabase**
(managed Postgres). Results come from **ESPN** (no key) and optionally
**football-data.org** (free token).

You can deploy to **Fly.io** or **Railway**. Both use the same `Dockerfile`.

---

## 1. Prerequisites

- A **Supabase** project (free tier is fine).
- A **football-data.org** account + API token (optional — ESPN works without any
  key; football-data is a secondary results source).
- For Fly.io: the [`flyctl`](https://fly.io/docs/flyctl/install/) CLI + a Fly
  account.
- For Railway: the [`railway`](https://docs.railway.com/guides/cli) CLI + a
  Railway account (or just the web dashboard).
- Docker locally is **not** required — both platforms build the image remotely.

---

## 2. Set up Supabase

1. Create a project at <https://supabase.com>. Pick a region near your users.
2. Get the **connection string** (this becomes `SUPABASE_DB_URL`):
   - Supabase Dashboard → your project → **Connect** (top bar) → **Connection
     string** → choose **Transaction pooler** (recommended for serverless / a
     single small instance) or **Session pooler**.
   - It looks like:
     ```
     postgresql://postgres.<ref>:<PASSWORD>@aws-0-<region>.pooler.supabase.com:6543/postgres
     ```
   - Replace `<PASSWORD>` with your database password (Dashboard → Project
     Settings → Database if you need to reset it). URL-encode any special
     characters in the password.
   - The app uses **psycopg 3** (installed via the `supabase` extra), which
     accepts standard `postgresql://...` URLs.
3. **Run the schema migration.** The SQL lives in
   `supabase/migrations/0001_init.sql` (created alongside the Supabase store).
   Apply it once against your project — easiest path:
   - Supabase Dashboard → **SQL Editor** → paste the contents of
     `supabase/migrations/0001_init.sql` → **Run**.
   - Or via `psql`:
     ```bash
     psql "$SUPABASE_DB_URL" -f supabase/migrations/0001_init.sql
     ```

> If `supabase/migrations/0001_init.sql` is not present yet, it is being added
> by the backend/store work. The backend's `init` CLI command (step 5) also
> creates the tables it needs, so you can rely on that as a fallback.

---

## 3. Environment variables

| Variable               | Required | What it does |
|------------------------|----------|--------------|
| `SUPABASE_DB_URL`      | Yes (prod) | Postgres connection string. When set, the app uses the Supabase store instead of local SQLite. |
| `FOOTBALL_DATA_TOKEN`  | Optional | football-data.org API token for results. ESPN needs no key, so this is optional. |
| `WC2026_DISABLE_POLLER`| Optional | Set to any value (e.g. `1`) to **disable** the background live polling loop. Leave **unset** in production so odds update live during matches. |
| `PORT`                 | Auto     | The HTTP port. Fly and Railway inject this automatically; the image defaults to `8080`. Do not hardcode it unless you know why. |

The app starts a **background ESPN poller** on startup (see `live.py`). It needs
no API key. Keep the poller enabled in production (do **not** set
`WC2026_DISABLE_POLLER`) so the dashboard re-simulates after each goal/result.

---

## 4. Deploy

### Option A — Fly.io

The repo includes `fly.toml` (app name placeholder: `wc2026-tracker`).

```bash
# 1. Log in
fly auth login

# 2. Create the app WITHOUT deploying yet (so we can set secrets first).
#    This also reconciles the app name in fly.toml — accept the generated name
#    or edit `app = "..."` in fly.toml to a unique name you own.
fly launch --no-deploy --copy-config --name wc2026-tracker

# 3. Set secrets (encrypted env vars). ESPN needs no key.
fly secrets set \
  SUPABASE_DB_URL='postgresql://postgres.<ref>:<PASSWORD>@aws-0-<region>.pooler.supabase.com:6543/postgres' \
  FOOTBALL_DATA_TOKEN='<your-token-or-omit-this-line>'

# 4. Deploy (builds the Dockerfile remotely).
fly deploy

# 5. Open it
fly open
```

**Why `min_machines_running = 1` and `auto_stop_machines = "off"` in
`fly.toml`:** the live poller is an in-process background loop. If Fly stopped
the only machine between web requests (the usual cost-saving auto-stop), the
poller would stop too and odds would freeze mid-match. Keeping one machine
always running guarantees continuous polling/re-simulation during the
tournament. After July 19 you can flip auto-stop back on to save money.

### Option B — Railway

The repo includes `railway.json` (builder = `DOCKERFILE`, healthcheck = `/`).

Dashboard route (simplest):
1. New Project → **Deploy from GitHub repo** → pick this repo. Railway detects
   the `Dockerfile` / `railway.json`.
2. Service → **Variables** → add `SUPABASE_DB_URL` (and `FOOTBALL_DATA_TOKEN` if
   used). Do **not** set `WC2026_DISABLE_POLLER`. `PORT` is provided by Railway.
3. Deploy. Railway gives you a public URL (Settings → Networking → Generate
   Domain).

CLI route:
```bash
railway login
railway init           # or: railway link  (to an existing project)
railway variables set SUPABASE_DB_URL='postgresql://...:6543/postgres'
railway variables set FOOTBALL_DATA_TOKEN='<token>'   # optional
railway up             # builds & deploys the Dockerfile
```

> Railway has no "always-on min instance" toggle like Fly; a single replica
> stays running by default (it is not request-scaled to zero), so the poller
> keeps running. Keep `numReplicas: 1` — running multiple replicas would start
> multiple independent pollers writing to the same DB.

---

## 5. Seed data on first deploy (run once against prod)

The backend ships a CLI (`python -m wc2026_backend ...`). On a fresh database
run these **once**, with `SUPABASE_DB_URL` pointing at your Supabase project, so
the CLI writes to prod (not local SQLite):

```bash
python -m wc2026_backend init         # create tables + seed groups/fixtures
python -m wc2026_backend import-elo    # load team Elo ratings
python -m wc2026_backend fetch         # pull any results played so far
python -m wc2026_backend resim         # optional: run sims -> first snapshot
```

Run them **inside the deployed environment** so they hit the prod DB:

**Fly.io** — open a shell on the running machine:
```bash
fly ssh console
# now inside the container (SUPABASE_DB_URL is already set from secrets):
python -m wc2026_backend init
python -m wc2026_backend import-elo
python -m wc2026_backend fetch
python -m wc2026_backend resim
exit
```

**Railway** — run a one-off command with the service's env injected:
```bash
railway run python -m wc2026_backend init
railway run python -m wc2026_backend import-elo
railway run python -m wc2026_backend fetch
railway run python -m wc2026_backend resim
```
(`railway run` loads the service variables, including `SUPABASE_DB_URL`, into the
command's environment.)

Alternatively, run them from your laptop by exporting the same
`SUPABASE_DB_URL` locally — the result lands in the same Supabase DB either way:
```bash
export SUPABASE_DB_URL='postgresql://...:6543/postgres'
python -m wc2026_backend init && python -m wc2026_backend import-elo && python -m wc2026_backend fetch
```

After seeding, the background poller takes over: it fetches new results, updates
Elo + state, and re-simulates automatically. `/api/odds/latest` will return the
newest snapshot, and the dashboard renders it.

---

## 6. Verify

- `GET /` → the dashboard loads.
- `GET /api/teams` → 200 with the 48 teams (after `init` + `import-elo`).
- `GET /api/odds/latest` → 200 with the latest snapshot (after a `resim`/poll;
  404 until the first snapshot exists — expected on a brand-new DB, which is why
  the health check targets `/`, not this endpoint).
- Trigger a poll manually any time: `POST /api/poll`.

---

## 7. Notes / gotchas

- **Image layout.** The image installs the package in *editable* mode
  (`pip install -e .[supabase]`) on purpose. `app.py` computes the frontend path
  as `parents[2]/frontend/dist` relative to
  `backend/wc2026_backend/app.py`. Editable install keeps the source at
  `/app/backend/wc2026_backend/app.py`, so `parents[2]` resolves to `/app`, and
  the build places the compiled frontend at `/app/frontend/dist`. A normal
  (copy-into-site-packages) install would move `app.py` and break that path.
  This was verified inside the built container: `FRONTEND_DIST=/app/frontend/dist`,
  exists=True.
- **psycopg.** Comes from the `supabase` extra (`psycopg[binary]`), installed in
  the image. No system Postgres client libraries are needed at runtime because
  the binary wheel bundles them.
- **No `pyproject.toml` change required.** The `supabase` extra already pulls in
  psycopg; the Dockerfile installs `.[supabase]`. If you ever want a smaller
  prod image, you could drop the `[standard]` uvicorn extras, but it is not
  necessary.
- **Single replica only.** The poller is in-process. Run exactly one instance
  (Fly `min_machines_running = 1` with auto-stop off; Railway `numReplicas: 1`)
  to avoid duplicate pollers double-writing to Supabase.
- **GitHub Actions cron alternative.** If you would rather not keep a machine
  always on, you can set `WC2026_DISABLE_POLLER=1` and instead hit
  `POST /api/poll` from a scheduled GitHub Action during June 11–July 19. The
  in-process poller is simpler, though.
