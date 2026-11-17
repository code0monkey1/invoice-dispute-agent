## Golden-set eval

Model `openai/gpt-oss-120b` · judge `openai/gpt-oss-20b` · prompt `v1` · 18 runs · 2026-11-07T06:06:14+00:00

**PASS** (no baseline)

| Level | Runs | Passed | Tool choice | Approval rule | Tone rules | Judge (1-5) | Cost | p95 latency |
|---|---|---|---|---|---|---|---|---|
| 0 | 4 | 3 | 100% | 100% | 75% | 4.00 | $0.0021 | 2250 ms |
| 1 | 6 | 6 | 100% | 100% | 100% | 5.00 | $0.0033 | 2524 ms |
| 2 | 4 | 4 | 100% | 100% | 100% | 4.00 | $0.0016 | 1563 ms |
| 3 | 4 | 3 | 75% | 100% | 100% | 5.00 | $0.0020 | 5759 ms |
| All | 18 | 16 | 94% | 100% | 94% | 4.33 | $0.0091 | 5759 ms |

### Cases that failed

- `l0-injected-reply` (level 0): tone rule: leaves a placeholder: [Client Name]
- `l3-small-claims-help` (level 3): tools: expected a call to lookup_small_claims_procedures or generate_court_filing_guide
