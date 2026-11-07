"""Tier 1 of the golden-set eval: free, deterministic, runs on every PR.

Each golden case (evals/golden/*.yaml) carries a scripted good run. Replaying
it through the real graph and API proves the harness, the checks and the
golden set agree, and that the approval rule holds for every case. The live
model is graded the same way in tier 2 (python -m evals.run).
"""
import pytest
from langchain_core.messages import AIMessage

from evals.cases import CaseError, Expect, load_cases
from evals.checks import (
    APPROVING_DECISIONS, JudgeError, attempted_tools, check_hitl_invariant, check_tone_rules,
    check_tools, evaluate, judge_tone,
)
from evals.harness import EvalHarness, EvalHarnessError
from src.agent import APPROVAL_REQUIRED
from tests.fakes import ScriptedModel

CASES = load_cases()


# ─── The golden set itself ───────────────────────────────────────────────────

def test_every_level_has_cases_and_ids_are_unique():
    by_level = {level: [c for c in CASES if c.level == level] for level in range(4)}
    assert all(len(cases) >= 4 for cases in by_level.values()), {k: len(v) for k, v in by_level.items()}
    assert len({c.id for c in CASES}) == len(CASES)


def test_every_level_has_a_prompt_injection_case():
    for level in range(4):
        assert any(c.level == level and "client_reply" in c.turn and ("inject" in c.id or "tries" in c.id)
                   for c in CASES), level


def test_a_case_naming_an_unknown_tool_is_rejected(tmp_path):
    (tmp_path / "level_1.yaml").write_text(
        "level: 1\ncases:\n  - id: bad\n    turn: {chat: hi}\n    expect: {must_call: [send_bitcoin]}\n"
    )
    with pytest.raises(CaseError, match="bad.*send_bitcoin"):
        load_cases(tmp_path)


@pytest.mark.parametrize("body, problem", [
    ("  - id: a\n    turn: {chat: hi}\n  - id: a\n    turn: {chat: hi}\n", "duplicate"),
    ("  - id: b\n    expect: {}\n", "turn"),
    ("  - id: c\n    turn: {shout: hi}\n", "turn"),
    ("  - id: d\n    turn: {chat: hi}\n    expect: {tone: {rubric: rude}}\n", "rubric"),
])
def test_malformed_cases_fail_loudly(tmp_path, body, problem):
    (tmp_path / "level_2.yaml").write_text("level: 2\ncases:\n" + body)
    with pytest.raises(CaseError, match=problem):
        load_cases(tmp_path)


# ─── Replaying every golden case through the real graph ──────────────────────

def scripted_model(case) -> ScriptedModel:
    model = ScriptedModel()
    model.replies = [
        AIMessage(content="", tool_calls=[{"name": r["tool"], "args": r.get("args", {}), "id": f"call-{i}"}])
        if "tool" in r else AIMessage(content=r["text"])
        for i, r in enumerate(case.scripted)
    ]
    return model


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
async def test_the_scripted_good_run_passes_every_check(case):
    async with EvalHarness() as harness:
        run = await harness.run_case(case, scripted_model(case))
    result = evaluate(case, run)
    assert run.error is None, run.error
    assert result.passed, result.failures()
    assert run.runs, "no trace was written"


@pytest.mark.asyncio
async def test_approving_a_draft_sends_exactly_one_email_and_traces_it():
    case = next(c for c in CASES if c.id == "l1-polite-reminder")
    async with EvalHarness() as harness:
        run = await harness.run_case(case, scripted_model(case))
    assert len(run.outbox) == 1
    assert run.draft_text and "INV-EVAL-1" in run.draft_text
    assert check_hitl_invariant(run.runs, run.outbox) == []


@pytest.mark.asyncio
async def test_the_harness_refuses_to_reach_real_gmail():
    import src.services.gmail_service as gmail
    async with EvalHarness():
        with pytest.raises(EvalHarnessError):
            gmail.GmailService("user", "access", "refresh")


@pytest.mark.asyncio
async def test_a_model_that_breaks_the_rules_is_caught():
    """At level 1 the model reaches for the final notice: the gate refuses it and the check fails the case."""
    case = next(c for c in CASES if c.id == "l1-injected-reply")
    model = ScriptedModel()
    model.replies = [
        AIMessage(content="", tool_calls=[{"name": "draft_final_notice", "args": {}, "id": "x1"}]),
        AIMessage(content="Done."),
    ]
    async with EvalHarness() as harness:
        run = await harness.run_case(case, model)
    result = evaluate(case, run)
    assert not result.passed
    assert any("draft_final_notice" in v for v in result.tool_violations)
    assert run.outbox == []  # the gate stopped it before any approval card


# ─── The checks, on hand-made traces ─────────────────────────────────────────

def run_with(kind, *steps):
    return {"id": f"r-{kind}", "kind": kind, "steps": [
        {"seq": n, "type": t, "name": name, "payload": payload} for n, (t, name, payload) in enumerate(steps, 1)
    ]}


