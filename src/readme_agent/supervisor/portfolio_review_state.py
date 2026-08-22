"""TW-03 (freshness-service plan): portfolio-wide review/approval readiness.

This is a distinct layer from `portfolio.py`'s `PortfolioPocSummaryV1` (which
tracks per-repo LLM-call accounting and local no-op-proof lifecycle status --
"has this repo's candidate reached NO_OP_PROVEN"). TW-03 answers a different,
later question this plan's binding amendment introduces: "has the complete
reviewed portfolio been human-approved for remote eligibility." A product can
be `NO_OP_PROVEN` in `portfolio.py`'s sense and still be `PLANNED` here --
generation completing locally is a prerequisite for review, not the same as
being reviewed.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProductReviewStatus = Literal[
    "DISCOVERED",
    "INPUTS_PINNED",
    "GENERATED",
    "LOCALLY_VALIDATED",
    "LOCALLY_E2E_VERIFIED",
    "READY_FOR_PORTFOLIO_REVIEW",
    "HUMAN_APPROVED",
    "REMOTE_ELIGIBLE",
    "QUARANTINED",
    "EXCLUDED",
]

PortfolioReviewStatus = Literal[
    "PORTFOLIO_DISCOVERED",
    "PORTFOLIO_GENERATING",
    "PORTFOLIO_LOCALLY_VALIDATED",
    "PORTFOLIO_E2E_VERIFIED",
    "PORTFOLIO_AGENT_ACCEPTED",
    "PORTFOLIO_PUBLICATION_READY_AWAITING_EFFECT_AUTHORIZATION",
    "BLOCKED_PORTFOLIO",
]

# A product state's position in this order must be >= HUMAN_APPROVED's for the
# portfolio to be reviewable/approvable. QUARANTINED/EXCLUDED never satisfy
# that comparison -- they are handled as their own explicit branch below.
_PRODUCT_ORDER: tuple[ProductReviewStatus, ...] = (
    "DISCOVERED",
    "INPUTS_PINNED",
    "GENERATED",
    "LOCALLY_VALIDATED",
    "LOCALLY_E2E_VERIFIED",
    "READY_FOR_PORTFOLIO_REVIEW",
    "HUMAN_APPROVED",
    "REMOTE_ELIGIBLE",
)


class PortfolioProductRowV1(BaseModel):
    """One accountability-matrix row. Every in-scope registry entry gets
    exactly one row -- silent omission is a validation failure at the
    matrix-builder level, not something this model can detect on its own
    (a missing row IS the omission)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    org_repo: str = Field(min_length=1)
    family: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    active: bool
    exclusion_reason: str | None = None
    candidate_path: str | None = None
    source_revision: str | None = None
    existing_readme_hash: str | None = None
    candidate_hash: str | None = None
    validation_result: str | None = None
    e2e_result: str | None = None
    review_status: ProductReviewStatus

    def is_approvable(self) -> bool:
        if self.review_status in ("QUARANTINED",):
            return False
        if self.review_status == "EXCLUDED":
            return self.exclusion_reason is not None
        return _PRODUCT_ORDER.index(self.review_status) >= _PRODUCT_ORDER.index("HUMAN_APPROVED")


class PortfolioAccountabilityMatrixV1(BaseModel):
    """The complete-portfolio ledger this plan's amendment requires: every
    active in-scope product accounted for, with no silent omission."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rows: tuple[PortfolioProductRowV1, ...]

    def portfolio_status(self) -> PortfolioReviewStatus:
        """Derive review and publication readiness without granting effect authority.

        Agent acceptance, publication readiness, and an authorized remote effect
        are separate boundaries. This reducer stops at publication readiness; no
        returned status enables a product write or requires a human content-review
        step.
        """

        active_rows = [row for row in self.rows if row.active]
        if not active_rows:
            return "PORTFOLIO_DISCOVERED"

        invalid_exclusions = [
            row
            for row in active_rows
            if row.review_status == "EXCLUDED" and row.exclusion_reason is None
        ]
        quarantined = [row for row in active_rows if row.review_status == "QUARANTINED"]
        if invalid_exclusions or quarantined:
            return "BLOCKED_PORTFOLIO"

        # A valid EXCLUDED row already passed `is_approvable()` above (it has an
        # authoritative reason); it is neither for nor against these "every row
        # reached X" checks -- it is simply outside the review-status ladder.
        reviewable_rows = [row for row in active_rows if row.review_status != "EXCLUDED"]
        if not reviewable_rows:
            # Every active product is an authoritative exclusion -- there is
            # nothing left to review or approve, so this is not a false
            # "portfolio ready" signal; treat it the same as no active rows.
            return "PORTFOLIO_DISCOVERED"

        all_remote_eligible = all(row.review_status == "REMOTE_ELIGIBLE" for row in reviewable_rows)
        if all_remote_eligible:
            return "PORTFOLIO_PUBLICATION_READY_AWAITING_EFFECT_AUTHORIZATION"

        all_ready_for_review = all(
            _PRODUCT_ORDER.index(row.review_status)
            >= _PRODUCT_ORDER.index("READY_FOR_PORTFOLIO_REVIEW")
            for row in reviewable_rows
        )
        if all_ready_for_review:
            return "PORTFOLIO_AGENT_ACCEPTED"

        all_e2e_verified = all(
            _PRODUCT_ORDER.index(row.review_status) >= _PRODUCT_ORDER.index("LOCALLY_E2E_VERIFIED")
            for row in active_rows
            if row.review_status != "EXCLUDED"
        )
        if all_e2e_verified:
            return "PORTFOLIO_E2E_VERIFIED"

        return "PORTFOLIO_GENERATING"


__all__ = [
    "PortfolioAccountabilityMatrixV1",
    "PortfolioProductRowV1",
    "PortfolioReviewStatus",
    "ProductReviewStatus",
]
