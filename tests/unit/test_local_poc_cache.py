"""Complete-input cache decisions for accepted local README bundles."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.facts.acceptance_contract import current_fact_acceptance_contract
from readme_agent.facts.local_verification import local_verification_contract_hash
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.llm import prompt_registry
from readme_agent.llm.verification_prompts import separated_reviewer_standard_hash
from readme_agent.readme import document_templates
from readme_agent.readme.document_templates import document_template_hash
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2, SupervisorStateV1
from readme_agent.supervisor import local_poc_cache, local_poc_noop_reuse
from readme_agent.supervisor.local_poc_acceptance_binding import (
    bind_deterministic_validation,
    build_review_acceptance_binding,
)
from readme_agent.supervisor.portfolio_scheduler.contracts import canonical_sha256
from readme_agent.supervisor.stage_dependencies import (
    SelectedDependencyV1,
    build_stage_dependency_manifest,
    current_candidate_stage_dependency_manifest,
)

ORG_REPO = "org/repo"
SOURCE_REVISION = "a" * 40
CONTROL_FINGERPRINT = "b" * 64


def _ready_product_facts() -> ProductFactsV2:
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://org/repo",
        source_revision=SOURCE_REVISION,
    )
    renderable_values = {
        "product.audience": ["Developers using Python"],
        "product.problems_solved": ["Process widget files"],
        "product.capabilities": ["Create and inspect widgets"],
        "product.formats": ["WGT"],
    }
    records = [
        FactRecordV2(
            fact_id=descriptive_fact_id(field, "cache-fixture"),
            field=field,
            value=renderable_values.get(field, {"field": field}),
            source=source,
            verification_state="verified",
            authoritative_owner="repository-owner",
            confidence=1.0,
            affected_surfaces=["readme"],
        )
        for field in REQUIRED_PRODUCT_FIELDS
    ]
    return ProductFactsV2(
        org_repo=ORG_REPO,
        facts=records,
        selected_fact_ids={fact.field: fact.fact_id for fact in records},
    )


def _valid_cache(tmp_path):
    fact_contract = current_fact_acceptance_contract()
    reviewer_standard = separated_reviewer_standard_hash()
    product_facts = _ready_product_facts()
    state = RunStateV2(
        org_repo=ORG_REPO,
        readme_poc_lifecycle=ReadmePocLifecycleStateV2(
            status="NO_OP_PROVEN",
            source_revision=SOURCE_REVISION,
            facts_hash=product_facts.canonical_hash(),
            assessment_hash="d" * 64,
            presentation_plan_hash="e" * 64,
            candidate_hash="f" * 64,
            prompt_hash=None,
            fact_acceptance_contract_hash=fact_contract.canonical_hash(),
            fact_acceptance_component_hashes=fact_contract.component_hashes,
            reviewer_standard_hash=reviewer_standard,
            repair_budget_origin_hash="2" * 64,
        ),
        supervisor_state=SupervisorStateV1(
            control_plane_fingerprint=CONTROL_FINGERPRINT,
        ),
    )
    lifecycle = state.readme_poc_lifecycle
    bundle = tmp_path / SOURCE_REVISION
    component_manifest = current_candidate_stage_dependency_manifest(
        repository=ORG_REPO,
        source_revision=SOURCE_REVISION,
        ecosystem=None,
    )
    write_redacted_json(
        bundle / "manifest.json",
        {
            "org_repo": ORG_REPO,
            "source_revision": SOURCE_REVISION,
            "content_assurance": "repository_verified",
            "resolution_source": "repository_and_policy",
            "lifecycle_status": "NO_OP_PROVEN",
            "complete": True,
            "completed_stages": ["NO_OP_PROVEN"],
            "facts_hash": lifecycle.facts_hash,
            "assessment_hash": lifecycle.assessment_hash,
            "presentation_plan_hash": lifecycle.presentation_plan_hash,
            "candidate_hash": lifecycle.candidate_hash,
            "prompt_hash": lifecycle.prompt_hash,
            "fact_acceptance_contract_hash": fact_contract.canonical_hash(),
            "fact_acceptance_component_hashes": fact_contract.component_hashes,
            "local_verification_contract_hash": local_verification_contract_hash(),
            "prompt_registry_content_hash": prompt_registry.content_hash(),
            "prompt_dependency_hashes": prompt_registry.dependency_hashes(),
            "candidate_stage_dependency_key": component_manifest.stage_key,
            "candidate_stage_dependency_manifest": component_manifest.model_dump(mode="json"),
            "reviewer_standard_hash": reviewer_standard,
            "repair_budget_origin_hash": lifecycle.repair_budget_origin_hash,
        },
    )
    validation, deterministic_binding = bind_deterministic_validation(
        {
            "verdict": "accept",
            "official_mermaid_render": {
                "status": "not_applicable",
                "reason": "fixture has no diagram",
            },
        },
        candidate_hash=lifecycle.candidate_hash,
        candidate_stage_dependency_key=component_manifest.stage_key,
    )
    review_binding = build_review_acceptance_binding(
        validation,
        deterministic_binding,
        reviewer_standard_hash=reviewer_standard,
    ).model_dump(mode="json")
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["deterministic_validation_hash"] = canonical_sha256(validation)
    write_redacted_json(manifest_path, manifest)
    write_redacted_json(bundle / "review" / "deterministic-validation.json", validation)
    write_redacted_json(
        bundle / "review" / "independent-agent-review.json",
        {"verdict": "ACCEPT", "acceptance_binding": review_binding},
    )
    write_redacted_json(
        bundle / "planning" / "readme-document-plan.json",
        {"template_sha256": document_template_hash()},
    )
    write_redacted_json(
        bundle / "planning" / "agentic-composition-plan.json",
        {"prompt_sha256": prompt_registry.prompt_hash("plan_readme_composition")},
    )
    write_redacted_json(
        bundle / "review" / "final-verdict.json",
        {
            "verdict": "AGENT_APPROVED",
            "agent_approved": True,
            "deterministic_validation_passed": True,
            "acceptance_binding": review_binding,
        },
    )
    write_redacted_json(
        bundle / "review" / "no-op-proof.json",
        {
            "verdict": "NO_OP_PROVEN",
            "candidate_hash": lifecycle.candidate_hash,
            "patch_created": False,
            "duplicate_bundle_created": False,
            "agentic_review_reused": True,
            "llm_accounting_status": "EXACT",
            "new_provider_call_count": 0,
            "acceptance_binding": review_binding,
        },
    )
    write_redacted_json(
        bundle / "facts" / "product-facts.json",
        product_facts.model_dump(mode="json"),
    )
    refresh_sha256sums(bundle)
    return state, bundle


def _decision(state, bundle, *, source_revision=SOURCE_REVISION, control=CONTROL_FINGERPRINT):
    return local_poc_cache.evaluate_completed_local_poc_cache(
        state,
        bundle,
        current_source_revision=source_revision,
        current_control_plane_fingerprint=control,
    )


@pytest.mark.parametrize(
    ("ecosystem", "org_repo", "family"),
    [
        ("python", "aspose-3d-foss/Aspose.3D-FOSS-for-Python", "3d"),
        ("net", "aspose-3d-foss/Aspose.3D-FOSS-for-.NET", "3d"),
        ("java", "aspose-3d-foss/Aspose.3D-FOSS-for-Java", "3d"),
    ],
)
def test_cache_resolves_registry_family_before_hashing(monkeypatch, ecosystem, org_repo, family):
    contract = current_fact_acceptance_contract()
    observed: list[tuple[str | None, str | None]] = []
    monkeypatch.setattr(
        local_poc_cache,
        "require_listed",
        lambda observed_org_repo: SimpleNamespace(family=family),
    )

    def current(ecosystem=None, family=None):
        observed.append((ecosystem, family))
        return contract

    monkeypatch.setattr(local_poc_cache, "current_fact_acceptance_contract", current)

    local_poc_cache._current_dependencies(
        source_revision=SOURCE_REVISION,
        control_plane_fingerprint=CONTROL_FINGERPRINT,
        inventory_sha256=None,
        content_assurance="repository_verified",
        org_repo=org_repo,
        ecosystem=ecosystem,
    )

    assert observed == [(ecosystem, family)]


def _approved_cache(tmp_path):
    state, bundle = _valid_cache(tmp_path)
    lifecycle = state.readme_poc_lifecycle.model_copy(update={"status": "AGENT_APPROVED"})
    state = state.model_copy(update={"readme_poc_lifecycle": lifecycle})
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "lifecycle_status": "AGENT_APPROVED",
            "complete": False,
            "completed_stages": ["AGENT_APPROVED"],
        }
    )
    write_redacted_json(manifest_path, manifest)
    (bundle / "review" / "no-op-proof.json").unlink()
    refresh_sha256sums(bundle)
    return state, bundle


def test_complete_current_bundle_is_reusable_with_an_inspectable_cache_key(tmp_path):
    state, bundle = _valid_cache(tmp_path)

    first = _decision(state, bundle)
    second = _decision(state, bundle)

    assert first.reusable is True
    assert first.status == "NO_OP_PROVEN"
    assert first.mismatch_reasons == []
    assert first.earliest_affected_stage is None
    assert first.cache_key == second.cache_key


def test_reconciliation_error_denies_reuse_of_an_otherwise_valid_bundle(tmp_path):
    """Stage 3A: `candidate/readme-reconciliation.json` recording an
    `{"error": ...}` result must block reuse/promotion, not silently persist
    alongside an otherwise-accepted bundle."""

    state, bundle = _valid_cache(tmp_path)
    write_redacted_json(
        bundle / "candidate" / "readme-reconciliation.json",
        {"schema_version": 1, "error": "unaccounted source loss: bytes [10, 20)"},
    )
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert any(
        reason.startswith("readme_reconciliation_error") for reason in decision.mismatch_reasons
    )


def test_missing_reconciliation_evidence_does_not_by_itself_deny_reuse(tmp_path):
    """A bundle that never ran reconciliation at all (pre-Stage-3A, or one
    that simply has no `candidate/readme-reconciliation.json`) is not itself
    denied reuse -- only an explicit, persisted failure blocks."""

    state, bundle = _valid_cache(tmp_path)

    decision = _decision(state, bundle)

    assert decision.reusable is True
    assert not any(
        reason.startswith("readme_reconciliation") for reason in decision.mismatch_reasons
    )


def test_blocking_check_error_in_coverage_evidence_denies_reuse(tmp_path):
    """Stage 3B: a classified-blocking check recorded as *errored* (raised,
    or returned an uninterpretable shape) in `candidate/check-coverage.json`
    must deny reuse/promotion, not silently persist alongside an otherwise-
    accepted bundle."""

    state, bundle = _valid_cache(tmp_path)
    write_redacted_json(
        bundle / "candidate" / "check-coverage.json",
        {
            "schema_version": 1,
            "check_count": 1,
            "pass_count": 0,
            "fail_count": 0,
            "skip_count": 0,
            "error_count": 1,
            "not_applicable_count": 0,
            "entries": [
                {
                    "check_name": "check_banner_present",
                    "outcome": "error",
                    "severity": "hard_gate",
                    "classification": "applicable_reusable",
                    "blocking": True,
                    "reason": "raised TypeError",
                }
            ],
        },
    )
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert any(
        reason.startswith("blocking_check_gap:check_banner_present:error")
        for reason in decision.mismatch_reasons
    )


def _knowledge_application_payload(*, status="final", candidate_sha256="f" * 64, **overrides):
    payload = {
        "schema_version": 4,
        "status": status,
        "org_repo": "acme/product",
        "family": "cells",
        "platform": "java",
        "source_revision": SOURCE_REVISION,
        "facts_hash": None,
        "document_plan_hash": None,
        "candidate_sha256": candidate_sha256,
        "reviewer_disposition": None,
        "imported_bundle_repo_sha": None,
        "freshness": "current",
        "considered_count": 0,
        "selected_count": 0,
        "rejected_count": 0,
        "fact_fields_produced": [],
        "sections_considered": [],
        "sections_selected_for_planning": [],
        "sections_influenced": [],
        "rendered_output_spans": [],
        "final_dispositions": [],
        "load_findings": [],
        "dispositions": [],
        "seo_keyword_dispositions": [],
    }
    payload.update(overrides)
    return payload


def test_knowledge_application_error_denies_reuse_of_an_otherwise_valid_bundle(tmp_path):
    """K3-4: a top-level `{error: ...}` knowledge-application artifact must
    block reuse/promotion, not silently persist alongside an otherwise-
    accepted bundle."""

    state, bundle = _valid_cache(tmp_path)
    write_redacted_json(
        bundle / "knowledge-application.json",
        {"schema_version": 4, "error": "no post-render knowledge_application in render_result"},
    )
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert any(
        reason.startswith("knowledge_application_error") for reason in decision.mismatch_reasons
    )


def test_missing_knowledge_application_evidence_does_not_by_itself_deny_reuse(tmp_path):
    """A bundle with no `knowledge-application.json` at all (pre-K3, or a
    synthetic/unit-test bundle exercising unrelated acceptance-binding
    logic) is not itself denied reuse -- only an explicit, persisted
    failure blocks (same rationale as readme_reconciliation/check_coverage)."""

    state, bundle = _valid_cache(tmp_path)

    decision = _decision(state, bundle)

    assert decision.reusable is True
    assert not any(
        reason.startswith("knowledge_application") for reason in decision.mismatch_reasons
    )


def test_valid_final_knowledge_application_does_not_deny_reuse(tmp_path):
    state, bundle = _valid_cache(tmp_path)
    write_redacted_json(
        bundle / "knowledge-application.json",
        _knowledge_application_payload(),
    )
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is True
    assert not any(
        reason.startswith("knowledge_application") for reason in decision.mismatch_reasons
    )


def test_provisional_knowledge_application_at_acceptance_time_denies_reuse(tmp_path):
    """A still-`status="provisional"` report lingering at acceptance time
    means K3's real post-render call never landed for this candidate."""

    state, bundle = _valid_cache(tmp_path)
    write_redacted_json(
        bundle / "knowledge-application.json",
        _knowledge_application_payload(status="provisional"),
    )
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert "knowledge_application_not_final" in decision.mismatch_reasons


