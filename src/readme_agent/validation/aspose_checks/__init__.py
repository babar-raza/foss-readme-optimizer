"""T3 -- registry over the vendored aspose.org check battery.

Wraps every `check_*` function in the vendored `readme_refresh_checks` module
with typed metadata (section-scoped vs document-global; hard-gate vs
heuristic) derived mechanically from the vendored module's own docstring
conventions, rather than hand-maintained -- this repo's own resolution 7
("check inventory is derived, never a binding constant") applies here too.

Path/config indirection: the vendored module is never imported by its
original package-relative form (`from lib.api_table_dupes import ...`);
this module resolves it once, from a fixed, explicit sys.path insertion
scoped to this repo's vendored copy, so nothing here depends on aspose.org's
original package layout still existing anywhere.
"""

from __future__ import annotations

import inspect
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

_REPO_ROOT = Path(__file__).resolve().parents[4]
_VENDORED_PIPELINE_ROOT = (
    _REPO_ROOT / "src" / "readme_agent" / "vendored_asposeorg" / "scripts" / "pipeline"
)
_VENDORED_FOSS_ROOT = _VENDORED_PIPELINE_ROOT / "commands" / "foss"

CheckSeverity = Literal["hard_gate", "heuristic"]
CheckScope = Literal["section", "document_global"]


def _ensure_vendored_on_path() -> None:
    for path in (str(_VENDORED_PIPELINE_ROOT), str(_VENDORED_FOSS_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)


def _load_vendored_checks_module() -> Any:
    _ensure_vendored_on_path()
    import readme_refresh_checks  # noqa: PLC0415 -- deliberately lazy; see module docstring

    return readme_refresh_checks


# Section inference: mechanical, name-prefix-driven. Every prefix here was
# read from the actual 89 check names (T1B closeout); a name that matches no
# rule is classified `document_global` by default -- the safer default,
# since a document-global check running on a section that didn't change is
# merely redundant, while a section-scoped check that should have run
# document-globally could silently miss a real cross-section defect.
_SECTION_PREFIX_RULES: tuple[tuple[str, str], ...] = (
    ("check_diagram_", "At a Glance"),
    ("check_banner_", "header"),
    ("check_badge_", "header"),
    ("check_enterprise_edition_", "Scope and Limitations"),
    ("check_license_", "License"),
    ("check_dependency_", "Dependencies"),
    ("check_dependencies_", "Dependencies"),
    ("check_api_reference_", "API Reference"),
    ("check_key_capabilities_", "Key Capabilities"),
    ("check_examples_table_", "Additional Examples"),
    ("check_dev_test_", "Development and Testing"),
    ("check_development_testing_", "Development and Testing"),
    ("check_scope_limitations_", "Scope and Limitations"),
    ("check_project_structure_", "Project Structure"),
    ("check_capability_scope_", "Key Capabilities"),
)

# Cross-cutting/reconciliation checks that inherently span the whole
# document by design (disposition coverage, duplicate detection across all
# units, diff/idempotency checks, narration/casing/structure rules that
# apply document-wide) -- classified document_global explicitly, not by
# falling through the default, so the reasoning is visible and testable.
_EXPLICIT_DOCUMENT_GLOBAL_PREFIXES: tuple[str, ...] = (
    "check_content_unit_",
    "check_structural_unit_",
    "check_code_example_",
    "check_no_",
    "check_process_narration_",
    "check_section_",
    "check_heading_title_case",
    "check_required_sections",
    "check_dropped_content",
    "check_only_mermaid_block_changed",
    "check_only_sections_changed",
    "check_format_name_casing",
    "check_named_member_accuracy",
    "check_unqualified_dependency_claims",
)

_HARD_GATE_PATTERN = re.compile(r"\bhard gate\b", re.IGNORECASE)
_HEURISTIC_PATTERN = re.compile(r"\bheuristic\b", re.IGNORECASE)


@dataclass(frozen=True)
class AsposeCheckDescriptorV1:
    """One classified, invocable check from the vendored battery."""

    name: str
    function: Callable[..., Any]
    severity: CheckSeverity
    scope: CheckScope
    section: str | None
    doc_summary: str
    parameters: tuple[str, ...]

    def invoke(self, **kwargs: Any) -> Any:
        """Call the underlying vendored function with exactly the keyword
        arguments it declares; raises TypeError (not silently drops) if the
        caller supplies an argument the check doesn't accept, or omits one
        it requires -- fail closed, matching this repo's own convention."""

        accepted = set(self.parameters)
        extra = set(kwargs) - accepted
        if extra:
            raise TypeError(f"{self.name} does not accept: {sorted(extra)}")
        return self.function(**kwargs)


def _classify_severity(docstring: str) -> CheckSeverity:
    hard = _HARD_GATE_PATTERN.search(docstring)
    heuristic = _HEURISTIC_PATTERN.search(docstring)
    if hard and heuristic:
        # Several docstrings mention both (e.g. explaining a heuristic was
        # "downgraded from an originally-planned hard gate") -- whichever
        # term appears FIRST is the check's actual current classification;
        # the vendored module's own convention states the current status
        # up front and explains history afterward.
        return "hard_gate" if hard.start() < heuristic.start() else "heuristic"
    if hard:
        return "hard_gate"
    if heuristic:
        return "heuristic"
    # No explicit marker found: fail closed to the stricter classification
    # rather than silently treating an unmarked check as non-blocking.
    return "hard_gate"


def _classify_scope(name: str) -> tuple[CheckScope, str | None]:
    for prefix, section in _SECTION_PREFIX_RULES:
        if name.startswith(prefix):
            return "section", section
    for prefix in _EXPLICIT_DOCUMENT_GLOBAL_PREFIXES:
        if name.startswith(prefix):
            return "document_global", None
    return "document_global", None


def load_check_registry() -> dict[str, AsposeCheckDescriptorV1]:
    """Derive the complete, current check inventory from the vendored module
    itself -- never a hand-maintained count (this repo's resolution 7)."""

    module = _load_vendored_checks_module()
    registry: dict[str, AsposeCheckDescriptorV1] = {}
    for name in sorted(dir(module)):
        if not name.startswith("check_"):
            continue
        function = getattr(module, name)
        if not callable(function):
            continue
        docstring = inspect.getdoc(function) or ""
        severity = _classify_severity(docstring)
        scope, section = _classify_scope(name)
        parameters = tuple(inspect.signature(function).parameters)
        registry[name] = AsposeCheckDescriptorV1(
            name=name,
            function=function,
            severity=severity,
            scope=scope,
            section=section,
            doc_summary=docstring.splitlines()[0] if docstring else "",
            parameters=parameters,
        )
    return registry


__all__ = [
    "AsposeCheckDescriptorV1",
    "CheckScope",
    "CheckSeverity",
    "load_check_registry",
]
