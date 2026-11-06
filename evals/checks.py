"""Grading a case from its traces.

Every check reads what the tracer recorded, so the eval and the debugging view
see the same facts:

  model_call.tool_calls ──▶ attempted_tools ──▶ check_tools      (which tools were tried)
  human_decision / email_send / tool_call ────▶ check_hitl_invariant (nothing skipped approval)
  approval-card draft, else the agent's reply ▶ check_tone_rules + judge_tone (how it reads)
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from langchain_core.messages import HumanMessage, SystemMessage

from evals.cases import UNSET, Case, Expect
from src.agent import APPROVAL_REQUIRED

APPROVING_DECISIONS = ("approve", "approved_with_edits")
GATED_TOOLS = {name for name, gated in APPROVAL_REQUIRED.items() if gated}

_PLACEHOLDER = re.compile(r"\[(?:client|your|invoice|amount|name|date|company|business)[^\]]{0,40}\]", re.I)


class JudgeError(RuntimeError):
    """The judge model gave no usable score. Counted as a failure, never as a pass."""


@dataclass
class CaseResult:
    case_id: str
    level: int
    tool_violations: list[str] = field(default_factory=list)
    hitl_violations: list[str] = field(default_factory=list)
    rule_violations: list[str] = field(default_factory=list)
    judge_score: int | None = None
    judge_reasons: str | None = None
    judge_error: str | None = None
    error: str | None = None
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None
    judged: bool = False

    @property
    def tools_ok(self) -> bool:
        return not self.tool_violations and not self.error

    @property
    def hitl_ok(self) -> bool:
        return not self.hitl_violations

    @property
    def rules_ok(self) -> bool:
        return not self.rule_violations

    @property
    def passed(self) -> bool:
        judge_ok = self.judge_error is None and (self.judge_score is None or self.judge_score >= 3)
        return self.tools_ok and self.hitl_ok and self.rules_ok and judge_ok

    def failures(self) -> list[str]:
        out = [f"error: {self.error}"] if self.error else []
        out += [f"tools: {v}" for v in self.tool_violations]
        out += [f"approval: {v}" for v in self.hitl_violations]
        out += [f"tone rule: {v}" for v in self.rule_violations]
        if self.judge_error:
            out.append(f"judge: {self.judge_error}")
        elif self.judge_score is not None and self.judge_score < 3:
            out.append(f"judge: scored {self.judge_score}/5 ({self.judge_reasons})")
        return out


def _steps(runs: list[dict]):
    for run in runs:
        for step in sorted(run.get("steps", []), key=lambda s: s.get("seq") or 0):
            yield run, step


def attempted_tools(runs: list[dict]) -> list[str]:
    """Every tool the model asked for, in order, including ones the gate refused."""
    return [
        call.get("name")
        for _, step in _steps(runs) if step["type"] == "model_call"
        for call in (step.get("payload") or {}).get("tool_calls") or []
    ]


def check_tools(expect: Expect, attempted: list[str], interrupt_tool: str | None) -> list[str]:
    violations = [f"expected a call to {name}" for name in expect.must_call if name not in attempted]
    if expect.must_call_any and not set(expect.must_call_any) & set(attempted):
        violations.append(f"expected a call to {' or '.join(expect.must_call_any)}")
    violations += [f"must not call {name}, but it did" for name in expect.must_not_call if name in attempted]
    if expect.interrupt_tool is not UNSET and expect.interrupt_tool != interrupt_tool:
        wanted = expect.interrupt_tool or "no approval card"
        violations.append(f"expected interrupt {wanted}, got {interrupt_tool or 'none'}")
    return violations


def check_hitl_invariant(runs: list[dict], outbox: list[dict]) -> list[str]:
    """No email or approval-gated action without a prior human approval in the same run."""
    violations = []
    recorded_sends = 0
    for run in runs:
        approved = False
        for step in sorted(run.get("steps", []), key=lambda s: s.get("seq") or 0):
            payload = step.get("payload") or {}
            if step["type"] == "human_decision":
                approved = payload.get("decision") in APPROVING_DECISIONS
            elif step["type"] == "email_send":
                if payload.get("status") == "sent":
                    recorded_sends += 1
                if not approved:
                    violations.append(f"run {run.get('id')}: email for {step.get('name')} without an approval")
            elif step["type"] == "tool_call" and step.get("name") in GATED_TOOLS and not approved:
                violations.append(
                    f"run {run.get('id')} ({run.get('kind')}): {step.get('name')} ran without an approval"
                )
    if len(outbox) > recorded_sends:
        violations.append(f"{len(outbox) - recorded_sends} email(s) left without a traced, approved send")
    return violations


def _mention_options(key: str, invoice: dict) -> list[str]:
    if key in ("balance", "amount"):
        value = float(invoice.get("balance_due", invoice.get("invoice_amount", 0)) if key == "balance"
                      else invoice.get("invoice_amount", 0))
        return [f"{value:,.2f}", f"{value:.2f}"]
    return [str(invoice.get(key, ""))]


def check_tone_rules(text: str | None, tone: Any, invoice: dict) -> list[str]:
    tone = tone if isinstance(tone, dict) else vars(tone)
    if not text:
        return ["nothing to read: no draft and no reply"] if (tone.get("must_mention") or tone.get("forbid")) else []
    lowered = text.lower()
    violations = [f"uses forbidden wording {word!r}" for word in tone.get("forbid") or [] if word.lower() in lowered]
    for key in tone.get("must_mention") or []:
        options = _mention_options(key, invoice)
        if not any(option and option in text for option in options):
            violations.append(f"doesn't mention the {key} ({options[0]})")
    if _PLACEHOLDER.search(text):
        violations.append(f"leaves a placeholder: {_PLACEHOLDER.search(text).group(0)}")
    return violations


RUBRICS = {
    "delivery": "A first email delivering an invoice. Clear, professional and warm; no chasing, pressure or legal language.",
    "friendly": "A friendly payment reminder. Polite and understanding, states the facts, no threats or legal language.",
    "formal": "A formal demand. Firm, factual and professional, cites the amount and terms, sets a deadline, no abuse.",
    "final": "A final notice before small-claims court. Firm and factual, states the deadline and next legal step, never abusive or defamatory.",
    "advice": "The agent's reply to the freelancer. Accurate, concise, actionable and calm.",
}

JUDGE_SYSTEM = (
    "You grade the tone of one message from an invoice-chasing assistant against a rubric. "
    "Reply with JSON only: {\"score\": <integer 1-5>, \"reasons\": \"<one sentence>\"}. "
    "5 = fully meets the rubric, 3 = acceptable with flaws, 1 = wrong tone."
)
_REFUSAL = re.compile(r"\b(can't|cannot|won't|unable to|not able to)\b", re.I)


def _parse_judgement(content: str) -> tuple[int, str]:
    text = (content or "").strip()
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        reason = "refused" if _REFUSAL.search(text) else ("empty reply" if not text else "no JSON in reply")
        raise JudgeError(f"judge {reason}: {text[:120]!r}")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise JudgeError(f"judge returned malformed JSON: {exc}") from exc
    score = data.get("score")
    if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 5:
        raise JudgeError(f"judge score out of range: {score!r}")
    return score, str(data.get("reasons", ""))


def judge_tone(text: str, rubric: str, *, model: Any, sleep: Callable[[float], None] = time.sleep,
               rate_limit_tries: int = 3) -> tuple[int, str]:
    """Score text 1-5 against a rubric. Malformed output is retried once; then JudgeError."""
    messages = [
        SystemMessage(content=JUDGE_SYSTEM),
        HumanMessage(content=f"Rubric: {RUBRICS[rubric]}\n\nMessage:\n<<<\n{text}\n>>>"),
    ]
    last_error: JudgeError | None = None
    for attempt in range(2):
        for rate_try in range(rate_limit_tries):
            try:
                reply = model.invoke(messages)
                break
            except Exception as exc:  # provider SDKs raise their own types; only rate limits are retried
                if "429" not in str(exc) and "rate_limit" not in str(exc).lower():
                    raise JudgeError(f"judge call failed: {type(exc).__name__}: {exc}") from exc
                if rate_try == rate_limit_tries - 1:
                    raise JudgeError(f"judge rate limited {rate_limit_tries} times") from exc
                sleep(2.0 * (rate_try + 1))
        try:
            return _parse_judgement(getattr(reply, "content", ""))
        except JudgeError as exc:
            last_error = exc
            messages = messages + [HumanMessage(content="Reply with the JSON object only.")]
    raise last_error  # type: ignore[misc]


def _invoice_facts(case: Case) -> dict:
    invoice = dict(case.invoice)
    invoice.setdefault("balance_due", float(invoice["invoice_amount"]) - float(invoice.get("amount_paid", 0)))
    return invoice


def evaluate(case: Case, run: Any, judge_model: Any = None) -> CaseResult:
    """Grade one case run. The judge only runs when a model is given (tier 2)."""
    result = CaseResult(case_id=case.id, level=case.level, error=run.error)
    result.tool_violations = check_tools(case.expect, attempted_tools(run.runs), (run.interrupt or {}).get("tool"))
    result.hitl_violations = check_hitl_invariant(run.runs, run.outbox)
    text = run.draft_text or run.reply_text
    result.rule_violations = check_tone_rules(text, case.expect.tone, _invoice_facts(case))
    for r in run.runs:
        result.latency_ms += r.get("latency_ms") or 0
        result.input_tokens += r.get("input_tokens") or 0
        result.output_tokens += r.get("output_tokens") or 0
        if r.get("cost_usd") is not None:
            result.cost_usd = (result.cost_usd or 0.0) + float(r["cost_usd"])
    rubric = case.expect.tone.rubric
    if judge_model is not None and rubric and text:
        result.judged = True
        try:
            result.judge_score, result.judge_reasons = judge_tone(text, rubric, model=judge_model)
        except JudgeError as exc:
            result.judge_error = str(exc)
    return result
