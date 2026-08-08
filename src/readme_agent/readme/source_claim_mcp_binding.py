"""Bind exact inherited MCP guidance to mechanically extracted repository facts."""

from __future__ import annotations

import ast
import re

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2

_FENCE = re.compile(r"^\s*```(?:python|py)\s*\r?\n(?P<code>.*)\r?\n```\s*$", re.DOTALL)
_TOOL_ITEM = re.compile(r"^\s*[-+*]\s+`(?P<tool>[A-Za-z_][A-Za-z0-9_]*)`\s*$")
_CODE_REFERENCE = re.compile(r"`([A-Za-z_][A-Za-z0-9_-]*)`")


def _accepted(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    fact_id = facts.selected_fact_ids.get(field)
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return None
    return None if fact.has_unresolved_conflict else fact


def _mcp_value(api: FactRecordV2 | None) -> dict[str, object] | None:
    if api is None or not isinstance(api.value, dict):
        return None
    value = api.value.get("mcp_server")
    return value if isinstance(value, dict) else None


def _dependency(
    facts: ProductFactsV2,
    distribution: str,
    *,
    purpose: str | None = None,
) -> FactRecordV2 | None:
    fact = _accepted(facts, "installation.capability_dependencies")
    entries = (
        fact.value.get("entries") if fact is not None and isinstance(fact.value, dict) else None
    )
    if not isinstance(entries, list):
        return None
    matches = [
        item
        for item in entries
        if isinstance(item, dict)
        and str(item.get("distribution") or "").casefold() == distribution.casefold()
        and (purpose is None or str(item.get("purpose") or "").casefold() == purpose.casefold())
    ]
    return fact if len(matches) == 1 else None


def _factory_example_matches(code: str, mcp: dict[str, object]) -> bool:
    if mcp.get("factory_instance_run") is not True:
        return False
    module = str(mcp.get("module") or "")
    factory = str(mcp.get("factory") or "")
    defaults = mcp.get("runner_defaults")
    if not module or not factory or not isinstance(defaults, dict):
        return False
    host = defaults.get("host")
    port = defaults.get("port")
    if not isinstance(host, str) or not isinstance(port, int):
        return False
    expected = (
        f"from {module} import {factory}\n\n"
        f"server = {factory}()\n"
        f"server.run(host={host!r}, port={port})\n"
    )
    try:
        return ast.dump(ast.parse(code), include_attributes=False) == ast.dump(
            ast.parse(expected), include_attributes=False
        )
    except SyntaxError:
        return False


def mcp_source_claim_fact_ids(text: str, facts: ProductFactsV2) -> set[str]:
    """Return exact fact bindings for a bounded MCP source-claim grammar."""

    api = _accepted(facts, "api.public_surface")
    mcp = _mcp_value(api)
    if api is None or mcp is None:
        return set()
    raw_tools = mcp.get("tools")
    tools = (
        {str(item) for item in raw_tools if isinstance(item, str)}
        if isinstance(raw_tools, list)
        else set()
    )
    stripped = text.strip()
    folded = " ".join(stripped.casefold().split())
    if folded in {"mcp tools currently exposed:", "run mcp server:"}:
        return {api.fact_id}
    if folded == "important notes:":
        fastmcp = _dependency(facts, str(mcp.get("dependency_package") or ""))
        return {api.fact_id, fastmcp.fact_id} if fastmcp is not None else set()
    tool_match = _TOOL_ITEM.fullmatch(stripped)
    if tool_match is not None:
        return {api.fact_id} if tool_match.group("tool") in tools else set()
    fence = _FENCE.fullmatch(stripped)
    if fence is not None:
        return {api.fact_id} if _factory_example_matches(fence.group("code") + "\n", mcp) else set()
    dependency_package = str(mcp.get("dependency_package") or "")
    if folded == f"- `{dependency_package.casefold()}` is required to start the mcp server.":
        dependency = _dependency(facts, dependency_package)
        return {api.fact_id, dependency.fact_id} if dependency is not None else set()
    if folded.startswith("- `skia-python` is required for image conversion flows"):
        mentioned_tools = set(_CODE_REFERENCE.findall(stripped)) - {"skia-python"}
        dependency = _dependency(facts, "skia-python", purpose="image conversion")
        if dependency is not None and mentioned_tools and mentioned_tools.issubset(tools):
            return {api.fact_id, dependency.fact_id}
    return set()


__all__ = ["mcp_source_claim_fact_ids"]
