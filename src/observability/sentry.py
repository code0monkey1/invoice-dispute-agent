"""Sentry composition and the telemetry privacy boundary (no business payloads)."""
import logging
import os
import re
from urllib.parse import urlsplit, urlunsplit

import sentry_sdk
from sentry_sdk.integrations.atexit import AtexitIntegration
from sentry_sdk.integrations.dedupe import DedupeIntegration
from sentry_sdk.integrations.excepthook import ExcepthookIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.threading import ThreadingIntegration


def clean_text(value):
    text = str(value)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[Filtered]", text)
    text = re.sub(r"(?i)(bearer\s+|(?:token|secret|password|code|api_key)[=:]\s*)[^\s&,]+", r"\1[Filtered]", text)
    return text


def clean_url(value):
    parts = urlsplit(str(value))
    path = re.sub(r"(/invoices?/)(?!parse(?:/|$)|upload(?:/|$)|generated(?:/|$))[^/]+", r"\1:id", parts.path)
    return urlunsplit((parts.scheme, parts.netloc.split("@")[-1], path, "", ""))


def scrub_event(event, hint):
    for key in ("user", "extra", "breadcrumbs"):
        event.pop(key, None)
    if "request" in event:
        request = event["request"]
        event["request"] = {key: clean_url(value) if key == "url" else value
                            for key, value in request.items() if key in {"url", "method"}}
    # Log templates retain grouping without interpolated invoice IDs or provider bodies.
    if "logentry" in event:
        entry = event["logentry"]
        event["logentry"] = {"message": clean_text(entry.get("message", "Application error"))}
    if "message" in event:
        event["message"] = clean_text(event["message"])
    for exception in event.get("exception", {}).get("values", []):
        # Provider exceptions can embed entire failed rows, prompts or replies.
        # Retain only our deliberately public smoke marker; types and stack
        # locations still identify every other fault without arbitrary values.
        value = str(exception.get("value", ""))
        exception["value"] = value if re.fullmatch(r"Sentry test error InvoiceChaser (backend|frontend) \d{8}", value) else "[Filtered exception message]"
        for frame in exception.get("stacktrace", {}).get("frames", []):
            frame.pop("vars", None)
    return event


def flush_sentry():
    if sentry_sdk.get_client().is_active():
        sentry_sdk.flush(timeout=2)


def scrub_transaction(event, hint):
    scrub_event(event, hint)
    event["transaction"] = clean_url(event.get("transaction", "request"))
    for span in event.get("spans", []):
        span["data"] = {}
        span["description"] = span.get("op", "operation")
    return event


def scrub_log(log, hint):
    attributes = log.get("attributes", {})
    # Only first-party log templates are useful here. Third-party SDK logs can
    # include response bodies and prompt content even at warning level.
    if not str(attributes.get("logger.name", "")).startswith("invoicechaser"):
        return None
    log["body"] = clean_text(attributes.get("sentry.message.template") or log.get("body", ""))
    log["attributes"] = {key: value for key, value in attributes.items()
                         if key.startswith("code.") or key in {"logger.name", "sentry.environment", "sentry.release"}}
    return log


def initialize_sentry(environ=None, *, transport=None):
    env = os.environ if environ is None else environ
    if not env.get("SENTRY_DSN"):
        return None
    environment = env.get("SENTRY_ENVIRONMENT") or env.get("VERCEL_ENV") or "development"
    return sentry_sdk.init(
        dsn=env["SENTRY_DSN"],
        environment=environment,
        release=env.get("SENTRY_RELEASE") or env.get("VERCEL_GIT_COMMIT_SHA"),
        sample_rate=1.0,
        traces_sample_rate=0.1 if environment in {"production", "preview"} else 1.0,
        enable_logs=True,
        data_collection={
            "user_info": False, "http_bodies": [], "stack_frame_variables": False,
            "frame_context_lines": 0, "cookies": {"mode": "off"},
            "http_headers": {"request": {"mode": "off"}},
            "url_query_params": {"mode": "off"}, "gen_ai": {"inputs": False, "outputs": False},
            "database_query_data": False,
        },
        include_local_variables=False,
        include_source_context=False,
        max_request_body_size="never",
        default_integrations=False,
        integrations=[
            FastApiIntegration(), StarletteIntegration(),
            LoggingIntegration(level=None, event_level=logging.ERROR, sentry_logs_level=logging.WARNING),
            DedupeIntegration(), ExcepthookIntegration(), ThreadingIntegration(), AtexitIntegration(),
        ],
        before_send=scrub_event,
        before_send_transaction=scrub_transaction,
        before_send_log=scrub_log,
        transport=transport,
        shutdown_timeout=2,
    )
