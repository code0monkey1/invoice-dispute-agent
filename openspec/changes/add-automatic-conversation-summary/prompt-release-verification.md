# Prompt and sequence gate release — 2026-11-14

[PR #30](https://github.com/code0monkey1/invoice-dispute-agent/pull/30) merged to main as `6c34e0d3557f543a00b68bbf89cf963ba3ce1902`. Prompt commit `c6e0ed59fc1c45f759873ab8c35366eaaa304079` was committed only after local automated, live golden and holdout checks passed.

Production: https://invoice-chaser-chi.vercel.app

Vercel deployment `dpl_7Zfb6rygUSqtXwUavMDD8zYxqK33`: https://invoice-chaser-d0habqcct-code0monkey1s-projects.vercel.app. Verified READY, production target, canonical alias deployment ID and Git metadata matching the merged SHA. Public health reports healthy persistent PostgreSQL checkpoints.

## Quality and verification

[Trusted CI run](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43572060889) passed all unchanged 85% cohort gates: 19/20 singles (95%), 7/8 complete sequences (87.5%) and 28/31 checkpoints (90.3%). Three rate-limited checkpoints counted as failures; the other failed single was an attribution error. No threshold or fixture was weakened. Prompt and both fixture hashes match the tested commit. Protected backend, frontend, golden-set and summary-golden-set checks all succeeded before merge, without an administrator bypass. The push-to-main test workflow also succeeded.

Local evidence before commit: 19/20 singles, 8/8 sequences, 31/31 checkpoints; two additional holdout sequences passed all eight checkpoints. Service/eval tests 63 passed; full backend 496 passed with 13 environment-dependent skips; frontend 172 passed with six existing skips; lint/build, strict OpenSpec validation and independent review passed. Existing Pydantic and bundle-size warnings remain.

## Production checks

An owned disposable guest invoice with an invalid recipient address had its conversation and pending polite-reminder approval committed before deployment, without generating a summary. After deployment, it passed:

- Restoration of the same earlier user message and pending approval.
- Lazy summary creation and unchanged version/timestamp reuse.
- A committed synthetic client reply leaving the saved summary unchanged/stale until the next opening POST, then a successful cumulative refresh.
- Saved summary/history agreement, compact summary/dashboard responses, no internal storage ID in summary text, and cross-owner 404.
- No outbound delivery records and no email sending.

The new deployment's last-15-minute error/fatal scan returned zero records with no excluded intervals. Evidence: `/tmp/invoice-summary-prompt-production-evidence.json`, `/tmp/invoice-summary-prompt-final-production-proof.json`, `/tmp/invoice-summary-prompt-production-inspect.json`, `/tmp/invoice-summary-prompt-production-alias.json`, `/tmp/invoice-summary-prompt-release-deployments.json`, `/tmp/invoice-summary-prompt-production-errors.jsonl`, and `/tmp/invoice-summary-prompt-final-ci/summary-latest.json`. Temporary test session cookies were removed after verification. Original local user edits were preserved byte-for-byte.

## What changed

The earlier prompt generally requested cumulative summaries. The revised prompt explicitly carries forward conversation attribution, current balances, payment corrections, original/corrected/withdrawn promises and unresolved objection details, while separating follow-up dates from payment promises. The new evaluation independently checks every intermediate summary against cumulative authoritative history and prevents strong single-summary scores from hiding sequence failures.

Production source collection and generation timing remain unchanged: saved summaries are reused, and changed conversations are rebuilt on opening. This release prepares and verifies the prompt for incremental inputs; database coverage checkpoints and delta-only production retrieval remain a separate backend implementation. No schema migration or eager backfill was performed.

## Rollback

Redeploy the prior application commit `29c395aa3f1128ac9bfbd6593be5456fba577e33`, previous ready production deployment https://invoice-chaser-hs3298ncp-code0monkey1s-projects.vercel.app (`dpl_7PECSMqmZxoCwjARYcjxqoLpcWbp`), or revert PR #30 through the protected branch. Retain Supabase invoices, communications, summaries and checkpoints.
