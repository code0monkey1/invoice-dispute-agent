# Feature evidence

Add one declaration to a pull request description.

| Declaration | Use it when | After the merge |
| --- | --- | --- |
| `Evidence: browser-video invoice-number-ownership` | A change affects what someone can see or do in the app | Actions tests the merged revision and posts the passing MP4 to Slack |
| `Evidence: test-summary invoice-owner-api` | An API or background change has no browser-visible effect | Actions runs the selected integration test and posts a passing summary |
| `Evidence: ci-only` | Normal CI is enough for a behavior-preserving change or documentation | Normal CI runs |

The IDs above are starter scenarios. For a new change, add or update the test and register its ID, path, and description in `scripts/feature_evidence.json`. The evidence check on the pull request runs the selected test. You can browse failure traces and screenshots in the Actions run. A failed test or missing recording prevents publication.

## Run the browser scenario locally

Install the backend requirements into your Python environment and activate it. Run the following from `frontend`.

```sh
npm ci
npx playwright install chromium
npm run build
RECORD_FEATURE_EVIDENCE=1 npx playwright test
```

The test uses the FastAPI app and synthetic data in an isolated local store. The clips appear under `frontend/test-results`. GitHub Actions assembles them into an MP4.

## Configure Slack

Use the InvoiceChaser Slack app with the bot scopes `files:write` and `chat:write`. Reinstall the app after adding scopes and invite its bot to the [InvoiceChaser channel](https://software-factoryorg.slack.com/archives/C0CJJPTLWM9). Store the bot token in the GitHub repository's Actions secrets as `SLACK_BOT_TOKEN`. The separate delivery job uses the token after the test and artifact upload succeed.

If delivery fails, check the **Deliver to Slack** job. The passing evidence is available in Actions for three days. Before rerunning a failed delivery, check the channel for the pull request link in case Slack accepted the post before the connection failed. If it is absent and the artifact is still available, rerun the failed delivery job after correcting the issue.
