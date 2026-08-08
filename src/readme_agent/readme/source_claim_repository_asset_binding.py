"""Bind exact inherited repository-result images to checksum-bound inventory facts."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2

_IMAGE = re.compile(r"^\s*!\[(?P<alt>[^\]]+)\]\((?P<path>[^)]+)\)\s*$")


def repository_asset_source_claim_fact_ids(text: str, facts: ProductFactsV2) -> set[str]:
    """Return the repository-examples fact for one exact inventoried result image."""

    match = _IMAGE.fullmatch(text.strip())
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
    matches = [
        item
        for item in assets
        if isinstance(item, dict)
        and str(item.get("alt") or "") == match.group("alt")
        and str(item.get("path") or "") == match.group("path")
        and isinstance(item.get("sha256"), str)
        and len(str(item["sha256"])) == 64
    ]
    return {fact.fact_id} if len(matches) == 1 else set()


__all__ = ["repository_asset_source_claim_fact_ids"]
