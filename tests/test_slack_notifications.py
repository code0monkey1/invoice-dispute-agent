import io
import json
from types import SimpleNamespace
from urllib.error import HTTPError, URLError

import pytest
from httpx import ASGITransport, AsyncClient

from web.app import Deps, create_app
from web.identity import Identity, get_caller


def test_slack_posts_only_safe_metadata_and_a_sentry_link(monkeypatch):
    from src.adapters.slack_notifications import SlackNotifications
    sent = []
    monkeypatch.setattr('urllib.request.urlopen', lambda request, timeout: sent.append(json.loads(request.data)) or io.BytesIO(b'ok'))
    notifier = SlackNotifications('https://hooks.slack.com/services/TEST/TEST/secret', 'referfee', {'server': '1', 'frontend': '2'})
    notifier.enqueue({'event_id': 'a' * 32, 'environment': 'production', 'exception': {'values': [{'value': 'private invoice data'}]}})
    notifier.flush()
    assert len(sent) == 1
    text = sent[0]['text']
    assert 'InvoiceChaser' in text and 'production' in text
    assert 'https://referfee.sentry.io/issues/' in text
    assert '?project=1&query=id%3A' + 'a' * 32 in text
    assert 'private' not in text and 'secret' not in text


def test_missing_webhook_disables_notifications(monkeypatch):
    from src.adapters.slack_notifications import SlackNotifications
    def unexpected(*args, **kwargs):
        raise AssertionError('disabled notifications must not use network')
    monkeypatch.setattr('urllib.request.urlopen', unexpected)
    notifier = SlackNotifications('', 'referfee', {})
    notifier.enqueue({'event_id': 'a' * 32})
    notifier.flush()


def test_failed_delivery_is_retried_without_changing_app_behavior(monkeypatch):
    from src.adapters.slack_notifications import SlackNotifications
    attempts = []
    now = [0.0]
    monkeypatch.setattr('src.adapters.slack_notifications.time.monotonic', lambda: now[0])
    def deliver(request, timeout):
        attempts.append(request)
        if len(attempts) == 1:
            raise URLError('unavailable')
        return io.BytesIO(b'ok')
    monkeypatch.setattr('urllib.request.urlopen', deliver)
    notifier = SlackNotifications('https://hooks.slack.com/services/TEST/TEST/secret', 'referfee', {'server': '1'})
    notifier.enqueue({'event_id': 'a' * 32})
    notifier.flush()
    now[0] += 6
    notifier.flush()
    assert len(attempts) == 2


def test_slack_retry_after_is_respected_without_blocking_requests(monkeypatch):
    from src.adapters.slack_notifications import SlackNotifications
    now = [0.0]
    attempts = []
    monkeypatch.setattr('src.adapters.slack_notifications.time.monotonic', lambda: now[0])
    def deliver(request, timeout):
        attempts.append(request)
        if len(attempts) == 1:
            raise HTTPError(request.full_url, 429, 'rate limited', {'Retry-After': '30'}, None)
        return io.BytesIO(b'ok')
    monkeypatch.setattr('urllib.request.urlopen', deliver)
    notifier = SlackNotifications('https://hooks.slack.com/services/TEST/TEST/secret', 'referfee', {'server': '1'})
    notifier.enqueue({'event_id': 'a' * 32})
    notifier.flush()
    notifier.flush()
    assert len(attempts) == 1
    now[0] = 31
    notifier.flush()
    assert len(attempts) == 2


@pytest.mark.asyncio
async def test_browser_notification_endpoint_validates_origin_payload_and_limits():
    from web.routers.monitoring import create_monitoring_router
    alerts = []
    deps = Deps(agent=None)
    deps.slack_notifications = SimpleNamespace(enqueue_browser=lambda event_id: alerts.append(event_id))
    app = create_app(deps, Identity('test-secret', store=lambda: None))
    app.include_router(create_monitoring_router(deps, get_caller))
    async with AsyncClient(transport=ASGITransport(app), base_url='http://test') as client:
        path = '/api/monitoring/browser-error'
        assert (await client.post(path, json={'event_id': 'a' * 32})).status_code == 403
        assert (await client.post(path, headers={'Origin': 'https://evil.test'}, json={'event_id': 'a' * 32})).status_code == 403
        assert (await client.post(path, headers={'Origin': 'http://test'}, json={'event_id': 'invalid'})).status_code == 400
        assert (await client.post(path, headers={'Origin': 'http://test'}, content='x' * 1025)).status_code == 413
        for _ in range(10):
            response = await client.post(path, headers={'Origin': 'http://test'}, json={'event_id': 'a' * 32})
            assert response.status_code == 202
        assert (await client.post(path, headers={'Origin': 'http://test'}, json={'event_id': 'b' * 32})).status_code == 429
    assert alerts == ['a' * 32] * 10
