"""Guard a Mermaid syntax pitfall that broke GitHub's README rendering."""
from pathlib import Path
import re


def _sequence_note_errors(markdown: str) -> list[str]:
    errors = []
    for block in re.findall(r"```mermaid\s*\n(.*?)```", markdown, re.DOTALL):
        if not block.lstrip().startswith("sequenceDiagram"):
            continue
        for line in block.splitlines():
            if re.match(r"\s*Note\s+(?:over|left of|right of)\s+", line) and ";" in line:
                errors.append(line)
    return errors


def test_raw_semicolons_are_rejected_only_in_sequence_notes():
    broken = "```mermaid\nsequenceDiagram\nNote over A,B: first; second\n```"
    valid = "```mermaid\nsequenceDiagram\nNote over A,B: first. second\nA->>B: first and second\n```\n```mermaid\nflowchart LR\nA-->B; B-->C\n```"
    assert _sequence_note_errors(broken)
    assert not _sequence_note_errors(valid)


def test_readme_sequence_notes_do_not_split_on_semicolons():
    readme = Path(__file__).resolve().parents[1] / "README.md"
    assert not _sequence_note_errors(readme.read_text())
