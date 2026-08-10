"""Match Python format-I/O claims to checksum-bound implementation components."""

from __future__ import annotations

import hashlib
import json
import re

from readme_agent.readme.claim_accountability_models import StructuredFactCoordinateV1

_ROLE_WORDS = {
    "read": re.compile(r"(?i)\b(?:load|loads|loading|parse|parses|parsing|read|reads|reader)\b"),
    "write": re.compile(r"(?i)\b(?:save|saves|saving|write|writes|writer|writing)\b"),
}
_ONLY_STDLIB = re.compile(r"(?i)\b(?:only\s+the\s+standard library|standard-library)\b")


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _mentions(text: str, token: str) -> bool:
    return bool(re.search(rf"(?i)(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", text))


def implementation_component_coordinates(
    text: str,
    fact_id: str,
    value: object,
    *,
    known_non_dependency_names: set[str] | frozenset[str] = frozenset(),
) -> list[StructuredFactCoordinateV1]:
    """Return exact capability-group coordinates supported by one public claim."""

    if text.lstrip().startswith("```"):
        return []
    if not isinstance(value, dict) or not isinstance(value.get("capability_groups"), list):
        return []
    coordinates: list[StructuredFactCoordinateV1] = []
    for group in value["capability_groups"]:
        if not isinstance(group, dict):
            continue
        format_name = str(group.get("format") or "")
        roles = {str(role) for role in group.get("roles", [])}
        requested_roles = {role for role, pattern in _ROLE_WORDS.items() if pattern.search(text)}
        if not format_name or not _mentions(text, format_name) or not requested_roles:
            continue
        if not requested_roles.issubset(roles):
            continue
        runtime_imports = {str(name) for name in group.get("runtime_imports", [])}
        stdlib_imports = {str(name) for name in group.get("stdlib_imports", [])}
        mentioned_runtime = {name for name in runtime_imports if _mentions(text, name)}
        mentioned_stdlib = {name for name in stdlib_imports if _mentions(text, name)}
        coded_or_named = set(re.findall(r"`([^`]+)`", text))
        named_dependencies = {
            name for name in coded_or_named if re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", name)
        } - set(known_non_dependency_names)
        known_names = runtime_imports | stdlib_imports
        if named_dependencies & known_names != named_dependencies:
            continue
        if _ONLY_STDLIB.search(text) and runtime_imports:
            continue
        evidence_text = str(group.get("source_summary") or "").casefold()
        if "97-2003" in text and "97-2003" not in evidence_text:
            continue
        if re.search(r"(?i)\bbinary\b", text) and "binary" not in evidence_text:
            continue
        if any(_mentions(text, name) for name in known_names) and not (
            mentioned_runtime or mentioned_stdlib
        ):
            continue
        coordinates.append(
            StructuredFactCoordinateV1(
                fact_id=fact_id,
                field="repository.implementation_components",
                path=f"/capability_groups/{_canonical_sha256(group)[:16]}",
                value_sha256=_canonical_sha256(group),
            )
        )
    return coordinates


__all__ = ["implementation_component_coordinates"]
