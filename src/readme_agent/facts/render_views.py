"""Build typed visitor-facing phrases from selected product facts."""

from __future__ import annotations

import re
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2

_ACCEPTED_STATES = {"verified", "policy_approved"}
_ECOSYSTEM_LABELS = {
    "cpp": "C++",
    "dotnet": ".NET",
    "go": "Go",
    "java": "Java",
    "net": ".NET",
    "python": "Python",
    "rust": "Rust",
    "typescript": "TypeScript",
}
_FAMILY_LABELS = {
    "3d": "Aspose.3D",
    "cells": "Aspose.Cells",
    "pdf": "Aspose.PDF",
}
_RUNTIME_LABELS = {
    ".net": ".NET",
    "cmake": "CMake",
    "go": "Go",
    "java": "Java",
    "node": "Node.js",
    "node.js": "Node.js",
    "python": "Python",
    "rust": "Rust",
}
_INTERNAL_TOKEN_RE = re.compile(
    r"(?:[a-z0-9]+_[a-z0-9_]+|[a-z0-9]+(?:-[a-z0-9]+)+/[A-Za-z0-9._-]+|://)",
    flags=re.IGNORECASE,
)
_KEY_VALUE_RE = re.compile(r"^[a-z][a-z0-9_]*\s*[:=]")
_VISITOR_REQUIRED_FIELDS = {
    "product.audience",
    "product.problems_solved",
    "product.capabilities",
    "product.formats",
}
_INTERPRETIVE_FIELDS = {"product.audience", "product.problems_solved"}


