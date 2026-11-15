"""The Gmail adapter receives persistence instead of reaching into storage."""

from types import SimpleNamespace


def test_refreshed_tokens_are_saved_through_the_injected_callback(monkeypatch):
    from src.services import gmail_service

    saved = []
    credentials = SimpleNamespace(
        expired=True,
        refresh_token="refresh-token",
        token="stale-token",
    )

    def refresh(_request):
        credentials.token = "fresh-token"

    credentials.refresh = refresh
    google_service = SimpleNamespace()
    monkeypatch.setattr(gmail_service, "Credentials", lambda **_kwargs: credentials)
    monkeypatch.setattr(gmail_service, "build", lambda *_args, **_kwargs: google_service)

    service = gmail_service.GmailService(
        "user-1",
        "access-token",
        "refresh-token",
        lambda user_id, access, refresh: saved.append((user_id, access, refresh)),
    )

    assert service.service is google_service
    assert saved == [("user-1", "fresh-token", "refresh-token")]
