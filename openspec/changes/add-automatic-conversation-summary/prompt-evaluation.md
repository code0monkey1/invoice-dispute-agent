# Incremental-specific prompt verification

The original prompt passed only 4/8 sequences locally and 5/8 in trusted GitHub run `43569867974`. The user authorized fixing the prompt before committing, merging and production release.

The shared prompt now explicitly merges earlier memory with new communications; preserves current financial position, correction/withdrawal chronology and unresolved objection details; distinguishes follow-ups from payment promises; and retains participant attribution, unverified claims and specific recorded outcomes. It avoids empty template headings and generic absence claims. No fixture values or expected answers were added to the prompt.

| Complete local cohort | Positive | Gate |
| --- | --- | --- |
| Unchanged single summaries | 19/20 (95%) | Pass |
| Unchanged update sequences | 8/8 (100%) | Pass |
| Unchanged sequence checkpoints | 31/31 (100%) | Pass |
| Additional holdout sequences | 2/2 (100%) | Pass |
| Holdout checkpoints | 8/8 (100%) | Pass |

Both golden fixture files are byte-for-byte identical to `f76c568`. Judge rubric, generator `openai/gpt-oss-20b`, independent judge `qwen/qwen3.8-27b`, fail-closed behavior and the separate 85% cohort gates are unchanged. The one failed single case was a judged attribution error, not a provider failure; its output is retained.

Auditable reports: `evals/results/summary-incremental-prompt/` contains the complete fixed-set result and hashes. `evals/results/summary-incremental-holdouts/` contains two additional synthetic sequences with different amounts, currencies and dates, their generated checkpoints and judgments. An earlier template-heavy prompt attempt introduced communication omissions and was stopped; its incomplete failed scorecard is preserved under `summary-incremental-prompt-first-attempt/` and is not release evidence.

Before committing: service/evaluation tests 63 passed; full backend 496 passed with 13 environment-dependent skips; frontend 172 passed with 6 existing skips; lint/build and strict OpenSpec validation passed. Independent review of both the initial and final prompt refinements found no significant issues. Existing Pydantic and bundle-size warnings remain.

Release still requires all protected GitHub checks on the final commit, merge to main and verification of the merged production deployment. The prompt is shared by existing full-history refresh/chunking and experimental incremental inputs; this release does not implement database coverage cursors or delta-only production retrieval. Saved summaries still refresh only on opening after communications change.
