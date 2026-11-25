# Proposal

## Why

The InvoiceChaser Slack channel needs a quick way to see what a merge changed and verify that the behavior actually works. A recording from a passing feature test gives the team evidence tied to the code that landed on `main`.

## What Changes

- Let each PR declare browser video, test summary, or CI only based on the behavior it changes.
- Run the declared test against the landed revision and automatically post the passing recording or test summary to the InvoiceChaser Slack channel.
- Use the first real browser scenario to verify that two invoice owners can each create `inv-1` and see their own invoice. Verify that a second `inv-1` submitted by the same owner is rejected and that their original invoice is preserved.
- Run in GitHub Actions on standard runners, using isolated synthetic data and existing test infrastructure where possible.

## Capabilities

### New Capabilities

- `post-merge-feature-evidence` defines how InvoiceChaser selects, verifies, and shares evidence for a merged change.

### Modified Capabilities

None.

## Impact

GitHub Actions, PR metadata, a Playwright test harness, and one Slack bot credential are affected. Existing React and FastAPI code runs through its normal entry points in the browser scenario. No production deployment or runtime service is required for recording.
