# WC2026 Live Odds Tracker

## Goal
A live-updating 2026 World Cup probability dashboard. After every real match result —
and **after every goal in a live match** — re-run the Monte Carlo simulation
**conditioned on actual results so far (and the live scoreline)** and push updated odds
(champion / final / top-4 / QF / R16 / advance-from-group, per team) to all open
browsers. An odds-over-time history (including per-goal drift during matches) powers a
FiveThirtyEight-style title-race chart.

## What already exists
A working, NumPy-vectorized 20,000-iteration Monte Carlo simulator with:
- All 48 teams and the real group draw (verified June 2026, incl. March playoff
  winners: Bosnia, Sweden, Türkiye, Czechia in UEFA; DR Congo → Group K, Iraq → Group I)
- Elo-based match model: logistic expected score, Poisson goal model in groups (gives
  W/D/L *and* goal difference natively), penalty compression (0.88 toward 0.5) in knockouts
- Host bonus +60 (USA/Mexico/Canada), Americas bonus +15
- Exact FIFA bracket, verified against the official schedule:
  - R32: M73 2A-2B, M74 1E-3rd(ABCDF), M75 1F-2C, M76 1C-2F, M77 1I-3rd(CDFGH),
    M78 2E-2I, M79 1A-3rd(CEFHI), M80 1L-3rd(EHIJK), M81 1D-3rd(BEFIJ),
    M82 1G-3rd(AEHIJ), M83 2K-2L, M84 1H-2J, M85 1B-3rd(EFGIJ), M86 1J-2H,
    M87 1K-3rd(DEIJL), M88 2D-2G
  - R16: M89 W74-W77, M90 W73-W75, M91 W76-W78, M92 W79-W80, M93 W83-W84,
    M94 W81-W82, M95 W86-W88, M96 W85-W87
  - QF: M97 W89-W90, M98 W93-W94, M99 W91-W92, M100 W95-W96
  - SF: M101 W97-W98, M102 W99-W100; Final W101-W102; 3rd place L101-L102
  - Best 8 of 12 third-place teams advance; slot assignment implemented as a
    deterministic, memoized constraint-satisfying matching (FIFA Annex C defines the
    exact 495-row table; our matching is constraint-valid but may differ from FIFA's
    canonical pick when multiple matchings exist — fine for odds, could be made exact by
    encoding Annex C, or neutralized by overriding with the real R32 pairings once groups finish)

## Architecture
A single FastAPI service hosts the engine, ingestion, live loop, and REST API, and
serves the built React frontend. Postgres (Supabase) is the production store with
Realtime pushing snapshots to browsers; SQLite is the local store.

1. **Engine** (`engine/wc2026/`) — a pure simulation package, no I/O. Inputs and outputs
   are plain data; the backend maps DB rows ↔ engine structures.
   - `structure.py` — `GROUPS`, the `BRACKET` slot-grammar dict (`"1E"`, `"2B"`,
     `"3:ABCDF"`, `"W74"`, `"L101"`), `THIRD_SLOTS`, `DEFAULT_ELO`, host/Americas sets
   - `model.py` — Elo logistic expected score, Poisson goal λ split, KO penalty
     compression, host/Americas bonuses
   - `standings.py` — vectorized FIFA tiebreaks (points → GD → GF → head-to-head → random)
     over combined real + simulated goals
   - `thirds.py` — deterministic, memoized third-place slot assignment (cached per
     qualified-group set)
   - `simulate.py` — `run_sims(spec, state, n, seed)`; NumPy-vectorized across iterations;
     conditioning on completed real results and on the live scoreline of an in-play match
     (remaining minutes use time-scaled Poisson on top of the current score)
   - `elo.py` — standard World Football Elo update, K=60, goal-margin multiplier (pure function)
