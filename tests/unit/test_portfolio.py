"""Tests for the derived full-registry local-POC portfolio summary."""

from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.supervisor.portfolio import (
    PortfolioPocSummaryV1,
    PortfolioRepositoryResultV1,
    completed_local_poc_status,
    mark_failed_member_retryable,
    select_portfolio_trigger,
    write_portfolio_summary,
)


def _ready_product_facts(source_revision: str) -> ProductFactsV2:
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://org/repo",
        source_revision=source_revision,
    )
    renderable_values = {
        "product.audience": ["Developers using Python"],
        "product.problems_solved": ["Process widget files"],
        "product.capabilities": ["Create and inspect widgets"],
        "product.formats": ["WGT"],
    }
    records = [
        FactRecordV2(
            fact_id=descriptive_fact_id(field, "portfolio-fixture"),
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
        org_repo="org/repo",
        facts=records,
        selected_fact_ids={fact.field: fact.fact_id for fact in records},
    )


def test_summary_derives_counts_and_writes_a_checksum(tmp_path):
    summary = PortfolioPocSummaryV1(
        registry_path="data/products.json",
        registry_count=2,
        results=[
            PortfolioRepositoryResultV1(org_repo="org/one", status="NO_OP_PROVEN", exit_code=0),
            PortfolioRepositoryResultV1(
                org_repo="org/two",
                status="SYSTEM_FAILURE",
                exit_code=1,
                blocked_category="agent_fixable",
            ),
        ],
    )

    path = tmp_path / "portfolio-summary.json"
    write_portfolio_summary(path, summary)

    assert summary.complete_agent_approved_count == 1
    assert summary.raw_agent_approved_count == 1
    assert summary.target_complete_count == 1
    assert summary.system_failure_count == 1
    assert summary.execution_slice_complete is True
    assert "agent_approved=1/2 complete_bundles=1/2" in summary.summary_line()
    assert '"registry_count": 2' in path.read_text(encoding="utf-8")
    assert (
        path.with_suffix(".sha256")
        .read_text(encoding="utf-8")
        .endswith("  portfolio-summary.json\n")
    )


def test_facts_target_summary_counts_only_fact_ready_or_later_lifecycle_states():
    summary = PortfolioPocSummaryV1(
        registry_path="data/products.json",
        target_lifecycle_stage="FACTS_READY",
        registry_count=5,
        results=[
            PortfolioRepositoryResultV1(org_repo="org/ready", status="FACTS_READY", exit_code=0),
            PortfolioRepositoryResultV1(org_repo="org/later", status="NO_OP_PROVEN", exit_code=0),
            PortfolioRepositoryResultV1(
                org_repo="org/missing",
                status="BLOCKED_MISSING_EVIDENCE",
                exit_code=1,
            ),
            PortfolioRepositoryResultV1(
                org_repo="org/active", status="ACTIVE_TRIGGER", exit_code=1
            ),
            PortfolioRepositoryResultV1(
                org_repo="org/stale-later", status="NO_OP_PROVEN", exit_code=1
            ),
        ],
    )

    assert summary.target_complete_count == 2
    assert "target=FACTS_READY complete=2/5" in summary.summary_line()


def test_summary_distinguishes_reviewed_approval_from_complete_bundle():
    summary = PortfolioPocSummaryV1(
        registry_path="data/products.json",
        registry_count=2,
        results=[
            PortfolioRepositoryResultV1(
                org_repo="org/reviewed", status="AGENT_APPROVED", exit_code=0
            ),
            PortfolioRepositoryResultV1(
                org_repo="org/complete", status="NO_OP_PROVEN", exit_code=0
            ),
        ],
    )

    assert summary.raw_agent_approved_count == 2
    assert summary.complete_agent_approved_count == 1
    assert "agent_approved=2/2 complete_bundles=1/2" in summary.summary_line()


def test_intake_target_counts_ready_and_later_but_not_prefighting_or_blocked():
    summary = PortfolioPocSummaryV1(
        registry_path="data/products.json",
        target_lifecycle_stage="INTAKE_READY",
        registry_count=4,
        results=[
            PortfolioRepositoryResultV1(org_repo="org/intake", status="INTAKE_READY", exit_code=0),
            PortfolioRepositoryResultV1(org_repo="org/later", status="FACTS_READY", exit_code=0),
            PortfolioRepositoryResultV1(
                org_repo="org/pending", status="INTAKE_PREFLIGHTING", exit_code=1
            ),
            PortfolioRepositoryResultV1(
                org_repo="org/blocked", status="SYSTEM_FAILURE", exit_code=1
            ),
        ],
    )

    assert summary.target_complete_count == 2
    assert "target=INTAKE_READY complete=2/4" in summary.summary_line()


def test_trigger_selection_resumes_retryable_but_never_steals_active_work():
    from readme_agent.state.lifecycle_schema import TriggerEnvelopeV2, TriggerLifecycleV2
    from readme_agent.state.schema import RunStateV2

    retryable = TriggerLifecycleV2(
        envelope=TriggerEnvelopeV2(
            provider_event_id="retry",
            event_type="cli_manual",
            repository_scope="org/repo",
            dedup_key="retry",
        ),
        status="retryable",
    )
    active = TriggerLifecycleV2(
        envelope=TriggerEnvelopeV2(
            provider_event_id="active",
            event_type="cli_manual",
            repository_scope="org/repo",
            dedup_key="active",
        ),
        status="processing",
    )

    selected = select_portfolio_trigger(
        RunStateV2(
            org_repo="org/repo",
            trigger_lifecycles={"retry": retryable, "active": active},
        )
    )
    assert selected.resume_trigger_key == "retry"
    assert selected.active_trigger_key is None

    selected = select_portfolio_trigger(
        RunStateV2(org_repo="org/repo", trigger_lifecycles={"active": active})
    )
    assert selected.resume_trigger_key is None
    assert selected.active_trigger_key == "active"


def test_completed_local_poc_status_advances_only_with_valid_bundle(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import readme_agent.supervisor.local_poc_cache as cache_module
    from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
    from readme_agent.facts.acceptance_contract import current_fact_acceptance_contract
    from readme_agent.facts.local_verification import local_verification_contract_hash
    from readme_agent.llm import prompt_registry
    from readme_agent.llm.verification_prompts import separated_reviewer_standard_hash
    from readme_agent.readme.document_templates import document_template_hash
    from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
    from readme_agent.state.schema import RunStateV2, SupervisorStateV1
    from readme_agent.supervisor.convergence import compute_control_plane_fingerprint
    from readme_agent.supervisor.stage_dependencies import (
        current_candidate_stage_dependency_manifest,
    )

    source_revision = "a" * 40
    ecosystem = "python"
    family = "note"
    facts_hash = "b" * 64
    assessment_hash = "c" * 64
    presentation_plan_hash = "d" * 64
    candidate_hash = "e" * 64
    prompt_hash = "f" * 64
    monkeypatch.setattr(
        cache_module,
        "require_listed",
        lambda org_repo: SimpleNamespace(family=family),
    )
    fact_contract = current_fact_acceptance_contract(ecosystem, family)
    candidate_dependency_key = current_candidate_stage_dependency_manifest(
        repository="org/repo",
        source_revision=source_revision,
        ecosystem=ecosystem,
    ).stage_key
    reviewer_standard = separated_reviewer_standard_hash()
    control_plane = compute_control_plane_fingerprint(None)
    state = RunStateV2(
        org_repo="org/repo",
        readme_poc_lifecycle=ReadmePocLifecycleStateV2(
            org_repo="org/repo",
            source_revision=source_revision,
            status="NO_OP_PROVEN",
            facts_hash=facts_hash,
            assessment_hash=assessment_hash,
            presentation_plan_hash=presentation_plan_hash,
            candidate_hash=candidate_hash,
            prompt_hash=prompt_hash,
            fact_acceptance_contract_hash=fact_contract.canonical_hash(),
            fact_acceptance_component_hashes=fact_contract.component_hashes,
            reviewer_standard_hash=reviewer_standard,
        ),
        supervisor_state=SupervisorStateV1(control_plane_fingerprint=control_plane),
    )
    bundle_dir = tmp_path / source_revision
    write_redacted_json(
        bundle_dir / "manifest.json",
        {
            "org_repo": "org/repo",
            "source_revision": source_revision,
            "lifecycle_status": "NO_OP_PROVEN",
            "complete": True,
            "completed_stages": ["NO_OP_PROVEN"],
            "facts_hash": facts_hash,
            "assessment_hash": assessment_hash,
            "presentation_plan_hash": presentation_plan_hash,
            "candidate_hash": candidate_hash,
            "prompt_hash": prompt_hash,
            "fact_acceptance_contract_hash": fact_contract.canonical_hash(),
            "fact_acceptance_component_hashes": fact_contract.component_hashes,
            "local_verification_contract_hash": local_verification_contract_hash(ecosystem),
            "prompt_registry_content_hash": prompt_registry.content_hash(),
            "prompt_dependency_hashes": prompt_registry.dependency_hashes(),
            "candidate_stage_dependency_key": candidate_dependency_key,
            "reviewer_standard_hash": reviewer_standard,
        },
    )
    write_redacted_json(
        bundle_dir / "planning" / "readme-document-plan.json",
        {"template_sha256": document_template_hash()},
    )
    write_redacted_json(
        bundle_dir / "facts" / "product-facts.json",
        _ready_product_facts(source_revision).model_dump(mode="json"),
    )
    write_redacted_json(
        bundle_dir / "planning" / "agentic-composition-plan.json",
        {"prompt_sha256": prompt_registry.prompt_hash("plan_readme_composition")},
    )
    write_redacted_json(
        bundle_dir / "review" / "final-verdict.json",
        {
            "verdict": "AGENT_APPROVED",
            "agent_approved": True,
            "deterministic_validation_passed": True,
        },
    )
    write_redacted_json(
        bundle_dir / "review" / "no-op-proof.json",
        {
            "verdict": "NO_OP_PROVEN",
            "candidate_hash": candidate_hash,
            "patch_created": False,
            "duplicate_bundle_created": False,
            "agentic_review_reused": True,
            "llm_accounting_status": "EXACT",
            "new_provider_call_count": 0,
        },
    )
    refresh_sha256sums(bundle_dir)

    assert (
        completed_local_poc_status(
            state,
            bundle_dir,
            current_source_revision=source_revision,
            current_control_plane_fingerprint=control_plane,
            ecosystem=ecosystem,
        )
        == "NO_OP_PROVEN"
    )
    assert (
        completed_local_poc_status(
            state.model_copy(
                update={
                    "readme_poc_lifecycle": state.readme_poc_lifecycle.model_copy(
                        update={"status": "AGENT_APPROVED"}
                    )
                }
            ),
            bundle_dir,
            current_source_revision=source_revision,
            current_control_plane_fingerprint=control_plane,
            ecosystem=ecosystem,
        )
        is None
    )
    assert (
        completed_local_poc_status(
            state,
            bundle_dir,
            current_source_revision="9" * 40,
            current_control_plane_fingerprint=control_plane,
            ecosystem=ecosystem,
        )
        is None
    )

    write_redacted_json(bundle_dir / "review" / "final-verdict.json", {"agent_approved": False})
    assert (
        completed_local_poc_status(
            state,
            bundle_dir,
            current_source_revision=source_revision,
            current_control_plane_fingerprint=control_plane,
            ecosystem=ecosystem,
        )
        is None
    )


def test_failed_member_returns_its_processing_trigger_to_retryable():
    from readme_agent.state.lifecycle import accept_trigger, transition_trigger
    from readme_agent.state.trigger_v2 import normalize_trigger_envelope
    from tests.unit.test_state_backend import FakeStateBackend

    backend = FakeStateBackend()
    envelope = normalize_trigger_envelope(
        "org/repo",
        event_type="cli_manual",
        provider_event_id="failed-member",
    )
    accept_trigger(backend, envelope)
    transition_trigger(backend, "org/repo", envelope.dedup_key, "processing")

    changed = mark_failed_member_retryable(
        backend,
        "org/repo",
        envelope.dedup_key,
        failure_detail="portfolio_member_failure:RuntimeError",
    )

    assert changed is True
    state = backend.load("org/repo")
    assert state is not None
    lifecycle = state.trigger_lifecycles[envelope.dedup_key]
    assert lifecycle.status == "retryable"
    assert lifecycle.failure_detail == "portfolio_member_failure:RuntimeError"
