"""Load a repo-root .env into the environment (no external dependency).

Reads KEY=VALUE lines (ignoring comments/blanks) and does NOT override values
already present in the real environment, so deploy-platform secrets always win
over a local .env. Importing this module runs the load once.

Recognized keys: SUPABASE_DB_URL (Postgres connection -> use Supabase instead
of SQLite), FOOTBALL_DATA_TOKEN (authoritative results), WC2026_DISABLE_POLLER.
"""
import os
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def load_env(path=ENV_PATH):
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()
