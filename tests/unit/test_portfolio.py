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
    assert summary.system_failure_count == 1
    assert summary.execution_slice_complete is True
    assert '"registry_count": 2' in path.read_text(encoding="utf-8")
    assert (
        path.with_suffix(".sha256")
        .read_text(encoding="utf-8")
        .endswith("  portfolio-summary.json\n")
    )


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


def test_completed_local_poc_status_advances_later_portfolio_slices():
    from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
    from readme_agent.state.schema import RunStateV2

    state = RunStateV2(
        org_repo="org/repo",
        readme_poc_lifecycle=ReadmePocLifecycleStateV2(
            org_repo="org/repo",
            source_revision="abc123",
            status="NO_OP_PROVEN",
        ),
    )

    assert completed_local_poc_status(state) == "NO_OP_PROVEN"
    assert (
        completed_local_poc_status(
            state.model_copy(
                update={
                    "readme_poc_lifecycle": state.readme_poc_lifecycle.model_copy(
                        update={"status": "AGENT_APPROVED"}
                    )
                }
            )
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
