"""Command-line entry points.

    python -m wc2026_backend init           # create db + seed 104 fixtures
    python -m wc2026_backend import-elo      # fetch live eloratings.net
    python -m wc2026_backend fetch           # ESPN ingest + Elo + resim
    python -m wc2026_backend add-result A B 2 1 [--ko WINNER] [--minute 60] [--live]
    python -m wc2026_backend resim [N]
    python -m wc2026_backend show            # latest odds table
    python -m wc2026_backend migrate         # run SQL migrations on Supabase
    python -m wc2026_backend backfill        # ingest all match days so far
    python -m wc2026_backend rebuild-history # one odds snapshot per played match
    python -m wc2026_backend importance      # rank upcoming matches by impact

With SUPABASE_DB_URL set (e.g. in .env) every command targets Supabase
Postgres; otherwise a local SQLite db. --db forces a specific SQLite path.
"""
import argparse
import os
import sys

from . import config  # noqa: F401 — loads .env on import
from .fixtures import seed_matches
from .store import Store
from .store_factory import get_store
from . import service


def _show(store, top=16):
    snap = store.latest_snapshot()
    if not snap:
        print("no snapshot yet — run `fetch` or `resim`")
        return
    probs = snap["probs"]
    print(f"snapshot #{snap['id']}  trigger={snap['trigger']}  "
          f"n={snap['n_sims']}  {snap['ts']}\n")
    print(f"{'Team':<14}{'Champ%':>8}{'Final%':>8}{'Top4%':>8}{'QF%':>7}"
          f"{'R16%':>7}{'Adv%':>7}")
    print("-" * 59)
    for team in sorted(probs, key=lambda t: probs[t]["champ"], reverse=True)[:top]:
        p = probs[team]
        print(f"{team:<14}{p['champ']:>8.1f}{p['final']:>8.1f}{p['top4']:>8.1f}"
              f"{p['qf']:>7.1f}{p['r16']:>7.1f}{p['advance']:>7.1f}")


def _migrate():
    """Run supabase/migrations/*.sql against SUPABASE_DB_URL (Postgres)."""
    dsn = os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        sys.exit("SUPABASE_DB_URL not set (put it in .env)")
    try:
        import psycopg
    except ImportError:
        sys.exit("psycopg not installed — run: uv pip install -e '.[supabase]'")
    from pathlib import Path
    mig_dir = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
    files = sorted(mig_dir.glob("*.sql"))
    if not files:
        sys.exit(f"no migrations in {mig_dir}")
    with psycopg.connect(dsn, autocommit=True) as conn:
        for f in files:
            conn.execute(f.read_text())
            print(f"applied {f.name}")
    print(f"migrated {len(files)} file(s)")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="wc2026_backend")
    parser.add_argument("--db", default=None, help="SQLite path")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")
    sub.add_parser("import-elo")
    sub.add_parser("fetch")
    sub.add_parser("show")
    sub.add_parser("migrate")
    sub.add_parser("rebuild-history")
    sub.add_parser("importance")
    sub.add_parser("bracket")
    p_backfill = sub.add_parser("backfill")
    p_backfill.add_argument("--start", default=service.TOURNAMENT_START)
    p_backfill.add_argument("--end", default=None)
    p_resim = sub.add_parser("resim")
    p_resim.add_argument("n", nargs="?", type=int, default=20000)
    p_add = sub.add_parser("add-result")
    p_add.add_argument("home")
    p_add.add_argument("away")
    p_add.add_argument("home_score", type=int)
    p_add.add_argument("away_score", type=int)
    p_add.add_argument("--ko", help="winner team name (knockout match)")
    p_add.add_argument("--decided-by", default="regular",
                       choices=["regular", "et", "pens"])
    p_add.add_argument("--minute", type=int)
    p_add.add_argument("--live", action="store_true",
                       help="mark in_play instead of finished")

    args = parser.parse_args(argv)

    if args.cmd == "migrate":
        _migrate()
        return

    store = Store(args.db) if args.db else get_store()
    backend = type(store).__name__

    if args.cmd == "init":
        seed_matches(store)
        where = getattr(store, "path", backend)
        print(f"seeded {len(store.all_matches())} matches into {where}")
    elif args.cmd == "import-elo":
        ratings = service.import_elo(store)
        print(f"imported {len(ratings)} Elo ratings from eloratings.net")
    elif args.cmd == "add-result":
        match = store.match_by_teams(args.home, args.away)
        if not match:
            sys.exit(f"no fixture for {args.home} vs {args.away}")
        if args.home == match["home"]:
            hs, as_ = args.home_score, args.away_score
        else:
            hs, as_ = args.away_score, args.home_score
        row = dict(match, status="in_play" if args.live else "finished",
                   home_score=hs, away_score=as_, minute=args.minute)
        if args.ko:
            row["ko_winner"] = args.ko
            row["ko_decided_by"] = args.decided_by
        store.upsert_match(service._to_upsert(row))
        service.apply_elo_updates(store)
        out = service.resimulate(store, trigger="manual", match_id=match["id"])
        print(f"recorded; snapshot #{out['snapshot_id']}")
        _show(store)
    elif args.cmd == "fetch":
        changed = service.ingest_espn(store)
        print(f"ESPN: {len(changed)} matches changed {changed}")
        updated = service.apply_elo_updates(store)
        if updated:
            print(f"Elo updated for matches {updated}")
        out = service.resimulate(store, trigger="scheduled")
        print(f"snapshot #{out['snapshot_id']}")
        _show(store)
    elif args.cmd == "backfill":
        changed = service.backfill_espn(store, args.start, args.end)
        print(f"backfill: {len(changed)} matches changed {sorted(changed)}")
        updated = service.apply_elo_updates(store)
        if updated:
            print(f"Elo updated for matches {sorted(updated)}")
        out = service.resimulate(store, trigger="scheduled")
        print(f"snapshot #{out['snapshot_id']}")
        _show(store)
    elif args.cmd == "resim":
        out = service.resimulate(store, n=args.n, trigger="manual")
        print(f"snapshot #{out['snapshot_id']} ({args.n} sims)")
        _show(store)
    elif args.cmd == "rebuild-history":
        count = service.rebuild_history(store)
        print(f"rebuilt history: 1 baseline + {count} per-match snapshots")
        _show(store)
    elif args.cmd == "importance":
        data = service.compute_and_store_importance(store)
        print(f"computed importance for {len(data['matches'])} upcoming matches:")
        for m in sorted(data["matches"],
                        key=lambda x: x["total"]["advance"], reverse=True)[:8]:
            print(f"  {m['home']} v {m['away']}  "
                  f"advance-impact {m['total']['advance']:.1f}  "
                  f"title-impact {m['total']['champ']:.2f}")
    elif args.cmd == "bracket":
        data = service.compute_and_store_bracket(store)
        print(f"computed most-likely bracket ({len(data['r32'])} R32 pairings):")
        for r in data["r32"]:
            print(f"  M{r['match']}: {r['home']} v {r['away']}")
    elif args.cmd == "show":
        _show(store)

    store.close()


if __name__ == "__main__":
    main()