def test_stale_knowledge_application_candidate_sha256_denies_reuse(tmp_path):
    """The report's own `candidate_sha256` must match this exact candidate
    -- a mismatch means the report is bound to a different, superseded
    candidate and must never authorize this one's promotion."""

    state, bundle = _valid_cache(tmp_path)
    write_redacted_json(
        bundle / "knowledge-application.json",
        _knowledge_application_payload(candidate_sha256="0" * 64),
    )
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert "knowledge_application_stale" in decision.mismatch_reasons


def test_internally_inconsistent_knowledge_application_denies_reuse(tmp_path):
    """An "unaccounted rendered claim" (a fact_id in `rendered_output_spans`
    with no matching `rendered_with_exact_spans` disposition) is exactly the
    shape `KnowledgeApplicationV1`'s own model validator refuses to
    construct -- re-parsing a tampered/stale file on disk must fail closed
    here too, not just at original construction time."""

    state, bundle = _valid_cache(tmp_path)
    inconsistent = _knowledge_application_payload(
        rendered_output_spans=[
            {
                "fact_id": "aspose.feature_claims:aspose-knowledge",
                "section": "Key Capabilities",
                "operation_id": "op.1",
                "operation": "replace",
                "replacement_sha256": "a" * 64,
                "fact_coordinates": [
                    {
                        "fact_id": "aspose.feature_claims:aspose-knowledge",
                        "field": "aspose.feature_claims",
                        "path": "/items/0123456789abcdef",
                        "value_sha256": "b" * 64,
                        "normalization_version": "structured-fact-coordinate-v1",
                    }
                ],
            }
        ],
    )
    write_redacted_json(bundle / "knowledge-application.json", inconsistent)
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert any(
        reason.startswith("knowledge_application_invalid") for reason in decision.mismatch_reasons
    )


