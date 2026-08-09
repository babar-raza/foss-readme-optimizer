"""Prove explicit source-claim contradictions from complete accepted repository facts."""

from __future__ import annotations

import hashlib
import re

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.claim_accountability_api_index import (
    ApiCoordinateIndexV1,
    api_coordinate_index,
)
from readme_agent.readme.claim_accountability_api_shapes import (
    class_headers,
    coded_references,
    compatible_member_reference,
    context_classes,
    member_surfaces,
)

_LIST_ITEM = re.compile(r"(?s)^\s*[-+*]\s+(?P<body>.+?)\s*$")
_BASE_OF = re.compile(
    r"(?is)^\s*[-+*]\s+`(?P<base>[A-Za-z_][A-Za-z0-9_]*)`\s+"
    r"\(base\s+of\s+`(?P<derived>[A-Za-z_][A-Za-z0-9_]*)`"
)
_SHELL_FENCE = re.compile(
    r"\A```(?:bash|sh|shell|console|powershell|ps1)?[^\S\r\n]*\r?\n"
    r"(?P<body>.*?)\r?\n```\Z",
    re.DOTALL | re.IGNORECASE,
)
_PIP_PACKAGE_INSTALL = re.compile(
    r"\A(?:python(?:3(?:\.\d+)?)?\s+-m\s+)?pip\s+install\s+"
    r"(?:(?:--pre|-e)\s+)*['\"]?(?P<target>[A-Za-z0-9](?:[A-Za-z0-9._-]*"
    r"[A-Za-z0-9])?)(?:\[[A-Za-z0-9_.,-]+\])?['\"]?\Z",
    re.IGNORECASE,
)


def _accepted_fact(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    fact_id = facts.selected_fact_ids.get(field)
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return None
    return None if fact.has_unresolved_conflict else fact


def _normalized_python_distribution(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).casefold()


def _source_build_acquisition_contradiction(
    claim_text: str,
    facts: ProductFactsV2,
) -> set[str]:
    """Disprove one exact package-target pip command under source-only acquisition truth."""

    acquisition = _accepted_fact(facts, "installation.verified_acquisition")
    coordinates = _accepted_fact(facts, "installation.coordinates")
    if acquisition is None or not isinstance(acquisition.value, dict):
        return set()
    value = acquisition.value
    if (
        value.get("method") != "source_build"
        or value.get("outcome") != "SOURCE_BUILD_VERIFIED"
        or value.get("truth_eligible") is not True
    ):
        return set()
    command = claim_text.strip()
    fence = _SHELL_FENCE.fullmatch(command)
    if fence is not None:
        command = fence.group("body").strip()
    match = _PIP_PACKAGE_INSTALL.fullmatch(command)
    if match is None:
        return set()
    target = _normalized_python_distribution(match.group("target"))
    if target == ".":
        return set()
    names: set[str] = set()
    selected_coordinate = value.get("coordinate")
    if isinstance(selected_coordinate, dict) and selected_coordinate.get("name"):
        names.add(_normalized_python_distribution(str(selected_coordinate["name"])))
    coordinate_rows = (
        coordinates.value
        if coordinates is not None and isinstance(coordinates.value, list)
        else [coordinates.value]
        if coordinates is not None
        else []
    )
    for row in coordinate_rows:
        if isinstance(row, dict) and row.get("name"):
            names.add(_normalized_python_distribution(str(row["name"])))
    if target not in names:
        return set()
    return {
        acquisition.fact_id,
        *([coordinates.fact_id] if coordinates is not None else []),
    }


def _complete_api_fact(facts: ProductFactsV2) -> tuple[FactRecordV2, ApiCoordinateIndexV1] | None:
    fact = _accepted_fact(facts, "api.public_surface")
    if fact is None or not isinstance(fact.value, dict):
        return None
    index = api_coordinate_index(fact.value)
    if index.coordinate_prefix != "/coordinate_catalog":
        return None
    unresolved = fact.value.get("unresolved_reexports")
    if unresolved != [] or not index.classes_by_name:
        return None
    return fact, index


def _api_contradiction(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
    claim_text: str,
    facts: ProductFactsV2,
) -> set[str]:
    selected = _complete_api_fact(facts)
    if selected is None:
        return set()
    fact, index = selected
    relationship = _BASE_OF.match(claim_text)
    if relationship is not None:
        base = relationship.group("base")
        derived = relationship.group("derived")
        derived_item = index.classes_by_name.get(derived)
        if base in index.classes_by_name and isinstance(derived_item, dict):
            bases = derived_item.get("bases")
            if isinstance(bases, list) and base not in bases:
                return {fact.fact_id}

    item = _LIST_ITEM.fullmatch(claim_text)
    if item is None:
        return set()
    body = item.group("body")
    if "—" in body:
        left, right = body.split("—", 1)
        headers = class_headers(left)
        if headers is None:
            return set()
        class_names = [name for name, _, _ in headers]
        if any(name not in index.classes_by_name for name in class_names):
            return {fact.fact_id}
        references = coded_references(right)
    else:
        references = coded_references(body)
        direct_names = [reference for reference, _ in references]
        if direct_names and all(
            re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) for name in direct_names
        ):
            missing_exports = [
                name
                for name in direct_names
                if name in index.classes_by_name and name not in index.package_export_names
            ]
            if missing_exports:
                return {fact.fact_id}
        character_start = len(document.encode("utf-8")[: claim.source_byte_start].decode("utf-8"))
        line_start = document.rfind("\n", 0, character_start) + 1
        current_line = document[line_start : document.find("\n", line_start)]
        current_indent = len(current_line) - len(current_line.lstrip())
        context = ""
        if current_indent:
            context = next(
                (
                    match.group("body")
                    for line in reversed(document[:line_start].splitlines())
                    if (match := re.match(r"^(?P<indent>\s*)[-+*]\s+(?P<body>.+)$", line))
                    and len(match.group("indent")) < current_indent
                ),
                "",
            )
        class_names = context_classes(context, index.classes_by_name)
    if not class_names:
        return set()
    for reference, _tail in references:
        if reference in index.classes_by_name:
            continue
        member_name = reference.split("(", 1)[0].split(":", 1)[0].strip()
        groups = [
            member
            for class_name in class_names
            for member in index.classes_by_name[class_name].get("members", [])
            if member.get("name") == member_name
        ]
        if groups and not compatible_member_reference(reference, member_surfaces(groups)):
            return {fact.fact_id}
    return set()


