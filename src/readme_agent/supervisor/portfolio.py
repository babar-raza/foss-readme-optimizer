"""Aggregate fail-closed local-POC results from the canonical supervisor."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator

from readme_agent.state.assurance import ContentAssuranceV1
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle import transition_trigger
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2
from readme_agent.supervisor.stage_limit import lifecycle_stage_reaches_limit

_COMPLETE_LOCAL_POC_STATUSES = {
    "NO_OP_PROVEN",
    "HUMAN_REVIEW_READY",
    "HUMAN_ACCEPTED",
    "PR_ELIGIBLE",
    "PR_PROOF_COMPLETE",
}
PortfolioTargetStageV1 = Literal[
    "INTAKE_READY",
    "FACTS_READY",
    "CANDIDATE_GENERATED",
    "DETERMINISTIC_VALIDATED",
    "TRUSTED_TRANSFORM_APPROVED",
    "TRUSTED_NO_OP_PROVEN",
    "NO_OP_PROVEN",
]


class PortfolioRepositoryResultV1(BaseModel):
    """Terminal result for one registry entry within a local POC pass."""

    org_repo: str
    content_assurance: ContentAssuranceV1 = "repository_verified"
    status: str
    exit_code: int
    blocked_reason: str | None = None
    blocked_category: str | None = None
    llm_accounting_status: Literal["EXACT", "UNKNOWN_LEGACY"] = "UNKNOWN_LEGACY"
    llm_call_count: int | None = Field(default=None, ge=0)
    llm_call_ids: list[str] = Field(default_factory=list)
    llm_calls_by_job: dict[str, int] = Field(default_factory=dict)
    llm_fixture_call_count: int | None = Field(default=None, ge=0)
    llm_cache_reuse_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _reconcile_llm_calls(self) -> PortfolioRepositoryResultV1:
        if self.llm_accounting_status == "UNKNOWN_LEGACY":
            if self.llm_call_count is not None or self.llm_call_ids:
                raise ValueError("UNKNOWN_LEGACY portfolio member cannot claim exact calls")
            return self
        if self.llm_call_count != len(self.llm_call_ids):
            raise ValueError("portfolio member call count does not match unique call IDs")
        if len(set(self.llm_call_ids)) != len(self.llm_call_ids):
            raise ValueError("portfolio member contains duplicate LLM call IDs")
        if self.llm_call_count != sum(self.llm_calls_by_job.values()):
            raise ValueError("portfolio member per-job LLM totals do not reconcile")
        return self


class PortfolioPocSummaryV1(BaseModel):
    """Derived portfolio state; never a hand-maintained progress ledger."""

    schema_version: int = 3
    registry_path: str
    target_lifecycle_stage: PortfolioTargetStageV1 = "NO_OP_PROVEN"
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    registry_count: int = Field(ge=0)
    execution_slice_complete: bool = True
    results: list[PortfolioRepositoryResultV1]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def llm_accounting_status(self) -> Literal["EXACT", "UNKNOWN_LEGACY"]:
        return (
            "EXACT"
            if len(self.results) == self.registry_count
            and all(result.llm_accounting_status == "EXACT" for result in self.results)
            else "UNKNOWN_LEGACY"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def llm_provider_call_count(self) -> int | None:
        if self.llm_accounting_status != "EXACT":
            return None
        return sum(result.llm_call_count or 0 for result in self.results)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def llm_calls_by_job(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for result in self.results:
            for job, count in result.llm_calls_by_job.items():
                totals[job] = totals.get(job, 0) + count
        return dict(sorted(totals.items()))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def llm_cache_reuse_count(self) -> int | None:
        if self.llm_accounting_status != "EXACT":
            return None
        return sum(result.llm_cache_reuse_count or 0 for result in self.results)

    @property
    def complete_agent_approved_count(self) -> int:
        # `AGENT_APPROVED` alone is not a complete local bundle: the
        # unchanged rerun is a mandatory proof boundary.  Every later state
        # retains that approval, so this derives the headline denominator
        # without a separate mutable counter.
        return sum(
            result.exit_code == 0 and result.status in _COMPLETE_LOCAL_POC_STATUSES
            for result in self.results
        )

    @property
    def trusted_facts_extracted_count(self) -> int:
        return sum(
            result.content_assurance == "trusted_inherited"
            and result.status
            in {
                "TRUSTED_FACTS_EXTRACTED",
                "TRUSTED_PLAN_READY",
                "TRUSTED_CANDIDATE_GENERATED",
                "TRUSTED_DETERMINISTIC_VALIDATED",
                "TRUSTED_REVIEWING",
                "TRUSTED_REVIEW_REJECTED",
                "TRUSTED_REPAIRING",
                "TRUSTED_TRANSFORM_APPROVED",
                "TRUSTED_NO_OP_PROVEN",
                "TRUSTED_PR_ELIGIBLE",
                "TRUSTED_PR_OPEN",
            }
            for result in self.results
        )

    @property
    def trusted_candidate_generated_count(self) -> int:
        return sum(
            result.content_assurance == "trusted_inherited"
            and result.status
            in {
                "TRUSTED_CANDIDATE_GENERATED",
                "TRUSTED_DETERMINISTIC_VALIDATED",
                "TRUSTED_REVIEWING",
                "TRUSTED_REVIEW_REJECTED",
                "TRUSTED_REPAIRING",
                "TRUSTED_TRANSFORM_APPROVED",
                "TRUSTED_NO_OP_PROVEN",
                "TRUSTED_PR_ELIGIBLE",
                "TRUSTED_PR_OPEN",
            }
            for result in self.results
        )

    @property
    def trusted_transform_approved_count(self) -> int:
        return sum(
            result.content_assurance == "trusted_inherited"
            and result.status
            in {
                "TRUSTED_TRANSFORM_APPROVED",
                "TRUSTED_NO_OP_PROVEN",
                "TRUSTED_PR_ELIGIBLE",
                "TRUSTED_PR_OPEN",
            }
            for result in self.results
        )

    @property
    def trusted_no_op_proven_count(self) -> int:
        return sum(
            result.content_assurance == "trusted_inherited"
            and result.status in {"TRUSTED_NO_OP_PROVEN", "TRUSTED_PR_ELIGIBLE", "TRUSTED_PR_OPEN"}
            for result in self.results
        )

    @property
    def trusted_pr_open_count(self) -> int:
        return sum(
            result.content_assurance == "trusted_inherited" and result.status == "TRUSTED_PR_OPEN"
            for result in self.results
        )

    @property
    def system_failure_count(self) -> int:
        return sum(
            result.status == "SYSTEM_FAILURE" or result.blocked_category == "agent_fixable"
            for result in self.results
        )

    @property
    def target_complete_count(self) -> int:
        """Count repositories that honestly reached this bounded campaign target."""

        if self.target_lifecycle_stage in {
            "INTAKE_READY",
            "FACTS_READY",
            "CANDIDATE_GENERATED",
            "DETERMINISTIC_VALIDATED",
            "TRUSTED_TRANSFORM_APPROVED",
            "TRUSTED_NO_OP_PROVEN",
        }:
            return sum(
                result.exit_code == 0
                and lifecycle_stage_reaches_limit(self.target_lifecycle_stage, result.status)
                for result in self.results
            )
        return self.complete_agent_approved_count

    def summary_line(self) -> str:
        return (
            "local_poc portfolio: "
            f"target={self.target_lifecycle_stage} "
            f"complete={self.target_complete_count}/{self.registry_count} "
            f"agent_approved={self.complete_agent_approved_count}/{self.registry_count} "
            f"trusted_approved={self.trusted_transform_approved_count}/{self.registry_count} "
            f"trusted_no_op={self.trusted_no_op_proven_count}/{self.registry_count} "
            f"trusted_pr_open={self.trusted_pr_open_count}/{self.registry_count} "
            f"system_failed={self.system_failure_count} processed={len(self.results)} "
            f"slice_complete={self.execution_slice_complete} "
            f"llm_accounting={self.llm_accounting_status} "
            f"provider_calls={self.llm_provider_call_count}"
        )


class PortfolioTriggerSelectionV1(BaseModel):
    """Restart decision derived from one repository's durable trigger state."""

    resume_trigger_key: str | None = None
    active_trigger_key: str | None = None


