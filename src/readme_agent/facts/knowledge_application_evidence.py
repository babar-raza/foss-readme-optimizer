"""Build the per-run `knowledge-application.json` evidence artifact: the
auditable answer to "exactly which imported knowledge affected this
candidate, where did it affect it, and why was it trusted?"

Deterministic and cheap (pure file I/O plus in-memory filtering, zero
network/LLM work) -- it recomputes `select_knowledge_claims()` rather than
threading the result through the fact-collection call chain, so it can be
called independently from evidence-writing code without changing that
chain's return contract.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.aspose_knowledge_claims import KnowledgeLoadFindingV1
from readme_agent.facts.aspose_knowledge_selection import (
    KnowledgeClaimDispositionV1,
    select_knowledge_claims,
)
from readme_agent.facts.aspose_seo_keyword_facts import (
    SeoKeywordDispositionV1,
    seo_keyword_dispositions,
)


class KnowledgeApplicationV1(BaseModel):
    """One repository/run's complete imported-knowledge accountability
    record. Every field here is either read directly off the real
    `KnowledgeSelectionResultV1` this run computed, or derived from it --
    never narrated."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    org_repo: str
    family: str
    platform: str
    source_revision: str | None
    imported_bundle_repo_sha: str | None
    freshness: str
    considered_count: int
    selected_count: int
    rejected_count: int
    fact_fields_produced: tuple[str, ...]
    sections_influenced: tuple[str, ...]
    load_findings: tuple[KnowledgeLoadFindingV1, ...]
    dispositions: tuple[KnowledgeClaimDispositionV1, ...]
    seo_keyword_dispositions: tuple[SeoKeywordDispositionV1, ...]


def build_knowledge_application_report(
    org_repo: str,
    family: str,
    platform: str,
    *,
    data_root: Path,
    clone_cache: Path,
    source_revision: str | None,
) -> KnowledgeApplicationV1:
    result = select_knowledge_claims(
        family,
        platform,
        data_root=data_root,
        clone_cache=clone_cache,
        source_revision=source_revision,
    )
    fact_fields = tuple(sorted({fact.field for fact in result.fact_records}))
    sections = tuple(
        sorted({d.intended_section for d in result.dispositions if d.intended_section})
    )
    seo_dispositions = seo_keyword_dispositions(family, platform, data_root=data_root)
    return KnowledgeApplicationV1(
        org_repo=org_repo,
        family=family,
        platform=platform,
        source_revision=source_revision,
        imported_bundle_repo_sha=result.bundle_repo_sha,
        freshness=result.freshness,
        considered_count=len(result.dispositions),
        selected_count=result.selected_count,
        rejected_count=result.rejected_count,
        fact_fields_produced=fact_fields,
        sections_influenced=sections,
        load_findings=result.load_findings,
        dispositions=result.dispositions,
        seo_keyword_dispositions=seo_dispositions,
    )


__all__ = ["KnowledgeApplicationV1", "build_knowledge_application_report"]
