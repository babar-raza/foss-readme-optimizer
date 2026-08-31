"""Every format corroborator must emit only canonical, recognized format codes.

PWD-008: `python_words_format_functionality.py` emitted `format="MD"` for Markdown
import/export -- but the project's own canonical vocabulary (`format_vocabulary.py`)
only ever recognizes `"MARKDOWN"`; `"MD"` is not a registered format abbreviation
anywhere. A corroborator authorizing a real, test-proven capability under an
unrecognized name is silently useless: `explicit_format_roles()` never matches it
against a candidate's real mention of the canonical name, so the capability stays
rejected as unauthorized regardless of how solid the underlying evidence is. No
existing test caught this, because each corroborator's own test only ever checked
internal consistency (does the corroborator return what the corroborator itself
defines), never cross-checked against the shared vocabulary every other part of the
pipeline actually matches against. This statically parses every corroborator's source
for every literal `format=` argument it can emit and requires each one to be a real,
recognized `DOCUMENT_FORMAT_ABBREVIATIONS` member -- closing the whole class of bug,
not just this one instance.
"""

from __future__ import annotations

import ast
from pathlib import Path

from readme_agent.facts.format_vocabulary import DOCUMENT_FORMAT_ABBREVIATIONS

FACTS_ROOT = Path(__file__).resolve().parents[2] / "src" / "readme_agent" / "facts"


def _corroborator_format_literals(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    literals: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        callee = node.func
        name = callee.id if isinstance(callee, ast.Name) else getattr(callee, "attr", None)
        if name != "AsposeOrgFormatEvidenceV1":
            continue
        for keyword in node.keywords:
            if (
                keyword.arg == "format"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                literals.add(keyword.value.value)
    return literals


def test_every_format_corroborator_emits_only_canonical_format_codes() -> None:
    corroborator_paths = sorted(FACTS_ROOT.glob("*_format_functionality.py"))
    assert corroborator_paths, "expected at least one format corroborator module"

    unrecognized: dict[str, set[str]] = {}
    for path in corroborator_paths:
        literals = _corroborator_format_literals(path)
        bad = literals - DOCUMENT_FORMAT_ABBREVIATIONS
        if bad:
            unrecognized[path.name] = bad

    assert not unrecognized, (
        "corroborator(s) emit a format code absent from DOCUMENT_FORMAT_ABBREVIATIONS -- such a "
        f"fact can never match a candidate's real mention of the canonical name: {unrecognized}"
    )