def _format_contradiction(claim_text: str, facts: ProductFactsV2) -> set[str]:
    folded = " ".join(claim_text.casefold().split())
    if ".mtl" in folded and "import obj" in folded:
        fact = _accepted_fact(facts, "repository.format_directions")
        directions = fact.value.get("directions") if fact and isinstance(fact.value, dict) else None
        if isinstance(directions, list) and any(
            isinstance(item, dict)
            and str(item.get("format")).casefold() == "obj"
            and item.get("direction") == "input"
            and item.get("material_library_support") is False
            for item in directions
        ):
            assert fact is not None
            return {fact.fact_id}
    if "in and out of" in folded and "collada" in folded:
        limitations = _accepted_fact(facts, "product.limitations")
        values = limitations.value if limitations and isinstance(limitations.value, list) else []
        if any(
            isinstance(item, dict) and item.get("kind") == "collada_dispatch_blocked"
            for item in values
        ):
            assert limitations is not None
            return {limitations.fact_id}
    return set()


def _import_shadowing_contradiction(claim_text: str, facts: ProductFactsV2) -> set[str]:
    folded = " ".join(claim_text.casefold().split())
    if "fbxloadoptions" not in folded or "unaffected" not in folded:
        return set()
    fact = _accepted_fact(facts, "repository.python_import_shadowing")
    entries = fact.value.get("entries") if fact and isinstance(fact.value, dict) else None
    if not isinstance(entries, list):
        return set()
    if any(
        isinstance(item, dict)
        and item.get("symbol") in {"FbxLoadOptions", "FbxSaveOptions"}
        and item.get("inheritance_changed") is True
        for item in entries
    ):
        assert fact is not None
        return {fact.fact_id}
    return set()


def contradicted_source_claim_fact_ids(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
    facts: ProductFactsV2,
) -> set[str]:
    """Return accepted facts that mechanically disprove an exact immutable source claim."""

    source_bytes = document.encode("utf-8")
    claim_bytes = source_bytes[claim.source_byte_start : claim.source_byte_end]
    if hashlib.sha256(claim_bytes).hexdigest() != claim.content_sha256:
        raise ValueError("source claim hash does not match immutable document bytes")
    if claim_bytes.decode("utf-8", errors="strict") == "":
        return set()
    claim_text = claim_bytes.decode("utf-8")
    return (
        _format_contradiction(claim_text, facts)
        | _import_shadowing_contradiction(claim_text, facts)
        | _api_contradiction(document, claim, claim_text, facts)
        | _source_build_acquisition_contradiction(claim_text, facts)
    )


__all__ = ["contradicted_source_claim_fact_ids"]
