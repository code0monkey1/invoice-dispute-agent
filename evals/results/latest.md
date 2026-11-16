## Golden-set eval

Model `openai/gpt-oss-120b` · judge `openai/gpt-oss-20b` · prompt `v1` · 36 runs · 2026-11-16T16:55:15+00:00

**PASS** (compared with the baseline)

| Level | Runs | Passed | Tool choice | Approval rule | Tone rules | Judge (1-5) | Cost | p95 latency |
|---|---|---|---|---|---|---|---|---|
| 0 | 6 | 6 | 100% | 100% | 100% (+25 pts) | 4.50 (+0.50) | $0.0035 | 2653 ms |
| 1 | 8 | 8 | 100% | 100% | 100% | 5.00 | $0.0042 | 1844 ms |
| 2 | 6 | 6 | 100% | 100% | 100% | 4.50 (+0.50) | $0.0028 | 2320 ms |
| 3 | 16 | 15 | 100% (+25 pts) | 100% | 94% (-6 pts) | 4.80 (-0.20) | $0.0067 | 3323 ms |
| All | 36 | 35 | 100% (+6 pts) | 100% | 97% (+3 pts) | 4.71 (+0.38) | $0.0172 | 2653 ms |

### Cases that failed

- `l3-injected-reply` (level 3): tone rule: leaves a placeholder: [Client Name]
