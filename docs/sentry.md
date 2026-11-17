# Sentry monitoring

InvoiceChaser uses two projects in the `referfee` Sentry organization:

- `invoice-dispute-agent-server`: FastAPI exceptions, HTTP 5xx errors, error logs,
  warning/error structured logs and request traces.
- `invoice-dispute-agent-frontend`: React 19 root errors, browser exceptions and
  unhandled promises, plus handled API network/5xx/invalid JSON failures. Upload
  requests use the same reporting path as JSON requests.

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

## Slack alerts

Use Sentry's native Slack integration. It does not require Slack credentials in
the application. Connect workspace `Software-Factory` (`T0CDB5RT4TH`) under
Sentry organization settings, select an alert channel and grant the Sentry app
access to it. Then create an alert scoped to these two project issue streams,
triggered on first-seen issues and regressions, with the Slack channel action.
Keep email alerts enabled as a fallback. Private channels require inviting Sentry.

Workflow `6360535` ("InvoiceChaser — new issues and regressions") already covers
both projects and sends email to the verified Sentry account. Add Slack to this
workflow after authorization; retain its email action. The two project-creation
default high-priority workflows are disabled to avoid overlapping notifications.

Verify a fresh error in each project creates a Slack notification containing its
Sentry link. An installed Slack desktop app or coding skills plugin does not prove
this integration is connected. Slack's skills plugin currently installs only
skills on Codex; see the [official guide](https://docs.slack.dev/ai/slack-skills-plugin/).

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
