"""Account use cases are framework-free and depend only on injected stores."""

import pytest


class Users:
    def __init__(self):
        self.rows = {}
        self.upserts = []

    def upsert_user(self, **fields):
        self.upserts.append(fields)
        self.rows[fields["user_id"]] = {"id": fields["user_id"], **fields}
        return self.rows[fields["user_id"]]

    def get_user(self, user_id):
        return self.rows.get(user_id)

    def update_user_sender_profile(self, user_id, profile):
        self.rows.setdefault(user_id, {"id": user_id})["sender_profile"] = profile
        return profile


def test_plain_sign_in_does_not_replace_gmail_tokens():
    from src.usecases.auth import AuthUseCases

    users = Users()
    usecases = AuthUseCases(users, gmail_tokens=lambda _user_id: ("saved", "refresh"))

    result = usecases.persist_google_user(
        {"id": "u1", "email": "one@example.com", "name": "One"},
        access_token="profile-access",
        refresh_token="",
        send_granted=False,
    )

    assert users.upserts[0]["access_token"] is None
    assert users.upserts[0]["refresh_token"] is None
    assert result["gmail_connected"] is True


def test_sender_profile_patch_validates_and_merges():
    from src.usecases.sender_profile import InvalidSenderProfile, SenderProfileUseCases

    users = Users()
    users.rows["u1"] = {"id": "u1", "sender_profile": {"business_name": "Acme"}}
    usecases = SenderProfileUseCases(users)

    assert usecases.update("u1", {"your_email": "jane@acme.example"}) == {
        "business_name": "Acme",
        "your_email": "jane@acme.example",
    }
    with pytest.raises(InvalidSenderProfile, match="Invalid email"):
        usecases.update("u1", {"your_email": "not-an-email"})
    with pytest.raises(InvalidSenderProfile, match="http"):
        usecases.update("u1", {"logo_url": "file:///etc/passwd"})
