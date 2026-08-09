"""Match bounded structured source claims to exact accepted repository facts."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.source_claim_api_detail_binding import api_detail_fact_ids
from readme_agent.readme.source_claim_capability_binding import feature_detail_fact_ids
from readme_agent.readme.source_claim_conversion_binding import (
    conversion_source_claim_fact_ids,
)
from readme_agent.readme.source_claim_exact_structured_binding import exact_structured_fact_ids
from readme_agent.readme.source_claim_major_capability_binding import (
    api_overview_fact_ids,
    major_capability_fact_ids,
)
from readme_agent.readme.source_claim_mcp_binding import mcp_source_claim_fact_ids
from readme_agent.readme.source_claim_overview_binding import (
    product_positioning_overview_fact_ids,
    python_product_architecture_fact_ids,
)
from readme_agent.readme.source_claim_portfolio_binding import portfolio_source_claim_fact_ids
from readme_agent.readme.source_claim_repository_asset_binding import (
    repository_asset_source_claim_fact_ids,
)

_MARKDOWN = re.compile(r"[`*_>#\[\]()]")


def _accepted_fact(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    fact_id = facts.selected_fact_ids.get(field)
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return None
    return None if fact.has_unresolved_conflict else fact


def structured_source_claim_fact_ids(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
    text: str,
    facts: ProductFactsV2,
) -> set[str]:
    """Return facts proving exact bounded structured source-claim grammars."""

    return (
        exact_structured_fact_ids(document, claim, text, facts)
        | feature_detail_fact_ids(document, claim, text, facts)
        | api_detail_fact_ids(document, claim, text, facts)
        | major_capability_fact_ids(text, facts)
        | api_overview_fact_ids(text, facts)
        | python_product_architecture_fact_ids(text, facts)
        | product_positioning_overview_fact_ids(text, facts)
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
