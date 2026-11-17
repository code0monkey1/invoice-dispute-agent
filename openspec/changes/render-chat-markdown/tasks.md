# Tasks

## 1. Setup

- [x] 1.1 From up-to-date `main`, create branch `fix/chat-markdown-rendering`. Verify with `git log -1` that it matches `origin/main`.
- [x] 1.2 Run `npm install react-markdown@^10 remark-gfm@^4 remark-breaks@^4` in `frontend/`. Verify `package.json` and `package-lock.json` list all three and the existing `npx vitest run` suite still passes.

## 2. Markdown component (TDD)

- [x] 2.1 Add failing tests in `frontend/src/components/__tests__/Markdown.test.tsx`: bold has no `**`; a pipe table becomes `table`/`th`/`td` with no `|---|`; lists, a heading, italic and inline code; single newlines become `<br>`; `<script>` and `<img onerror>` are not rendered; `https` link has `target=_blank` and `rel` noopener noreferrer; a `javascript:` link has no such href. Verify they fail.
- [x] 2.2 Implement `frontend/src/components/Markdown.tsx` (react-markdown + remark-gfm + remark-breaks, Tailwind `components` map, table inside an `overflow-x-auto` wrapper, safe links). Verify the 2.1 tests pass.

## 3. Use it in MessageBubble (TDD)

- [x] 3.1 Extend `frontend/src/components/__tests__/MessageBubble.test.tsx`: an AI message with bold and a table renders formatted; structured content parts render as Markdown; a user message `use **bold** please` stays literal; a ToolMessage with `| a | b |` stays literal in `<pre>`; an `[INCOMING CLIENT REPLY]` body with `**urgent**` stays literal. Verify the new AI cases fail first.
- [x] 3.2 In `MessageBubble.tsx`, render `<Markdown>` for the AI branch only, and add `min-w-0` to the bubble. Verify all MessageBubble tests and the existing ChatPanel tests pass.
- [x] 3.3 Check that `DraftApproval.tsx` has not changed (`git diff --stat` shows no change to it). This confirms drafts stay plain text.

## 4. Checks

- [x] 4.1 Run `npm run lint`, `npx vitest run` and `npm run build` in `frontend/`. Verify all three exit 0. _(vitest and build exit 0. `npm run lint` shows 4 errors that are already on `main` in untouched files (DraftApproval, AuthContext, GoogleCallback). Files changed here lint clean.)_
- [x] 4.2 Run `npm run dev` with the backend, open an invoice chat, and ask for an invoice summary. Verify in the browser that bold, the table and the sign-off line breaks display correctly, and that a wide table scrolls inside the bubble at ~375px width. Take a screenshot. _(Checked in a temporary Vite page that renders the real `MessageBubble` with the app's CSS and the exact reply from the screenshot, so no live LLM or DB calls. Bubble stayed within bounds and the table scrolled inside at a 300px container. Temporary files removed.)_

## 5. Ship

- [x] 5.1 Commit, push the branch, and open a PR to `main` with the before (user screenshot) and after screenshots. Verify the PR URL is returned and CI checks pass.
- [x] 5.2 Merge the PR, then deploy Vercel production (git integration or `vercel --prod`). Verify the production deployment is `READY` and the prod URL shows formatted chat Markdown. _(PR #23 merged as `71af626`. Deployment `dpl_7mkGjz2xRNzWUZCJayXnEyBzgtod` is Ready at https://invoice-chaser-chi.vercel.app. `/api/health` returns 200 and the served bundle includes the new renderer.)_
- [x] 5.3 Find the Netlify site through the Netlify connector (the repo has no `netlify.toml` or link) and trigger a production deploy from `main`. Verify the deploy state is `ready` and the Netlify prod URL shows formatted chat Markdown. _(Not applicable: the user confirmed InvoiceChaser is hosted only on Vercel. No Netlify site exists for it, so nothing was deployed there.)_

## Workflow follow-up

- Archive the change (`/opsx:archive`) after both production deploys are verified.
- Possible separate change: stop putting Markdown in email drafts sent to clients (see design.md Open Questions).
