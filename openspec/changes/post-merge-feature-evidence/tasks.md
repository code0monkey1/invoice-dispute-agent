# Tasks

## 1. App harness and first scenario

- [x] 1.1 Add Playwright Test and a test-only ASGI launcher that serves the built React app and real FastAPI routes with isolated test adapters through `Deps`. Verify that a fresh guest browser session can open the dashboard and submit a synthetic invoice without production credentials.
- [x] 1.2 Write and record the invoice-number ownership scenario. Verify two independent guest owners can each create `inv-1` through the real API. Retry from one owner and verify HTTP 409 and the visible duplicate error. Reload both dashboards and verify that each owner sees exactly one `inv-1` with their own original details. Review the passing recording for readability.

## 2. Scenario selection and merge execution

- [x] 2.1 Add the PR declaration, checked-in scenario mapping, and credential-free pre-merge validation. Test the three modes, missing or malformed selections, unknown IDs, and the use of a backend change with a browser-visible outcome.
- [x] 2.2 Add post-merge execution on a standard Linux runner. Verify merged PRs targeting main use their landed SHA even after a later merge, closed unmerged PRs do not run, and CI-only PRs leave normal checks in place without recording.
- [x] 2.3 Publish the passing recording or integration result as short-lived CI artifacts. Test that a missing recording or failed test produces a failure and preserves available diagnostics.

## 3. Slack publishing and verification

- [x] 3.1 Add a separate publisher for file uploads and test summaries. Test that it accepts only passing evidence, posts with the PR and CI run links, and surfaces Slack API failures separately. Document bot membership, permissions, the repository secret, and rerun recovery.
- [x] 3.2 Verify the complete workflow for browser video, test summary, and CI only. Confirm one passing browser recording reaches Slack channel `C0CJJPTLWM9` during an authorized smoke test, confirm a failing scenario produces no Slack success post, and record the verification evidence in the change.

## Local verification

- Playwright verified both owners could create `inv-1`, the same-owner retry returned HTTP 409 and showed an alert, and the dashboards and API stayed owner-scoped. The reviewed MP4 contains all three submissions and both final dashboards.
- The test summary integration case passed. CI-only selection ran no evidence test. A failing browser run retained a trace, and a missing recording could not produce passing evidence.
- The publisher tests verified Slack upload and summary payloads, absence of a passing result, and a rejected Slack response.

## Post-merge verification

- Merging [PR #47](https://github.com/code0monkey1/invoice-dispute-agent/pull/47) triggered the [Feature evidence workflow](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/45653046012). Its revision check and browser test passed at landed SHA `5ac9bb7c7b6dbe4f74d1bee617bd0146b05aa57d`. The workflow pins each merge's SHA, skips closed unmerged PRs, and skips capture and publication in CI-only mode.
- The delivery job confirmed that Slack accepted the MP4 recording in channel `C0CJJPTLWM9`.
