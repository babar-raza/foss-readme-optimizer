"""Retain current verified facts when a replacement evidence path is unavailable."""

from __future__ import annotations

from collections.abc import Iterable

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2


def retain_current_verified_truth(
    base_facts: ProductFactsV2,
    replacements: dict[str, FactRecordV2],
    *,
    fields: Iterable[str],
) -> None:
    """Mutate replacements so failed recollection cannot erase current accepted truth."""

    for field in fields:
        try:
            established = base_facts.selected_fact(field)
            replacement = replacements[field]
        except KeyError:
            continue
        same_revision = (
            established.source.source_revision is not None
            and established.source.source_revision == replacement.source.source_revision
        )
        accepted = (
            established.verification_state in {"verified", "policy_approved"}
            and not established.has_unresolved_conflict
        )
        unavailable = replacement.verification_state in {"blocked", "missing"}
        if same_revision and accepted and unavailable:
            replacements[field] = established


__all__ = ["retain_current_verified_truth"]
