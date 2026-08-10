"""Distill repository-bound .NET API summaries into public capability phrases."""

from __future__ import annotations

import re
from collections.abc import Iterable

from readme_agent.facts.dotnet_repository_evidence_schema import DotnetApiTypeEvidenceV1

_MAX_CAPABILITIES = 8
_GENERIC_SUMMARY = re.compile(r"(?i)^represents (?:an? |the )?[a-z0-9_. ]+\.?$")
_CAPABILITY_VERBS = re.compile(
    r"(?i)\b(?:access|build|convert|create|extract|generate|load|manage|parse|process|"
    r"provide|read|render|save|transform|write)\w*\b"
)
_LOW_VALUE_TYPE_SUFFIXES = (
    "collection",
    "enum",
    "eventargs",
    "exception",
    "options",
    "parameter",
    "parameters",
    "settings",
    "style",
    "type",
)
_NON_VISITOR_SUMMARY = re.compile(
    r"(?i)\b(?:base (?:class|interface)|returned to the caller|reserved (?:for|sector)|"
    r"red-black tree|unallocated, storage, stream|\[content_types\]\.xml|"
    r"transformparams|matches docs\.aspose\.com)\b"
)
_ACTION_FORMS: dict[str, str] = {
    "access": "Access",
    "accesses": "Access",
    "build": "Build",
    "builds": "Build",
    "calculate": "Calculate",
    "calculates": "Calculate",
    "convert": "Convert",
    "converts": "Convert",
    "create": "Create",
    "creates": "Create",
    "delete": "Delete",
    "deletes": "Delete",
    "edit": "Edit",
    "edits": "Edit",
    "export": "Export",
    "exports": "Export",
    "extract": "Extract",
    "extracts": "Extract",
    "generate": "Generate",
    "generates": "Generate",
    "import": "Import",
    "imports": "Import",
    "load": "Load",
    "loads": "Load",
    "manage": "Manage",
    "manages": "Manage",
    "modify": "Modify",
    "modifies": "Modify",
    "process": "Process",
    "processes": "Process",
    "read": "Read",
    "reads": "Read",
    "render": "Render",
    "renders": "Render",
    "save": "Save",
    "saves": "Save",
    "transform": "Transform",
    "transforms": "Transform",
    "update": "Update",
    "updates": "Update",
    "write": "Write",
    "writes": "Write",
}


def _capability_score(record: DotnetApiTypeEvidenceV1) -> tuple[int, int, int, str]:
    summary = (record.summary or "").strip()
    return (
        0 if summary and not _GENERIC_SUMMARY.fullmatch(summary) else 1,
        -len(_CAPABILITY_VERBS.findall(summary)),
        1 if record.name.casefold().endswith(_LOW_VALUE_TYPE_SUFFIXES) else 0,
        record.qualified_name.casefold(),
    )


