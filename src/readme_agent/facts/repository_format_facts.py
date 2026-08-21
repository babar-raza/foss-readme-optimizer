"""Promote current-revision repository format evidence into canonical facts."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from readme_agent.facts.format_direction import directional_format_fact_from_verified_evidence
from readme_agent.facts.repository_format_extraction import extract_repository_format_directions
from readme_agent.facts.schema_v2 import FactRecordV2
from readme_agent.registry.models import EvidenceBackedProductFact


def repository_format_fact_candidate(
    repository_root: Path,
    *,
    source_revision: str,
    family: str,
    platform: str,
    specifications: Sequence[EvidenceBackedProductFact],
    candidates: Sequence[FactRecordV2],
) -> FactRecordV2 | None:
    """Return a verified format fact only when accepted candidates do not already provide one."""

    if any(
        fact.field == "product.formats"
        and fact.verification_state in {"verified", "policy_approved"}
        and not fact.has_unresolved_conflict
        for fact in candidates
    ):
        return None

    example_fact = next(
        (fact for fact in reversed(candidates) if fact.field == "example.minimal"),
        None,
    )

    native_extraction = extract_repository_format_directions(
        repository_root,
        platform=platform,
        family=family,
        source_revision=source_revision,
    )
    fact = directional_format_fact_from_verified_evidence(
        source_revision=source_revision,
        specifications=specifications,
        example_fact=example_fact,
        native_extraction=native_extraction,
    )
    if fact.verification_state != "verified":
        return None
    return fact


__all__ = ["repository_format_fact_candidate"]
