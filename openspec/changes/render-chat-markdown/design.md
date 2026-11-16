# Design

## Context

On `main` (prod, `ca5263e`), `frontend/src/components/MessageBubble.tsx` shows the user and AI branches the same way: `<p className="whitespace-pre-wrap">{content}</p>` (line 104). `messageText()` already turns string or structured content into a single string, so only the final display step changes. Tool results (`<pre>`, line 83) and inbound client replies (line 68) have their own branches. `DraftApproval.tsx` shows the email draft in a `<pre>` and an editable textarea. The frontend has no Markdown library yet (React 19, Tailwind 4, no `@tailwindcss/typography`).

Deploy: `vercel.json` builds `frontend/` and serves it with `api/index.py`. The repo has no `netlify.toml`, `.netlify/` link or Netlify CLI, so the Netlify site must be found through the Netlify MCP connector or the dashboard.

## Goals / Non-Goals

**Goals:**
- Show assistant chat Markdown (CommonMark + GFM tables) as formatted text that matches the current bubble style.
- Keep display safe without adding a sanitizer, by never parsing raw HTML.
- Keep the change limited to the AI branch of `MessageBubble`.

**Non-Goals:**
- Syntax highlighting for code blocks.
- Changing prompts so the model writes less Markdown, or removing Markdown from sent emails (possible follow-up, see Open Questions).
- Formatting the Trace panel, tool results or client replies.

## Decisions

### D1: `react-markdown@10` + `remark-gfm@4` + `remark-breaks@4`
- `react-markdown` builds React elements directly (no `dangerouslySetInnerHTML`). It ignores raw HTML unless `rehype-raw` is added. Its default `urlTransform` removes `javascript:` and other unsafe schemes. This covers the safety requirement without DOMPurify.
- `remark-gfm` adds pipe tables, strikethrough and autolinks, which the model uses (see the screenshot).
- `remark-breaks` turns single newlines into `<br>`. Without it, email-style sign-offs ("Best regards,\nName") would join into one line. That would be a regression from today's `pre-wrap`.
- **Alternatives:** `marked` + `DOMPurify` (uses HTML strings and `dangerouslySetInnerHTML`, so it needs a sanitizer, which is riskier); a hand-written regex formatter (tables and nesting are easy to get wrong); `markdown-to-jsx` (fine, but has a smaller plugin ecosystem for GFM).

### D2: A `Markdown` component with explicit Tailwind element mappings
Add `frontend/src/components/Markdown.tsx`. It wraps `ReactMarkdown` and passes a `components` map that styles `p`, `strong`, `em`, `ul/ol/li`, `h1–h4`, `code/pre`, `blockquote`, `a`, `table/thead/th/td`, and `hr` with Tailwind classes that match the bubble (`text-sm`, gray-700, compact spacing). The `table` mapping wraps the table in `<div className="overflow-x-auto max-w-full">`. The `a` mapping sets `target="_blank" rel="noopener noreferrer"`.
- **Alternative:** add `@tailwindcss/typography` and use `prose prose-sm`. That means another plugin and Tailwind 4 config work, and `prose` margins are too large for chat bubbles. Explicit mappings are small and easier to control.

### D3: Only the AI branch changes
`MessageBubble` uses `<Markdown>` when `isAI`. User messages keep `<p className="whitespace-pre-wrap">`. Users don't write Markdown on purpose, and showing it could change what they meant. The bubble also gets `min-w-0` so a wide table can't push it past `max-w-[75%]`.

## Risks / Trade-offs

- [Model writes text that looks like Markdown by accident (for example `*` in an amount note)] → Some italics may appear where none were meant. This is acceptable and much rarer than the broken display today.
- [Bundle size: react-markdown + remark/unified ≈ 40–50 kB gzip] → Acceptable. If needed, it can later be loaded lazily with the ChatPanel route.
- [Table overflow on narrow screens] → The `overflow-x-auto` wrapper and `min-w-0` on the bubble handle it. Check in the browser at mobile width.
- [jsdom tests and ESM-only react-markdown] → Vitest handles ESM. If it fails, add `server.deps.inline` in `vite.config`.

## Migration Plan

1. Branch from up-to-date `main` (`fix/chat-markdown-rendering`), implement, run `npm run test`, `npm run lint` and `npm run build` in `frontend/`.
2. Open a PR to `main`, merge after checks pass.
3. Production deploys: Vercel prod (git integration on merge to `main`, or `vercel --prod`), and Netlify prod for the site found through the Netlify connector.
4. Check that both production URLs show the screenshot's invoice summary as a formatted table.
5. **Rollback:** revert the merge commit and redeploy. There is no data or API change.

## Open Questions

- Should the agent's email drafts stop including Markdown (`**name**` in signatures)? This is separate from chat display. It would be a prompt change in `src/prompts.py` / drafting tools with a live eval run, so it is better as its own change.
