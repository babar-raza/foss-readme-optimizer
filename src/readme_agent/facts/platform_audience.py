"""Derive a conservative audience fact from a verified platform fact."""

from readme_agent.facts.compatibility_rendering import ecosystem_display_label
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2, descriptive_fact_id


def derive_platform_audience(facts: ProductFactsV2) -> FactRecordV2 | None:
    """Return a source-bound developer audience without product interpretation."""

    platform = facts.selected_fact("product.platforms")
    if platform.verification_state not in {"verified", "policy_approved"}:
        return None
    if platform.has_unresolved_conflict:
        return None
    values = platform.value if isinstance(platform.value, list) else [platform.value]
    labels = list(
        dict.fromkeys(
            ecosystem_display_label(text)
            for value in values
            if isinstance(value, str) and (text := value.strip())
        )
    )
    if not labels:
        return None
    audience = [f"Developers using {label}." for label in labels]
    return FactRecordV2(
        fact_id=descriptive_fact_id("product.audience", "platform-derived"),
        field="product.audience",
        value=audience,
        source=platform.source,
        verification_state=platform.verification_state,
        authoritative_owner=platform.authoritative_owner,
        confidence=platform.confidence,
        supporting_fact_ids=[platform.fact_id],
        affected_surfaces=SURFACE_DEPENDENCIES["product.audience"],
    )


__all__ = ["derive_platform_audience"]
