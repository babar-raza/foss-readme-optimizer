"""The real candidate-generation entry point for the section-cluster authoring engine.

A candidate-generation caller (deterministic assembly, a future replacement for the monolithic
`readme/agentic_composition.py` single-call composer, or a section-level repair path) supplies
one `SectionAuthoringSpecV1` per README section it wants authored and calls
`author_readme_sections()` once. This is the seam: it chains the deterministic cluster planner,
the packet builder, and the bounded authoring call/cache for every section, so a caller never
hand-assembles those three pieces itself. A cluster failure raises and stops only that
document's remaining unauthored clusters -- already-produced outcomes for earlier sections are
returned to the caller in the exception's `outcomes` attribute so a partial document is never
silently discarded.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from readme_agent.facts.protected_content import ProtectedContentSnapshotV1
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm.section_authoring_prompts import SectionAuthoringTaskFamily
from readme_agent.readme.section_cluster_planner import plan_section_clusters
from readme_agent.specialists.section_authoring_contracts import SectionAuthoringOutcomeV1
from readme_agent.specialists.section_authoring_packet import build_section_authoring_packet
from readme_agent.specialists.section_cluster_authoring import (
    SectionAuthoringAcceptanceError,
    SectionClusterAuthorClientLike,
    execute_section_cluster_authoring,
)


@dataclass(frozen=True)
class SectionAuthoringSpecV1:
    """One README section's authoring request -- fact selection is the caller's deterministic
    decision (e.g. the presentation plan's per-section `fact_ids`); this module only plans
    clusters, builds packets, and executes/caches the bounded calls those facts require."""

    section_id: str
    task_family: SectionAuthoringTaskFamily
    section_objective: str
    accepted_fact_ids: tuple[str, ...]
    do_not_claim_fact_ids: tuple[str, ...] = ()
    seo_vocabulary: tuple[str, ...] = ()
    current_source_text: str | None = None


class SectionAuthoringDocumentError(SectionAuthoringAcceptanceError):
    """One section's authoring call failed; `outcomes` carries every section already produced
    before it, so a caller can decide to keep partial progress rather than lose it."""

    def __init__(self, message: str, *, outcomes: list[SectionAuthoringOutcomeV1]) -> None:
        super().__init__(message)
        self.outcomes = outcomes


def author_readme_sections(
    *,
    org_repo: str,
    source_revision: str,
    product_facts: ProductFactsV2,
    protected_content: ProtectedContentSnapshotV1,
    section_specs: Sequence[SectionAuthoringSpecV1],
    client: SectionClusterAuthorClientLike,
    cache_dir: Path | None = None,
) -> list[SectionAuthoringOutcomeV1]:
    """Author (or reuse) every requested section's cluster(s) for one document.

    Deterministic code (unchanged) owns everything downstream of this call: assembling the
    returned prose units into README order, splicing in real commands/code/links/badges, and
    validating the assembled candidate.
    """

    outcomes: list[SectionAuthoringOutcomeV1] = []
    for spec in section_specs:
        clusters = plan_section_clusters(
            section_id=spec.section_id, fact_ids=spec.accepted_fact_ids
        )
        for cluster in clusters:
            packet = build_section_authoring_packet(
                org_repo=org_repo,
                source_revision=source_revision,
                target_section_id=cluster.target_section_id,
                task_family=spec.task_family,
                section_objective=spec.section_objective,
                product_facts=product_facts,
                accepted_fact_ids=cluster.accepted_fact_ids,
                do_not_claim_fact_ids=spec.do_not_claim_fact_ids,
                protected_content=protected_content,
                seo_vocabulary=spec.seo_vocabulary,
                current_source_text=spec.current_source_text,
            )
            try:
                outcomes.append(
                    execute_section_cluster_authoring(
                        packet=packet, client=client, cache_dir=cache_dir
                    )
                )
            except SectionAuthoringAcceptanceError as exc:
                raise SectionAuthoringDocumentError(
                    f"document authoring stopped at section {cluster.target_section_id!r}: {exc}",
                    outcomes=outcomes,
                ) from exc
    return outcomes
