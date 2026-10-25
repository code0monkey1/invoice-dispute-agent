"""Reply tracking through Resend Inbound.

Approved emails are sent from the freelancer's own Gmail with a Reply-To of
``inv-<token>@<RESEND_INBOUND_DOMAIN>`` (Resend's free ``<id>.resend.app``
address works). Resend posts every received email to our webhook; the token
in the recipient address finds the one invoice the reply belongs to, which
keeps every customer's mail separate without reading anyone's inbox.

Configuration is read from the environment on each call:
  RESEND_INBOUND_DOMAIN  e.g. abc123.resend.app
  RESEND_WEBHOOK_SECRET  the webhook's signing secret (whsec_...)
  RESEND_API_KEY         used to fetch the body of a received email
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import urllib.request
from email.utils import getaddresses

WEBHOOK_TOLERANCE_SECONDS = 5 * 60
RESEND_API = "https://api.resend.com"


def new_reply_token() -> str:
    """A random, lowercase, email-safe token (80 bits)."""
    return secrets.token_hex(10)


def inbound_domain() -> str | None:
    domain = (os.getenv("RESEND_INBOUND_DOMAIN") or "").strip().lower()
    return domain or None


def reply_address(token: str) -> str | None:
    domain = inbound_domain()
    return f"inv-{token}@{domain}" if domain else None


def parse_reply_token(addresses: list[str]) -> str | None:
    """Return the token from the first ``inv-<token>@<our domain>`` address, if any."""
    domain = inbound_domain()
    if not domain:
        return None
    pattern = re.compile(rf"^inv-([a-z0-9]+)@{re.escape(domain)}$")
    for _name, addr in getaddresses(addresses or []):
        match = pattern.match(addr.strip().lower())
        if match:
            return match.group(1)
    return None


def verify_webhook(body: bytes, headers, secret: str, now: float | None = None) -> None:
    """Verify a Svix-signed Resend webhook. Raises ValueError if it isn't genuine."""
    msg_id = headers.get("svix-id")
    timestamp = headers.get("svix-timestamp")
    signatures = headers.get("svix-signature")
    if not (msg_id and timestamp and signatures and secret):
        raise ValueError("missing webhook signature headers or secret")
    try:
        sent_at = int(timestamp)
    except ValueError as exc:
        raise ValueError("bad webhook timestamp") from exc
    if abs((now or time.time()) - sent_at) > WEBHOOK_TOLERANCE_SECONDS:
        raise ValueError("webhook timestamp outside tolerance")

    key = base64.b64decode(secret.removeprefix("whsec_"))
    signed = f"{msg_id}.{timestamp}.".encode() + body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    for candidate in signatures.split():
        version, _, sig = candidate.partition(",")
        if version == "v1" and hmac.compare_digest(sig, expected):
            return
    raise ValueError("webhook signature mismatch")


def fetch_received_email(email_id: str) -> dict:
    """Fetch a received email's content (text, html, headers) from Resend."""
    req = urllib.request.Request(
        f"{RESEND_API}/emails/receiving/{email_id}",
        headers={
            "Authorization": f"Bearer {os.getenv('RESEND_API_KEY', '')}",
            "User-Agent": "invoicechaser/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def plain_text(email: dict) -> str:
    """Best-effort plain text for a received email."""
    text = (email or {}).get("text")
    if text:
        return text
    html = (email or {}).get("html") or ""
    html = re.sub(r"(?is)<(script|style).*?</\1>", "", html)
    html = re.sub(r"(?i)<br\s*/?>|</p>", "\n", html)
    return re.sub(r"<[^>]+>", "", html).strip()
