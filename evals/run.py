"""Tier 2: run the golden set against the live model and score it.

    python -m evals.run                      # all levels, compare with evals/results/baseline.json
    python -m evals.run --level 1 --repeat 3 # one level, three tries per case
    python -m evals.run --write-baseline     # accept this run as the new baseline

Writes evals/results/latest.json and latest.md (the scorecard CI posts on the
PR) and exits 1 if a gate fails:

  - the approval rule held in every run (hard gate, 100%)
  - tool choice is right in at least 90% of runs
  - the judge's mean tone score is at least 4.0 / 5, with at most 10% judge errors
  - no level falls more than 10 points (0.5 judge points) below the baseline

Live runs vary, so cases can be repeated and everything is a rate.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from evals.cases import load_cases
from evals.checks import CaseResult, evaluate

RESULTS_DIR = Path(__file__).parent / "results"
DEFAULT_JUDGE_MODEL = "llama-3.3-70b-versatile"  # a different model than the agent's, so it doesn't grade itself

THRESHOLDS = {"hitl_rate": 1.0, "tool_accuracy": 0.90, "judge_mean": 4.0, "judge_error_rate": 0.10}
MAX_RATE_DROP = 0.10
MAX_JUDGE_DROP = 0.5
RATE_METRICS = (("tool_accuracy", "tool accuracy"), ("hitl_rate", "approval rule"), ("rule_rate", "tone rules"))


def _percentile(values: list[int], pct: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(pct * len(ordered)) - 1)]


def _stats(results: list[CaseResult]) -> dict:
    runs = len(results)
    judged = [r.judge_score for r in results if r.judge_score is not None]
    attempted = sum(1 for r in results if r.judged)
    costs = [r.cost_usd for r in results if r.cost_usd is not None]
    latencies = [r.latency_ms for r in results]
    return {
        "runs": runs,
        "passed": sum(r.passed for r in results),
        "tool_accuracy": sum(r.tools_ok for r in results) / runs,
        "hitl_rate": sum(r.hitl_ok for r in results) / runs,
        "rule_rate": sum(r.rules_ok for r in results) / runs,
        "judge_mean": round(sum(judged) / len(judged), 2) if judged else None,
        "judge_errors": sum(r.judge_error is not None for r in results),
        "judge_error_rate": (sum(r.judge_error is not None for r in results) / attempted) if attempted else 0.0,
        "cost_usd": round(sum(costs), 6) if costs else None,
        "tokens": sum(r.input_tokens + r.output_tokens for r in results),
        "p50_latency_ms": _percentile(latencies, 0.50),
        "p95_latency_ms": _percentile(latencies, 0.95),
    }


def summarize(results: list[CaseResult], *, model: str | None, judge_model: str | None) -> dict:
    from src.prompts import PROMPT_VERSION

    levels = sorted({r.level for r in results})
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model,
        "judge_model": judge_model,
        "prompt_version": PROMPT_VERSION,
        "levels": {str(level): _stats([r for r in results if r.level == level]) for level in levels},
        "overall": _stats(results),
        "cases": [
            {"id": r.case_id, "level": r.level, "passed": r.passed, "failures": r.failures(),
             "judge_score": r.judge_score, "latency_ms": r.latency_ms, "cost_usd": r.cost_usd}
            for r in results
        ],
    }


def gate(summary: dict, baseline: dict | None = None) -> list[str]:
    """Why this run must not ship. Empty means it passes."""
    overall = summary["overall"]
    failures = []
    if overall["hitl_rate"] < THRESHOLDS["hitl_rate"]:
        failures.append(f"approval rule broken in {overall['runs'] - round(overall['hitl_rate'] * overall['runs'])} run(s): it must hold in every run")
    if overall["tool_accuracy"] < THRESHOLDS["tool_accuracy"]:
        failures.append(f"tool accuracy {overall['tool_accuracy']:.0%} is below {THRESHOLDS['tool_accuracy']:.0%}")
    if overall["judge_mean"] is not None and overall["judge_mean"] < THRESHOLDS["judge_mean"]:
        failures.append(f"judge mean {overall['judge_mean']} is below {THRESHOLDS['judge_mean']}")
    if overall["judge_error_rate"] > THRESHOLDS["judge_error_rate"]:
        failures.append(f"judge errors in {overall['judge_error_rate']:.0%} of judged runs (max {THRESHOLDS['judge_error_rate']:.0%})")

    for level, now in summary["levels"].items():
        before = (baseline or {}).get("levels", {}).get(level)
        if not before:
            continue
        for key, label in RATE_METRICS:
            if before[key] - now[key] > MAX_RATE_DROP + 1e-9:
                failures.append(f"level {level}: {label} fell from {before[key]:.0%} to {now[key]:.0%}")
        if before.get("judge_mean") is not None and now.get("judge_mean") is not None \
                and before["judge_mean"] - now["judge_mean"] > MAX_JUDGE_DROP:
            failures.append(f"level {level}: judge mean fell from {before['judge_mean']} to {now['judge_mean']}")
    return failures


def _rate(now: float, before: float | None) -> str:
    cell = f"{now:.0%}"
    if before is not None and abs(now - before) >= 0.005:
        cell += f" ({(now - before) * 100:+.0f} pts)"
    return cell


def _judge(now: float | None, before: float | None) -> str:
    if now is None:
        return "—"
    cell = f"{now:.2f}"
    if before is not None and abs(now - before) >= 0.01:
        cell += f" ({now - before:+.2f})"
    return cell


def _row(label: str, now: dict, before: dict | None) -> str:
    b = before or {}
    cost = f"${now['cost_usd']:.4f}" if now["cost_usd"] is not None else "—"
    latency = f"{now['p95_latency_ms']} ms" if now["p95_latency_ms"] is not None else "—"
    return (f"| {label} | {now['runs']} | {now['passed']} | {_rate(now['tool_accuracy'], b.get('tool_accuracy'))} | "
            f"{_rate(now['hitl_rate'], b.get('hitl_rate'))} | {_rate(now['rule_rate'], b.get('rule_rate'))} | "
            f"{_judge(now['judge_mean'], b.get('judge_mean'))} | {cost} | {latency} |")


def render_markdown(summary: dict, baseline: dict | None, failures: list[str]) -> str:
    base_levels = (baseline or {}).get("levels", {})
    lines = [
        "## Golden-set eval",
        "",
        f"Model `{summary['model']}` · judge `{summary['judge_model'] or 'off'}` · prompt `{summary['prompt_version']}` · "
        f"{summary['overall']['runs']} runs · {summary['generated_at']}",
        "",
        f"**{'FAIL' if failures else 'PASS'}**" + (" (compared with the baseline)" if baseline else " (no baseline)"),
        "",
        "| Level | Runs | Passed | Tool choice | Approval rule | Tone rules | Judge (1-5) | Cost | p95 latency |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for level, stats in summary["levels"].items():
        lines.append(_row(level, stats, base_levels.get(level)))
    lines.append(_row("All", summary["overall"], (baseline or {}).get("overall")))
    if failures:
        lines += ["", "### Why it fails", ""] + [f"- {f}" for f in failures]
    failed_cases = [c for c in summary["cases"] if not c["passed"]]
    if failed_cases:
        lines += ["", "### Cases that failed", ""]
        lines += [f"- `{c['id']}` (level {c['level']}): {'; '.join(c['failures'])}" for c in failed_cases]
    return "\n".join(lines) + "\n"


def _parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m evals.run", description=__doc__.split("\n\n")[0])
    p.add_argument("--level", type=int, choices=range(4))
    p.add_argument("--repeat", type=int, default=1, help="tries per case (live runs vary)")
    p.add_argument("--out-dir", type=Path, default=RESULTS_DIR)
    p.add_argument("--baseline", type=Path, help="defaults to OUT_DIR/baseline.json if it exists")
    p.add_argument("--write-baseline", action="store_true", help="save this run as OUT_DIR/baseline.json")
    p.add_argument("--no-judge", action="store_true", help="skip the LLM tone judge")
    p.add_argument("--model", help="agent model (default: GROQ_MODEL)")
    p.add_argument("--judge-model", help=f"judge model (default: EVAL_JUDGE_MODEL or {DEFAULT_JUDGE_MODEL})")
    p.add_argument("--pace", type=float, default=2.0, help="seconds between cases, to stay under rate limits")
    return p.parse_args(argv)


async def _run_all(cases, repeat, model_factory, judge, pace) -> list[CaseResult]:
    from evals.harness import EvalHarness

    results = []
    async with EvalHarness() as harness:
        for case in cases:
            for attempt in range(repeat):
                run = await harness.run_case(case, model_factory(case))
                res = evaluate(case, run, judge)
                results.append(res)
                mark = "pass" if res.passed else "FAIL"
                print(f"[{mark}] {case.id} #{attempt + 1}" + ("" if res.passed else f": {'; '.join(res.failures())}"),
                      file=sys.stderr)
                if pace:
                    await asyncio.sleep(pace)
    return results


def main(argv: list[str] | None = None, *, model_factory: Callable[[Any], Any] | None = None,
         judge_factory: Callable[[], Any] | None = None, model_name: str | None = None,
         judge_name: str | None = None) -> int:
    args = _parse(argv)
    if model_factory is None:
        if not os.getenv("GROQ_API_KEY"):
            print("GROQ_API_KEY is not set: the live eval needs it.", file=sys.stderr)
            return 2
        from langchain.chat_models import init_chat_model
        from src.agent import GROQ_MODEL
        model_name = args.model or GROQ_MODEL
        live = init_chat_model(model_name, model_provider="groq")
        model_factory = lambda case: live  # noqa: E731
    judge = None
    if not args.no_judge:
        if judge_factory is None:
            from langchain.chat_models import init_chat_model
            judge_name = args.judge_model or os.getenv("EVAL_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)
            judge = init_chat_model(judge_name, model_provider="groq", temperature=0)
        else:
            judge = judge_factory()

    baseline_path = args.baseline or args.out_dir / "baseline.json"
    if args.baseline and not args.baseline.exists():
        print(f"No baseline at {args.baseline}", file=sys.stderr)
        return 2
    baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else None

    cases = load_cases(level=args.level)
    results = asyncio.run(_run_all(cases, args.repeat, model_factory, judge, args.pace))
    summary = summarize(results, model=model_name, judge_model=judge_name if judge else None)
    failures = gate(summary, baseline)
    report = render_markdown(summary, baseline, failures)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "latest.json").write_text(json.dumps(summary, indent=2) + "\n")
    (args.out_dir / "latest.md").write_text(report)
    if args.write_baseline:
        (args.out_dir / "baseline.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(report)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
