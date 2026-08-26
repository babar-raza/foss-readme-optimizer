"""Prefer maintainer capability bullets the authored cluster would bind less precisely."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Protocol, TypeVar

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.document_structure import heading_identity, parse_headings
from readme_agent.readme.source_claim_fact_binding import complete_source_claim_fact_binding


class _AuthoringSpecLike(Protocol):
    """The two fields the capability decision reads from a section-authoring spec.

    Structurally typed over `SectionAuthoringSpecV1` rather than importing it: the
    spec type lives in `specialists`, which imports this layer, so naming it here
    would close an import cycle for an annotation nothing needs at runtime.
    """

    @property
    def section_id(self) -> str: ...

    @property
    def accepted_fact_ids(self) -> tuple[str, ...]: ...


_SpecT = TypeVar("_SpecT", bound=_AuthoringSpecLike)

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


def section_specs_without_superseded_capability_authoring(
    specs: Sequence[_SpecT],
    source_text: str,
    facts: ProductFactsV2,
) -> tuple[_SpecT, ...]:
    """Drop the `key_capabilities` authoring job the source's own bullets already outbind.

    This is the *upstream* half of the duplicate-capability repair, and it has to
    run here rather than at composition time. Once a cluster is authored it is
    checksum-bound into the composition plan, so it can no longer be withheld;
    and a reworded cluster can never clear claim accountability by equivalence,
    because `_coordinates_cover` demands exact list-item coordinate identity that
    a rewrite does not reproduce. Both halves therefore survive into one section
    and repeat the same inventory, which idea.md l.85 forbids.

    Skipping the job instead leaves the deterministic fact-bound rows in place.
    Those *do* bind the exact `product.capabilities` list coordinates (measured on
    the C++ canary: the required `/items/e98ef500be51ad93` is covered by the
    deterministic rows and by none of the authored prose), so the inherited
    bullets resolve as `verified_equivalence`, need no verbatim placement, and
    the duplicate never forms.

    Only the capability job is affected, and only when the source genuinely binds
    more than the authored cluster would -- a source with no `Key Capabilities`
    bullets, or one whose bullets bind nothing extra, leaves authoring untouched.
    """

    kept: list[_SpecT] = []
    for spec in specs:
        if spec.section_id == "key_capabilities":
            authored_fields = tuple(
                facts.fact_by_id(fact_id).field for fact_id in spec.accepted_fact_ids
            )
            if authored_cluster_loses_source_facts(source_text, facts, authored_fields):
                continue
        kept.append(spec)
    return tuple(kept)


__all__ = [
    "authored_cluster_loses_source_facts",
    "section_specs_without_superseded_capability_authoring",
    "source_capability_bullet_fact_ids",
]
