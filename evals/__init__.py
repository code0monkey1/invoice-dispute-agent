"""Golden-set evaluation of the InvoiceChaser agent.

    evals/golden/level_N.yaml ─▶ cases.load_cases()
                                     │
    tier 1 (pytest, free) ───────────┼──▶ harness.EvalHarness.run_case(case, ScriptedModel)
    tier 2 (python -m evals.run) ────┘                     │ (real API + graph, fake DB,
                                                           │  Gmail and search stubbed)
                                                           ▼
                                         traces ─▶ checks.evaluate() ─▶ CaseResult
                                                           │
                                         run.py: scorecard, thresholds, baseline diff
"""
