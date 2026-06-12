# WC2026 Live Odds Tracker

## Goal
A live-updating 2026 World Cup probability dashboard. After every real match result,
re-run the Monte Carlo simulation **conditioned on actual results so far** and publish
updated odds (champion / final / top-4 / QF / advance-from-group, per team), plus an
odds-over-time history so we can chart how each team's title probability evolves
through the tournament (FiveThirtyEight-style race chart).

## What already exists
`engine/wc2026_sim.py` — a working 20,000-iteration Monte Carlo simulator with:
- All 48 teams and the real group draw (verified June 2026, incl. March playoff
  winners: Bosnia, Sweden, Türkiye, Czechia in UEFA; DR Congo → Group K, Iraq → Group I)
- Elo-based match model: logistic expected score, draw model in groups, penalty
  compression (0.88 toward 0.5) in knockouts
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
    constraint-satisfying backtracking matching (FIFA Annex C defines the exact
    495-row table; our matching is constraint-valid but may differ from FIFA's
    canonical pick when multiple matchings exist — fine for odds, could be made
    exact by encoding Annex C)

## Architecture (suggested — challenge if you have better ideas)
1. **State layer** (`data/state.json` or SQLite): every real match result entered so
   far (group games with scores; knockout games with winner). Group standings,
   qualified teams, and bracket slots are *derived* from this, never hand-edited.
2. **Conditioning**: modify the simulator so completed matches use their real result
   and only remaining matches are sampled. Mid-group this means simulating only the
   unplayed fixtures and computing standings from real + simulated points (real goal
   difference matters for tiebreaks — store scores, not just W/D/L).
3. **Elo updates**: after each real result, update team ratings with the standard
   World Football Elo rule (K=60 for World Cup, goal-margin multiplier). So upsets
   shift future match probabilities, not just bracket position.
4. **Results ingestion**: start with a manual `add-result` CLI command (fast, zero
   dependencies, works day 1). Then add a fetcher — football-data.org v4 (free tier
   includes the World Cup) or API-Football — behind the same interface.
5. **Snapshot history**: every re-run appends per-team probabilities with a
   timestamp/matchday to `data/history.json` → powers the race chart.
6. **Frontend**: static site (fits GitHub Pages — nilsbacklund.github.io). A single
   page reading the latest JSON: title-odds race chart over time, current top-8 table,
   bracket view with per-slot probabilities, and a Sweden panel (group scenarios,
   round-by-round survival). Chart.js or Observable Plot, no build step needed.
7. **Automation**: GitHub Action on cron (every 2h during June 11–July 19): fetch
   results → if new, update Elo + state → run 20k sims → commit JSON → Pages redeploys.
   Fully serverless.

## Milestones
- [ ] M1: refactor sim into a package with `state` conditioning + `add-result` CLI;
      unit tests for bracket logic (e.g. feed 2022-style fake results, assert slots)
- [ ] M2: Elo update rule + snapshot history
- [ ] M3: static dashboard reading the JSON
- [ ] M4: football-data.org fetcher + GitHub Action cron
- [ ] M5 (stretch): odds-vs-bookmakers comparison, Sweden deep-dive panel,
      "what must happen" scenario explorer for any team

## Known caveats to preserve in the UI
- Only 4 of 48 Elo ratings are verified (Spain 2157, Argentina 2115, France 2063,
  England 2024, June 11 2026); the rest are informed estimates — consider fetching
  the real eloratings.net table as an early task.
- Tiebreakers beyond points use an Elo+noise proxy for goal difference in *simulated*
  matches; real matches should use real GD once scores are stored.