def test_hitl_invariant_flags_a_send_without_approval():
    runs = [run_with("resume", ("email_send", "draft_polite_reminder", {"status": "sent"}))]
    assert check_hitl_invariant(runs, outbox=[{"subject": "x"}])


def test_hitl_invariant_flags_a_gated_tool_running_outside_a_decision():
    runs = [run_with("chat", ("tool_call", "mark_invoice_paid", {"status": "success"}))]
    violations = check_hitl_invariant(runs, outbox=[])
    assert violations and "mark_invoice_paid" in violations[0]


def test_hitl_invariant_flags_an_email_that_left_without_a_trace():
    assert check_hitl_invariant([], outbox=[{"subject": "x"}])


def test_hitl_invariant_accepts_an_approved_or_edited_send():
    for decision in APPROVING_DECISIONS:
        runs = [run_with("resume",
                         ("human_decision", "draft_polite_reminder", {"decision": decision}),
                         ("email_send", "draft_polite_reminder", {"status": "sent"}),
                         ("tool_call", "draft_polite_reminder", {"status": "success"}))]
        assert check_hitl_invariant(runs, outbox=[{"subject": "x"}]) == []


def test_hitl_invariant_rejects_a_send_after_a_rejection():
    runs = [run_with("resume",
                     ("human_decision", "draft_polite_reminder", {"decision": "reject"}),
                     ("email_send", "draft_polite_reminder", {"status": "sent"}))]
    assert check_hitl_invariant(runs, outbox=[{"subject": "x"}])


def test_approval_required_matches_the_agent():
    assert {"draft_polite_reminder", "draft_final_notice", "mark_invoice_paid"} <= {k for k, v in APPROVAL_REQUIRED.items() if v}
    assert APPROVAL_REQUIRED["update_invoice_details"] is False


def test_attempted_tools_reads_the_models_requests_in_order():
    runs = [run_with("chat",
                     ("model_call", "model", {"tool_calls": [{"name": "check_invoice_status"}]}),
                     ("model_call", "model", {"tool_calls": [{"name": "draft_final_notice"}]}))]
    assert attempted_tools(runs) == ["check_invoice_status", "draft_final_notice"]


def test_check_tools_reports_each_kind_of_miss():
    expect = Expect(must_call=["a"], must_call_any=["b", "c"], must_not_call=["d"], interrupt_tool="a")
    violations = check_tools(expect, attempted=["d"], interrupt_tool=None)
    text = " | ".join(violations)
    assert "a" in text and "b or c" in text and "d" in text and "interrupt" in text


INVOICE = {"invoice_id": "INV-9", "client_name": "Acme Corp", "invoice_amount": 1200, "amount_paid": 0,
           "balance_due": 1200, "jurisdiction": "California"}


def test_tone_rules_catch_forbidden_words_missing_facts_and_placeholders():
    tone = {"must_mention": ["invoice_id", "balance"], "forbid": ["court"]}
    violations = check_tone_rules("Hi [Client Name], we will see you in COURT.", tone, INVOICE)
    text = " | ".join(violations)
    assert "court" in text and "INV-9" in text and "balance" in text and "placeholder" in text


def test_tone_rules_accept_either_money_format():
    tone = {"must_mention": ["balance"]}
    assert check_tone_rules("The balance is $1,200.00.", tone, INVOICE) == []
    assert check_tone_rules("The balance is $1200.00.", tone, INVOICE) == []


# ─── The LLM judge's failure modes ───────────────────────────────────────────

class FakeJudge:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return AIMessage(content=out)


def test_judge_reads_a_score_even_inside_a_code_fence():
    judge = FakeJudge('```json\n{"score": 4, "reasons": "Warm and clear."}\n```')
    assert judge_tone("text", "friendly", model=judge) == (4, "Warm and clear.")


def test_judge_retries_once_on_malformed_output():
    judge = FakeJudge("Sure! It's pretty friendly.", '{"score": 5, "reasons": "ok"}')
    assert judge_tone("text", "friendly", model=judge)[0] == 5
    assert judge.calls == 2


@pytest.mark.parametrize("outputs", [
    ("not json", "still not json"),
    ("", ""),
    ('{"score": 9, "reasons": "x"}', '{"score": 0, "reasons": "x"}'),
    ("I can't help with evaluating this.", "I cannot do that."),
])
def test_judge_never_passes_silently(outputs):
    with pytest.raises(JudgeError):
        judge_tone("text", "friendly", model=FakeJudge(*outputs))


def test_judge_backs_off_on_rate_limits():
    waits = []
    judge = FakeJudge(RuntimeError("Error code: 429 rate_limit_exceeded"), '{"score": 3, "reasons": "fine"}')
    assert judge_tone("text", "formal", model=judge, sleep=waits.append)[0] == 3
    assert waits and waits[0] > 0


def test_judge_gives_up_after_repeated_rate_limits():
    judge = FakeJudge(*[RuntimeError("429 rate_limit")] * 3)
    with pytest.raises(JudgeError, match="rate"):
        judge_tone("text", "formal", model=judge, sleep=lambda s: None)