2. **Backend** (`backend/wc2026_backend/`) — FastAPI app importing the engine directly.
   - `app.py` — REST API: `/api/odds/latest`, `/api/odds/history`, `/api/matches`,
     `/api/standings`, `/api/teams`, `/api/simulate` (server-side what-ifs: Elo overrides
     / hypothetical results, never persisted), plus the live poller and `/api/live`,
     `/api/poll`; serves the frontend build
   - `store.py` — SQLite behind a `Store` interface (matches, Elo + history, snapshots, teams)
   - `store_factory.py` + `store_supabase.py` — Supabase/Postgres adapter; the **production
     store** (Supabase Realtime publishes new snapshot rows to all browsers)
   - `service.py` — `ingest_espn`, `apply_elo_updates`, `resimulate`, `import_elo`
   - `sources/` — `eloratings.py` (initial Elo table import), `espn.py` (live scores),
     `football_data.py` (authoritative full-time results), with name mapping (`names.py`)
   - `fixtures.py` — seeds all 104 matches (KO teams null until known; bracket keys off 73–104)
   - `cli.py` — `init`, `import-elo`, `fetch`, `add-result`, `resim`, `show`
3. **Frontend** (`frontend/`) — React + Vite + TypeScript. Two modes: **Sverigeläge**
   (Swedish, blue/yellow theme, Sweden-first layout) and a **neutral** English view
   (i18n string table + CSS theme variables). Odds table, group standings, match list,
   title-race chart, Sweden panel. Polls the API today as a stand-in for Supabase Realtime.
4. **Data sources**
   - **ESPN unofficial scoreboard API** — live scores, keyless, browser-CORS-friendly;
     polled server-side during match windows
   - **football-data.org v4** (comp `WC`) — authoritative full-time results; needs
     `FOOTBALL_DATA_TOKEN`
   - **eloratings.net** — one-time import of the real Elo table at init
5. **Live loop** — during a match window, poll ESPN; on a score/status change, condition
   the sim on the live scoreline and re-simulate, writing a tagged odds snapshot
   (`goal`/`kickoff`/`fulltime`/`scheduled`). At full time, confirm against
   football-data.org and apply the Elo update.
6. **Elo updates** — full-time only, K=60 with goal-margin multiplier, idempotent per
   match id. Upsets shift future match probabilities. **No mid-match Elo changes** — live
   updates work purely by conditioning on the scoreline, not by touching ratings.
7. **Deployment** — one service (FastAPI serving the built frontend) on Fly.io or Railway;
   Supabase hosts the production Postgres + Realtime. Secrets: `FOOTBALL_DATA_TOKEN`,
   Supabase URL/keys, admin token.

## Development
- Python 3.11 venv at `.venv`.
- Tests: `.venv/bin/python -m pytest`
- Backend: `.venv/bin/uvicorn wc2026_backend.app:app --port 8137`
- Frontend: `cd frontend && npm run dev`
- CLI: `.venv/bin/python -m wc2026_backend init | import-elo | fetch | add-result | resim`

## Milestones
- [x] M1: pure NumPy-vectorized engine package with state + live conditioning; data-driven
      bracket; deterministic memoized thirds; pytest suite (standings/tiebreaks, bracket,
      mid-group conditioning, Elo)
- [x] M2: Elo import from eloratings.net + full-time K=60 updates; odds snapshot history
- [x] M3: FastAPI backend + Store interface (SQLite local, Supabase/Postgres prod) + CLI
- [x] M4: React/Vite frontend (Sverigeläge + neutral), odds table, standings, match list, race chart
- [x] M5: goal-triggered live loop (ESPN poll → live conditioning → per-goal snapshots →
      football-data.org full-time confirmation)
- [ ] M6: create the Supabase project + wire Realtime in the frontend (replace polling); deploy to Fly.io/Railway
- [ ] M7 (stretch): what-if sliders UI on top of `/api/simulate`; Sweden survival deep-dive
      (round-by-round, group scenarios); bracket view with per-slot probabilities;
      bookmaker comparison; exact Annex C encoding

## Known caveats to preserve in the UI
- Elo ratings are now imported from **eloratings.net** at init and evolve via full-time
  K=60 updates (with goal-margin multiplier). The old "only 4 of 48 verified, rest
  estimated" caveat is largely resolved; ratings remain a model input, not ground truth.
- Tiebreakers beyond points use **real goal difference for played matches** and
  Poisson-sampled goals for simulated ones (the old Elo+noise GD proxy is gone), so real
  and simulated matches feed identical standings arithmetic. Head-to-head is applied;
  fair-play tiebreak is deferred and documented.
