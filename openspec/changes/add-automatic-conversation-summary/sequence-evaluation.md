# Sequential evaluation evidence

The user requested an evaluation-only extension after exploring incremental summaries. Production refresh, prompt, model configuration, API, storage and UI remain unchanged.

The complete live Groq run used generator `openai/gpt-oss-20b` with independent judge `qwen/qwen3.8-27b`. All expected evaluations completed without provider-error cases.

| Cohort | Positive | Rate | 85% gate |
| --- | --- | --- | --- |
| Existing single summaries | 20/20 | 100% | Pass |
| Complete update sequences | 4/8 | 50% | **Fail** |
| Individual sequence checkpoints | 27/31 | 87.1% | Pass |
| Combined cases | 24/28 | 85.7% | Rejected by sequence gate |

The four failed sequences exposed omitted payment-date history/unpaid status, an explicitly requested currency detail, a corrected duplicate-payment history, and a client payment promise when summarizing an approved follow-up. The original unresolved objection survived all eight refreshes, but that complete sequence still failed its currency checkpoint. No fixture was removed, no threshold was lowered, and no judge feedback repaired the generation chain.

The scorecard and generated candidates are stored in `evals/results/summary-sequences/summary-latest.json` and `.md`, with prompt and both fixture SHA-256 hashes. This result assesses proposed incremental model inputs, not production coverage-cursor correctness. The existing full-history production summarizer was not changed. Keep the evaluation PR in draft while the expanded sequence quality gate fails; do not bypass branch protection or treat the combined 85.7% rate as a pass.

Verification: 46 focused deterministic tests passed; full backend suite 486 passed with 23 existing/environment-dependent skips. Strict OpenSpec validation and independent review passed. Unit tests exercise the actual CLI runner/report path and prove a combined rate above 85% cannot hide a failing sequence cohort.
