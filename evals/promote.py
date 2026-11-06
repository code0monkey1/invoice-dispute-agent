"""Turn a real (bad) agent run into a golden case, so every bug found becomes a regression test.

    python -m evals.promote --run-id <X-Trace-Id> --level 1 --name court-threat \\
        [--out evals/golden/level_1.yaml]

Reads the run from Supabase (needs SUPABASE_URL/SUPABASE_KEY), and drafts a
case: the message that started the run, the tools the gate refused as
must_not_call, and the approval card it stopped at. Trace text is already
redacted. Review the expectations before committing: they describe what
should happen, not what did.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

from evals.cases import CaseError, _parse_case

_CLIENT_REPLY = re.compile(r"<client_reply>\s*(?P<body>.*?)\s*</client_reply>", re.S)


def _first_message(run: dict) -> str:
    for step in sorted(run.get("steps", []), key=lambda s: s.get("seq") or 0):
        if step["type"] == "model_call":
            return str(((step.get("payload") or {}).get("last_message") or {}).get("content") or "")
    return ""


def _turn(run: dict) -> dict:
    text = _first_message(run)
    match = _CLIENT_REPLY.search(text)
    if run.get("kind") != "inbound_reply" or not match:
        return {"chat": text}
    header, _, body = match.group("body").partition("\n\n")
    subject = next((line.split(":", 1)[1].strip() for line in header.splitlines() if line.startswith("Subject:")), "Re: Invoice")
    return {"client_reply": body.strip(), "subject": subject}


def case_from_run(run: dict, *, level: int, name: str) -> dict:
    steps = sorted(run.get("steps", []), key=lambda s: s.get("seq") or 0)
    attempted = [c.get("name") for s in steps if s["type"] == "model_call"
                 for c in (s.get("payload") or {}).get("tool_calls") or []]
    blocked = sorted({s["name"] for s in steps if s["type"] == "gate_blocked"})
    interrupt = next((s["name"] for s in steps if s["type"] == "interrupt"), None)
    expect: dict = {"must_not_call": blocked}
    if interrupt:
        expect["interrupt_tool"] = interrupt
    return {
        "id": f"l{level}-{name}",
        "description": (f"Promoted from trace run {run['id']} ({run.get('kind')}). "
                        f"The model asked for: {', '.join(attempted) or 'no tools'}. "
                        "Edit the expectations to the behaviour you want."),
        "turn": _turn(run),
        "expect": expect,
    }


def fetch_run(run_id: str) -> dict | None:
    from src import db

    run = db.get_agent_run(run_id)
    if run is None:
        return None
    run["steps"] = db.get_trace_steps([run_id]).get(run_id, [])
    return run


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m evals.promote", description=__doc__.split("\n\n")[0])
    p.add_argument("--run-id", required=True)
    p.add_argument("--level", type=int, choices=range(4), required=True)
    p.add_argument("--name", required=True, help="short slug; the case id becomes l<level>-<name>")
    p.add_argument("--out", type=Path, help="golden file to append to (default: print the case)")
    args = p.parse_args(argv)

    run = fetch_run(args.run_id)
    if run is None:
        print(f"No trace run with id {args.run_id}", file=sys.stderr)
        return 2
    case = case_from_run(run, level=args.level, name=args.name)
    try:
        _parse_case(case, args.level, "promoted")
    except CaseError as exc:
        print(f"The drafted case is invalid: {exc}", file=sys.stderr)
        return 2

    if args.out:
        doc = yaml.safe_load(args.out.read_text()) if args.out.exists() else {"level": args.level, "cases": []}
        doc.setdefault("cases", []).append(case)
        args.out.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
        print(f"Added {case['id']} to {args.out}")
    else:
        print(yaml.safe_dump(case, sort_keys=False, allow_unicode=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
