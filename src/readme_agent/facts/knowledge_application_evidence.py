"""Build the per-run `knowledge-application.json` evidence artifact: the
auditable answer to "exactly which imported knowledge affected this
candidate, where did it affect it, and why was it trusted?"

Deterministic and cheap (pure file I/O plus in-memory filtering, zero
network/LLM work) -- it recomputes `select_knowledge_claims()` rather than
threading the result through the fact-collection call chain, so it can be
called independently from evidence-writing code without changing that
chain's return contract.

Four distinct, never-conflated stages (Gate R5 of the 2026-08-19
knowledge-to-output pipeline course-correction review -- "evidence records
intent instead of actual influence" was a confirmed defect: the prior
version derived a single `sections_influenced` field from every disposition
carrying an `intended_section`, including claims this run went on to
*reject*, and did so before any document was ever rendered):

* **considered** -- every claim this run examined (`considered_count`,
  `dispositions`). Nothing here implies the claim reached output.
* **selected for planning** -- claims that survived corroboration/
  freshness/relevance gating into a `FactRecordV2`
  (`sections_selected_for_planning`, `fact_fields_produced`). Still not
  proof the renderer used them -- a selected fact can go uncited if the
  agentic composition plan chose not to reference it.
* **influenced** -- sections where a real, *surviving*
  `ReadmeDocumentPlanV1` operation actually cites one of this run's
  selected fact IDs in its own `fact_ids` (`sections_influenced`). Requires
  the caller to pass the real `document_plan` from
  `document_renderer.build_readme_document_candidate()`; when no plan is
  available yet (this evidence is written once at fact-collection time,
  before any candidate has been rendered, and again -- superseding the
  first -- once `readme/idea_candidate.py` has a real plan) this is
  correctly empty, never guessed from intent.
* **rendered output spans** -- the exact operation(s) that carried each
  influencing fact into the candidate (`rendered_output_spans`): operation
  id, section, and the operation's own `replacement_sha256` (the same hash
  `ReadmeDocumentOperationV1` already carries and `document_validation.py`
  already verifies against the rendered candidate bytes -- reused as the
  span's own integrity anchor rather than re-deriving a second, possibly
  drifting, byte range).
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
from readme_agent.facts.schema_v2 import descriptive_fact_id
from readme_agent.readme.document_plan import ReadmeDocumentPlanV1


class RenderedOutputSpanV1(BaseModel):
    """One surviving document-plan operation that actually carried a
    selected knowledge fact into the rendered candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: str
    section: str | None
    operation_id: str
    operation: str
    replacement_sha256: str


class KnowledgeApplicationV1(BaseModel):
    """One repository/run's complete imported-knowledge accountability
    record. Every field here is either read directly off the real
    `KnowledgeSelectionResultV1`/`ReadmeDocumentPlanV1` this run computed,
    or derived from them -- never narrated."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 2
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
    sections_considered: tuple[str, ...]
    sections_selected_for_planning: tuple[str, ...]
    sections_influenced: tuple[str, ...]
    rendered_output_spans: tuple[RenderedOutputSpanV1, ...]
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
    document_plan: ReadmeDocumentPlanV1 | None = None,
) -> KnowledgeApplicationV1:
    result = select_knowledge_claims(
        family,
        platform,
        data_root=data_root,
        clone_cache=clone_cache,
        source_revision=source_revision,
    )
    fact_fields = tuple(sorted({fact.field for fact in result.fact_records}))
    field_fact_ids = {
        field: descriptive_fact_id(field, "aspose-knowledge") for field in fact_fields
    }
    sections_considered = tuple(
        sorted({d.intended_section for d in result.dispositions if d.intended_section})
    )
    sections_selected_for_planning = tuple(
        sorted(
            {d.intended_section for d in result.dispositions if d.accepted and d.intended_section}
        )
    )

    rendered_output_spans: tuple[RenderedOutputSpanV1, ...] = ()
    sections_influenced: tuple[str, ...] = ()
    if document_plan is not None:
        spans: list[RenderedOutputSpanV1] = []
        influenced: set[str] = set()
        field_by_fact_id = {fact_id: field for field, fact_id in field_fact_ids.items()}
        section_by_field = {
            d.resulting_fact_field: d.intended_section
            for d in result.dispositions
            if d.accepted and d.resulting_fact_field is not None and d.intended_section
        }
        for operation in document_plan.operations:
            for fact_id in operation.fact_ids:
                field = field_by_fact_id.get(fact_id)
                if field is None:
                    continue
                section = section_by_field.get(field)
                spans.append(
                    RenderedOutputSpanV1(
                        fact_id=fact_id,
                        section=section,
                        operation_id=operation.operation_id,
                        operation=operation.operation,
                        replacement_sha256=operation.replacement_sha256,
                    )
                )
                if section is not None:
                    influenced.add(section)
        rendered_output_spans = tuple(spans)
        sections_influenced = tuple(sorted(influenced))

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
        sections_considered=sections_considered,
        sections_selected_for_planning=sections_selected_for_planning,
        sections_influenced=sections_influenced,
        rendered_output_spans=rendered_output_spans,
        load_findings=result.load_findings,
        dispositions=result.dispositions,
        seo_keyword_dispositions=seo_dispositions,
    )


__all__ = ["KnowledgeApplicationV1", "RenderedOutputSpanV1", "build_knowledge_application_report"]