def completed_local_poc_status(
    state: RunStateV2 | None,
    bundle_dir: Path,
    *,
    current_source_revision: str | None,
    current_control_plane_fingerprint: str,
) -> str | None:
    """Return a completed status only under the complete current cache contract."""

    from readme_agent.supervisor.local_poc_cache import evaluate_completed_local_poc_cache

    decision = evaluate_completed_local_poc_cache(
        state,
        bundle_dir,
        current_source_revision=current_source_revision,
        current_control_plane_fingerprint=current_control_plane_fingerprint,
    )
    return decision.status if decision.reusable else None


def recover_completed_local_poc_status(
    backend: StateBackend,
    org_repo: str,
) -> str | None:
    """Recover a member that completed before portfolio aggregation failed."""

    state = backend.load(org_repo)
    if (
        state is None
        or not isinstance(state.readme_poc_lifecycle, ReadmePocLifecycleStateV2)
        or not state.readme_poc_lifecycle.source_revision
    ):
        return None
    from readme_agent import paths

    org, repo = org_repo.split("/", maxsplit=1)
    bundle_dir = paths.readme_poc_repository_dir(
        org,
        repo,
        state.readme_poc_lifecycle.source_revision,
    )
    from readme_agent.gitsafety.clone import remote_head_sha
    from readme_agent.registry.loader import find_entry
    from readme_agent.supervisor.convergence import compute_control_plane_fingerprint

    entry = find_entry(org_repo)
    if entry is None:
        return None
    current_source_revision = remote_head_sha(entry.clone_url)
    if current_source_revision is None:
        return None
    return completed_local_poc_status(
        state,
        bundle_dir,
        current_source_revision=current_source_revision,
        current_control_plane_fingerprint=compute_control_plane_fingerprint(entry.policy_profile),
    )