def test_blocking_check_skip_in_coverage_evidence_does_not_deny_reuse(tmp_path):
    """A classified-blocking check recorded merely as *skipped* does not
    deny reuse -- narrowed deliberately after `check_banner_present` (whose
    family/platform is only ever derived from a real imported-knowledge
    fact location) was found to skip in nearly every non-full-portfolio
    run, including this repo's own synthetic-fixture and end-to-end
    lifecycle tests. See GOV-014 (`plans/backlog-post-poc.md`) for the
    deferred, correctly-scoped fix."""

    state, bundle = _valid_cache(tmp_path)
    write_redacted_json(
        bundle / "candidate" / "check-coverage.json",
        {
            "schema_version": 1,
            "check_count": 1,
            "pass_count": 0,
            "fail_count": 0,
            "skip_count": 1,
            "error_count": 0,
            "not_applicable_count": 0,
            "entries": [
                {
                    "check_name": "check_banner_present",
                    "outcome": "skip",
                    "severity": "hard_gate",
                    "classification": "applicable_reusable",
                    "blocking": True,
                    "reason": "family/platform were not available this run",
                }
            ],
        },
    )
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is True
    assert not any(reason.startswith("blocking_check_gap") for reason in decision.mismatch_reasons)


def test_non_blocking_check_gap_in_coverage_evidence_does_not_deny_reuse(tmp_path):
    """A skipped/errored check that is NOT classified blocking must not
    affect acceptance -- only blocking-check gaps are gating."""

    state, bundle = _valid_cache(tmp_path)
    write_redacted_json(
        bundle / "candidate" / "check-coverage.json",
        {
            "schema_version": 1,
            "check_count": 1,
            "pass_count": 0,
            "fail_count": 0,
            "skip_count": 0,
            "error_count": 1,
            "not_applicable_count": 0,
            "entries": [
                {
                    "check_name": "check_dependency_snapshot_completeness",
                    "outcome": "error",
                    "severity": "hard_gate",
                    "classification": "applicable_after_adaptation",
                    "blocking": False,
                    "reason": "no committed fixture carries real data for it",
                }
            ],
        },
    )
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is True
    assert not any(reason.startswith("blocking_check_gap") for reason in decision.mismatch_reasons)


