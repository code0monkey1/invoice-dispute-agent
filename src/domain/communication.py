"""Policy over saved invoice communications."""
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta, timezone

DUPLICATE_SEND_WINDOW = timedelta(minutes=30)


def was_sent_recently(
    communications: Iterable[Mapping],
    subject: str,
    body: str,
    *,
    now: datetime | None = None,
) -> bool:
    """Return whether the exact email has a recent successful outbound record."""
    cutoff = (now or datetime.now(timezone.utc)) - DUPLICATE_SEND_WINDOW
    for entry in communications:
        if entry.get("direction") != "outbound" or entry.get("subject") != subject or entry.get("content") != body:
            continue
        try:
            sent_at = datetime.fromisoformat(str(entry.get("timestamp", "")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        if sent_at >= cutoff:
            return True
    return False
