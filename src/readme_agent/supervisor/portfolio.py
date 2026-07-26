"""Aggregate fail-closed local-POC results from the canonical supervisor."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle import transition_trigger
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2

_COMPLETE_LOCAL_POC_STATUSES = {
    "NO_OP_PROVEN",
    "HUMAN_REVIEW_READY",
    "HUMAN_ACCEPTED",
    "PR_ELIGIBLE",
    "PR_PROOF_COMPLETE",
}


class PortfolioRepositoryResultV1(BaseModel):
    """Terminal result for one registry entry within a local POC pass."""

    org_repo: str
    status: str
    exit_code: int
    blocked_reason: str | None = None
    blocked_category: str | None = None


class PortfolioPocSummaryV1(BaseModel):
    """Derived portfolio state; never a hand-maintained progress ledger."""

    schema_version: int = 2
    registry_path: str
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    registry_count: int = Field(ge=0)
    execution_slice_complete: bool = True
    results: list[PortfolioRepositoryResultV1]

    @property
    def complete_agent_approved_count(self) -> int:
        # `AGENT_APPROVED` alone is not a complete local bundle: the
        # unchanged rerun is a mandatory proof boundary.  Every later state
        # retains that approval, so this derives the headline denominator
        # without a separate mutable counter.
        return sum(result.status in _COMPLETE_LOCAL_POC_STATUSES for result in self.results)

    @property
    def system_failure_count(self) -> int:
        return sum(
            result.status == "SYSTEM_FAILURE" or result.blocked_category == "agent_fixable"
            for result in self.results
        )

    def summary_line(self) -> str:
        return (
            "local_poc portfolio: "
            f"agent_approved={self.complete_agent_approved_count}/{self.registry_count} "
            f"system_failed={self.system_failure_count} processed={len(self.results)} "
            f"slice_complete={self.execution_slice_complete}"
        )


class PortfolioTriggerSelectionV1(BaseModel):
    """Restart decision derived from one repository's durable trigger state."""

    resume_trigger_key: str | None = None
    active_trigger_key: str | None = None


def completed_local_poc_status(
    state: RunStateV2 | None,
    bundle_dir: Path,
) -> str | None:
    """Return a complete status only when its revision bundle is checksum-valid."""

    if state is None or not isinstance(
        state.readme_poc_lifecycle,
        ReadmePocLifecycleStateV2,
    ):
        return None
    lifecycle = state.readme_poc_lifecycle
    if lifecycle.status not in _COMPLETE_LOCAL_POC_STATUSES:
        return None

    manifest_path = bundle_dir / "manifest.json"
    inventory_path = bundle_dir / "sha256sums.txt"
    document_plan_path = bundle_dir / "planning" / "readme-document-plan.json"
    agentic_plan_path = bundle_dir / "planning" / "agentic-composition-plan.json"
    if (
        not manifest_path.is_file()
        or not inventory_path.is_file()
        or not document_plan_path.is_file()
        or not agentic_plan_path.is_file()
    ):
        return None

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        document_plan = json.loads(document_plan_path.read_text(encoding="utf-8"))
        agentic_plan = json.loads(agentic_plan_path.read_text(encoding="utf-8"))
        inventory_lines = inventory_path.read_text(encoding="utf-8").splitlines()
        expected: dict[str, str] = {}
        for line in inventory_lines:
            digest, relative = line.split("  ", maxsplit=1)
            if (
                len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)
                or not relative
                or relative in expected
            ):
                return None
            expected[relative] = digest
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return None

    if (
        manifest.get("complete") is not True
        or manifest.get("org_repo") != state.org_repo
        or manifest.get("source_revision") != lifecycle.source_revision
        or manifest.get("lifecycle_status") != lifecycle.status
    ):
        return None

    from readme_agent.llm import prompt_registry
    from readme_agent.readme.document_templates import document_template_hash

    if document_plan.get("template_sha256") != document_template_hash():
        return None
    if agentic_plan and agentic_plan.get("prompt_sha256") != prompt_registry.prompt_hash(
        "plan_readme_composition"
    ):
        return None
    if manifest.get("reviewer_standard_hash") != prompt_registry.prompt_hash(
        "independent_readme_review"
    ):
        return None

    actual = {
        path.relative_to(bundle_dir).as_posix(): path
        for path in bundle_dir.rglob("*")
        if path.is_file() and path.name != "sha256sums.txt"
    }
    if set(expected) != set(actual):
        return None

    from readme_agent.evidence.writer import sha256_file

    if any(sha256_file(actual[relative])[0] != digest for relative, digest in expected.items()):
        return None
    return lifecycle.status


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
    return completed_local_poc_status(state, bundle_dir)


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
