## Golden-set eval

Model `openai/gpt-oss-120b` · judge `openai/gpt-oss-20b` · prompt `v1` · 36 runs · 2026-11-17T06:05:40+00:00

**FAIL** (compared with the baseline)

| Level | Runs | Passed | Tool choice | Approval rule | Tone rules | Judge (1-5) | Cost | p95 latency |
|---|---|---|---|---|---|---|---|---|
| 0 | 6 | 6 | 100% | 100% | 100% (+25 pts) | 4.50 (+0.50) | $0.0031 | 1740 ms |
| 1 | 8 | 8 | 100% | 100% | 100% | 5.00 | $0.0048 | 2332 ms |
| 2 | 6 | 5 | 100% | 100% | 83% (-17 pts) | 5.00 (+1.00) | $0.0028 | 1965 ms |
| 3 | 16 | 16 | 100% (+25 pts) | 100% | 100% | 4.80 (-0.20) | $0.0066 | 4737 ms |
| All | 36 | 35 | 100% (+6 pts) | 100% | 97% (+3 pts) | 4.81 (+0.48) | $0.0173 | 2332 ms |

### Why it fails

- level 2: tone rules fell from 100% to 83%

### Cases that failed

- `l2-quality-dispute` (level 2): tone rule: leaves a placeholder: [date]
