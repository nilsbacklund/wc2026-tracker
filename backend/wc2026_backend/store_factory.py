"""Store backend selection.

get_store() returns the persistence backend chosen by environment:
  - SUPABASE_DB_URL set  -> SupabaseStore (Postgres via psycopg 3)
  - otherwise            -> Store (local SQLite)

The SupabaseStore import is kept lazy (inside the branch) so psycopg is only
required when the Supabase backend is actually selected; SQLite-only runs need
no extra dependencies.
"""
import os

from .store import Store


def get_store():
    if os.environ.get("SUPABASE_DB_URL"):
        from .store_supabase import SupabaseStore
        return SupabaseStore()
    return Store()
