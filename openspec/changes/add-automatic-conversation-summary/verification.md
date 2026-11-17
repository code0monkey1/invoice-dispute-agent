# Release verification — 2026-11-14

- Feature merged in [PR #29](https://github.com/code0monkey1/invoice-dispute-agent/pull/29), merge commit `29c395aa3f1128ac9bfbd6593be5456fba577e33`.
- Production: https://invoice-chaser-chi.vercel.app
- Vercel deployment `dpl_7PECSMqmZxoCwjARYcjxqoLpcWbp`, https://invoice-chaser-hs3298ncp-code0monkey1s-projects.vercel.app. Verified `READY`, production alias ownership, and Git metadata matching the merge commit.
- Supabase production project `fdsglieendnihbfozbag`: additive private summary table/RPC migration and compact communication overview migration applied. Summary persistence verified through the deployed application; public access remains denied.

## Verification

- Backend: 491 passed, including real throwaway PostgreSQL summary/checkpoint integration tests. Existing Pydantic warnings remain.
- Frontend: 172 passed, 6 existing skipped; lint and production build passed. Existing bundle-size warning remains.
- [Final GitHub summary evaluation](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43497385953): 19/20 positive (95%), required 85%. Generator `openai/gpt-oss-20b`, independent judge `qwen/qwen3.8-27b`. Report prompt/fixture SHA-256 hashes match the merged source. One judged case failed; this is a measured pass rate, not a guarantee of perfect summaries.
- Protected `main` requires `backend`, `frontend`, `golden-set`, and `summary-golden-set`, with strict up-to-date checks and administrator enforcement. Relevant missing/failed/skipped evaluations fail closed. All required checks succeeded before merge.

## Live production checks

An owned disposable guest invoice with an invalid recipient address passed all of these checks without sending email:

- Fresh summary GET returned no saved summary and no prior message/email bodies.
- Committed chat alone did not generate a summary.
- Opening POST created and persisted a summary; unchanged POST reused the identical version/timestamp.
- A subsequent committed message left the saved summary unchanged and stale; the next opening POST refreshed it.
- Explicit history agreed with the saved summary and preserved the pending polite-reminder approval.
- A different owner received 404.
- Health reported persistent PostgreSQL checkpoints.

A conversation and summary created on an earlier preview deployment were also retrieved unchanged from the new production deployment, including the pending draft approval. This verified persistence across application deployments without forcing a production restart.

Local evidence: `/tmp/invoice-summary-production-evidence.json`, `/tmp/invoice-summary-production-persistence-proof.json`, `/tmp/invoice-summary-production-alias-proof.json`, `/tmp/invoice-summary-production-sha-proof.json`, and `/tmp/invoice-summary-ci-43497385953/summary-latest.json`. Evidence contains no provider keys or session cookies. Temporary credential files/cookie jars are removed after verification.

## Rollback

Redeploy the preceding application commit `4cb07e2d976dc4fe8f29e4878af2493022f37baa` (previous ready production deployment: https://invoice-chaser-6v4ekhl16-code0monkey1s-projects.vercel.app), or revert the feature merge through the protected branch. Retain the additive private Supabase summary table and saved summaries; do not drop invoice, communication, or checkpoint data.
