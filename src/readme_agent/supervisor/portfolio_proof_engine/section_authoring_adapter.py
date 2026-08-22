"""Observe checksum-valid section packet/authoring evidence for portfolio stages."""

from __future__ import annotations

from dataclasses import dataclass

from readme_agent import env
from readme_agent.llm.prompt_registry import prompt_hash
from readme_agent.specialists.section_authoring_contracts import (
    SECTION_AUTHORING_CONTRACT_VERSION,
)
from readme_agent.specialists.section_authoring_store import (
    load_section_authoring_document,
    section_authoring_document_path,
)


@dataclass(frozen=True)
class SectionAuthoringProgressV1:
    packets_ready: bool
    sections_authored: bool
    evidence_ref: str | None = None


def resolve_section_authoring_progress(
    org_repo: str,
    source_revision: str | None,
    facts_hash: str | None = None,
) -> SectionAuthoringProgressV1 | None:
    """Return progress only from a structurally valid record for the lifecycle revision."""

    if not source_revision:
        return None
    document = load_section_authoring_document(
        org_repo,
        source_revision,
        facts_hash=facts_hash,
    )
    if document is None:
        return None
    current_prompt_hash = prompt_hash("section_cluster_authoring")
    current_model = env.llm_model_for_job("section_cluster_authoring")
    if document.authoring_contract_version != SECTION_AUTHORING_CONTRACT_VERSION:
        return None
    if any(
        outcome.receipt.prompt_sha256 != current_prompt_hash
        or outcome.receipt.provider_model != current_model
        for outcome in document.outcomes
    ):
        return None
    return SectionAuthoringProgressV1(
        packets_ready=bool(document.expected_cluster_ids),
        sections_authored=document.complete,
        evidence_ref=str(section_authoring_document_path(org_repo, source_revision)),
    )