class VisitorFactRenderViewV1(BaseModel):
    """Fact-bound prose fragments that are safe to offer to an author."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: str
    field: str
    phrases: list[str]
    citation_fact_ids: list[str] = Field(min_length=1)


def _is_visitor_phrase(value: str) -> bool:
    phrase = value.strip()
    return bool(
        phrase
        and "\n" not in phrase
        and not _INTERNAL_TOKEN_RE.search(phrase)
        and not _KEY_VALUE_RE.search(phrase)
        and not any(character in phrase for character in "{}[]")
    )


def _text_phrases(value: object) -> list[str]:
    values = value if isinstance(value, list) else [value]
    return [
        str(item).strip() for item in values if isinstance(item, str) and _is_visitor_phrase(item)
    ]


def _sentence_phrases(value: object) -> list[str]:
    return [
        phrase for phrase in _text_phrases(value) if len(re.findall(r"[A-Za-z0-9]+", phrase)) >= 2
    ]


def _audience_phrases(value: object) -> list[str]:
    phrases = _sentence_phrases(value)
    normalized: list[str] = []
    for phrase in phrases:
        for ecosystem, label in _ECOSYSTEM_LABELS.items():
            phrase = re.sub(
                rf"\busing\s+{re.escape(ecosystem)}\b",
                f"using {label}",
                phrase,
                flags=re.IGNORECASE,
            )
        normalized.append(phrase)
    return normalized


def _identity_phrases(value: object) -> list[str]:
    if not isinstance(value, dict):
        return []
    family = _FAMILY_LABELS.get(str(value.get("family") or "").strip().lower())
    ecosystem = str(value.get("ecosystem") or value.get("platform") or "").strip().lower()
    platform = _ECOSYSTEM_LABELS.get(ecosystem)
    return [f"{family} FOSS for {platform}"] if family and platform else []


def _normalized_runtime(label: str, runtime: str) -> str:
    value = runtime.strip()
    value = re.sub(rf"^{re.escape(label)}\s*", "", value, flags=re.IGNORECASE)
    value = value.removesuffix("+").strip()
    if label == ".NET":
        folded = value.casefold()
        if folded.startswith("netcoreapp"):
            value = "Core " + value[len("netcoreapp") :]
        elif folded.startswith("netstandard"):
            value = "Standard " + value[len("netstandard") :]
        elif folded.startswith("net"):
            value = value[3:]
    if value.startswith(">=") and not re.search(r"[,<|^~*]", value[2:]):
        value = value[2:].strip()
    return value


def _compatibility_phrases(value: object) -> list[str]:
    rows = value if isinstance(value, list) else [value]
    phrases: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ecosystem = str(row.get("ecosystem") or row.get("platform") or "").strip().lower()
        runtime = str(row.get("minimum_runtime") or "").strip()
        runtime_label = str(row.get("runtime_label") or "").strip().lower()
        label = _RUNTIME_LABELS.get(runtime_label) or _ECOSYSTEM_LABELS.get(ecosystem)
        if label and runtime:
            normalized_runtime = _normalized_runtime(label, runtime)
            if normalized_runtime:
                has_upper_bound = bool(re.search(r"[,<|^~*]", runtime.removeprefix(">=")))
                suffix = "." if has_upper_bound else " or later."
                phrases.append(f"Requires {label} {normalized_runtime}{suffix}")
    return phrases


def _acquisition_manifest_path(facts: ProductFactsV2) -> str | None:
    """Resolve the manifest that owns the package users actually acquire."""

    acquisition = facts.selected_fact("installation.verified_acquisition")
    coordinates = facts.selected_fact("installation.coordinates")
    if (
        acquisition.verification_state not in _ACCEPTED_STATES
        or coordinates.verification_state not in _ACCEPTED_STATES
        or not isinstance(acquisition.value, dict)
    ):
        return None
    coordinate = acquisition.value.get("coordinate")
    if not isinstance(coordinate, dict):
        return None
    rows = coordinates.value if isinstance(coordinates.value, list) else [coordinates.value]
    coordinate_name = str(coordinate.get("name") or "").casefold()
    coordinate_group = str(coordinate.get("group_id") or "").casefold()
    coordinate_artifact = str(coordinate.get("artifact_id") or "").casefold()
    for row in rows:
        if not isinstance(row, dict):
            continue
        name_matches = coordinate_name and str(row.get("name") or "").casefold() == coordinate_name
        maven_matches = (
            coordinate_group
            and coordinate_artifact
            and str(row.get("group_id") or "").casefold() == coordinate_group
            and str(row.get("artifact_id") or "").casefold() == coordinate_artifact
        )
        if name_matches or maven_matches:
            manifest_path = str(row.get("manifest_path") or "").strip()
            return manifest_path or None
    return None


def _acquired_package_compatibility(facts: ProductFactsV2, value: object) -> object:
    manifest_path = _acquisition_manifest_path(facts)
    if manifest_path is None or not isinstance(value, list):
        return value
    matched = [
        row
        for row in value
        if isinstance(row, dict) and str(row.get("manifest_path") or "") == manifest_path
    ]
    return matched or value


def _no_direct_prose(_value: object) -> list[str]:
    """Keep internal policy codes and structured contracts out of authored prose."""

    return []


_FIELD_RENDERERS: dict[str, Callable[[object], list[str]]] = {
    "product.audience": _audience_phrases,
    "product.problems_solved": _sentence_phrases,
    "product.capabilities": _text_phrases,
    "product.formats": _text_phrases,
    "product.limitations": _text_phrases,
    "product.identity": _identity_phrases,
    "product.compatibility": _compatibility_phrases,
    "installation.verified_acquisition": _no_direct_prose,
    "relationship.commercial_foss": _no_direct_prose,
    "support.routes": _no_direct_prose,
}


def visitor_fact_render_view(
    facts: ProductFactsV2,
    field: str,
) -> VisitorFactRenderViewV1 | None:
    """Return a safe render view for one accepted selected fact, if supported."""

    renderer = _FIELD_RENDERERS.get(field)
    if renderer is None:
        return None
    fact: FactRecordV2 = facts.selected_fact(field)
    if fact.verification_state not in _ACCEPTED_STATES or fact.has_unresolved_conflict:
        return None
    if (
        field in _INTERPRETIVE_FIELDS
        and fact.source.source_type == "agent_drafted"
        and not fact.supporting_fact_ids
    ):
        return None
    value = (
        _acquired_package_compatibility(facts, fact.value)
        if field == "product.compatibility"
        else fact.value
    )
    phrases = list(dict.fromkeys(renderer(value)))
    if field in _VISITOR_REQUIRED_FIELDS and not phrases:
        return None
    return VisitorFactRenderViewV1(
        fact_id=fact.fact_id,
        field=field,
        phrases=phrases,
        citation_fact_ids=list(dict.fromkeys([fact.fact_id, *fact.supporting_fact_ids])),
    )
