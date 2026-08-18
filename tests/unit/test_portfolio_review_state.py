"""TW-03 -- portfolio-wide review readiness never opens on less than the complete portfolio."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from readme_agent.supervisor.portfolio_review_state import (
    PortfolioAccountabilityMatrixV1,
    PortfolioProductRowV1,
)


def _row(org_repo: str, status: str, *, active: bool = True, exclusion_reason=None):
    return PortfolioProductRowV1(
        org_repo=org_repo,
        family="pdf",
        platform="python",
        active=active,
        exclusion_reason=exclusion_reason,
        review_status=status,
    )


def test_one_approved_product_cannot_open_the_global_gate():
    """The amendment's own required regression test, by name."""

    matrix = PortfolioAccountabilityMatrixV1(
        rows=(
            _row("org/approved", "HUMAN_APPROVED"),
            _row("org/still-generating", "GENERATED"),
        )
    )

    assert matrix.portfolio_status() == "BLOCKED_PORTFOLIO"


def test_an_unreviewed_product_blocks_all_remote_writes():
    matrix = PortfolioAccountabilityMatrixV1(
        rows=(
            _row("org/a", "HUMAN_APPROVED"),
            _row("org/b", "HUMAN_APPROVED"),
            _row("org/c", "READY_FOR_PORTFOLIO_REVIEW"),
        )
    )

    assert matrix.portfolio_status() == "BLOCKED_PORTFOLIO"


def test_a_quarantined_product_blocks_the_whole_portfolio():
    matrix = PortfolioAccountabilityMatrixV1(
        rows=(
            _row("org/a", "HUMAN_APPROVED"),
            _row("org/b", "QUARANTINED"),
        )
    )

    assert matrix.portfolio_status() == "BLOCKED_PORTFOLIO"


def test_a_stale_or_failed_product_blocks_review_readiness():
    matrix = PortfolioAccountabilityMatrixV1(
        rows=(
            _row("org/a", "HUMAN_APPROVED"),
            _row("org/b", "LOCALLY_VALIDATED"),  # stalled before E2E verification
        )
    )

    assert matrix.portfolio_status() == "BLOCKED_PORTFOLIO"


def test_fully_approved_unchanged_portfolio_reaches_awaiting_review():
    matrix = PortfolioAccountabilityMatrixV1(
        rows=(
            _row("org/a", "HUMAN_APPROVED"),
            _row("org/b", "HUMAN_APPROVED"),
        )
    )

    assert matrix.portfolio_status() == "AWAITING_GLOBAL_HUMAN_REVIEW"


def test_all_remote_eligible_reaches_remote_writes_enabled():
    matrix = PortfolioAccountabilityMatrixV1(
        rows=(
            _row("org/a", "REMOTE_ELIGIBLE"),
            _row("org/b", "REMOTE_ELIGIBLE"),
        )
    )

    assert matrix.portfolio_status() == "REMOTE_WRITES_ENABLED"


def test_authoritative_exclusion_is_not_counted_against_approval():
    matrix = PortfolioAccountabilityMatrixV1(
        rows=(
            _row("org/a", "HUMAN_APPROVED"),
            _row(
                "org/legacy-unsupported",
                "EXCLUDED",
                exclusion_reason="registry marks this platform end-of-life as of 2026-06-01",
            ),
        )
    )

    assert matrix.portfolio_status() == "AWAITING_GLOBAL_HUMAN_REVIEW"


def test_exclusion_without_a_reason_is_treated_as_blocking_not_a_silent_pass():
    matrix = PortfolioAccountabilityMatrixV1(
        rows=(
            _row("org/a", "HUMAN_APPROVED"),
            _row("org/undocumented-skip", "EXCLUDED", exclusion_reason=None),
        )
    )

    assert matrix.portfolio_status() == "BLOCKED_PORTFOLIO"


def test_inactive_registry_entries_are_not_counted_at_all():
    matrix = PortfolioAccountabilityMatrixV1(
        rows=(
            _row("org/a", "HUMAN_APPROVED"),
            _row("org/deregistered", "DISCOVERED", active=False),
        )
    )

    assert matrix.portfolio_status() == "AWAITING_GLOBAL_HUMAN_REVIEW"


def test_row_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        PortfolioProductRowV1.model_validate(
            {
                "org_repo": "org/a",
                "family": "pdf",
                "platform": "python",
                "active": True,
                "review_status": "HUMAN_APPROVED",
                "unexpected_field": "not allowed",
            }
        )


def test_row_rejects_an_invalid_review_status():
    with pytest.raises(ValidationError):
        PortfolioProductRowV1.model_validate(
            {
                "org_repo": "org/a",
                "family": "pdf",
                "platform": "python",
                "active": True,
                "review_status": "NOT_A_REAL_STATUS",
            }
        )


def test_all_active_rows_excluded_is_not_a_false_ready_signal():
    matrix = PortfolioAccountabilityMatrixV1(
        rows=(
            _row("org/a", "EXCLUDED", exclusion_reason="end-of-life"),
            _row("org/b", "EXCLUDED", exclusion_reason="end-of-life"),
        )
    )

    assert matrix.portfolio_status() == "PORTFOLIO_DISCOVERED"
