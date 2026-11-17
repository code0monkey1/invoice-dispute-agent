# Test and dead-code review

Baseline: `2dab98c` (main). Scope: the backend and frontend in this repository.

## Selection rule

Following [Khorikov's four pillars](https://livebook.manning.com/book/unit-testing/chapter-4/v-3), retain tests that protect meaningful behavior, tolerate internal refactoring, give useful feedback and remain maintainable. A small financial or security rule can deserve exhaustive cases. A high test count alone is not a reason to delete tests.

Keep policy edge cases in domain tests, representative persistence checks at the adapter boundary, and critical journeys through the API or UI. Keep the API/OpenAPI contracts, architecture rules, golden wording, security cases and evaluation gates.

## Test decisions

| Change | Reason and remaining protection |
| --- | --- |
| Delete `test_supabase_adapter.py` | Both imports resolved to the same module; it tested Python alias identity rather than a migration contract. |
| Delete `test_ports.py` | Attribute-presence checks cannot validate signatures or adapter behavior; the service test checked its own fakes. Use cases, adapter tests and API journeys exercise the actual collaborators. |
| Replace `test_invoice_service.py` with `test_approval_usecases.py` | The service no longer exists. Retain seven approval persistence cases. Remove repeated payment bounds, escalation, settlement, field filtering and follow-up-state checks already covered by domain/use-case tests and API/real-graph journeys. Retain one rejected-date persistence case plus the hostile-date tests. |
| Remove the unused settled-status parameter | Both parameter values ran exactly the same body; settled-invoice protection remains. |
| Remove the malformed-base64 character-dropping assertion | It pinned a decoder quirk for IDs the application never generates. Public-ID round trips, Unicode and legacy/unreadable-ID fallback remain covered. |
| Replace three PDF snapshot suites with `templates.test.tsx` | Nine focused cases replace fourteen tests and 1,349 snapshot lines. Each template checks invoice facts, totals, dates, payment destination, optional sections and all 50 items in a long invoice. Font sizes, style objects and wrapper structure are free to change. These tests do not validate PDF layout or pagination. |
| Replace six skipped generator-page cases with three active journeys | Exercise real form, hooks and preview with PDF byte generation stubbed: save/download/navigation, upload failure, and download without persistence. Profile prefilling and invalid-form disabling are checked in the save journey; template options remain covered by `TemplatePicker.test.tsx`. |
| Delete `hooks/__tests__/invoiceFiles.test.tsx` | The active page journeys now verify metadata propagation and failure ordering through the real hook. Its parse case only checked a direct gateway passthrough; backend parser/API tests and dashboard upload tests remain. |

Collected cases: backend **1,024 → 1,004**; frontend **192 → 181**. This removes 31 cases while activating critical UI journeys. Conditional SPA tests run when `frontend/dist` exists; database integration tests still require a disposable `TEST_DATABASE_URL`.

## Dead code and comments

- Remove `init_db()` and its only caller: it never initialized anything. Keep `supabase/schema.sql` as the schema setup.
- Remove the uncalled Supabase SDK client factory/singleton and its dependency. Persistence uses the existing REST/storage transport.
- Remove uncalled `get_user_by_email` and Gmail history-ID persistence, unused `InboundMail`/`Clock` ports and runtime protocol decorators whose only consumers were the removed tests.
- Remove unused domain-helper re-exports. Placeholder tests import the owning domain module directly.
- Remove unused research/drafting prompt constants and their files. The four active escalation prompt files and conversation-summary prompt are unchanged.
- Remove completed-migration instructions and obsolete PDFViewer/cache commentary; correct README paths to the current use cases. Keep comments explaining security, approval ordering, retries and compatibility that still affects behavior.

Empty exception classes, protocol methods, Python package initializers and `InvoiceUploadMetadata` remain purposeful. The latter is a named schema in the published OpenAPI contract; an empty class body alone does not make code dead.

## Verification

Run from this worktree (Node 22):

```sh
.venv/bin/python -m pytest -q
cd frontend
npm test
npm run lint
npm run build
```

Additional checks:

- ASGI startup succeeds with imports of the external Supabase SDK explicitly blocked.
- All five active prompt inputs match main.
- Six temporary faults are detected by retained tests: removing payment clamping, removing the escalation cap, changing a payment destination, dropping line items, dropping uploaded metadata, and swallowing an upload failure. Source files are restored after each fault.
- The optional frontend coverage command already failed on main. Coverage thresholds and includes are unchanged. Reported lines improve from **51.38% to 85.76%**, statements **50.59% to 82.93%**, branches **42.65% to 79.02%**, and functions **41.90% to 71.42%**. The command still fails the existing thresholds; the test cleanup does not resolve that separate coverage gap.

Before merging, run the repository's trusted live CI evaluation gates (`golden-set` and `summary-golden-set`), using the dedicated evaluation organization. These are required by the changed adapter/bootstrap/prompt paths even though active prompts and tool behavior are preserved. No live-model quality result is claimed by this local verification.
