"""Canonical Qwen section authoring: planning, persistence, reuse, and template consumption."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from section_authoring_test_support import build_product_facts_v2

from readme_agent.evidence.writer import verify_sha256sums
from readme_agent.facts.protected_content import fingerprint_protected_content
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.prompt_registry import prompt_hash
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.presentation.verified_template_draft import build_verified_template_draft
from readme_agent.presentation.verified_template_runtime import build_verified_template_compilation
from readme_agent.readme.agentic_composition_models import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.claim_accountability import build_readme_claim_accountability_map
from readme_agent.readme.claim_map import ReadmeClaimMapV1
from readme_agent.readme.public_limitations import public_limitation_phrases
from readme_agent.readme.section_authoring_specs import build_canonical_section_authoring_specs
from readme_agent.specialists.independent_readme_review import IndependentReadmeReviewResultV1
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
from readme_agent.specialists.section_authoring_repair import reauthor_rejected_sections
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
        is_example = "Task family: example_framing" in messages[-1]["content"]
        return AnalysisResult(
            parsed={
                "units": [
                    {
                        "heading": (
                            "Public API Introduction"
                            if is_example
                            else "Process Repository Content"
                        ),
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
    quick_start = next(spec for spec in specs if spec.section_id == "quick_start")
    limitations = next(spec for spec in specs if spec.section_id == "scope_and_limitations")
    assert all(spec.max_facts_per_cluster == 4 for spec in specs)
    assert quick_start.seo_vocabulary == ()
    assert "verified" not in quick_start.section_objective.casefold()
    assert "minimal" not in quick_start.section_objective.casefold()
    assert "do not enumerate" in limitations.section_objective.casefold()
    assert "supplied separately" in limitations.section_objective.casefold()
    assert all(1 <= len(spec.accepted_fact_ids) <= 4 for spec in specs)


def test_directional_format_names_do_not_leak_through_prose_job_seo_vocabulary():
    facts = build_product_facts_v2(
        field_values={
            "product.capabilities": [
                "Create document objects",
                "File format import and export for OBJ and GLTF",
            ],
            "product.formats": ["Input format: OBJ", "Output format: GLTF"],
        }
    )

    specs = build_canonical_section_authoring_specs(facts)

    for spec in specs:
        assert all("OBJ" not in term and "GLTF" not in term for term in spec.seo_vocabulary)


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
    assert len(first_client.calls) == 3
    assert first.expected_cluster_ids == (
        "summary",
        "key_capabilities",
        "installation",
    )

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
    assert second.reused_cluster_count == 3

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
    assert third.reused_cluster_count == 2
    assert load_section_authoring_document(ORG_REPO, REVISION) == third


def test_review_repair_reauthors_only_the_rejected_prose_slot(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    facts = build_product_facts_v2()
    specs = build_canonical_section_authoring_specs(facts)
    cache_dir = default_section_authoring_cache_dir(
        "aspose-3d-foss", ORG_REPO.split("/")[1], REVISION
    )
    first_client = CountingClient()
    first = author_and_persist_readme_sections(
        org_repo=ORG_REPO,
        source_revision=REVISION,
        source_text=SOURCE,
        product_facts=facts,
        protected_content=fingerprint_protected_content(SOURCE),
        section_specs=specs,
        client=first_client,
        cache_dir=cache_dir,
    )
    review = IndependentReadmeReviewResultV1(
        verdict="REJECT_REPAIRABLE",
        reasoning="The capability wording is not visitor-facing.",
        failed_criteria=["clarity"],
        sections_affected=["key-capabilities"],
        required_repair="Describe the concrete developer outcome instead of the mechanism.",
    )
    repair_client = CountingClient()

    repaired = reauthor_rejected_sections(
        org_repo=ORG_REPO,
        source_revision=REVISION,
        source_text=SOURCE,
        product_facts_v2=facts.model_dump(mode="json"),
        prior_document=first.model_dump(mode="json"),
        review=review,
        client=repair_client,
    )

    assert repaired is not None
    assert len(repair_client.calls) == 1
    assert repaired.provider_logical_calls == 1
    assert repaired.reused_cluster_count == len(first.outcomes) - 1
    assert (
        next(
            outcome
            for outcome in repaired.outcomes
            if outcome.target_section_id == "key_capabilities"
        ).packet_hash
        != next(
            outcome for outcome in first.outcomes if outcome.target_section_id == "key_capabilities"
        ).packet_hash
    )


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
    accountability = build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=SOURCE,
        candidate_text=compiled.candidate,
        facts=facts,
        generated_claim_map=ReadmeClaimMapV1(
            org_repo=facts.org_repo,
            facts_hash=facts.canonical_hash(),
            candidate_sha256=hashlib.sha256(compiled.candidate.encode("utf-8")).hexdigest(),
            claims=[],
        ),
        candidate_content_provenance=compiled.provenance,
    )
    candidate_claims = assess_material_claims(compiled.candidate)
    for outcome in outcomes:
        expected_text = outcome.result.units[0].text
        claim = next(
            claim
            for claim in candidate_claims
            if expected_text
            in compiled.candidate.encode("utf-8")[
                claim.source_byte_start : claim.source_byte_end
            ].decode("utf-8")
        )
        record = next(
            item for item in accountability.claims if item.claim_id == f"candidate:{claim.claim_id}"
        )
        assert set(outcome.result.units[0].fact_ids) <= set(record.accepted_fact_ids)
        assert record.currently_accountable is True


def test_verified_template_deduplicates_authored_limitation_against_canonical_list():
    expected_limitation = "Mesh boolean operations are not implemented."
    facts = build_product_facts_v2(field_values={"product.limitations": [expected_limitation]})
    source_revision = facts.selected_fact("product.identity").source.source_revision
    assert source_revision is not None
    limitation = public_limitation_phrases(facts)[0]
    assert limitation == expected_limitation
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
        repository_summary="Bounded scope deduplication fixture.",
        section_decisions=[],
        overview_sentences=[],
    )
    outcome = _outcome(
        "scope_and_limitations",
        limitation,
        (facts.selected_fact("product.limitations").fact_id,),
    )
    document = SectionAuthoringDocumentV1(
        authoring_contract_version=SECTION_AUTHORING_CONTRACT_VERSION,
        org_repo=facts.org_repo,
        source_revision=source_revision,
        source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),
        facts_hash=facts.canonical_hash(),
        protected_literal_hash=fingerprint_protected_content(SOURCE).maintainer_region_hash,
        specs_sha256="1" * 64,
        expected_cluster_ids=("scope_and_limitations",),
        outcomes=(outcome,),
        complete=True,
    )

    draft = build_verified_template_draft(
        facts,
        SOURCE,
        source_revision,
        plan,
        section_authoring_document=document,
    )

    assert draft.sections["scope_and_limitations"].markdown.count(limitation) == 1
    assert "### Feature and Workflow Boundaries" in draft.sections["scope_and_limitations"].markdown


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
        model="deterministic-verified-section-authoring-v1",
        model_dump=lambda **_kwargs: {"model": "deterministic-verified-section-authoring-v1"},
    )
    captured: dict = {}
    dispatched_tools: list[str] = []

    def dispatch(tool_call, *_args, **kwargs):
        dispatched_tools.append(tool_call["function"]["name"])
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
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        readme_presentation,
        "build_verified_section_authoring_composition_plan",
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

    assert "section_authoring_document" in captured, result
    document = SectionAuthoringDocumentV1.model_validate(captured["section_authoring_document"])
    assert document.complete
    assert len(client.calls) == len(document.expected_cluster_ids)
    assert dispatched_tools == ["render_readme_candidate"]
    render_result = result["details"]["render_result"]
    assert render_result["section_authoring_provider_calls"] == len(client.calls)
    assert render_result["llm_called"] is True
    assert render_result["composition_provider_calls"] == 0
    assert render_result["composition_strategy"] == "deterministic_verified_section_authoring"
    bundle_dir = section_authoring_document_path(facts.org_repo, source_revision).parents[2]
    assert verify_sha256sums(bundle_dir)
