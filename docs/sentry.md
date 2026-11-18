# Sentry monitoring

InvoiceChaser uses two projects in the `referfee` Sentry organization:

- `invoice-dispute-agent-server`: FastAPI exceptions, HTTP 5xx errors, error logs,
  warning/error structured logs and request traces.
- `invoice-dispute-agent-frontend`: React 19 root errors, browser exceptions and
  unhandled promises, plus handled API network/5xx/invalid JSON failures. Upload
  requests use the same reporting path as JSON requests.

Summary read/refresh fallbacks report their caught exceptions even though the
HTTP request can complete successfully with a pending/failed summary result.

Errors are sampled at 100%. Traces are sampled at 10% in production and 100% in
development. Expected HTTP 4xx responses and browser request cancellation do not
create issues. Missing DSNs disable monitoring. Tests use an in-memory transport;
ordinary test runs never send events to the live projects.

The Python SDK starts in `web/bootstrap.py` before the agent and database adapters
load. Each HTTP invocation drains queued telemetry with a two-second timeout after
error handling, so Vercel does not freeze it before delivery. Browser initialization
is the first import in `frontend/src/main.tsx`.
Existing domain/use-case boundaries and HTTP response contracts stay intact.

## Configuration

Copy the Sentry settings in `.env.example`. Python reads root `.env`; Vite reads
`frontend/.env`. DSNs are public ingestion identifiers, not API authentication
tokens. Use environment-specific DSNs if separate ingestion keys are desired.

Production is the existing Vercel project `invoice-chaser`. Configure:

| Variable | Purpose |
| --- | --- |
| `SENTRY_DSN` | Backend project ingestion |
| `VITE_SENTRY_DSN` | Frontend project ingestion |
| `SENTRY_ENVIRONMENT`, `VITE_SENTRY_ENVIRONMENT` | `production` on production deployments |
| `SENTRY_ORG` | `referfee` |
| `SENTRY_PROJECT` | `invoice-dispute-agent-frontend` for source map upload |
| `SENTRY_AUTH_TOKEN` | Build-only organization token with `org:ci`, stored as a Vercel Secret |

Vercel's commit SHA supplies both releases automatically. Outside Vercel, use
`SENTRY_RELEASE` and `VITE_SENTRY_RELEASE` to set the same version explicitly.

When the source-map upload variables are present, the Vite plugin generates hidden
maps, uploads them and deletes the local maps before publication. Builds without
upload credentials generate no source maps. The token is never exposed to client
code. Confirm fresh production errors are symbolicated after deployment; a local
development stack alone does not prove production symbolication.

## Data collection

Request/response bodies, cookies, headers, URL query strings, stack locals,
breadcrumbs, extra data and user identity are excluded from error reports.
Invoice IDs in API URLs are replaced with `:id`. Backend log arguments are omitted
and only first-party warning/error templates enter structured logs. Traces omit
span payload data. Arbitrary exception messages are replaced with a fixed marker;
exception types and stack locations remain available. Only fixed frontend API
failure messages and deliberately public smoke markers are allowlisted. This
prevents provider response bodies and failed database rows from entering issues.
Use Sentry server-side data scrubbing as an additional boundary.

Replay and AI prompt recording are not enabled. LangSmith remains the existing
agent-observability system. Sentry reports runtime faults; silent business-logic
mistakes still need tests or explicit failure reporting.

## Free Slack alerts

The user requires a free setup. Sentry's native Slack integration requires a paid
plan, so the app posts through the free Slack Web API instead. `InvoiceChaser
Alerts` (`A0CKKBJDQ9E`) is installed in `Software-Factory` (`T0CDB5RT4TH`) and
posts to `#invoicechaser-alerts` (`C0CJJPTLWM9`). Vercel Production has
`SLACK_BOT_TOKEN` as a server-only Secret, `SLACK_ALERT_CHANNEL=C0CJJPTLWM9`, and
`VITE_SLACK_ERROR_ALERTS=true` for the frontend build. These settings take effect
in the next production deployment. The app has `chat:write`, `channels:read` and
`channels:manage` scopes for posting and channel provisioning; it cannot read
channel history. No always-on bot hosting is needed.

For another installation, authorize a Slack app with `chat:write`, add it to the
destination channel, and configure the same variables. An incoming webhook is
also supported through server-only `SLACK_WEBHOOK_URL` when bot credentials are
absent. Never prefix either credential with `VITE_`.

Backend Sentry events enqueue only their event ID, source and environment after
scrubbing. The request-end drain posts a generic message with an event-specific
Sentry link. Browser events send only their Sentry event ID to
`POST /api/monitoring/browser-error`; the route checks origin, accepts at most 1KB,
validates the ID and limits each caller to 10 reports per minute. No Slack
credential or business payload enters the browser.

Slack notifications are best-effort per error occurrence, with a bounded
per-process queue, duplicate-event suppression and retry on a later invocation.
Queue state is not durable across Vercel cold starts; Slack/network failures can
lose notifications. Sentry remains the tracker, and email alerts remain enabled
for grouped new issues and regressions. Workflow `6360535` ("InvoiceChaser — new
issues and regressions") covers both projects and sends email to the verified
Sentry account. The two project-creation default high-priority workflows are
disabled to avoid overlapping notifications.

Verify fresh backend and browser errors appear in Sentry and post their Sentry
links in Slack. An installed Slack desktop app or coding skills plugin does not
prove delivery. On November 18, 2026, real local backend and React lifecycle smoke
errors reached Sentry and Slack returned `ok: true` for both messages in the
configured channel. Production delivery still requires the reviewed deployment.
Slack's skills plugin currently installs only skills on Codex;
see the [official guide](https://docs.slack.dev/ai/slack-skills-plugin/).

## Verification

Run the repository's full checks before merging:

```sh
.venv/bin/python -m pytest -q
cd frontend
npm test
npm run lint
npm run build
```

Live smoke errors must go through the app's actual initialization. Use a temporary
local-only route before the SPA catch-all for the backend, and a temporary error
in a rendered React component for the frontend. Do not ship public crash routes.
Check issue title, environment, release, request-data exclusion and stack frames
in Sentry, then remove triggers. After merge, verify Vercel is Ready,
`/api/health` reports healthy Postgres checkpoints, and the SPA/assets load.
