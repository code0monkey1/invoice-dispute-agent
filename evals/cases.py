"""Golden cases: load and validate evals/golden/level_N.yaml.

Validation is strict on purpose. A misspelt tool name or rubric would make a
check vacuous (a must_not_call that can never match passes forever), so it
fails loading instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

GOLDEN_DIR = Path(__file__).parent / "golden"

TOOL_NAMES = {
    "update_invoice_details", "check_invoice_status", "draft_invoice_delivery_email",
    "draft_polite_reminder", "escalate_dispute", "draft_formal_demand_letter",
    "lookup_small_claims_procedures", "generate_court_filing_guide", "draft_final_notice",
    "mark_invoice_pending", "mark_invoice_paid", "record_partial_payment",
}
RUBRICS = {"delivery", "friendly", "formal", "final", "advice"}
MENTION_KEYS = {"invoice_id", "client_name", "balance", "amount", "jurisdiction"}

# Unset expectations are distinguished from "expect no interrupt" (None).
UNSET = object()

DEFAULT_INVOICE = {
    "client_name": "Acme Corp",
    "client_email": "ap@acme.example",
    "invoice_amount": 1200,
    "amount_paid": 0,
    "days_overdue": 21,
    "jurisdiction": "California",
}


class CaseError(ValueError):
    """A golden case file is malformed."""


@dataclass
class Tone:
    rubric: str | None = None
    must_mention: list[str] = field(default_factory=list)
    forbid: list[str] = field(default_factory=list)


@dataclass
class Expect:
    must_call: list[str] = field(default_factory=list)
    must_call_any: list[str] = field(default_factory=list)
    must_not_call: list[str] = field(default_factory=list)
    interrupt_tool: Any = UNSET  # a tool name, None for "no approval card", or UNSET
    tone: Tone = field(default_factory=Tone)


@dataclass
class Case:
    id: str
    level: int
    description: str
    turn: dict
    expect: Expect
    scripted: list[dict]
    invoice: dict
    source: str

    @property
    def invoice_number(self) -> str:
        return self.invoice["invoice_id"]


def _names(case_id: str, key: str, value: Any) -> list[str]:
    names = list(value or [])
    unknown = [n for n in names if n not in TOOL_NAMES]
    if unknown:
        raise CaseError(f"case {case_id}: {key} names unknown tool(s) {', '.join(unknown)}")
    return names


def _parse_case(raw: dict, level: int, source: str) -> Case:
    case_id = raw.get("id")
    if not case_id:
        raise CaseError(f"{source}: a case has no id")
    turn = raw.get("turn")
    if not isinstance(turn, dict) or not ({"chat", "client_reply"} & set(turn)):
        raise CaseError(f"case {case_id}: turn must have 'chat' or 'client_reply'")

    exp = raw.get("expect") or {}
    tone_raw = exp.get("tone") or {}
    rubric = tone_raw.get("rubric")
    if rubric is not None and rubric not in RUBRICS:
        raise CaseError(f"case {case_id}: unknown rubric {rubric!r} (use one of {sorted(RUBRICS)})")
    mentions = list(tone_raw.get("must_mention") or [])
    bad_mentions = [m for m in mentions if m not in MENTION_KEYS]
    if bad_mentions:
        raise CaseError(f"case {case_id}: must_mention keys {bad_mentions} (use {sorted(MENTION_KEYS)})")
    interrupt = exp["interrupt_tool"] if "interrupt_tool" in exp else UNSET
    if interrupt not in (UNSET, None):
        _names(case_id, "interrupt_tool", [interrupt])

    expect = Expect(
        must_call=_names(case_id, "must_call", exp.get("must_call")),
        must_call_any=_names(case_id, "must_call_any", exp.get("must_call_any")),
        must_not_call=_names(case_id, "must_not_call", exp.get("must_not_call")),
        interrupt_tool=interrupt,
        tone=Tone(rubric=rubric, must_mention=mentions, forbid=list(tone_raw.get("forbid") or [])),
    )
    scripted = list(raw.get("scripted") or [])
    for step in scripted:
        if "tool" in step:
            _names(case_id, "scripted", [step["tool"]])
        elif "text" not in step:
            raise CaseError(f"case {case_id}: scripted steps need 'tool' or 'text'")

    invoice = {**DEFAULT_INVOICE, "invoice_id": f"INV-EVAL-{level}", **(raw.get("invoice") or {})}
    return Case(
        id=case_id, level=level, description=raw.get("description", ""), turn=turn,
        expect=expect, scripted=scripted, invoice=invoice, source=source,
    )


def load_cases(directory: Path | str | None = None, level: int | None = None) -> list[Case]:
    directory = Path(directory) if directory else GOLDEN_DIR
    cases: list[Case] = []
    seen: set[str] = set()
    for path in sorted(directory.glob("level_*.yaml")):
        doc = yaml.safe_load(path.read_text()) or {}
        file_level = doc.get("level")
        if file_level not in (0, 1, 2, 3):
            raise CaseError(f"{path.name}: level must be 0-3")
        for raw in doc.get("cases") or []:
            case = _parse_case(raw, file_level, path.name)
            if case.id in seen:
                raise CaseError(f"case {case.id}: duplicate id")
            seen.add(case.id)
            cases.append(case)
    if level is not None:
        cases = [c for c in cases if c.level == level]
    return cases
