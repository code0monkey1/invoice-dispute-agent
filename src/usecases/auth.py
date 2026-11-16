"""Authentication account orchestration without HTTP or provider details."""

from collections.abc import Callable

from src.ports import UserStore


class AuthUseCases:
    def __init__(
        self,
        users: UserStore,
        gmail_tokens: Callable[[str], tuple[str, str] | None],
    ):
        self._users = users
        self._gmail_tokens = gmail_tokens

    def persist_google_user(
        self,
        profile: dict,
        *,
        access_token: str,
        refresh_token: str,
        send_granted: bool,
    ) -> dict:
        keep_tokens = send_granted and bool(refresh_token)
        self._users.upsert_user(
            user_id=profile["id"],
            email=profile["email"],
            name=profile.get("name", ""),
            picture=profile.get("picture", ""),
            access_token=access_token if keep_tokens else None,
            refresh_token=refresh_token if keep_tokens else None,
        )
        return self.present_user(profile)

    def present_user(self, user: dict) -> dict:
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name", ""),
            "picture": user.get("picture", ""),
            "gmail_connected": self._gmail_tokens(user["id"]) is not None,
        }

    def migrate_guest(self, guest_id: str, user_id: str) -> None:
        self._users.migrate_guest_to_user(guest_id, user_id)
