"""FastAPI app: REST API + static frontend hosting.

Read endpoints serve stored state (snapshots, matches, standings). The
what-if endpoint runs the engine live with caller-supplied Elo overrides and
hypothetical results — never persisted. The live polling loop is started on
startup (see live.py).
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from . import config  # noqa: F401 — loads .env before env vars are read

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from wc2026.simulate import run_sims
from wc2026.structure import GROUPS, GROUP_LETTERS, TEAMS

from .store import Store
from .live import LivePoller
from . import service, standings_view

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from .store_factory import get_store
        app.state.store = get_store()
    except ImportError:
        app.state.store = Store()
    app.state.poller = LivePoller(app.state.store)
    if not os.getenv("WC2026_DISABLE_POLLER"):
        await app.state.poller.start()
    yield
    await app.state.poller.stop()
    app.state.store.close()


app = FastAPI(title="WC2026 Live Odds", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
    allow_headers=["*"])


def store() -> Store:
    return app.state.store


@app.get("/api/odds/latest")
def odds_latest():
    snap = store().latest_snapshot()
    if not snap:
        raise HTTPException(404, "no snapshot yet")
    return snap


@app.get("/api/odds/history")
def odds_history(since: str | None = None, team: str | None = None):
    snaps = store().history(since)
    if team:
        return {"team": team,
                "points": [{"ts": s["ts"], "trigger": s["trigger"],
                            "match_id": s["match_id"],
                            "probs": s["probs"].get(team)} for s in snaps]}
    return {"snapshots": snaps}


@app.get("/api/matches")
def matches():
    return {"matches": store().all_matches()}


@app.get("/api/live")
def live():
    """Matches currently in play, from the store."""
    return {"matches": [m for m in store().all_matches()
                        if m["status"] == "in_play"]}


@app.post("/api/poll")
async def poll():
    """Run one poll cycle now (manual/cron trigger). Returns the result."""
    return await app.state.poller.poll_once()


@app.get("/api/standings")
def standings():
    return {"groups": standings_view.current_standings(store())}


@app.get("/api/importance")
def importance():
    """Stored per-match importance analysis (may be null until first computed)."""
    return store().get_analysis("importance") or {"matches": []}


@app.get("/api/teams")
def teams():
    elo = store().get_elo()
    return {"teams": [{"name": t, "group": g, "elo": elo.get(t)}
                      for g in GROUP_LETTERS for t in GROUPS[g]]}


class SimRequest(BaseModel):
    elo_overrides: dict[str, float] = Field(default_factory=dict)
    n_sims: int = Field(default=20000, ge=1000, le=100000)
    hypotheticals: list[dict] = Field(default_factory=list)


@app.post("/api/simulate")
def simulate(req: SimRequest):
    """What-if: re-run with Elo overrides and/or hypothetical results layered
    on top of real state. Stateless — nothing is persisted."""
    spec = service.spec_from_store(store())
    for team, elo in req.elo_overrides.items():
        if team not in spec["teams"]:
            raise HTTPException(400, f"unknown team {team!r}")
        spec["teams"][team]["elo"] = float(elo)
    state = store().engine_state()
    if req.hypotheticals:
        state = _merge_hypotheticals(state, req.hypotheticals)
    result = run_sims(spec=spec, state=state, n=req.n_sims, seed=2026)
    return result


def _merge_hypotheticals(state, hypotheticals):
    by_id = {m["id"]: m for m in state["matches"] if "id" in m}
    for h in hypotheticals:
        m = by_id.get(h.get("id"))
        if m:
            m.update(h)
    return state


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True),
              name="frontend")
