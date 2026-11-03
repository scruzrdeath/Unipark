"""Hexagonal rule: dependencies point towards the domain."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "parking"

FORBIDDEN = {
    "domain": ("parking.application", "parking.infrastructure", "parking.api", "fastapi", "sqlalchemy"),
    "application": ("parking.infrastructure", "parking.api", "fastapi", "sqlalchemy"),
    "api": ("parking.infrastructure", "sqlalchemy"),
    "infrastructure": ("parking.api",),
}


def imports_of(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_layers_respect_dependency_direction():
    violations = []
    for layer, banned in FORBIDDEN.items():
        for py in (ROOT / layer).rglob("*.py"):
            for module in imports_of(py):
                if any(module == b or module.startswith(b + ".") for b in banned):
                    violations.append(f"{py.relative_to(ROOT)} imports {module}")
    assert not violations, "\n".join(violations)
