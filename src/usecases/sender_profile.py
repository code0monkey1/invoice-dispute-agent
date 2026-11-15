"""Sender-profile validation and patch semantics."""

import re
import urllib.parse

from src.ports import UserStore

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class InvalidSenderProfile(ValueError):
    pass


class SenderProfileUseCases:
    def __init__(self, users: UserStore):
        self._users = users

    def get(self, user_id: str) -> dict:
        user = self._users.get_user(user_id) or {}
        return user.get("sender_profile") or {}

    def update(self, user_id: str, incoming: dict) -> dict:
        email = incoming.get("your_email")
        if email and not _EMAIL_RE.match(email):
            raise InvalidSenderProfile("Invalid email format")

        logo_url = incoming.get("logo_url")
        if logo_url:
            parsed = urllib.parse.urlparse(logo_url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise InvalidSenderProfile("logo_url must be an http(s) URL")

        merged = {**self.get(user_id), **incoming}
        return self._users.update_user_sender_profile(user_id, merged)
