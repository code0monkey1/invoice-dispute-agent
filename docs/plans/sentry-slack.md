# Sentry and Slack monitoring

Capture backend exceptions, HTTP 5xx responses, and error logs through the Python
SDK. Initialize before the agent and database adapters so startup failures are
included. Capture browser exceptions, React 19 render errors, and handled API
network/server failures through the React SDK. Keep expected 4xx responses out of
issues. Error sampling is 100%; traces sample 10% in production and 100% locally.
Sanitized structured logs are enabled; replay and AI prompt recording are disabled.

Use explicit backend integrations to avoid collecting LLM prompts. Strip request
bodies, headers, query strings, user data, log arguments and stack locals. Keep
stack locations, exception types, environment and release for diagnosis. Upload
hidden frontend source maps only when Sentry build credentials are available;
delete maps from the published build in every case.

Use free Slack bot notifications linked to Sentry events, with native
Sentry email alerts for grouped new issues and regressions. The user declined the
paid Sentry plan required by the native Slack integration.
The organization is `referfee`, and workspace is Software-Factory (`T0CDB5RT4TH`).
The destination is `#invoicechaser-alerts` (`C0CJJPTLWM9`), with the installed
`InvoiceChaser Alerts` app (`A0CKKBJDQ9E`). Live completion requires a release
through a checked PR, and observed backend/browser smoke issues in Sentry and
Slack. No permanent public error-trigger route is added.

Implementation and verification:

1. Add SDK dependencies and tests that exercise real SDK events with an in-memory
   transport. Cover handled/unhandled backend failures, 4xx filtering and privacy.
2. Implement backend initialization and browser reporting with tests for network,
   server, upload and invalid JSON failures. Wire React root handlers.
3. Configure source maps, document environment variables and provide an explicit
   command-line smoke test. Configure accounts when access is available.
4. Run full pytest, frontend tests, lint and build; inspect the diff. Release via
   PR and verify production health, Sentry issues and Slack delivery when access
   and required configuration are available.

No prompts, agent tools, domain policy or evaluation thresholds change.

## Verification to date

- Created dedicated `invoice-dispute-agent-server` and `invoice-dispute-agent-frontend`
  projects after user authorization; existing ReferMe projects were left alone.
- Configured DSNs locally and production variables in Vercel `invoice-chaser`.
- Saved an `org:ci` build token to Vercel as Secret. An initial unused token was
  revoked after the CLI printed it; only the privately captured replacement remains.
- Backend live Uvicorn app smoke: `INVOICE-DISPUTE-AGENT-SERVER-1` received.
- Frontend actual entry-point/React lifecycle smoke in jsdom:
  `INVOICE-DISPUTE-AGENT-FRONTEND-3` received. Temporary triggers removed.
- Authenticated local source-map upload succeeded; zero `.map` files in output.
- Full checks after bot support and synchronization with main: 1011 backend
  tests passed, 13 skipped; 190 frontend tests passed; lint/build passed.
  Existing Pydantic/JWT test warnings and bundle-size warning remain.
- Installed the requested official Slack skills plugin globally, outside Git.
  Its official docs say Codex installation does not include Slack MCP connectivity.
- Independent review identified provider-error payload and singular invoice-page
  URL/transaction leaks. Added regression tests and fixed both; arbitrary exception
  values are excluded. Added a bounded request-end drain for Vercel invocations.
- Summary read/refresh exceptions now emit error events while preserving their
  existing fail-open responses; both paths have regression coverage.
- Created active alert workflow `6360535`, scoped only to the two new projects,
  for first-seen errors and regressions, with email to the verified Sentry user.
  Disabled the two newly created default high-priority workflows to avoid duplicates.
  Native Slack integration was omitted because the user requires a free plan.
- Added a free app-to-Slack notification adapter and browser event-ID-only relay.
  Slack delivery is best-effort; Sentry email remains the grouped-alert fallback.
- Preview build is Ready; preview API lacks all environment variables and fails
  startup on missing GROQ_API_KEY. Production configuration exists separately.
- Slack CLI authenticated to Software-Factory; app and channel provisioned.
  Saved the bot token as a Vercel Production Secret, channel ID as configuration,
  and enabled the frontend relay for the next production build.
- November 18 live backend and actual React lifecycle errors reached Sentry.
  Slack acknowledged both deliveries in the configured channel. Local-only
  triggers were removed. No channel-history access was granted.
- Final focused independent review found no actionable issues; 83 targeted
  Slack/Sentry/eval invariant tests passed.
- PR #36 at f705a37 passed all live gates. A later agent evaluation failed two
  placeholder-tone cases, with level 2 below its baseline. Summary gates passed.
  Preserve thresholds and require current gates before release.
- Pending: final CI checks, reviewed PR release approval, production health,
  production Slack delivery and production source-map verification.
