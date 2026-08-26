"""Prefer maintainer capability bullets the authored cluster would bind less precisely."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.document_structure import heading_identity, parse_headings
from readme_agent.readme.source_claim_fact_binding import complete_source_claim_fact_binding

_CAPABILITY_BULLET = re.compile(r"(?m)^\s*[-*+]\s+\*\*[^*]+\*\*")


def source_capability_bullet_fact_ids(
    source_text: str,
    facts: ProductFactsV2,
) -> frozenset[str]:
    """Return the accepted facts the source's own capability bullets bind.

    Only bullets inside a `Key Capabilities` section count, and only through the
    same complete binding the claim-accountability path uses, so this reports
    what the maintainer's wording actually proves rather than what it mentions.
    """

    target = heading_identity("Key Capabilities")
    for heading in parse_headings(source_text):
        if heading.level != 2 or heading_identity(heading.title) != target:
            continue
        body_start = len(source_text[: heading.heading_end].encode("utf-8"))
        body_end = len(source_text[: heading.section_end].encode("utf-8"))
        source_bytes = source_text.encode("utf-8")
        bound: set[str] = set()
        for claim in assess_material_claims(source_text):
            if not (body_start <= claim.source_byte_start and claim.source_byte_end <= body_end):
                continue
            text = source_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
            if _CAPABILITY_BULLET.match(text) is None:
                continue
            binding = complete_source_claim_fact_binding(source_text, claim, facts)
            if binding is not None:
                bound.update(coordinate.fact_id for coordinate in binding.fact_coordinates)
        return frozenset(bound)
    return frozenset()


def authored_cluster_loses_source_facts(
    source_text: str,
    facts: ProductFactsV2,
    authored_fact_fields: tuple[str, ...],
) -> bool:
    """Report whether authored capability prose binds fewer facts than the source.

    idea.md l.307-316: the existing README is "a high-value, product-agent-curated
    source to reuse wherever validation permits", and "regeneration convenience is
    never a reason to discard valuable curated information". When the maintainer's
    own capability bullets prove accepted facts that the authored rewording no
    longer binds, the rewrite is a net loss of grounding, so the deterministic
    fact-bound rows are preferred for that section.

    This also keeps the section resolvable: an inherited bullet can only clear
    claim accountability as `verified_equivalence` when the candidate binds the
    same facts (`fact_bound_capability_candidate_claims`). A rewording that drops
    one -- observed on the C++ canary, where the source bullets bind
    `product.problems_solved` and the authored prose does not -- leaves the bullet
    unresolvable, so it must be preserved verbatim *as well*, which is exactly the
    duplicate capability inventory idea.md l.85 forbids.
    """

    source_fact_ids = source_capability_bullet_fact_ids(source_text, facts)
    if not source_fact_ids:
        return False
    source_fields = {facts.fact_by_id(fact_id).field for fact_id in source_fact_ids}
    return not source_fields.issubset(set(authored_fact_fields))


__all__ = ["authored_cluster_loses_source_facts", "source_capability_bullet_fact_ids"]
