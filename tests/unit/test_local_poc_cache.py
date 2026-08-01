"""Complete-input cache decisions for accepted local README bundles."""

import json
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
from readme_agent.readme.document_templates import document_template_hash
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2, SupervisorStateV1
from readme_agent.supervisor import local_poc_cache, local_poc_noop_reuse

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
    state = RunStateV2(
        org_repo=ORG_REPO,
        readme_poc_lifecycle=ReadmePocLifecycleStateV2(
            status="NO_OP_PROVEN",
            source_revision=SOURCE_REVISION,
            facts_hash="c" * 64,
            assessment_hash="d" * 64,
            presentation_plan_hash="e" * 64,
            candidate_hash="f" * 64,
            prompt_hash="1" * 64,
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
    write_redacted_json(
        bundle / "manifest.json",
        {
            "org_repo": ORG_REPO,
            "source_revision": SOURCE_REVISION,
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
            "reviewer_standard_hash": reviewer_standard,
            "repair_budget_origin_hash": lifecycle.repair_budget_origin_hash,
        },
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
        },
    )
    write_redacted_json(
        bundle / "facts" / "product-facts.json",
        _ready_product_facts().model_dump(mode="json"),
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


def test_approved_bundle_dependency_change_denies_first_no_op_promotion(
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

    assert decision.reusable is False
    assert "template_hash_changed" in decision.mismatch_reasons
    assert decision.earliest_affected_stage == "PLAN_READY"


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
        ("template", "template_hash_changed", "PLAN_READY"),
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
            lambda: "9" * 64,
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
    monkeypatch.setattr(
        local_poc_cache,
        "current_fact_acceptance_contract",
        lambda: SimpleNamespace(
            canonical_hash=lambda: "9" * 64,
            component_hashes=current.component_hashes,
        ),
    )

    contract_change = _decision(state, bundle)
    assert contract_change.reusable is False
    assert "fact_acceptance_contract_hash_changed" in contract_change.mismatch_reasons
    assert contract_change.earliest_affected_stage == "FACTS_COLLECTING"

    monkeypatch.setattr(
        local_poc_cache,
        "current_fact_acceptance_contract",
        lambda: current,
    )
    (bundle / "review" / "final-verdict.json").write_text(
        '{"agent_approved": false}\n',
        encoding="utf-8",
    )
    corruption = _decision(state, bundle)
    assert corruption.reusable is False
    assert "artifact_inventory_invalid" in corruption.mismatch_reasons
    assert corruption.earliest_affected_stage == "CANDIDATE_GENERATED"


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
