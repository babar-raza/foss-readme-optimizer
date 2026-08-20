"""Deterministically group accepted facts into bounded section-authoring clusters.

Splits at the cap rather than letting one authoring call exceed it. The probe's one reproduced
defect (`STAGE3-INDIVIDUAL-limitations-3d-python` in
`runs/owner_audit_staging/qwen3-next-editorial-probe-aa9981021/`) was a single call left with 5
facts against a `maxItems=4` schema, silently dropping the 5th fact instead of merging two facts
into one unit -- decomposing into clusters that each stay under the cap avoided this entirely.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from readme_agent.specialists.section_authoring_contracts import MAX_ACCEPTED_FACTS


@dataclass(frozen=True)
class SectionClusterPlanV1:
    """One authoring call's target section identity and its accepted fact_ids."""

    target_section_id: str
    accepted_fact_ids: tuple[str, ...]


def plan_section_clusters(
    *,
    section_id: str,
    fact_ids: Sequence[str],
    max_facts_per_cluster: int = MAX_ACCEPTED_FACTS,
) -> tuple[SectionClusterPlanV1, ...]:
    """Split one section's accepted fact_ids into clusters of at most `max_facts_per_cluster`.

    Order-preserving and deterministic: the same `fact_ids` sequence always yields the same
    cluster IDs and membership, so a re-plan against unchanged facts reproduces identical
    cache keys (`specialists/section_authoring_cache.py`). A single-cluster section keeps the
    bare `section_id`; a split section gets a stable `-N` suffix per cluster.
    """

    if max_facts_per_cluster < 1:
        raise ValueError("max_facts_per_cluster must be at least 1")
    ordered = tuple(dict.fromkeys(fact_ids))
    if not ordered:
        return ()
    chunks = [
        ordered[index : index + max_facts_per_cluster]
        for index in range(0, len(ordered), max_facts_per_cluster)
    ]
    if len(chunks) == 1:
        return (SectionClusterPlanV1(target_section_id=section_id, accepted_fact_ids=chunks[0]),)
    return tuple(
        SectionClusterPlanV1(
            target_section_id=f"{section_id}-{position}",
            accepted_fact_ids=chunk,
        )
        for position, chunk in enumerate(chunks, start=1)
    )
