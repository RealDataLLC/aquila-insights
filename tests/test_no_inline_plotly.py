"""Guard: chart generators must load plotly.js from the CDN, not inline it.

Inlining adds ~4.8 MB per published page (see PR #66 and CLAUDE.md). Any
``write_html`` / ``to_html`` call in a generator has to pass
``include_plotlyjs`` with a value other than ``True`` (e.g. "cdn" or False).
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"archive", ".git", "tests", "notebooks"}


def _python_files():
    for path in ROOT.rglob("*.py"):
        if SKIP_DIRS.intersection(path.relative_to(ROOT).parts):
            continue
        yield path


def _inlining_calls(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name not in {"write_html", "to_html"}:
            continue
        kw = {k.arg: k.value for k in node.keywords}
        value = kw.get("include_plotlyjs")
        if value is None or (isinstance(value, ast.Constant) and value.value is True):
            yield f"{path.relative_to(ROOT)}:{node.lineno}"


def test_no_generator_inlines_plotly():
    offenders = [hit for p in _python_files() for hit in _inlining_calls(p)]
    assert offenders == [], "plotly.js would be inlined at: " + ", ".join(offenders)
