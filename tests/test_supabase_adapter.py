"""The legacy database import remains the exact Supabase adapter during migration."""


def test_legacy_database_module_is_the_supabase_adapter(monkeypatch):
    import src.db as legacy
    from src.adapters import supabase

    assert legacy is supabase

    sentinel = object()
    monkeypatch.setattr(legacy, "_supabase_rest_request", sentinel)
    assert supabase._supabase_rest_request is sentinel
