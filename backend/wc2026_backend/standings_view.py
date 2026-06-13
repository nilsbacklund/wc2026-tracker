"""Current group standings from real results only (for the standings table).

This is display state, not simulation: it ranks teams on the matches played
so far using FIFA criteria (points, GD, GF, then head-to-head among ties).
Unplayed matches simply don't contribute.
"""
from wc2026.structure import GROUPS, GROUP_LETTERS


def current_standings(store):
    played = {}
    for m in store.all_matches():
        if (m["stage"] == "group" and m["status"] in ("finished", "in_play")
                and m["home_score"] is not None):
            played.setdefault(m["grp"], []).append(m)

    out = {}
    for g in GROUP_LETTERS:
        rows = {t: {"team": t, "played": 0, "w": 0, "d": 0, "l": 0,
                    "gf": 0, "ga": 0, "gd": 0, "pts": 0} for t in GROUPS[g]}
        h2h = []
        for m in played.get(g, []):
            h, a, hs, as_ = m["home"], m["away"], m["home_score"], m["away_score"]
            h2h.append((h, a, hs, as_))
            for t, gf, ga in ((h, hs, as_), (a, as_, hs)):
                r = rows[t]
                r["played"] += 1
                r["gf"] += gf
                r["ga"] += ga
                r["gd"] += gf - ga
                if gf > ga:
                    r["w"] += 1
                    r["pts"] += 3
                elif gf == ga:
                    r["d"] += 1
                    r["pts"] += 1
                else:
                    r["l"] += 1
        out[g] = _rank(list(rows.values()), h2h)
    return out


def _rank(rows, h2h):
    def key(r):
        return (r["pts"], r["gd"], r["gf"])
    ordered = sorted(rows, key=key, reverse=True)
    # Head-to-head among teams exactly tied on (pts, gd, gf).
    result = []
    i = 0
    while i < len(ordered):
        tied = [r for r in ordered if key(r) == key(ordered[i])]
        if len(tied) > 1:
            tied = _h2h_order(tied, h2h)
        result.extend(tied)
        i += len(tied)
    for pos, r in enumerate(result, 1):
        r["rank"] = pos
    return result


def _h2h_order(tied, h2h):
    names = {r["team"] for r in tied}
    mini = {r["team"]: [0, 0, 0] for r in tied}  # pts, gd, gf
    for h, a, hs, as_ in h2h:
        if h in names and a in names:
            for t, gf, ga in ((h, hs, as_), (a, as_, hs)):
                mini[t][0] += 3 if gf > ga else 1 if gf == ga else 0
                mini[t][1] += gf - ga
                mini[t][2] += gf
    return sorted(tied, key=lambda r: tuple(mini[r["team"]]), reverse=True)
