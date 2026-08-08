"""Bind exact inherited conversion bullets to verified capability and API facts."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2

_CONVERSION = re.compile(
    r"^\s*[-+*]\s+Convert (?P<inputs>.+?) to (?P<outputs>.+?) in (?P<platform>Python)\s*$",
    re.IGNORECASE,
)
_CONVERSION_NOUN = re.compile(
    r"^\s*[-+*]\s+(?P<inputs>.+?) to (?P<outputs>PNG/JPEG|JPEG/PNG) conversion\s*$",
    re.IGNORECASE,
)
_MCP_WORKFLOW = "- integrate conversion workflows through mcp server tools"


def _accepted(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    fact_id = facts.selected_fact_ids.get(field)
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return None
    return None if fact.has_unresolved_conflict else fact


def _api_exports(api: FactRecordV2, names: set[str]) -> bool:
    if not isinstance(api.value, dict):
        return False
    modules = api.value.get("modules")
    exports = {
        str(export).casefold()
        for module in modules or []
        if isinstance(module, dict)
        for export in module.get("exports", [])
        if isinstance(export, str)
    }
    return names.issubset(exports)


def conversion_source_claim_fact_ids(text: str, facts: ProductFactsV2) -> set[str]:
    """Return fact IDs only when one conversion bullet is completely corroborated."""

    identity = _accepted(facts, "product.identity")
    capabilities = _accepted(facts, "product.capabilities")
    api = _accepted(facts, "api.public_surface")
    if (
        identity is None
        or capabilities is None
        or api is None
        or not isinstance(identity.value, dict)
        or not isinstance(capabilities.value, list)
    ):
        return set()
    folded = " ".join(text.casefold().split())
    capability_values = {str(item).casefold() for item in capabilities.value}
    if folded == _MCP_WORKFLOW:
        mcp = api.value.get("mcp_server") if isinstance(api.value, dict) else None
        tools = mcp.get("tools") if isinstance(mcp, dict) else None
        if (
            "mcp server hosting" in capability_values
            and isinstance(tools, list)
            and any("_to_" in str(item) for item in tools)
        ):
            return {capabilities.fact_id, api.fact_id}
        return set()
    match = _CONVERSION.fullmatch(text.strip())
    noun_match = _CONVERSION_NOUN.fullmatch(text.strip())
    if (match is None and noun_match is None) or str(
        identity.value.get("platform") or ""
    ).casefold() != "python":
        return set()
    selected_match = match or noun_match
    assert selected_match is not None
    inputs = " ".join(selected_match.group("inputs").split()).casefold()
    outputs = " ".join(selected_match.group("outputs").split()).casefold()
    direct = f"{inputs} to {outputs} conversion"
    if direct in capability_values:
        return {identity.fact_id, capabilities.fact_id}
    if outputs in {"png and jpeg", "jpeg and png", "png/jpeg", "jpeg/png"}:
        image_capability = f"{inputs} to image conversion"
        if image_capability in capability_values and _api_exports(
            api, {"encode_png", "encode_jpeg"}
        ):
            return {identity.fact_id, capabilities.fact_id, api.fact_id}
    return set()


__all__ = ["conversion_source_claim_fact_ids"]