def test_approved_current_bundle_is_reusable_only_for_first_no_op_promotion(tmp_path):
    state, bundle = _approved_cache(tmp_path)

    approved = local_poc_cache.evaluate_approved_local_poc_cache(
        state,
        bundle,
        current_source_revision=SOURCE_REVISION,
        current_control_plane_fingerprint=CONTROL_FINGERPRINT,
    )
    completed = _decision(state, bundle)

    assert approved.reusable is True
    assert approved.status == "AGENT_APPROVED"
    assert approved.mismatch_reasons == []
    assert completed.reusable is False
    assert "lifecycle_not_complete" in completed.mismatch_reasons


def test_legacy_template_hash_helper_cannot_override_exact_component_manifest(
    monkeypatch,
    tmp_path,
):
    state, bundle = _approved_cache(tmp_path)
    monkeypatch.setattr(local_poc_cache, "document_template_hash", lambda: "9" * 64)

    decision = local_poc_cache.evaluate_approved_local_poc_cache(
        state,
        bundle,
        current_source_revision=SOURCE_REVISION,
        current_control_plane_fingerprint=CONTROL_FINGERPRINT,
    )

    assert decision.reusable is True
    assert decision.decision_status == "REUSE_CURRENT"


def test_single_verified_template_owner_change_is_noncritical_update(
    monkeypatch,
    tmp_path,
):
    state, bundle = _valid_cache(tmp_path)
    project_root = Path(__file__).resolve().parents[2]
    owner = (
        project_root / "src" / "readme_agent" / "presentation" / "verified_template_sections.py"
    ).resolve()
    assert str(owner.relative_to(project_root)).replace("\\", "/") in (
        document_templates.DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS
    )
    original_read_bytes = Path.read_bytes

    def changed_owner_bytes(path: Path) -> bytes:
        content = original_read_bytes(path)
        return content + b"\ncache-invalidation-control" if path.resolve() == owner else content

    monkeypatch.setattr(Path, "read_bytes", changed_owner_bytes)

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert decision.decision_status == "VALID_UPDATE_AVAILABLE"
    assert decision.mismatch_reasons == []
    assert decision.earliest_affected_stage is None
    assert decision.update_earliest_stage == "PLAN_READY"


def test_acceptance_validator_change_invalidates_completed_bundle(monkeypatch, tmp_path):
    state, bundle = _valid_cache(tmp_path)
    project_root = Path(__file__).resolve().parents[2]
    owner = (
        project_root / "src" / "readme_agent" / "readme" / "claim_accountability_validation.py"
    ).resolve()
    original_read_bytes = Path.read_bytes

    def changed_owner_bytes(path: Path) -> bytes:
        content = original_read_bytes(path)
        return content + b"\ncache-invalidation-control" if path.resolve() == owner else content

    monkeypatch.setattr(Path, "read_bytes", changed_owner_bytes)

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert decision.decision_status == "INVALIDATED"
    assert "presentation_component_severe_acceptance_changed" in decision.mismatch_reasons
    assert decision.earliest_affected_stage == "CANDIDATE_GENERATED"


