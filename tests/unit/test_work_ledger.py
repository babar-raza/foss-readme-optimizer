"""Deterministic supervisor work-ledger contracts."""

from readme_agent.state.schema import DomainStateV1
from readme_agent.supervisor.work_ledger import build_work_ledger


def test_stale_readme_exposes_untried_deterministic_actions():
    ledger = build_work_ledger(
        {
            "readme_presentation": DomainStateV1(
                domain="readme_presentation",
                accepted_status="FIRST_OBSERVATION",
                details={"render_status": "STALE_NONCOMPLIANT"},
            )
        },
        attempted_capability_ids=["detect_readme_gaps"],
    )

    assert ledger.stop_allowed is False
    assert ledger.unresolved_findings == ("readme_presentation:STALE_NONCOMPLIANT",)
    assert ledger.eligible_capability_ids == (
        "get_product_facts",
        "verify_package_acquisition",
        "render_readme_candidate",
    )


def test_stop_is_allowed_after_every_mapped_action_was_attempted():
    ledger = build_work_ledger(
        {
            "metadata_presentation": DomainStateV1(
                domain="metadata_presentation",
                accepted_status="FIRST_OBSERVATION",
                details={
                    "blocked_findings": [
                        {"surface_id": "metadata.description", "reason": "missing facts"}
                    ]
                },
            )
        },
        attempted_capability_ids=["get_product_facts", "verify_package_acquisition"],
    )

    assert ledger.unresolved_findings == ("metadata_presentation:1_blocked",)
    assert ledger.eligible_capability_ids == ()
    assert ledger.stop_allowed is True


def test_verified_proposal_is_terminal_without_being_mislabeled_no_change():
    ledger = build_work_ledger(
        {
            "metadata_presentation": DomainStateV1(
                domain="metadata_presentation",
                accepted_status="FIRST_OBSERVATION",
                details={"has_proposal": True, "blocked_findings": []},
            )
        }
    )

    assert ledger.unresolved_findings == ()
    assert ledger.ready_proposals == ("metadata_presentation:proposal_ready",)
    assert ledger.stop_allowed is True
