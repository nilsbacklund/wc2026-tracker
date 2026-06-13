"""Seed the 104-match schedule.

Group matches (1-72) are keyed by team pair — the engine conditions on real
group results by pair, not by id, so exact FIFA group numbering isn't
required (kickoff times get refined from football-data.org when available).
Knockout matches (73-104) use the verified FIFA numbering, which the bracket
tables depend on, with teams null until resolved.
"""
from wc2026.structure import BRACKET, GROUPS, GROUP_LETTERS, GROUP_FIXTURES

# Knockout match number -> stage label.
KO_STAGE = {**{m: "R32" for m in range(73, 89)},
            **{m: "R16" for m in range(89, 97)},
            **{m: "QF" for m in range(97, 101)},
            101: "SF", 102: "SF", 103: "third_place", 104: "final"}


def seed_matches(store):
    """Idempotent: upserts all 104 matches, preserving any existing
    results/kickoffs already stored."""
    existing = {m["id"]: m for m in store.all_matches()}

    # Group stage: 6 fixtures per group, matchdays 1/2/3 in pairs.
    for gi, g in enumerate(GROUP_LETTERS):
        names = GROUPS[g]
        for f, (i, j) in enumerate(GROUP_FIXTURES):
            mid = 1 + gi * 6 + f
            prev = existing.get(mid, {})
            store.upsert_match({
                "id": mid, "stage": "group", "grp": g,
                "matchday": f // 2 + 1,
                "home": names[i], "away": names[j],
                "kickoff_utc": prev.get("kickoff_utc"),
                "status": prev.get("status", "scheduled"),
                "home_score": prev.get("home_score"),
                "away_score": prev.get("away_score"),
                "minute": prev.get("minute"),
            })

    # Knockouts: structure only; teams filled in as the bracket resolves.
    for m in BRACKET:
        prev = existing.get(m, {})
        store.upsert_match({
            "id": m, "stage": KO_STAGE[m], "grp": None, "matchday": None,
            "home": prev.get("home"), "away": prev.get("away"),
            "kickoff_utc": prev.get("kickoff_utc"),
            "status": prev.get("status", "scheduled"),
            "home_score": prev.get("home_score"),
            "away_score": prev.get("away_score"),
            "minute": prev.get("minute"),
            "ko_winner": prev.get("ko_winner"),
            "ko_decided_by": prev.get("ko_decided_by"),
        })