@pytest.mark.parametrize(
    ("cache_factory", "evaluate"),
    [
        (
            _approved_cache,
            local_poc_cache.evaluate_approved_local_poc_cache,
        ),
        (_valid_cache, local_poc_cache.evaluate_completed_local_poc_cache),
    ],
    ids=("approved", "no-op-proven"),
)
@pytest.mark.parametrize(
    "relative_input",
    (
        "src/readme_agent/links/contextual_selection.py",
        "data/aspose_org_links.json",
    ),
    ids=("link-algorithm-owner", "link-catalog"),
)
def test_link_contract_change_preserves_accepted_candidate_as_available_update(
    monkeypatch,
    tmp_path,
    cache_factory,
    evaluate,
    relative_input,
):
    state, bundle = cache_factory(tmp_path)
    project_root = Path(__file__).resolve().parents[2]
    contract_input = (project_root / relative_input).resolve()
    original_read_bytes = Path.read_bytes

    def changed_contract_bytes(path: Path) -> bytes:
        content = original_read_bytes(path)
        if path.resolve() == contract_input:
            return content + b"\ncache-invalidation-control"
        return content

    monkeypatch.setattr(Path, "read_bytes", changed_contract_bytes)

    decision = evaluate(
        state,
        bundle,
        current_source_revision=SOURCE_REVISION,
        current_control_plane_fingerprint=CONTROL_FINGERPRINT,
    )

    assert decision.reusable is False
    assert decision.decision_status == "VALID_UPDATE_AVAILABLE"
    assert decision.mismatch_reasons == []
    assert decision.update_earliest_stage == "PLAN_READY"


def test_unrelated_registry_change_does_not_invalidate_global_document_contract(
    monkeypatch,
):
    baseline = document_template_hash()
    project_root = Path(__file__).resolve().parents[2]
    registry = (project_root / "data" / "products.json").resolve()
    original_read_bytes = Path.read_bytes

    def changed_registry_bytes(path: Path) -> bytes:
        content = original_read_bytes(path)
        if path.resolve() == registry:
            return content + b"\ncache-scope-negative-control"
        return content

    monkeypatch.setattr(Path, "read_bytes", changed_registry_bytes)

    assert document_template_hash() == baseline


def test_approved_no_op_promotion_records_cache_before_state_and_evidence(
    monkeypatch,
    tmp_path,
):
    state, bundle = _approved_cache(tmp_path)
    decision = local_poc_cache.evaluate_approved_local_poc_cache(
        state,
        bundle,
        current_source_revision=SOURCE_REVISION,
        current_control_plane_fingerprint=CONTROL_FINGERPRINT,
    )
    events: list[str] = []
    monkeypatch.setattr(
        local_poc_noop_reuse,
        "evaluate_approved_local_poc_cache",
        lambda *args, **kwargs: decision,
    )
    monkeypatch.setattr(
        local_poc_noop_reuse,
        "bind_llm_repository_revision",
        lambda *args, **kwargs: events.append("bind"),
    )
    monkeypatch.setattr(
        local_poc_noop_reuse,
        "record_non_provider_call",
        lambda *args, **kwargs: events.append("cache"),
    )
    monkeypatch.setattr(
        local_poc_noop_reuse,
        "transition_readme_poc_status",
        lambda *args, **kwargs: events.append("transition"),
    )
    monkeypatch.setattr(
        local_poc_noop_reuse,
        "write_local_poc_no_op_evidence",
        lambda *args, **kwargs: events.append("evidence"),
    )
    monkeypatch.setattr(
        local_poc_noop_reuse,
        "save_domain",
        lambda *args, **kwargs: events.append("domain"),
    )
    backend = SimpleNamespace(load=lambda org_repo: state)

    result = local_poc_noop_reuse.promote_approved_local_poc_noop(
        backend=backend,
        state=state,
        bundle_dir=bundle,
        current_source_revision=SOURCE_REVISION,
        current_control_plane_fingerprint=CONTROL_FINGERPRINT,
    )

    assert result.promoted is True
    assert events == ["bind", "cache", "transition", "evidence"]


