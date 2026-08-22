"""Canonical Qwen section authoring: planning, persistence, reuse, and template consumption."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from section_authoring_test_support import build_product_facts_v2

from readme_agent.facts.protected_content import fingerprint_protected_content
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.prompt_registry import prompt_hash
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.presentation.verified_template_draft import build_verified_template_draft
from readme_agent.presentation.verified_template_runtime import build_verified_template_compilation
from readme_agent.readme.agentic_composition_models import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.section_authoring_specs import build_canonical_section_authoring_specs
from readme_agent.specialists.section_authoring_cache import (
    default_section_authoring_cache_dir,
)
from readme_agent.specialists.section_authoring_contracts import (
    SECTION_AUTHORING_CONTRACT_VERSION,
    SectionAuthoringDocumentV1,
    SectionAuthoringOutcomeV1,
    SectionAuthoringReceiptV1,
    SectionClusterAuthoringResultV1,
    SectionClusterUnitV1,
)
from readme_agent.specialists.section_authoring_document import (
    author_and_persist_readme_sections,
)
from readme_agent.specialists.section_authoring_store import (
    load_section_authoring_document,
    section_authoring_document_path,
)
from readme_agent.state.schema import DomainStateV1
from readme_agent.supervisor.portfolio_proof_engine.section_authoring_adapter import (
    resolve_section_authoring_progress,
)

ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
REVISION = "a" * 40
SOURCE = "# Aspose.3D FOSS for Python\n\nA focused 3D library.\n"
FACTS_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "readmes"
    / "verified_source_assurance"
    / "aspose-3d-python-facts-ab1a2267.json"
)


class CountingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def analyze_section_cluster(self, messages, accepted_fact_ids):
        self.calls.append(tuple(accepted_fact_ids))
        return AnalysisResult(
            parsed={
                "units": [
                    {
                        "heading": "Process Repository Content",
                        "text": "Professional visitor-facing prose grounded in this fact cluster.",
                        "fact_ids": list(accepted_fact_ids),
                    }
                ],
                "omitted": [],
            },
            meta=LLMResponseMeta(request_id=f"request-{len(self.calls)}", model="qwen3-next"),
        )


def _receipt(packet_hash: str) -> SectionAuthoringReceiptV1:
    return SectionAuthoringReceiptV1(
        actor_id="llm-route:section-cluster-authoring",
        prompt_id="section_cluster_authoring",
        prompt_sha256=prompt_hash("section_cluster_authoring"),
        packet_hash=packet_hash,
        raw_output_sha256="c" * 64,
        provider_model="qwen3-next",
        semantic_retry_used=False,
        logical_call_count=1,
    )


def _outcome(
    section: str,
    text: str,
    fact_ids: tuple[str, ...],
    *,
    heading: str = "Process 3D Content",
) -> SectionAuthoringOutcomeV1:
    packet_hash = hashlib.sha256(section.encode()).hexdigest()
    return SectionAuthoringOutcomeV1(
        target_section_id=section,
        packet_hash=packet_hash,
        result=SectionClusterAuthoringResultV1(
            units=(SectionClusterUnitV1(heading=heading, text=text, fact_ids=fact_ids),),
        ),
        receipt=_receipt(packet_hash),
    )


def test_canonical_specs_cover_five_bounded_public_prose_jobs():
    facts = build_product_facts_v2()
    specs = build_canonical_section_authoring_specs(facts)

    assert [spec.section_id for spec in specs] == [
        "summary",
        "key_capabilities",
        "installation",
        "quick_start",
        "scope_and_limitations",
    ]
    assert all(1 <= len(spec.accepted_fact_ids) <= 4 for spec in specs)


def test_document_reuses_unchanged_clusters_and_invalidates_only_one(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    facts = build_product_facts_v2()
    specs = build_canonical_section_authoring_specs(facts)[:3]
    protected = fingerprint_protected_content(SOURCE)
    cache_dir = default_section_authoring_cache_dir(
        "aspose-3d-foss",
        ORG_REPO.split("/")[1],
        REVISION,
    )
    first_client = CountingClient()

    first = author_and_persist_readme_sections(
        org_repo=ORG_REPO,
        source_revision=REVISION,
        source_text=SOURCE,
        product_facts=facts,
        protected_content=protected,
        section_specs=specs,
        client=first_client,
        cache_dir=cache_dir,
    )
    assert first.complete
    assert len(first_client.calls) == len(specs)

    second_client = CountingClient()
    second = author_and_persist_readme_sections(
        org_repo=ORG_REPO,
        source_revision=REVISION,
        source_text=SOURCE,
        product_facts=facts,
        protected_content=protected,
        section_specs=specs,
        client=second_client,
        cache_dir=cache_dir,
    )
    assert second_client.calls == []
    assert second.reused_cluster_count == len(specs)

    changed_specs = list(specs)
    changed_specs[1] = changed_specs[1].__class__(
        **{
            **changed_specs[1].__dict__,
            "section_objective": changed_specs[1].section_objective + " Keep it concise.",
        }
    )
    third_client = CountingClient()
    third = author_and_persist_readme_sections(
        org_repo=ORG_REPO,
        source_revision=REVISION,
        source_text=SOURCE,
        product_facts=facts,
        protected_content=protected,
        section_specs=changed_specs,
        client=third_client,
        cache_dir=cache_dir,
    )
    assert len(third_client.calls) == 1
    assert third.reused_cluster_count == len(specs) - 1
    assert load_section_authoring_document(ORG_REPO, REVISION) == third


def test_complete_document_is_visible_to_stage_adapter(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    facts = build_product_facts_v2()
    specs = build_canonical_section_authoring_specs(facts)[:1]
    author_and_persist_readme_sections(
        org_repo=ORG_REPO,
        source_revision=REVISION,
        source_text=SOURCE,
        product_facts=facts,
        protected_content=fingerprint_protected_content(SOURCE),
        section_specs=specs,
        client=CountingClient(),
        cache_dir=tmp_path / "cache",
    )

    progress = resolve_section_authoring_progress(ORG_REPO, REVISION, facts.canonical_hash())
    assert progress is not None
    assert progress.packets_ready
    assert progress.sections_authored
    assert progress.evidence_ref and progress.evidence_ref.endswith("document.json")
    assert resolve_section_authoring_progress(ORG_REPO, REVISION, "f" * 64) is None


def test_tampered_document_checksum_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    facts = build_product_facts_v2()
    author_and_persist_readme_sections(
        org_repo=ORG_REPO,
        source_revision=REVISION,
        source_text=SOURCE,
        product_facts=facts,
        protected_content=fingerprint_protected_content(SOURCE),
        section_specs=build_canonical_section_authoring_specs(facts)[:1],
        client=CountingClient(),
        cache_dir=tmp_path / "cache",
    )
    path = section_authoring_document_path(ORG_REPO, REVISION)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["document"]["failure"] = "tampered"
    path.write_text(json.dumps(record), encoding="utf-8")

    assert load_section_authoring_document(ORG_REPO, REVISION) is None
    assert resolve_section_authoring_progress(ORG_REPO, REVISION, facts.canonical_hash()) is None


def test_verified_template_consumes_authored_bytes_with_fact_lineage():
    facts = ProductFactsV2.model_validate_json(FACTS_FIXTURE.read_text(encoding="utf-8"))
    source_revision = facts.selected_fact("product.identity").source.source_revision
    assert source_revision is not None
    assessment = assess_readme_document(
        facts.org_repo,
        SOURCE,
        facts,
        base_revision=source_revision,
    )
    plan = ReadmeAgenticCompositionPlanV1(
        org_repo=facts.org_repo,
        source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),
        facts_hash=facts.canonical_hash(),
        assessment_hash=assessment.canonical_hash(),
        prompt_sha256="d" * 64,
        tool_schema_sha256="e" * 64,
        input_sha256="f" * 64,
        model="qwen3-next",
        attempt_count=1,
        repository_summary="Bounded section authoring fixture.",
        section_decisions=[],
        overview_sentences=[],
    )
    identity_id = facts.selected_fact("product.identity").fact_id
    audience_id = facts.selected_fact("product.audience").fact_id
    capability_id = facts.selected_fact("product.capabilities").fact_id
    outcomes = (
        _outcome(
            "summary",
            "Aspose.3D FOSS for Python helps Python developers work with 3D assets.",
            (identity_id, audience_id),
        ),
        _outcome(
            "key_capabilities",
            "Create and process 3D scenes with repository-verified functionality.",
            (capability_id,),
        ),
    )
    document = SectionAuthoringDocumentV1(
        authoring_contract_version=SECTION_AUTHORING_CONTRACT_VERSION,
        org_repo=facts.org_repo,
        source_revision=source_revision,
        source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),
        facts_hash=facts.canonical_hash(),
        protected_literal_hash=fingerprint_protected_content(SOURCE).maintainer_region_hash,
        specs_sha256="1" * 64,
        expected_cluster_ids=("summary", "key_capabilities"),
        outcomes=outcomes,
        complete=True,
    )

    draft = build_verified_template_draft(
        facts,
        SOURCE,
        source_revision,
        plan,
        section_authoring_document=document,
    )

    assert draft.summary.markdown == outcomes[0].result.units[0].text
    assert draft.summary.fact_fields == ["product.identity", "product.audience"]
    assert outcomes[1].result.units[0].text in draft.sections["key_capabilities"].markdown
    assert draft.sections["key_capabilities"].fact_fields == ["product.capabilities"]

    compiled = build_verified_template_compilation(
        facts,
        SOURCE,
        source_revision,
        plan,
        section_authoring_document=document,
    )
    assert outcomes[0].result.units[0].text in compiled.candidate
    assert outcomes[1].result.units[0].text in compiled.candidate
    authored_provenance = [
        binding
        for binding in compiled.provenance
        if binding.provenance_id.startswith("template.section-authoring.")
    ]
    assert {fact_id for binding in authored_provenance for fact_id in binding.fact_ids} >= {
        identity_id,
        audience_id,
        capability_id,
    }


def test_readme_specialist_passes_complete_section_document_to_canonical_renderer(
    tmp_path, monkeypatch
):
    from readme_agent.specialists import readme_presentation

    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    facts = ProductFactsV2.model_validate_json(FACTS_FIXTURE.read_text(encoding="utf-8"))
    source_revision = facts.selected_fact("product.identity").source.source_revision
    assert source_revision is not None
    readme_path = tmp_path / "README.md"
    readme_path.write_text(SOURCE, encoding="utf-8")
    snapshot = SimpleNamespace(
        root_path=tmp_path,
        readme_path="README.md",
        source_revision=source_revision,
    )
    prepared = SimpleNamespace(facts=facts, lifecycle_status="FACTS_READY")
    deterministic_plan = SimpleNamespace(
        model="deterministic-verified-preservation-v1",
        model_dump=lambda **_kwargs: {"model": "deterministic-verified-preservation-v1"},
    )
    captured: dict = {}

    def dispatch(_tool_call, *_args, **kwargs):
        captured.update(kwargs["extra_kwargs"])
        return SimpleNamespace(
            outcome="executed",
            error=None,
            result={"needs_write": True, "llm_called": False, "llm_calls": []},
        )

    monkeypatch.setattr(readme_presentation, "proposal_only_active", lambda: True)
    monkeypatch.setattr(readme_presentation, "current_repository_snapshot", lambda _repo: snapshot)
    monkeypatch.setattr(
        readme_presentation,
        "load_prepared_product_truth",
        lambda *_args, **_kwargs: prepared,
    )
    monkeypatch.setattr(
        readme_presentation,
        "build_verified_preservation_composition_plan",
        lambda *_args, **_kwargs: deterministic_plan,
    )
    monkeypatch.setattr(readme_presentation, "dispatch_tool_call", dispatch)
    client = CountingClient()

    result = readme_presentation._render_node(
        DomainStateV1(domain="readme_presentation"),
        {
            "configurable": {
                "org_repo": facts.org_repo,
                "backend": object(),
                "current_revision": source_revision,
                "section_authoring_client": client,
            }
        },
    )

    document = SectionAuthoringDocumentV1.model_validate(captured["section_authoring_document"])
    assert document.complete
    assert len(client.calls) == len(document.expected_cluster_ids)
    render_result = result["details"]["render_result"]
    assert render_result["section_authoring_provider_calls"] == len(client.calls)
    assert render_result["llm_called"] is True