def _imperative_action_list(value: str) -> str | None:
    action_forms = "|".join(
        re.escape(action) for action in sorted(_ACTION_FORMS, key=len, reverse=True)
    )
    match = re.fullmatch(
        rf"((?:{action_forms})(?:(?:,\s*(?:and\s+)?|\s+and\s+)"
        rf"(?:{action_forms}))+)[ ]+(.+)",
        value.strip().rstrip("."),
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    raw_actions = re.findall(action_forms, match.group(1), flags=re.IGNORECASE)
    optional_actions = [_ACTION_FORMS.get(action.casefold()) for action in raw_actions]
    actions = [action for action in optional_actions if action is not None]
    if not actions or len(actions) != len(optional_actions):
        return None
    if len(actions) == 1:
        action_text = str(actions[0])
    elif len(actions) == 2:
        action_text = f"{actions[0]} and {actions[1].casefold()}"
    else:
        action_text = ", ".join(
            str(action) if index == 0 else str(action).casefold()
            for index, action in enumerate(actions[:-1])
        )
        action_text += f", and {actions[-1].casefold()}"
    return f"{action_text} {match.group(2)}."


def _distill_capability(record: DotnetApiTypeEvidenceV1) -> str | None:
    summary = " ".join((record.summary or "").strip().split())
    if (
        not summary
        or _GENERIC_SUMMARY.fullmatch(summary)
        or _NON_VISITOR_SUMMARY.search(summary)
        or "/internal/" in f"/{record.source_path.casefold()}/"
        or record.name.casefold().endswith(_LOW_VALUE_TYPE_SUFFIXES)
    ):
        return None
    action_list = _imperative_action_list(summary)
    if action_list is not None:
        return action_list
    delegated_actions = re.search(r"(?i)\bused to (.+?)\.?$", summary)
    if delegated_actions is not None:
        action_list = _imperative_action_list(delegated_actions.group(1))
        if action_list is not None:
            return action_list
    facade = re.fullmatch(r"(?i)^facade for .+? manipulation:\s*(.+?)\.?$", summary)
    if facade is not None:
        return _imperative_action_list(facade.group(1))
    if all(
        term in summary.casefold()
        for term in ("translate", "scale", "rotation", "transform matrix")
    ):
        return "Transform objects with translation, scaling, rotation, and matrices."
    if re.search(r"(?i)gives a curve a placement by using a transformation matrix", summary):
        return "Transform curve placement with matrices."
    patterns: tuple[tuple[re.Pattern[str], str], ...] = (
        (
            re.compile(r"(?i)^provides static factory methods for creating (.+?)\.?$"),
            "Create {0}.",
        ),
        (re.compile(r"(?i)^provides access to (.+?)\.?$"), "Access {0}."),
        (re.compile(r"(?i)^provides helper functions to (.+?)\.?$"), "{0}."),
        (
            re.compile(r"(?i)^provides (.+?) management utilities(?: for .+?)?\.?$"),
            "Manage {0} resources.",
        ),
        (re.compile(r"(?i)^provides (.+?) operations\.?$"), "Apply {0} operations."),
        (re.compile(r"(?i)^manages (.+?)\.?$"), "Manage {0}."),
        (re.compile(r"(?i)^.+? uses .+? to manage (.+?)\.?$"), "Manage {0}."),
        (re.compile(r"(?i)^.+? creates (.+?)\.?$"), "Create {0}."),
        (
            re.compile(
                r"(?i)^represents the formatting properties of (?:an? |the )?(.+?),\s+"
                r"providing access to .+$"
            ),
            "Access {0} formatting properties.",
        ),
        (
            re.compile(r"(?i)^.+? implementation that saves (.+?) as (.+?)(?:\s*\(.+\))?\.?$"),
            "Save {0} as {1}.",
        ),
    )
    for pattern, template in patterns:
        match = pattern.fullmatch(summary)
        if match is None:
            continue
        groups = [group.strip().rstrip(".") for group in match.groups()]
        candidate = template.format(*groups)
        candidate = candidate[:1].upper() + candidate[1:]
        if len(candidate) <= 160 and "that represented" not in candidate.casefold():
            return candidate
    if re.search(r"(?i)\bMAPI property identifiers\b", summary) and re.search(
        r"(?i)\bMSG reader and writer\b", summary
    ):
        return "Read and write MSG message properties."
    return None


def distilled_dotnet_capability_entries(
    records: Iterable[DotnetApiTypeEvidenceV1],
) -> list[tuple[DotnetApiTypeEvidenceV1, str]]:
    """Select only concise public capabilities supported by exact API summaries."""

    selected: list[tuple[DotnetApiTypeEvidenceV1, str]] = []
    seen: set[str] = set()
    for record in sorted(records, key=_capability_score):
        capability = _distill_capability(record)
        if capability is None:
            continue
        normalized = capability.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        selected.append((record, capability))
        if len(selected) >= _MAX_CAPABILITIES:
            break
    return selected


__all__ = ["distilled_dotnet_capability_entries"]
