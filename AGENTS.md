# InvoiceChaser agent guidance

For architecture, deployment setup and external services, read [CLAUDE.md](CLAUDE.md). The backend uses FastAPI, LangGraph and Supabase/Postgres; production is the existing Vercel project `invoice-chaser`.

## Change boundaries

- Keep `api/index.py` as the Vercel entry point. Compose collaborators in `web/bootstrap.py` and read mutable `Deps` fields at call time.
- Keep domain policy in `src/domain/` dependent only on the standard library. Use cases depend inward on domain and ports. Adapters implement outside services.
- Replace dependencies in tests through `Deps`; preserve the route contract and policy golden expectations during structural refactors.
- Frontend components and context providers call the API gateway through hooks. Existing architecture tests enforce these boundaries.
- For an OpenSpec change, follow its proposal, design, tasks and handoff; record verification with the task. Keep unrelated working-tree changes outside the commit unless the user asks to include them.

## Verification

When a review or agent correction exposes a recurring failure, prefer a focused
architecture check or behavioral regression test where it can enforce the lesson
reliably. Test the check with both forbidden and legitimate examples. Keep
judgment in review when the rule cannot distinguish the cases reliably.

Run from the repository root:

```bash
.venv/bin/python -m pytest -q
cd frontend
npm test
npm run lint
npm run build
```

For prompt, tool or agent changes, require the relevant live CI evaluation gates. Use the dedicated eval Groq organization, one evaluation run at a time; production credentials must stay separate. Preserve existing gate thresholds and baselines.

## Release

Merge through a pull request after all required checks succeed. Main auto-deploys to Vercel. Verify the merged deployment is Ready, `/api/health` reports `ok` with Postgres checkpoints, and the SPA and built assets load. Keep local credentials, environment backups and personal tooling configuration out of Git.
