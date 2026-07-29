"""Tests for the derived full-registry local-POC portfolio summary."""

from readme_agent.supervisor.portfolio import (
    PortfolioPocSummaryV1,
    PortfolioRepositoryResultV1,
    completed_local_poc_status,
    mark_failed_member_retryable,
    select_portfolio_trigger,
    write_portfolio_summary,
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
    assert summary.target_complete_count == 1
    assert summary.system_failure_count == 1
    assert summary.execution_slice_complete is True
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


def test_completed_local_poc_status_advances_only_with_valid_bundle(tmp_path):
    from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
    from readme_agent.facts.acceptance_contract import current_fact_acceptance_contract
    from readme_agent.facts.local_verification import local_verification_contract_hash
    from readme_agent.llm import prompt_registry
    from readme_agent.llm.verification_prompts import separated_reviewer_standard_hash
    from readme_agent.readme.document_templates import document_template_hash
    from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
    from readme_agent.state.schema import RunStateV2, SupervisorStateV1
    from readme_agent.supervisor.convergence import compute_control_plane_fingerprint

    source_revision = "a" * 40
    facts_hash = "b" * 64
    assessment_hash = "c" * 64
    presentation_plan_hash = "d" * 64
    candidate_hash = "e" * 64
    prompt_hash = "f" * 64
    fact_contract = current_fact_acceptance_contract()
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
            "local_verification_contract_hash": local_verification_contract_hash(),
            "prompt_registry_content_hash": prompt_registry.content_hash(),
            "prompt_dependency_hashes": prompt_registry.dependency_hashes(),
            "reviewer_standard_hash": reviewer_standard,
        },
    )
    write_redacted_json(
        bundle_dir / "planning" / "readme-document-plan.json",
        {"template_sha256": document_template_hash()},
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
