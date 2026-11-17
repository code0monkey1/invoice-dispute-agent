# Historical evaluation evidence

These immutable reports document earlier application evaluations. They are release records; they are not agent inputs, evaluation fixtures or comparison baselines. The final documentation-only PR leaves the entire `evals/` tree identical to main.

| Snapshot | Source / CI | Outcome |
| --- | --- | --- |
| `2026-11-12-local/report.*` | Existing local run, generated 2026-11-12T10:34:18Z | Failed 21-run report, preserved byte-for-byte from the original uncommitted local files. |
| `2026-11-16-release-reference/report.*` | Source `dbdbc7d41a3aeeabe5863f381700ba4834ee5021`, merged as `1d8b02a2372f197421e50cc2177d0aa4c8e5dfbd`; [release CI](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43910288299) | Historical passing gate: 36 runs, 100% tool-choice accuracy and approval compliance, one tone case failed within the existing tolerance. |
| `pr35-attempt-1/report.*` | Source `358f2b8f96d5f61de224a7fea8c05cce4782461a`; [CI attempt 1](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43922328668/attempts/1) | Live gate failed: level-2 tone fell to 83% because `l2-quality-dispute` emitted `[Client Name]`. A level-3 tool-choice case also failed. |
| `pr35-attempt-2/report.*` | Same source; [CI attempt 2](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43922328668/attempts/2) | Live gate failed again: the same level-2 case emitted `[date]`. Tool choice and approval compliance were 100%. |

## Scope and unresolved issue

Both PR #35 attempts used application code, prompts, fixtures, evaluation implementation, workflow and comparison baseline identical to deployed main. They were triggered by generated report edits under `evals/results/`, which the broad classifier treats as agent-related. All raw reports, including both failures, are retained here rather than repeatedly rerunning unchanged application behavior.

The final PR restores `evals/results/` exactly to main and organizes these artifacts with OpenSpec release evidence. No workflow, gate threshold, fixture, baseline, prompt or application behavior is changed. Required CI gates still run under the existing classification rules; a successful documentation-only classification does not mean a new live model evaluation passed.

The pre-existing `l2-quality-dispute` placeholder issue remains unresolved. It was already recorded as variable on main in the refactor handoff. A separate behavior change should address this quality issue; this cleanup does not claim to fix it.
