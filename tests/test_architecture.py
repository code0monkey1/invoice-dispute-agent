"""The dependency rule: imports point toward business policy.

    api/index.py -> web -> usecases -> domain
                 adapters -> ports -> domain

- src/domain imports only the standard library.
- src/ports imports only the domain.
- src/usecases imports only the domain and ports.
- Nothing under src/ imports the HTTP layer.

Tests and evals replace collaborators through api.index.deps, never by
patching api.index itself: such a patch keeps "working" after the code it
targets moves elsewhere, while the real collaborator runs.

KNOWN_VIOLATIONS lists what breaks the rule today. It must match exactly, so
fixing one means deleting its line here, and nobody can add a new one unnoticed.
"""
import ast
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INNER_LAYERS = {
    "src/ports": ("src.domain",),
    "src/usecases": ("src.domain", "src.ports"),
}

# (file, imported module): policy and adapters reaching straight into the database layer.
KNOWN_VIOLATIONS = set()
DATABASE_MODULE = "src.adapters.supabase"
MAY_IMPORT_DATABASE = ("src/adapters/supabase/",)


def imports_of(path: Path) -> set[str]:
    """Absolute module names a file imports ('from src import db' gives 'src.db')."""
    found = set()
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                package = ".".join(path.relative_to(ROOT).parent.parts)
                module = importlib.util.resolve_name("." * node.level + (node.module or ""), package)
            else:
                module = node.module
            if module:
                found.add(module)
                found.update(f"{module}.{alias.name}" for alias in node.names)
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


def test_domain_imports_only_the_standard_library_and_other_domain_modules():
    problems = layer_violations("src/domain", ())
    assert not problems, "Domain may depend only on the standard library and domain modules:\n" + "\n".join(problems)


def test_inner_layers_import_only_what_is_further_in():
    problems = [p for folder, allowed in INNER_LAYERS.items() for p in layer_violations(folder, allowed)]
    assert not problems, "Inner layers may depend only on domain and ports as appropriate:\n" + "\n".join(problems)


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


def adapter_imports() -> list[str]:
    """Adapters are independently replaceable and never compose one another."""
    return [
        f"{relative(path)} imports {name}"
        for path in python_files("src/adapters")
        for name in sorted(imports_of(path))
        if name == "src.adapters" or name.startswith("src.adapters.")
    ]


def test_adapters_do_not_import_other_adapters():
    assert adapter_imports() == []


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


def test_the_adapter_rule_catches_cross_adapter_composition(tmp_path, monkeypatch):
    adapters = tmp_path / "src" / "adapters"
    adapters.mkdir(parents=True)
    (adapters / "gmail.py").write_text("from src.adapters import supabase\n")
    monkeypatch.setattr(sys.modules[__name__], "ROOT", tmp_path)

    assert adapter_imports() == [
        "src/adapters/gmail.py imports src.adapters",
        "src/adapters/gmail.py imports src.adapters.supabase",
    ]


ENTRY_MODULE = "api.index"
PATCHERS = {"setattr", "object"}  # monkeypatch.setattr / setattr / patch.object / mock.patch.object


def entry_module_aliases(tree: ast.AST) -> set[str]:
    """Names bound to api.index in a file: 'import api.index as x', and 'self._x = x' copies."""
    names = {alias.asname for node in ast.walk(tree) if isinstance(node, ast.Import)
             for alias in node.names if alias.name == ENTRY_MODULE and alias.asname}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name) and node.value.id in names:
            names.update(ast.unparse(t) for t in node.targets)
    return names


def entry_module_patches(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    aliases = entry_module_aliases(tree)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
        target = node.args[0]
        if name in PATCHERS and ast.unparse(target) in aliases:
            found.append(f"{relative(path)}:{node.lineno} patches {ENTRY_MODULE}")
        elif (name in {"patch", "setattr"} and isinstance(target, ast.Constant) and isinstance(target.value, str)
              and target.value.startswith(ENTRY_MODULE + ".")):
            found.append(f"{relative(path)}:{node.lineno} patches {target.value}")
    return found


def test_tests_and_evals_never_patch_the_entry_module():
    found = [p for folder in ("tests", "evals") for path in python_files(folder) for p in entry_module_patches(path)]
    assert found == []


def test_the_patch_rule_catches_every_spelling(tmp_path, monkeypatch):
    probe = tmp_path / "tests" / "test_probe.py"
    probe.parent.mkdir()
    probe.write_text(
        "import api.index as api_index\n"
        "from unittest.mock import patch\n"
        "def test(monkeypatch):\n"
        "    monkeypatch.setattr(api_index, 'agent', None)\n"          # line 4: forbidden
        "    monkeypatch.setattr(api_index.deps, 'agent', None)\n"     # allowed
        "    patch.object(api_index, 'get_invoice')\n"                # line 6: forbidden
        "    patch('api.index.get_invoice')\n"                         # line 7: forbidden
        "    monkeypatch.setattr('api.index.agent', None)\n"           # line 8: forbidden
        "class H:\n"
        "    def go(self):\n"
        "        self._api = api_index\n"
        "        patch.object(self._api, 'agent', None)\n"             # line 12: forbidden
    )
    monkeypatch.setattr(sys.modules[__name__], "ROOT", tmp_path)

    lines = [int(p.split(":")[1].split()[0]) for p in entry_module_patches(probe)]
    assert sorted(lines) == [4, 6, 7, 8, 12]


def test_relative_imports_cannot_bypass_layer_boundaries(tmp_path, monkeypatch):
    domain = tmp_path / "src" / "domain"
    domain.mkdir(parents=True)
    (domain / "rules.py").write_text(
        "from ..adapters import supabase\n"
        "from . import other\n"
        "from .other import policy\n"
    )
    monkeypatch.setattr(sys.modules[__name__], "ROOT", tmp_path)

    problems = layer_violations("src/domain", ())
    assert any("src.adapters.supabase" in problem for problem in problems)
    assert all("src.domain.other" not in problem for problem in problems)
