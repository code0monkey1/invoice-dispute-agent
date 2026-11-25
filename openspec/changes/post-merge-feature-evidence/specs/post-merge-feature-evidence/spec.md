# Spec Delta

## Purpose

Give the InvoiceChaser team verifiable evidence of changed behavior tied to the exact revision that landed on main.

## ADDED Requirements

### Requirement: Pull request evidence selection

The workflow SHALL use the pull request's explicit selection of browser video, test summary, or CI only. A video or summary selection SHALL identify a runnable test of the changed behavior. CI only SHALL be available for changes that preserve behavior or affect documentation alone.

#### Scenario: Backend change has a visible effect

- **WHEN** a backend-only pull request changes an outcome users can observe in the app and declares a browser scenario
- **THEN** the workflow selects that scenario for recording regardless of which files changed

#### Scenario: Backend change has no browser-visible effect

- **WHEN** a pull request changes only an API contract or background behavior and declares a test summary
- **THEN** the workflow selects the declared integration test

#### Scenario: Evidence declaration is invalid

- **WHEN** a pull request has no evidence declaration, has conflicting modes, or names an unknown test
- **THEN** the evidence check reports the invalid declaration and publishes no evidence

### Requirement: Evidence runs on the landed revision

The workflow SHALL automatically run the selected test once a pull request merges into main, using the exact revision that landed. Browser tests SHALL exercise the running app and assert the changed behavior with isolated synthetic data.

#### Scenario: A later merge lands before recording

- **WHEN** a newer pull request lands before an earlier pull request's test starts
- **THEN** the earlier test still runs on its own landed revision

#### Scenario: Pull request is closed without merging

- **WHEN** a pull request is closed without merging into main
- **THEN** the workflow publishes no evidence to Slack

#### Scenario: Different owners can use the same invoice number

- **WHEN** two different invoice owners each submit invoice number `inv-1` with different details
- **THEN** both submissions succeed
- **AND** each owner sees their own invoice with its own details

#### Scenario: The same owner cannot reuse an invoice number

- **WHEN** one of those owners submits another invoice with number `inv-1` and different details
- **THEN** the API rejects that owner's repeat submission with HTTP 409 and the app shows the duplicate error
- **AND** each owner still sees exactly one `inv-1` with their original details

### Requirement: Slack publication reflects the test result

The workflow SHALL post successful evidence to the InvoiceChaser Slack channel `C0CJJPTLWM9`. Each post SHALL identify the pull request and the behavior verified. A failing test SHALL produce a CI failure with available diagnostics and no success post.

#### Scenario: Browser scenario passes

- **WHEN** the declared browser test passes and its recording is available
- **THEN** the workflow posts the recording from that passing run to the channel

#### Scenario: Integration test passes

- **WHEN** the declared integration test passes in test summary mode
- **THEN** the workflow posts a short summary and CI run link to the channel

#### Scenario: A CI-only change merges

- **WHEN** a pull request declares CI only and merges into main
- **THEN** normal CI checks run and the workflow publishes no Slack post

#### Scenario: Test or recording fails

- **WHEN** the selected test fails or the required video cannot be produced
- **THEN** the evidence run fails, keeps the CI diagnostics that were produced, and publishes no Slack success post

#### Scenario: Slack rejects delivery

- **WHEN** Slack rejects a passing video's upload or a test summary
- **THEN** the publication job reports a delivery failure separately from the test result
