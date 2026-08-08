"""Match bounded structured source claims to exact accepted repository facts."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.claim_accountability_api_index import api_coordinate_index
from readme_agent.readme.claim_accountability_api_shapes import (
    coded_references,
    compatible_member_reference,
    has_only_api_punctuation,
)
from readme_agent.readme.source_claim_conversion_binding import (
    conversion_source_claim_fact_ids,
)
from readme_agent.readme.source_claim_mcp_binding import mcp_source_claim_fact_ids
from readme_agent.readme.source_claim_portfolio_binding import portfolio_source_claim_fact_ids
from readme_agent.readme.source_claim_repository_asset_binding import (
    repository_asset_source_claim_fact_ids,
)

_LIST_ITEM = re.compile(r"(?s)^(?P<indent>[ \t]*)[-+*]\s+(?P<body>.+?)\s*$")
_CLASS_REFERENCE = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:\([^)]*\))?$")
_MARKDOWN = re.compile(r"[`*_>#\[\]()]")
_UPPER_TECHNICAL_TOKEN = re.compile(r"\b[A-Z][A-Z0-9.+-]{1,9}\b")
_MAJOR_PREFIXES = (
    "- build 3d scenes programmatically with",
    "- import ",
    "- export ",
    "- assign ",
    "- convert built-in parametric primitives",
    "- work with ",
    "- animate scene properties",
)


def _accepted_fact(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    fact_id = facts.selected_fact_ids.get(field)
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return None
    return None if fact.has_unresolved_conflict else fact


def _parent_list_body(document: str, claim: ReadmeMaterialClaimAssessmentV1) -> str:
    character_start = len(document.encode("utf-8")[: claim.source_byte_start].decode("utf-8"))
    line_start = document.rfind("\n", 0, character_start) + 1
    current = document[line_start : document.find("\n", line_start)]
    current_indent = len(current) - len(current.lstrip())
    for line in reversed(document[:line_start].splitlines()):
        match = _LIST_ITEM.fullmatch(line)
        if match is not None and len(match.group("indent")) < current_indent:
            return match.group("body")
    return ""


def _class_names(value: str, classes_by_name: dict[str, dict]) -> list[str]:
    names: list[str] = []
    for reference, _tail in coded_references(value):
        match = _CLASS_REFERENCE.fullmatch(reference)
        if match is None or match.group("name") not in classes_by_name:
            return []
        names.append(match.group("name"))
    return names


def _api_union_fact_id(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
    text: str,
    facts: ProductFactsV2,
) -> str | None:
    fact = _accepted_fact(facts, "api.public_surface")
    if fact is None or not isinstance(fact.value, dict):
        return None
    item = _LIST_ITEM.fullmatch(text.strip())
    if item is None:
        return None
    index = api_coordinate_index(fact.value)
    body = item.group("body")
    if "—" in body:
        class_text, member_text = body.split("—", 1)
        if not has_only_api_punctuation(class_text):
            return None
    else:
        class_text, member_text = _parent_list_body(document, claim), body
    if not class_text or not has_only_api_punctuation(member_text):
        return None
    class_names = _class_names(class_text, index.classes_by_name)
    if not class_names:
        return None
    for reference, _tail in coded_references(member_text):
        if reference in index.classes_by_name:
            continue
        name = reference.split("(", 1)[0].split(":", 1)[0].strip()
        if not any(
            compatible_member_reference(
                reference,
                [
                    member["surface"]
                    for member in index.classes_by_name[class_name].get("members", [])
                    if member.get("name") == name and isinstance(member.get("surface"), str)
                ],
            )
            for class_name in class_names
        ):
            return None
    return fact.fact_id


def _format_names(text: str) -> set[str]:
    aliases = {
        "gltf": "gltf",
        "glb": "gltf",
        "3mf": "3mf",
        "obj": "obj",
        "stl": "stl",
        "collada": "collada",
        "fbx": "fbx",
    }
    folded = text.casefold()
    return {canonical for token, canonical in aliases.items() if re.search(rf"\b{token}\b", folded)}


def _capability_supports_format(fact: FactRecordV2, direction: str, name: str) -> bool:
    if not isinstance(fact.value, list):
        return False
    for item in fact.value:
        folded = str(item).casefold()
        direction_supported = direction in folded or "import and export" in folded
        if direction_supported and re.search(rf"\b{name}\b", folded):
            return True
    return False


def _collada_import_example(fact: FactRecordV2) -> bool:
    if not isinstance(fact.value, dict):
        return False
    examples = fact.value.get("inline_examples")
    if not isinstance(examples, list):
        return False
    return any(
        isinstance(item, dict)
        and item.get("static_api_verified") is True
        and isinstance(item.get("code"), str)
        and "colladaloadoptions" in item["code"].casefold()
        and "scene.open(" in item["code"].casefold()
        for item in examples
    )


def _collada_export_limitation(fact: FactRecordV2) -> bool:
    if not isinstance(fact.value, list):
        return False
    return any(
        isinstance(item, dict)
        and item.get("kind") == "collada_dispatch_blocked"
        and "collada export" in str(item.get("statement", "")).casefold()
        for item in fact.value
    )


def _format_direction_fact_ids(text: str, facts: ProductFactsV2) -> set[str] | None:
    folded = " ".join(text.casefold().split())
    direction = (
        "input"
        if folded.startswith("- import ")
        else "output"
        if folded.startswith("- export ")
        else None
    )
    if direction is None:
        return set()
    formats = _accepted_fact(facts, "product.formats")
    capability = _accepted_fact(facts, "product.capabilities")
    examples = _accepted_fact(facts, "repository.examples")
    limitations = _accepted_fact(facts, "product.limitations")
    repository_directions = _accepted_fact(facts, "repository.format_directions")
    declared = (
        {str(item).casefold() for item in formats.value}
        if formats is not None and isinstance(formats.value, list)
        else set()
    )
    result: set[str] = set()
    mentioned = _format_names(text)
    if not mentioned:
        return None

    def repository_supports(name: str, requested_direction: str) -> bool:
        if repository_directions is None or not isinstance(repository_directions.value, dict):
            return False
        directions = repository_directions.value.get("directions")
        return isinstance(directions, list) and any(
            isinstance(item, dict)
            and str(item.get("format")).casefold() == name
            and item.get("direction") == requested_direction
            for item in directions
        )

    for name in mentioned:
        if (
            name == "collada"
            and direction == "output"
            and "collada export is not currently reachable" in folded
        ):
            if limitations is None or not _collada_export_limitation(limitations):
                return None
            result.add(limitations.fact_id)
            if "collada import is supported" in folded:
                repository_import = repository_supports("collada", "input")
                if not repository_import and (
                    examples is None or not _collada_import_example(examples)
                ):
                    return None
                if repository_import and repository_directions is not None:
                    result.add(repository_directions.fact_id)
                elif examples is not None:
                    result.add(examples.fact_id)
            continue
        direct = any(item.startswith(f"{direction} format: {name}") for item in declared)
        repository_backed = repository_supports(name, direction)
        capability_backed = capability is not None and _capability_supports_format(
            capability,
            direction,
            name,
        )
        example_backed = (
            name == "collada"
            and direction == "input"
            and examples is not None
            and _collada_import_example(examples)
        )
        if not direct and not capability_backed and not example_backed and not repository_backed:
            return None
        if direct and formats is not None:
            result.add(formats.fact_id)
        if capability_backed and capability is not None:
            result.add(capability.fact_id)
        if example_backed and examples is not None:
            result.add(examples.fact_id)
        if repository_backed and repository_directions is not None:
            result.add(repository_directions.fact_id)
    return result


def _api_references_are_exact(text: str, value: dict) -> bool:
    index = api_coordinate_index(value)
    for reference, _tail in coded_references(text):
        if reference in {".mtl", ".dae", "..."}:
            continue
        if "." in reference and not reference.startswith("."):
            class_name, member_reference = reference.split(".", 1)
            class_item = index.classes_by_name.get(class_name)
            name = member_reference.split("(", 1)[0].split(":", 1)[0]
            members = class_item.get("members", []) if class_item else []
            surfaces = [
                item["surface"]
                for item in members
                if item.get("name") == name and isinstance(item.get("surface"), str)
            ]
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\(\.\.\.\)", member_reference):
                if not surfaces:
                    return False
                continue
            if not compatible_member_reference(member_reference, surfaces):
                return False
        elif (
            reference not in index.classes_by_name
            and reference.split("(", 1)[0] not in index.all_member_names
        ):
            return False
    return True


def _major_capability_fact_ids(text: str, facts: ProductFactsV2) -> set[str]:
    folded = " ".join(text.casefold().split())
    capability = _accepted_fact(facts, "product.capabilities")
    api = _accepted_fact(facts, "api.public_surface")
    if (
        not folded.startswith(_MAJOR_PREFIXES)
        or capability is None
        or api is None
        or not isinstance(api.value, dict)
        or not _api_references_are_exact(text, api.value)
    ):
        return set()
    format_fact_ids = _format_direction_fact_ids(text, facts)
    if format_fact_ids is None:
        return set()
    result = {capability.fact_id, api.fact_id}
    result.update(format_fact_ids)
    return result


def _api_overview_fact_ids(text: str, facts: ProductFactsV2) -> set[str]:
    folded = " ".join(text.casefold().split())
    if not (
        folded.startswith("the public entry points are organized under")
        and "scene.open()" in folded
        and "scene.save()" in folded
    ):
        return set()
    api = _accepted_fact(facts, "api.public_surface")
    capability = _accepted_fact(facts, "product.capabilities")
    if api is None or capability is None or not isinstance(api.value, dict):
        return set()
    index = api_coordinate_index(api.value)
    namespaces = api.value.get("package_namespaces")
    if not isinstance(namespaces, list):
        return set()
    namespace_set = {str(item) for item in namespaces}
    for reference, _tail in coded_references(text):
        if reference == "..." or reference in namespace_set or reference in index.classes_by_name:
            continue
        if reference.startswith("*") and reference[1:] in {"LoadOptions", "SaveOptions"}:
            if any(name.endswith(reference[1:]) for name in index.classes_by_name):
                continue
            return set()
        if "." in reference:
            class_name, member_reference = reference.split(".", 1)
            class_item = index.classes_by_name.get(class_name)
            member_name = member_reference.split("(", 1)[0].split(":", 1)[0]
            group = (
                [item for item in class_item.get("members", []) if item.get("name") == member_name]
                if class_item
                else []
            )
            if group and compatible_member_reference(
                member_reference,
                [str(item["surface"]) for item in group if isinstance(item.get("surface"), str)],
            ):
                continue
        return set()
    return {api.fact_id, capability.fact_id}


def _python_product_architecture_fact_ids(text: str, facts: ProductFactsV2) -> set[str]:
    """Bind a bounded public-API/parser architecture sentence to repository source facts."""

    folded = " ".join(text.casefold().split())
    api = _accepted_fact(facts, "api.public_surface")
    identity = _accepted_fact(facts, "product.identity")
    formats = _accepted_fact(facts, "product.formats")
    implementation = _accepted_fact(facts, "repository.implementation_components")
    if api is None or identity is None or not isinstance(api.value, dict):
        return set()
    namespaces = {
        str(item).casefold()
        for item in api.value.get("package_namespaces", [])
        if isinstance(item, str)
    }
    mentioned_namespaces = {
        reference.removesuffix(".*").casefold()
        for reference, _tail in coded_references(text)
        if reference.endswith(".*")
    }
    if mentioned_namespaces and not mentioned_namespaces.issubset(namespaces):
        return set()
    identity_value = identity.value if isinstance(identity.value, dict) else {}
    product_name = str(identity_value.get("product_name") or "").casefold()
    public_api_claim = "public api" in folded or "familiar surface" in folded
    if not public_api_claim or not product_name or product_name not in folded:
        return set()
    result = {api.fact_id, identity.fact_id}
    if "onenote" in folded and ".one" in folded:
        if formats is None or not any(
            "onenote" in str(item).casefold() and ".one" in str(item).casefold()
            for item in (formats.value if isinstance(formats.value, list) else [])
        ):
            return set()
        result.add(formats.fact_id)
    required_labels = {label for label in ("ms-one", "onestore") if label in folded}
    if "parser" in folded and required_labels:
        if implementation is None or not isinstance(implementation.value, dict):
            return set()
        components = implementation.value.get("components")
        if not isinstance(components, list):
            return set()
        labels = {
            str(label).casefold()
            for item in components
            if isinstance(item, dict) and isinstance(item.get("labels"), list)
            for label in item["labels"]
        }
        valid_parser = any(
            isinstance(item, dict)
            and item.get("kind") == "parser"
            and isinstance(item.get("source_sha256"), str)
            and len(str(item["source_sha256"])) == 64
            for item in components
        )
        if not required_labels.issubset(labels) or not valid_parser:
            return set()
        result.add(implementation.fact_id)
    return result


def _product_positioning_overview_fact_ids(text: str, facts: ProductFactsV2) -> set[str]:
    """Bind one conservative repository-authored opening to verified product facts."""

    folded = " ".join(_MARKDOWN.sub("", text).casefold().split())
    identity = _accepted_fact(facts, "product.identity")
    audience = _accepted_fact(facts, "product.audience")
    capabilities = _accepted_fact(facts, "product.capabilities")
    problems = _accepted_fact(facts, "product.problems_solved")
    formats = _accepted_fact(facts, "product.formats")
    if any(item is None for item in (identity, audience, capabilities, problems, formats)):
        return set()
    assert identity is not None
    assert audience is not None
    assert capabilities is not None
    assert problems is not None
    assert formats is not None
    identity_value = identity.value if isinstance(identity.value, dict) else {}
    product_name = str(identity_value.get("product_name") or "").casefold()
    platform = str(identity_value.get("platform") or "").casefold()
    if (
        not product_name
        or not folded.startswith(product_name)
        or "open-source" not in folded
        or not platform
        or platform not in folded
        or "developer" not in folded
    ):
        return set()
    evidence_text = " ".join(
        str(value)
        for fact in (capabilities, problems, formats)
        for value in (fact.value if isinstance(fact.value, list) else [fact.value])
    ).casefold()
    technical_tokens = {
        token.casefold()
        for token in _UPPER_TECHNICAL_TOKEN.findall(text)
        if token.casefold() not in {"foss", "api"}
    }
    if technical_tokens and not all(token in evidence_text for token in technical_tokens):
        return set()
    if "conversion" in folded and "conversion" not in evidence_text:
        return set()
    return {
        identity.fact_id,
        audience.fact_id,
        capabilities.fact_id,
        problems.fact_id,
        formats.fact_id,
    }


def structured_source_claim_fact_ids(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
    text: str,
    facts: ProductFactsV2,
) -> set[str]:
    """Return facts proving exact bounded structured source-claim grammars."""

    fact_id = _api_union_fact_id(document, claim, text, facts)
    return (
        ({fact_id} if fact_id is not None else set())
        | _major_capability_fact_ids(text, facts)
        | _api_overview_fact_ids(text, facts)
        | _python_product_architecture_fact_ids(text, facts)
        | _product_positioning_overview_fact_ids(text, facts)
        | conversion_source_claim_fact_ids(text, facts)
        | mcp_source_claim_fact_ids(text, facts)
        | repository_asset_source_claim_fact_ids(text, facts)
        | portfolio_source_claim_fact_ids(document, claim, text, facts)
    )


def verified_issue_route_fact_ids(claim_text: str, facts: ProductFactsV2) -> set[str]:
    """Bind only the exact issues route derived from the selected repository identity."""

    identity = _accepted_fact(facts, "product.identity")
    if identity is None or not isinstance(identity.value, dict):
        return set()
    repository = identity.value.get("repository")
    expected = (
        f"- Found a bug or have a feature request? [Open an issue]"
        f"(https://github.com/{repository}/issues) on GitHub."
    )
    normalized_claim = " ".join(_MARKDOWN.sub("", claim_text).casefold().split())
    normalized_expected = " ".join(_MARKDOWN.sub("", expected).casefold().split())
    return {identity.fact_id} if normalized_claim == normalized_expected else set()


__all__ = ["structured_source_claim_fact_ids", "verified_issue_route_fact_ids"]