def select_portfolio_trigger(state: RunStateV2 | None) -> PortfolioTriggerSelectionV1:
    """Resume retryable work, but never steal accepted/processing work.

    The recovery sweep owns expiry classification.  By the time this helper
    runs, an expired active trigger has become ``retryable``; anything still
    ``accepted`` or ``processing`` therefore retains its live lease and must
    be left to its current worker.
    """
    if state is None:
        return PortfolioTriggerSelectionV1()
    retryable = sorted(
        (
            (lifecycle.accepted_at, key)
            for key, lifecycle in state.trigger_lifecycles.items()
            if lifecycle.status == "retryable"
        )
    )
    if retryable:
        return PortfolioTriggerSelectionV1(resume_trigger_key=retryable[0][1])
    active = sorted(
        (
            (lifecycle.accepted_at, key)
            for key, lifecycle in state.trigger_lifecycles.items()
            if lifecycle.status in {"accepted", "processing"}
        )
    )
    return PortfolioTriggerSelectionV1(active_trigger_key=active[0][1] if active else None)


def mark_failed_member_retryable(
    backend: StateBackend,
    org_repo: str,
    trigger_key: str | None,
    *,
    failure_detail: str,
) -> bool:
    """Keep an isolated member exception resumable instead of orphaning its lease.

    The member command normally owns this transition. This portfolio-level
    fallback covers failures in command setup or terminal evidence handling
    that occur outside the member command's guarded runtime section.
    """

    if trigger_key is None:
        return False
    state = backend.load(org_repo)
    if state is None:
        return False
    lifecycle = state.trigger_lifecycles.get(trigger_key)
    if lifecycle is None or lifecycle.status not in {"accepted", "processing"}:
        return False
    transition_trigger(
        backend,
        org_repo,
        trigger_key,
        "retryable",
        failure_classification="transient",
        failure_detail=failure_detail,
    )
    return True


def write_portfolio_summary(path: Path, summary: PortfolioPocSummaryV1) -> None:
    """Write the one current, redacted summary for an idempotent portfolio pass."""
    from readme_agent.evidence.writer import sha256_file, write_redacted_json

    write_redacted_json(path, summary)
    digest, _size = sha256_file(path)
    path.with_suffix(".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8", newline="\n"
    )
