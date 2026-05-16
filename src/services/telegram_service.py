import os
import logging
import urllib.request
import urllib.parse
import json
from typing import Optional

logger = logging.getLogger("invoicechaser")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


def _send_to_chat(chat_id: str, message: str) -> bool:
    """Low-level Telegram sendMessage. Returns True on success."""
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }).encode()

    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                return True
            logger.error(f"Telegram API error: {result}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def send_telegram_notification(user_id: Optional[str], message: str) -> bool:
    """Send a notification to *user_id*'s Telegram chat.

    Returns True on success. Soft-fails (returns False, no exception) when the bot
    isn't configured globally or the user has not connected their Telegram chat —
    notifications are best-effort and must never break the calling flow.
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.info("Telegram bot token not configured — skipping notification")
        return False
    if not user_id:
        logger.info("No user_id provided for Telegram notification — skipping")
        return False

    # Local import to avoid a circular import at module load.
    from src.db import get_user

    user = get_user(user_id)
    chat_id = (user or {}).get("telegram_chat_id")
    if not chat_id:
        logger.info(f"User {user_id} has no telegram_chat_id — skipping notification")
        return False

    ok = _send_to_chat(chat_id, message)
    if ok:
        logger.info(f"Telegram notification sent to user {user_id}")
    return ok


def send_telegram_to_chat(chat_id: str, message: str) -> bool:
    """Direct send to a specific chat_id. Used during the connect handshake
    before we've persisted the chat_id to a user record."""
    return _send_to_chat(chat_id, message)


def set_telegram_webhook(webhook_url: str, secret_token: Optional[str] = None) -> dict:
    """Register *webhook_url* with Telegram. Idempotent. Returns the API response."""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not configured")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    params: dict = {"url": webhook_url, "allowed_updates": json.dumps(["message"])}
    if secret_token:
        params["secret_token"] = secret_token
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())
