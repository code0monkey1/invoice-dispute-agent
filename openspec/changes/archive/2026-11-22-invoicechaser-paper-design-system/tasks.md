# Tasks

## 1. File and tokens

- [x] 1.1 Confirm each draft token against its call sites in `frontend/src/components/landing/` (re-run the hex count; decide `#F6EDE3`); verify with a written keep/one-off list in the Paper file notes
- [x] 1.2 Create the Paper file `InvoiceChaser — Design System` and verify it appears in `list_resources` while the site's design-system file is unchanged
- [x] 1.3 Register colour, type, radius and spacing tokens and verify `get_tokens` returns exactly the decided set with no Paper default gray/blue scales

## 2. Foundations artboard

- [x] 2.1 Build colour swatches grouped brand/ink/surface/line/status, each labelled with name and hex, and verify against a screenshot
- [x] 2.2 Add the type scale, radius and spacing sections and verify they show every registered token
- [x] 2.3 Add the known-drift list (Tailwind greys, Outfit, Plus Jakarta Sans) and the "built by hand" note, and verify none of those values is registered
- [x] 2.4 Check whether Schibsted Grotesk and Source Serif 4 load via `get_font_family_info`; if not, substitute and add the disclosure note, then verify by screenshot

## 3. Components artboard

- [x] 3.1 Build the gradient demo button and secondary Google button; verify fills and borders reference tokens
- [x] 3.2 Build paid, overdue and escalated badges with the status pairs; verify each uses its own foreground/background tokens
- [x] 3.3 Build the invoice row and the agent-step row in automatic and "needs your approval" states; verify by screenshot that the two states differ in fill, border or accent, not only text
- [x] 3.4 Build the draft-email approval card using the approval treatment; verify with `get_computed_styles` that no component holds a hardcoded hex

## 4. Page sample artboard

- [x] 4.1 Compose the landing hero from the Components artboard's parts, including a freelancer image from `frontend/public/presenter/`; verify by screenshot that the product story (agent automatic, human approves) reads top to bottom
- [x] 4.2 Verify the Page sample uses only registered tokens and call `finish_working_on_nodes` on all artboards

## 5. Integration check

- [x] 5.1 Walk the spec scenarios against the finished file (token values, swatch labels, drift list, state distinction, font note) and confirm the site's Paper file and `frontend/src` are unchanged via `git status`
