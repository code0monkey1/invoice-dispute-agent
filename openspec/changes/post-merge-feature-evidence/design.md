# Design

## Context

The existing test workflow runs pytest, Vitest, lint, and the frontend build. The invoice storage key combines the owner ID and the invoice number. Two owners can use the same number, and the API returns HTTP 409 for a repeat number within one owner's invoices. FastAPI serves the built SPA, and the application composition root allows test collaborators to be substituted through `Deps`.

## Goals / Non-Goals

**Goals**

- Use the exact merged revision for verifiable, repeatable evidence.
- Exercise the app through its browser and HTTP boundaries with isolated data.
- Run on standard GitHub-hosted Linux runners and deliver files directly to Slack using an installed bot.

**Non-Goals**

- Production traffic or customer data in the capture environment.
- AI-generated demos, paid video hosting, and permanent video retention.

## Decisions

1. **Select evidence explicitly.** Add a PR template field with one mode and, for browser video or test summary, a stable scenario ID and short description. Map IDs to checked-in Playwright or pytest selections. PR text is data and cannot supply a shell command or an arbitrary test path. This preserves intent across backend and frontend changes and makes the selection reviewable. File-path heuristics cannot distinguish a user-visible backend fix from an internal refactor.
2. **Separate validation, capture, and publication.** Validate the declaration and run the selected test without Slack credentials on PRs, including updates to the declaration. For post-merge evidence, use the base-repository PR-closed event, gated on merged into `main`. Resolve the landed SHA from the merge payload, verify it belongs to `main`, and use it explicitly. For fork coverage, a `pull_request_target` merge job can use the trusted workflow definition with read-only repository permissions and the landed SHA. It must never execute the unmerged PR head. Keep normal CI independent. Avoid cancellation groups shared across PRs so a new merge does not discard an earlier recording.
3. **Run the production app entry points in a test harness.** Build `frontend/dist` before starting the local ASGI server so the app serves the SPA and API at one origin. Launch the server from a test entry point with the existing application composition and isolated test adapters behind `Deps`. Start two independent browser contexts with separate guest identities against the same store. Submit `inv-1` through each dashboard's invoice form with distinct client details and assert both real API requests succeed. Submit `inv-1` again in the first context and assert HTTP 409 and the visible duplicate error. Reload both dashboards and verify each shows only its own original invoice. Capture the two owners' successes and the retry in the Slack evidence.
4. **Publish using a separate GitHub Actions job.** Pass the scenario result and, when applicable, the finalized recording as CI artifacts from the credential-free test job. Use Slack's external upload API flow for video and message posting for test summaries. Keep the token in GitHub Actions secrets, inject it only into the publisher, and scope the bot to file upload and message posting in the target channel. Use the actual CI outcome and CI run URL in the message. Give temporary CI artifacts short retention.

## Risks / Trade-offs

- **Incomplete recordings or false positives.** Require explicit assertions on the changed behavior and finalize the browser recording before making it eligible for publication. Treat missing footage as a failed evidence run.
- **Duplicate Slack posts on reruns.** Provide a separate delivery result and avoid blindly repeating an upload if Slack may already have accepted it. Use the PR and landed SHA to identify the post when recovering an ambiguous delivery.
- **Workspace restrictions.** The Slack app needs installation approval if required by the workspace and must be a member of the channel. Free Slack retention settings determine how long old files remain accessible.

## Migration Plan

Land the harness, workflow, and PR template together. Set up the Slack bot and secret once, then verify delivery on a controlled merge or a dry run followed by an authorized live smoke test. Disable the publishing job if delivery must be rolled back. Normal CI continues independently.
