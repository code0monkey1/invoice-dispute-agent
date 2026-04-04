import os
import logging
import urllib.request
import urllib.parse
import json

logger = logging.getLogger("invoicechaser")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def send_telegram_notification(message: str) -> bool:
    """Send a notification message via Telegram Bot API. Returns True on success."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured — skipping notification")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }).encode()

    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                logger.info("Telegram notification sent")
                return True
            logger.error(f"Telegram API error: {result}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False