@pytest.mark.parametrize(
    ("affected_stage", "expected_target"),
    [
        ("FACTS_COLLECTING", "FACTS_COLLECTING"),
        ("PLAN_READY", "README_ASSESSED"),
        ("CANDIDATE_GENERATED", "README_ASSESSED"),
        ("AGENT_REVIEWING", "README_ASSESSED"),
    ],
)
def test_denied_completed_cache_reopens_the_durable_execution_boundary(
    affected_stage,
    expected_target,
    monkeypatch,
    tmp_path,
):
    state, bundle = _valid_cache(tmp_path)
    decision = _decision(state, bundle).model_copy(
        update={
            "reusable": False,
            "earliest_affected_stage": affected_stage,
            "mismatch_reasons": ["candidate_stage_dependency_key_changed"],
        }
    )
    calls: list[tuple] = []
    monkeypatch.setattr(
        local_poc_noop_reuse,
        "transition_readme_poc_status",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    reopened = local_poc_noop_reuse.reopen_invalidated_local_poc(
        backend=SimpleNamespace(),
        state=state,
        bundle_dir=bundle,
        decision=decision,
    )

    assert reopened is True
    assert calls[0][0][2] == expected_target
    assert "candidate_stage_dependency_key_changed" in calls[0][1]["reason"]


def test_source_revision_invalidation_is_left_to_snapshot_owner(monkeypatch, tmp_path):
    state, bundle = _valid_cache(tmp_path)
    decision = _decision(state, bundle).model_copy(
        update={
            "reusable": False,
            "earliest_affected_stage": "SNAPSHOTTED",
            "mismatch_reasons": ["source_revision_changed"],
        }
    )
    monkeypatch.setattr(
        local_poc_noop_reuse,
        "transition_readme_poc_status",
        lambda *args, **kwargs: pytest.fail("snapshot invalidation must own this transition"),
    )

    assert not local_poc_noop_reuse.reopen_invalidated_local_poc(
        backend=SimpleNamespace(),
        state=state,
        bundle_dir=bundle,
        decision=decision,
    )


def test_assurance_change_cannot_collide_with_verified_cache(tmp_path):
    state, bundle = _valid_cache(tmp_path)

    verified = _decision(state, bundle)
    trusted = local_poc_cache.evaluate_completed_local_poc_cache(
        state,
        bundle,
        current_source_revision=SOURCE_REVISION,
        current_control_plane_fingerprint=CONTROL_FINGERPRINT,
        content_assurance="trusted_inherited",
    )

    assert verified.reusable is True
    assert trusted.reusable is False
    assert "content_assurance_changed" in trusted.mismatch_reasons
    assert trusted.earliest_affected_stage == "FACTS_COLLECTING"
    assert trusted.cache_key != verified.cache_key


@pytest.mark.parametrize(
    ("change", "expected_reason", "expected_stage"),
    [
        ("source", "source_revision_changed", "SNAPSHOTTED"),
        ("facts", "manifest_facts_hash_mismatch", "FACTS_COLLECTING"),
        ("prompt", "prompt_registry_content_hash_changed", "FACTS_COLLECTING"),
        ("validator", "local_verification_contract_hash_changed", "FACTS_COLLECTING"),
        ("reviewer", "reviewer_standard_hash_changed", "AGENT_REVIEWING"),
        ("control_plane", "control_plane_fingerprint_changed", "FACTS_COLLECTING"),
        ("origin", "manifest_repair_budget_origin_hash_mismatch", "CANDIDATE_GENERATED"),
        ("completed_stages", "manifest_no_op_stage_missing", "CANDIDATE_GENERATED"),
    ],
)
def test_any_dependent_input_change_denies_reuse(
    change,
    expected_reason,
    expected_stage,
    monkeypatch,
    tmp_path,
):
    state, bundle = _valid_cache(tmp_path)
    source_revision = SOURCE_REVISION
    control = CONTROL_FINGERPRINT
    if change == "source":
        source_revision = "9" * 40
    elif change == "facts":
        lifecycle = state.readme_poc_lifecycle.model_copy(update={"facts_hash": "9" * 64})
        state = state.model_copy(update={"readme_poc_lifecycle": lifecycle})
    elif change == "prompt":
        monkeypatch.setattr(prompt_registry, "content_hash", lambda: "9" * 64)
    elif change == "template":
        monkeypatch.setattr(local_poc_cache, "document_template_hash", lambda: "9" * 64)
    elif change == "validator":
        monkeypatch.setattr(
            local_poc_cache,
            "local_verification_contract_hash",
            lambda _ecosystem=None: "9" * 64,
        )
    elif change == "reviewer":
        monkeypatch.setattr(
            local_poc_cache,
            "separated_reviewer_standard_hash",
            lambda: "9" * 64,
        )
    elif change == "control_plane":
        control = "9" * 64
    elif change == "origin":
        lifecycle = state.readme_poc_lifecycle.model_copy(
            update={"repair_budget_origin_hash": "9" * 64}
        )
        state = state.model_copy(update={"readme_poc_lifecycle": lifecycle})
    else:
        manifest_path = bundle / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["completed_stages"] = []
        write_redacted_json(manifest_path, manifest)
        refresh_sha256sums(bundle)

    decision = _decision(
        state,
        bundle,
        source_revision=source_revision,
        control=control,
    )

    assert decision.reusable is False
    assert decision.status is None
    assert expected_reason in decision.mismatch_reasons
    assert decision.earliest_affected_stage == expected_stage


def test_fact_contract_change_and_artifact_corruption_both_deny_reuse(monkeypatch, tmp_path):
    state, bundle = _valid_cache(tmp_path)
    current = current_fact_acceptance_contract()
    changed = current.model_copy(
        update={
            "accepted_verification_states": current.accepted_verification_states + ("test-only",)
        }
    )
    monkeypatch.setattr(
        local_poc_cache,
        "current_fact_acceptance_contract",
        lambda _ecosystem=None, _family=None: changed,
    )

    contract_change = _decision(state, bundle)
    assert contract_change.reusable is False
    assert "fact_acceptance_contract_hash_changed" in contract_change.mismatch_reasons
    assert contract_change.earliest_affected_stage == "FACTS_COLLECTING"

    monkeypatch.setattr(
        local_poc_cache,
        "current_fact_acceptance_contract",
        lambda _ecosystem=None, _family=None: current,
    )
    (bundle / "review" / "final-verdict.json").write_text(
        '{"agent_approved": false}\n',
        encoding="utf-8",
    )
    corruption = _decision(state, bundle)
    assert corruption.reusable is False
    assert "artifact_inventory_invalid" in corruption.mismatch_reasons
    assert corruption.earliest_affected_stage == "CANDIDATE_GENERATED"


def test_stale_drafted_truth_prompt_denies_completed_reuse(tmp_path):
    state, bundle = _valid_cache(tmp_path)
    stale_prompt_hash = "1" * 64
    lifecycle = state.readme_poc_lifecycle.model_copy(update={"prompt_hash": stale_prompt_hash})
    state = state.model_copy(update={"readme_poc_lifecycle": lifecycle})
    write_redacted_json(bundle / "facts" / "proposed-product-truth.json", {})
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["resolution_source"] = "agent_draft"
    manifest["prompt_hash"] = stale_prompt_hash
    write_redacted_json(manifest_path, manifest)
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert decision.status is None
    assert decision.mismatch_reasons == [
        "agent_draft_resolution_not_cacheable",
        "draft_product_truth_prompt_hash_changed",
    ]
    assert decision.earliest_affected_stage == "FACTS_COLLECTING"


def test_deterministic_salvage_proposal_is_not_prompt_bound(tmp_path):
    state, bundle = _valid_cache(tmp_path)
    lifecycle = state.readme_poc_lifecycle.model_copy(update={"prompt_hash": None})
    state = state.model_copy(update={"readme_poc_lifecycle": lifecycle})
    write_redacted_json(bundle / "facts" / "proposed-product-truth.json", {})
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["prompt_hash"] = None
    manifest["resolution_source"] = "deterministic_salvage"
    write_redacted_json(manifest_path, manifest)
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is True
    assert decision.mismatch_reasons == []


def test_unknown_product_truth_resolution_source_denies_reuse(tmp_path):
    state, bundle = _valid_cache(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["resolution_source"] = "unknown"
    write_redacted_json(manifest_path, manifest)
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert "product_truth_provenance_incoherent" in decision.mismatch_reasons
    assert decision.earliest_affected_stage == "FACTS_COLLECTING"


def test_checksum_valid_but_semantically_invalid_acceptance_evidence_denies_reuse(tmp_path):
    state, bundle = _valid_cache(tmp_path)
    no_op_path = bundle / "review" / "no-op-proof.json"
    no_op = json.loads(no_op_path.read_text(encoding="utf-8"))
    no_op["new_provider_call_count"] = 1
    write_redacted_json(no_op_path, no_op)
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert "artifact_inventory_invalid" not in decision.mismatch_reasons
    assert "no_op_proof_invalid" in decision.mismatch_reasons
    assert decision.earliest_affected_stage == "AGENT_REVIEWING"


def test_checksum_valid_but_blocked_product_truth_denies_reuse(tmp_path):
    state, bundle = _valid_cache(tmp_path)
    facts_path = bundle / "facts" / "product-facts.json"
    payload = json.loads(facts_path.read_text(encoding="utf-8"))
    example_id = payload["selected_fact_ids"]["example.minimal"]
    for fact in payload["facts"]:
        if fact["fact_id"] == example_id:
            fact["verification_state"] = "blocked"
            fact["confidence"] = 0.0
    write_redacted_json(facts_path, payload)
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert "product_truth_blocked_missing_evidence" in decision.mismatch_reasons
    assert decision.earliest_affected_stage == "FACTS_COLLECTING"


@pytest.mark.parametrize(
    ("scope", "expected_stage"),
    [
        ("FACTS_COLLECTING", "FACTS_COLLECTING"),
        ("README_ASSESSED", "README_ASSESSED"),
        ("PLAN_READY", "PLAN_READY"),
        ("DETERMINISTIC_VALIDATED", "CANDIDATE_GENERATED"),
        ("AGENT_REVIEWING", "AGENT_REVIEWING"),
    ],
)
def test_prompt_dependency_change_identifies_earliest_affected_stage(
    scope, expected_stage, monkeypatch, tmp_path
):
    state, bundle = _valid_cache(tmp_path)
    dependencies = prompt_registry.dependency_hashes()
    changed = {**dependencies, scope: "9" * 64}
    monkeypatch.setattr(prompt_registry, "dependency_hashes", lambda: changed)
    monkeypatch.setattr(prompt_registry, "content_hash", lambda: "8" * 64)

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert f"prompt_scope_{scope}_changed" in decision.mismatch_reasons
    assert decision.earliest_affected_stage == expected_stage


def _changed_component_manifest(current, component_id: str, digest: str):
    dependencies = []
    for dependency in current.dependencies:
        if dependency.dependency_id != component_id:
            dependencies.append(dependency)
            continue
        files = dict(dependency.files)
        files[next(iter(files))] = digest
        dependencies.append(
            SelectedDependencyV1(
                dependency_id=dependency.dependency_id,
                files=files,
                semantic_scope=dependency.semantic_scope,
                earliest_affected_stage=dependency.earliest_affected_stage,
            )
        )
    return build_stage_dependency_manifest(
        repository=current.repository,
        source_revision=current.source_revision,
        stage=current.stage,
        ecosystem=current.ecosystem,
        dependencies=dependencies,
        upstream_receipt_ids=current.upstream_receipt_ids,
    )


def test_critical_candidate_component_change_reopens_its_earliest_boundary(monkeypatch, tmp_path):
    state, bundle = _valid_cache(tmp_path)
    current = current_candidate_stage_dependency_manifest(
        repository=ORG_REPO,
        source_revision=SOURCE_REVISION,
        ecosystem=None,
    )
    changed = _changed_component_manifest(current, "composition_semantics", "9" * 64)
    monkeypatch.setattr(
        local_poc_cache,
        "current_candidate_stage_dependency_manifest",
        lambda **_kwargs: changed,
    )

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert "presentation_component_severe_acceptance_changed" in decision.mismatch_reasons
    assert decision.earliest_affected_stage == "PLAN_READY"
    assert decision.decision_status == "INVALIDATED"
    assert decision.fact_validity_preserved is True


def test_cosmetic_component_change_returns_valid_update_without_revoking_acceptance(
    monkeypatch, tmp_path
):
    state, bundle = _valid_cache(tmp_path)
    current = current_candidate_stage_dependency_manifest(
        repository=ORG_REPO,
        source_revision=SOURCE_REVISION,
        ecosystem=None,
    )
    changed = _changed_component_manifest(current, "header_visual", "8" * 64)
    monkeypatch.setattr(
        local_poc_cache,
        "current_candidate_stage_dependency_manifest",
        lambda **_kwargs: changed,
    )

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert decision.decision_status == "VALID_UPDATE_AVAILABLE"
    assert decision.mismatch_reasons == []
    assert decision.earliest_affected_stage is None
    assert decision.update_earliest_stage == "PLAN_READY"
    assert decision.fact_validity_preserved is True
    assert decision.presentation_validity_preserved is True
    assert decision.status == "NO_OP_PROVEN"


def test_noncritical_prompt_component_deduplicates_coarse_prompt_and_control_hashes(
    monkeypatch, tmp_path
):
    state, bundle = _valid_cache(tmp_path)
    current = current_candidate_stage_dependency_manifest(
        repository=ORG_REPO,
        source_revision=SOURCE_REVISION,
        ecosystem=None,
    )
    changed = _changed_component_manifest(
        current,
        "prompt:plan_readme_composition",
        "7" * 64,
    )
    monkeypatch.setattr(
        local_poc_cache,
        "current_candidate_stage_dependency_manifest",
        lambda **_kwargs: changed,
    )
    current_prompt_dependencies = prompt_registry.dependency_hashes()
    monkeypatch.setattr(prompt_registry, "content_hash", lambda: "6" * 64)
    monkeypatch.setattr(
        prompt_registry,
        "dependency_hashes",
        lambda: {**current_prompt_dependencies, "PLAN_READY": "5" * 64},
    )

    decision = _decision(state, bundle, control="4" * 64)

    assert decision.decision_status == "VALID_UPDATE_AVAILABLE"
    assert decision.mismatch_reasons == []
    assert decision.update_earliest_stage == "PLAN_READY"
    assert decision.fact_validity_preserved is True
    assert decision.presentation_validity_preserved is True


def test_noncritical_prompt_cannot_hide_a_simultaneous_critical_component_change(
    monkeypatch, tmp_path
):
    state, bundle = _valid_cache(tmp_path)
    current = current_candidate_stage_dependency_manifest(
        repository=ORG_REPO,
        source_revision=SOURCE_REVISION,
        ecosystem=None,
    )
    changed_prompt = _changed_component_manifest(
        current,
        "prompt:plan_readme_composition",
        "7" * 64,
    )
    changed_both = _changed_component_manifest(
        changed_prompt,
        "validation_ruleset",
        "6" * 64,
    )
    monkeypatch.setattr(
        local_poc_cache,
        "current_candidate_stage_dependency_manifest",
        lambda **_kwargs: changed_both,
    )
    monkeypatch.setattr(prompt_registry, "content_hash", lambda: "5" * 64)

    decision = _decision(state, bundle, control="4" * 64)

    assert decision.decision_status == "INVALIDATED"
    assert "presentation_component_severe_acceptance_changed" in decision.mismatch_reasons
    assert decision.presentation_validity_preserved is False


def test_noncritical_prompt_and_cosmetic_change_remain_a_valid_update(monkeypatch, tmp_path):
    state, bundle = _valid_cache(tmp_path)
    current = current_candidate_stage_dependency_manifest(
        repository=ORG_REPO,
        source_revision=SOURCE_REVISION,
        ecosystem=None,
    )
    changed_prompt = _changed_component_manifest(
        current,
        "prompt:plan_readme_composition",
        "7" * 64,
    )
    changed_both = _changed_component_manifest(changed_prompt, "header_visual", "6" * 64)
    monkeypatch.setattr(
        local_poc_cache,
        "current_candidate_stage_dependency_manifest",
        lambda **_kwargs: changed_both,
    )
    current_prompt_dependencies = prompt_registry.dependency_hashes()
    monkeypatch.setattr(prompt_registry, "content_hash", lambda: "5" * 64)
    monkeypatch.setattr(
        prompt_registry,
        "dependency_hashes",
        lambda: {**current_prompt_dependencies, "PLAN_READY": "4" * 64},
    )

    decision = _decision(state, bundle, control="3" * 64)

    assert decision.decision_status == "VALID_UPDATE_AVAILABLE"
    assert decision.mismatch_reasons == []
    assert decision.update_earliest_stage == "PLAN_READY"
    assert decision.fact_validity_preserved is True
    assert decision.presentation_validity_preserved is True


def test_missing_candidate_component_manifest_fails_closed_at_plan_boundary(tmp_path):
    state, bundle = _valid_cache(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("candidate_stage_dependency_manifest")
    write_redacted_json(manifest_path, manifest)
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert "candidate_stage_dependency_manifest_missing_or_invalid" in decision.mismatch_reasons
    assert decision.earliest_affected_stage == "PLAN_READY"


def test_partial_manifest_refresh_cannot_launder_stale_acceptance_proof(tmp_path):
    state, bundle = _valid_cache(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["candidate_stage_dependency_key"] = "1" * 64
    write_redacted_json(manifest_path, manifest)
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert decision.decision_status == "INVALIDATED"
    assert "deterministic_manifest_dependency_key_mismatch" in decision.mismatch_reasons
    assert decision.earliest_affected_stage == "AGENT_REVIEWING"


def test_mermaid_proof_contract_must_match_its_persisted_acceptance_binding(tmp_path):
    state, bundle = _valid_cache(tmp_path)
    validation_path = bundle / "review" / "deterministic-validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    validation["official_mermaid_render"] = {
        "status": "passed",
        "contract_version": "stale",
    }
    write_redacted_json(validation_path, validation)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["deterministic_validation_hash"] = canonical_sha256(validation)
    write_redacted_json(manifest_path, manifest)
    refresh_sha256sums(bundle)

    decision = _decision(state, bundle)

    assert decision.reusable is False
    assert "mermaid_render_binding_mismatch" in decision.mismatch_reasons
