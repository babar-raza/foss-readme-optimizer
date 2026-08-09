"""Bind product architecture and positioning overview source claims."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.claim_accountability_api_shapes import coded_references

_MARKDOWN = re.compile(r"[`*_>#\[\]()]")
_UPPER_TECHNICAL_TOKEN = re.compile(r"\b[A-Z][A-Z0-9.+-]{1,9}\b")


def _accepted_fact(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    fact_id = facts.selected_fact_ids.get(field)
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return None
    return None if fact.has_unresolved_conflict else fact


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


def python_product_architecture_fact_ids(text: str, facts: ProductFactsV2) -> set[str]:
    """Return exact Python product-architecture fact IDs."""

    return _python_product_architecture_fact_ids(text, facts)


def product_positioning_overview_fact_ids(text: str, facts: ProductFactsV2) -> set[str]:
    """Return exact product-positioning fact IDs."""

    return _product_positioning_overview_fact_ids(text, facts)


__all__ = [
    "product_positioning_overview_fact_ids",
    "python_product_architecture_fact_ids",
]
