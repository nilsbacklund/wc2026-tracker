"""Goal-triggered live polling loop — the headline feature.

While a match is in play we poll ESPN every ~20s. When a score or status
changes (goal, kickoff, full time) we re-ingest, apply full-time Elo, and
re-simulate conditioned on the new state, writing a snapshot tagged with the
trigger. Off-hours we back off to a slow interval to spare the ESPN API.
"""
import asyncio
import logging
import time

from . import service
from .sources import espn

log = logging.getLogger("wc2026.live")

# Trigger priority: the most significant change in a cycle wins the snapshot.
TRIGGER_PRIORITY = {"goal": 3, "fulltime": 2, "kickoff": 1, "scheduled": 0}

# How close (seconds) a scheduled kickoff must be to warrant fast polling.
KICKOFF_WINDOW = 15 * 60


def _parse_kickoff(ts):
    """Parse an ISO kickoff string to epoch seconds, or None."""
    if not ts:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%MZ"):
        try:
            return time.mktime(time.strptime(ts, fmt)) - time.timezone
        except (ValueError, TypeError):
            continue
    return None


class LivePoller:
    """Owns the async polling task. Inject `fetch` for tests."""

    def __init__(self, store, fetch=None, fast_interval=20.0,
                 slow_interval=300.0, n_sims=20000):
        self.store = store
        self.fetch = fetch or espn.fetch_scoreboard
        self.fast_interval = fast_interval
        self.slow_interval = slow_interval
        self.n_sims = n_sims
        self._task = None

    async def start(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    async def stop(self):
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self):
        # One-time catch-up: ESPN's default scoreboard only returns today, so
        # on (re)start walk every past match day to ingest results that landed
        # while we were down. Idempotent — only genuine changes re-simulate.
        try:
            changed = await asyncio.to_thread(service.backfill_espn, self.store)
            if changed:
                await asyncio.to_thread(service.apply_elo_updates, self.store)
                # Rebuild the clean one-snapshot-per-match history so the odds
                # chart stays correct and self-heals after any downtime.
                await asyncio.to_thread(service.rebuild_history, self.store)
                log.info("startup backfill updated %d matches", len(changed))
            await self._refresh_importance()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("startup backfill failed")

        while True:
            try:
                await self.poll_once()
            except asyncio.CancelledError:
                raise
            except Exception:  # never let a transient error kill the loop
                log.exception("poll cycle failed")
            await asyncio.sleep(self._next_interval())

    def _next_interval(self):
        """Fast when a match is in play or kicks off within the window."""
        now = time.time()
        for m in self.store.all_matches():
            if m["status"] == "in_play":
                return self.fast_interval
            if m["status"] == "scheduled":
                ko = _parse_kickoff(m.get("kickoff_utc"))
                if ko is not None and 0 <= ko - now <= KICKOFF_WINDOW:
                    return self.fast_interval
        return self.slow_interval

    async def poll_once(self):
        """One cycle: fetch, ingest, classify, re-sim if anything changed.

        Returns {changed, trigger, snapshot_id}. Network/parse errors are
        swallowed (logged) so a single bad cycle never raises to callers.
        """
        try:
            events = await asyncio.to_thread(self.fetch)
        except Exception:
            log.exception("fetch failed")
            return {"changed": [], "trigger": None, "snapshot_id": None}

        # Capture pre-ingest state so we can classify what changed.
        before = {m["id"]: (m["status"], m["home_score"], m["away_score"])
                  for m in self.store.all_matches()}

        changed = service.ingest_espn(self.store, events)
        if not changed:
            return {"changed": [], "trigger": None, "snapshot_id": None}

        after = {m["id"]: m for m in self.store.all_matches()}
        trigger, match_id = self._classify(changed, before, after)

        # Only re-simulate on a real event (kickoff/goal/full time). A bare
        # "scheduled" trigger means nothing material changed (e.g. just the
        # live minute ticking) — updating the match row is enough; writing a
        # snapshot every poll cycle would flood the odds history.
        if trigger == "scheduled":
            return {"changed": changed, "trigger": None, "snapshot_id": None}

        service.apply_elo_updates(self.store)
        out = service.resimulate(self.store, n=self.n_sims,
                                 trigger=trigger, match_id=match_id)
        # A completed match changes the set of remaining fixtures, so refresh
        # the per-match importance ranking (best-effort; it's heavy).
        if trigger == "fulltime":
            await self._refresh_importance()
        return {"changed": changed, "trigger": trigger,
                "match_id": match_id, "snapshot_id": out["snapshot_id"]}

    async def _refresh_importance(self):
        try:
            await asyncio.to_thread(service.compute_and_store_importance,
                                    self.store)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("importance refresh failed")

    def _classify(self, changed, before, after):
        """Pick the most significant trigger among changed matches."""
        best = ("scheduled", None, -1)
        for mid in changed:
            new = after.get(mid)
            if new is None:
                continue
            old_status, old_hs, old_as = before.get(mid, (None, None, None))
            tag = self._tag(old_status, old_hs, old_as, new)
            rank = TRIGGER_PRIORITY[tag]
            if rank > best[2]:
                best = (tag, mid, rank)
        return best[0], best[1]

    @staticmethod
    def _tag(old_status, old_hs, old_as, new):
        """Classify a single match's transition."""
        status = new["status"]
        if status == "finished" and old_status != "finished":
            return "fulltime"
        if status == "in_play" and old_status != "in_play":
            return "kickoff"
        if status == "in_play" and (new["home_score"] != old_hs
                                    or new["away_score"] != old_as):
            return "goal"
        return "scheduled"
