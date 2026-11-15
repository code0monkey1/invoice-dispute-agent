"""Per-process request limits (a sliding minute per caller and action)."""
import time

from fastapi import HTTPException

RATE_LIMITS: dict[str, list[float]] = {}
CHAT_LIMIT_PER_MINUTE = 20
SUMMARY_LIMIT_PER_MINUTE = 10
PARSE_LIMIT_PER_MINUTE = 8


def enforce_rate_limit(key: str, action: str, limit: int) -> None:
    now = time.time()
    window_start = now - 60
    bucket_key = f"{action}:{key}"
    hits = [ts for ts in RATE_LIMITS.get(bucket_key, []) if ts >= window_start]
    if len(hits) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit reached. Please wait a minute and try again.")
    hits.append(now)
    RATE_LIMITS[bucket_key] = hits
