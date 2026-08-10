"""Bind exact inherited repository-result images to checksum-bound inventory facts."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2

_IMAGE = re.compile(r"^\s*!\[(?P<alt>[^\]]+)\]\((?P<path>[^)]+)\)\s*$")
_RESOURCE_LINK = re.compile(r"\[[^\]]+\]\((?P<path>[^)]+)\)")
_RESOURCE_LINK_CLAIM = re.compile(
    r"(?is)^\s*(?:for\s+[^,\n.]{1,100},\s*)?see\s+\[[^\]]+\]\([^)]+\)\."
    r"(?:\s*(?:for\s+[^,\n.]{1,100},\s*)?see\s+\[[^\]]+\]\([^)]+\)\.)*\s*$"
)


def repository_asset_source_claim_fact_ids(text: str, facts: ProductFactsV2) -> set[str]:
    """Return the repository-examples fact for one exact inventoried result image."""

    match = _IMAGE.fullmatch(text.strip())
    if match is None and _RESOURCE_LINK_CLAIM.fullmatch(text):
        targets = [
            item.group("path").removeprefix("./").rstrip("/")
            for item in _RESOURCE_LINK.finditer(text)
        ]
        if not targets or any("://" in target or target.startswith("#") for target in targets):
            return set()
        owners: set[str] = set()
        documentation = _accepted_asset_fact(facts, "repository.documentation_assets")
        examples = _accepted_asset_fact(facts, "repository.examples")
        for target in targets:
            matches: set[str] = set()
            if documentation is not None and isinstance(documentation.value, dict):
                entries = documentation.value.get("entries", [])
                if any(
                    isinstance(item, dict)
                    and item.get("path") == target
                    and isinstance(item.get("sha256"), str)
                    and len(str(item["sha256"])) == 64
                    for item in entries
                ):
                    matches.add(documentation.fact_id)
            if examples is not None and isinstance(examples.value, dict):
                files = examples.value.get("files", [])
                if any(
                    isinstance(item, dict)
                    and (
                        item.get("path") == target
                        or (
                            target == "examples"
                            and str(item.get("path") or "").startswith("examples/")
                        )
                    )
                    and isinstance(item.get("sha256"), str)
                    and len(str(item["sha256"])) == 64
                    for item in files
                ):
                    matches.add(examples.fact_id)
            if not matches:
                return set()
            owners.update(matches)
        return owners
    fact_id = facts.selected_fact_ids.get("repository.examples")
    if match is None or fact_id is None:
        return set()
    fact = facts.fact_by_id(fact_id)
    if (
        fact.verification_state not in {"verified", "policy_approved"}
        or fact.has_unresolved_conflict
        or not isinstance(fact.value, dict)
    ):
        return set()
    assets = fact.value.get("result_assets")
    if not isinstance(assets, list):
        return set()
    asset_matches = [
        item
        for item in assets
        if isinstance(item, dict)
        and str(item.get("alt") or "") == match.group("alt")
        and str(item.get("path") or "") == match.group("path")
        and isinstance(item.get("sha256"), str)
        and len(str(item["sha256"])) == 64
    ]
    return {fact.fact_id} if len(asset_matches) == 1 else set()


def _accepted_asset_fact(facts: ProductFactsV2, field: str):
    fact_id = facts.selected_fact_ids.get(field)
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return None
    return None if fact.has_unresolved_conflict else fact


__all__ = ["repository_asset_source_claim_fact_ids"]
