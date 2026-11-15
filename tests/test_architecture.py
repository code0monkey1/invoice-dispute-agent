"""The dependency rule: imports point toward business policy.

    api/index.py -> web -> usecases -> domain
                 adapters -> ports -> domain

- src/domain imports only the standard library.
- src/ports imports only the domain.
- src/usecases imports only the domain and ports.
- Nothing under src/ imports the HTTP layer.

KNOWN_VIOLATIONS lists what breaks the rule today. It must match exactly, so
fixing one means deleting its line here, and nobody can add a new one unnoticed.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INNER_LAYERS = {
    "src/domain": (),
    "src/ports": ("src.domain",),
    "src/usecases": ("src.domain", "src.ports"),
}

# (file, imported module): policy and adapters reaching straight into the database layer.
KNOWN_VIOLATIONS = {
    ("src/services/invoice_service.py", "src.db"),
    ("src/services/conversation_summary.py", "src.db"),
    ("src/services/gmail_service.py", "src.db"),
    ("src/observability/tracer.py", "src.db"),
}
DATABASE_MODULE = "src.db"
MAY_IMPORT_DATABASE = ("src/db.py", "src/adapters/")


def imports_of(path: Path) -> set[str]:
    """Absolute module names a file imports ('from src import db' gives 'src.db')."""
    found = set()
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def python_files(folder: str):
    return sorted(p for p in (ROOT / folder).rglob("*.py") if "__pycache__" not in p.parts)


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_project_module(name: str) -> bool:
    return name.split(".")[0] in {"src", "api", "web", "evals", "tests"}


def is_stdlib(name: str) -> bool:
    return name.split(".")[0] in sys.stdlib_module_names


def layer_violations(folder: str, allowed: tuple[str, ...]) -> list[str]:
    problems = []
    for path in python_files(folder) + [p for p in [ROOT / f"{folder}.py"] if p.exists()]:
        for name in sorted(imports_of(path) - {"src"}):  # bare 'src' is only the package of 'from src import x'
            inside = name == folder.replace("/", ".") or name.startswith(folder.replace("/", ".") + ".")
            permitted = any(name == a or name.startswith(a + ".") for a in allowed)
            if is_project_module(name) and not (inside or permitted):
                problems.append(f"{relative(path)} imports {name}")
            elif not is_project_module(name) and not is_stdlib(name):
                problems.append(f"{relative(path)} imports third-party {name}")
    return problems


def test_inner_layers_import_only_what_is_further_in():
    problems = [p for folder, allowed in INNER_LAYERS.items() for p in layer_violations(folder, allowed)]
    assert problems == []


def test_nothing_under_src_imports_the_http_layer():
    offenders = [relative(p) for p in python_files("src")
                 if any(n.split(".")[0] in {"api", "web"} for n in imports_of(p))]
    assert offenders == []


def test_only_known_modules_reach_into_the_database_layer():
    actual = {
        (relative(path), DATABASE_MODULE)
        for path in python_files("src")
        if not relative(path).startswith(MAY_IMPORT_DATABASE)
        and any(n == DATABASE_MODULE or n.startswith(DATABASE_MODULE + ".") for n in imports_of(path))
    }
    assert actual == KNOWN_VIOLATIONS


def test_the_rule_catches_a_forbidden_import(tmp_path, monkeypatch):
    """The checker itself: a domain file importing the database or a framework is reported."""
    domain = tmp_path / "src" / "domain"
    domain.mkdir(parents=True)
    (domain / "rules.py").write_text("import json\nfrom src import db\nimport fastapi\nfrom src.domain import other\n")
    monkeypatch.setattr(sys.modules[__name__], "ROOT", tmp_path)

    assert sorted(layer_violations("src/domain", ())) == [
        "src/domain/rules.py imports src.db",
        "src/domain/rules.py imports third-party fastapi",
    ]
