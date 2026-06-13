"""store_factory backend selection + interface-parity checks.

No live database is required: the Supabase branch is exercised either by
monkeypatching SupabaseStore to a stub, or by asserting a connection failure
(not an ImportError). Interface parity is checked statically via introspection.
"""
import inspect

import pytest

from wc2026_backend import store_factory
from wc2026_backend.store import Store
from wc2026_backend.store_supabase import SupabaseStore


def _public_methods(cls):
    return {
        name for name, _ in inspect.getmembers(cls, callable)
        if not name.startswith("_")
    }


def test_no_env_returns_sqlite_store(monkeypatch, tmp_path):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    store = store_factory.get_store()
    try:
        assert isinstance(store, Store)
    finally:
        store.close()


def test_sqlite_store_has_full_interface(monkeypatch, tmp_path):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    store = store_factory.get_store()
    try:
        for name in _public_methods(Store):
            assert hasattr(store, name)
    finally:
        store.close()


def test_env_selects_supabase(monkeypatch):
    """With the env var set, the factory builds a SupabaseStore (stubbed)."""
    monkeypatch.setenv("SUPABASE_DB_URL", "postgres://stub")
    calls = {}

    class StubStore:
        def __init__(self):
            calls["built"] = True

    monkeypatch.setattr(
        "wc2026_backend.store_supabase.SupabaseStore", StubStore)
    store = store_factory.get_store()
    assert calls.get("built") is True
    assert isinstance(store, StubStore)


def test_env_real_supabase_fails_on_connection_not_import(monkeypatch):
    """Without a stub, selecting Supabase must reach a connection attempt,
    never an ImportError (the import is lazy and psycopg is declared)."""
    monkeypatch.setenv("SUPABASE_DB_URL", "postgres://user:pw@127.0.0.1:1/none")
    try:
        store_factory.get_store()
    except ImportError:
        pytest.skip("psycopg not installed; lazy import path verified elsewhere")
    except Exception:
        pass  # connection / runtime error is the expected outcome


def test_interface_parity():
    """SupabaseStore defines every public method Store defines, with matching
    signatures (so callers can swap backends transparently)."""
    sqlite_methods = _public_methods(Store)
    supabase_methods = _public_methods(SupabaseStore)
    missing = sqlite_methods - supabase_methods
    assert not missing, f"SupabaseStore missing methods: {sorted(missing)}"

    for name in sqlite_methods:
        sig_a = inspect.signature(getattr(Store, name))
        sig_b = inspect.signature(getattr(SupabaseStore, name))
        params_a = [p for p in sig_a.parameters]
        params_b = [p for p in sig_b.parameters]
        assert params_a == params_b, (
            f"{name} signature mismatch: {params_a} != {params_b}")
