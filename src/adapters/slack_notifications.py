"""Free Slack incoming-webhook alerts containing only Sentry event references."""
import json
import re
import threading
import time
import urllib.request
from urllib.error import HTTPError
from collections import deque
from urllib.parse import urlencode, urlsplit


class SlackNotifications:
    def __init__(self, webhook_url, organization, projects, *, environment="development"):
        url = urlsplit(webhook_url)
        self._enabled = bool(url.scheme == "https" and url.netloc == "hooks.slack.com"
                             and url.path.startswith("/services/") and re.fullmatch(r"[a-z0-9-]+", organization))
        self._url = webhook_url
        self._organization = organization
        self._projects = projects
        self._environment = environment
        self._queue = deque(maxlen=100)
        self._seen = deque(maxlen=1000)
        self._lock = threading.Lock()
        self._drain_lock = threading.Lock()
        self._next_send = 0.0

    def enqueue(self, event, *, source="server"):
        event_id = event.get("event_id", "")
        if not self._enabled or not re.fullmatch(r"[a-f0-9]{32}", event_id) or not self._projects.get(source):
            return
        # Never retain event messages, exceptions, requests, users or payloads.
        metadata = {"event_id": event_id, "source": source,
                    "environment": event.get("environment") or self._environment}
        with self._lock:
            if event_id in self._seen:
                return
            self._seen.append(event_id)
            self._queue.append(metadata)

    def enqueue_browser(self, event_id):
        self.enqueue({"event_id": event_id}, source="frontend")

    def flush(self):
        # Never wait behind another request's drain or sleep through a Slack
        # cooldown. Keep the event queued for a later invocation instead.
        if not self._drain_lock.acquire(blocking=False):
            return
        try:
            if time.monotonic() < self._next_send:
                return
            with self._lock:
                if not self._queue:
                    return
                event = self._queue.popleft()
            query = urlencode({"project": self._projects[event["source"]], "query": f"id:{event['event_id']}"})
            link = f"https://{self._organization}.sentry.io/issues/?{query}"
            environment = re.sub(r"[^a-zA-Z0-9_.-]", "", str(event["environment"]))[:32]
            text = f"InvoiceChaser {environment}: {event['source']} error\n<{link}|View in Sentry>"
            request = urllib.request.Request(self._url, data=json.dumps({"text": text}).encode(),
                                             headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=2) as response:
                    response.read()
                self._next_send = time.monotonic() + 1
            except Exception as exc:
                # A later invocation can retry. Never log the credential-bearing
                # URL or create a recursive Sentry/Slack error about delivery.
                delay = 5.0
                if isinstance(exc, HTTPError) and exc.code == 429:
                    try:
                        delay = min(86400, max(1, float(exc.headers.get("Retry-After", "30"))))
                    except (ValueError, TypeError):
                        delay = 30.0
                self._next_send = time.monotonic() + delay
                with self._lock:
                    self._queue.appendleft(event)
                return
        finally:
            self._drain_lock.release()
