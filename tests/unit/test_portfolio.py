"""Tests for the derived full-registry local-POC portfolio summary."""

from readme_agent.supervisor.portfolio import (
    PortfolioPocSummaryV1,
    PortfolioRepositoryResultV1,
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
