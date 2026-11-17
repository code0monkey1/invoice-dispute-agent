# Proposal

## Why

The agent (Groq / llama-3.3-70b) answers in Markdown — `**bold**`, `*italic*`, pipe tables, lists — but `MessageBubble.tsx` puts the text in a `<p className="whitespace-pre-wrap">`, so users see the raw syntax (`| Item | Details |`, `|------|`, `**$1,900.00**`). Chat answers are hard to read, and an invoice summary table looks broken.

## What Changes

- Show assistant (`AIMessage`) chat content as Markdown: bold, italic, inline code, headings, ordered and unordered lists, links, blockquotes, line breaks, and GitHub-flavored pipe tables.
- Style the rendered elements so they fit the existing chat bubble design (Tailwind). Wide tables scroll sideways inside the bubble and do not stretch it.
- Keep the output safe: raw HTML in model output is not rendered, and links open in a new tab with `rel="noopener noreferrer"`. Unsafe URL schemes such as `javascript:` are dropped.
- Leave these as they are now: user messages (plain text, line breaks kept), tool-result blocks (monospace `<pre>`), inbound client reply cards, and the `DraftApproval` editor (plain text, because it becomes the email body).

**Out of scope:** Markdown that ends up inside email drafts sent to clients (for example `**Chiranjeev Thomas**` in a signature). That is about the prompts and drafting, not chat display. It is noted in design.md as a possible follow-up.

## Capabilities

### New Capabilities
- `chat-message-rendering`: how messages in the invoice chat panel are displayed, by message type (assistant, user, tool result, inbound client reply). This includes Markdown formatting and safety rules.

### Modified Capabilities
_None. There are no existing specs under `openspec/specs/`._

## Impact

- **Code:** `frontend/src/components/MessageBubble.tsx` (AI branch). A new small `Markdown` component may be added under `frontend/src/components/`.
- **Dependencies (frontend):** add `react-markdown` and `remark-gfm` (for GFM table support).
- **Tests:** extend `frontend/src/components/__tests__/MessageBubble.test.tsx`.
- **Backend / API:** no changes.
- **Deploy:** frontend only. Ship through PR → merge → Vercel production deploy and Netlify production deploy (as the user asked). Implementation must find the Netlify site link, because the repo has no `netlify.toml`.
