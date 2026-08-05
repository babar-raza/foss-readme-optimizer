"""Derive portfolio progress and enforce mission-task contribution evidence."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from readme_agent import paths
from readme_agent.errors import ConfigError
from readme_agent.facts.acceptance_contract import current_fact_acceptance_contract
from readme_agent.facts.local_verification import local_verification_contract_hash
from readme_agent.registry.loader import PRODUCTS_PATH, load_products
from readme_agent.state.agile_execution_schema import TaskCloseoutControlEvidenceV1
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import (
    ReadmePocLifecycleStateV1,
    ReadmePocLifecycleStateV2,
)
from readme_agent.state.mission_goal_schema import (
    MissionContributionEvidenceV1,
    MissionLifecycleBoundary,
    MissionLifecycleScoreboardV1,
)
from readme_agent.supervisor.mission_lifecycle_freshness import (
    ACCEPTANCE_BOUNDARIES,
    ORDERED_BOUNDARIES,
    REACHED_STATUSES,
    TRUSTED_REACHED_STATUSES,
    evaluate_lifecycle_fact_freshness,
)
from readme_agent.supervisor.mission_schema import TaskCardV1
from readme_agent.supervisor.verification_policy import validate_closeout_control_evidence


def _canonical_text_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    canonical_text = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()


def derive_lifecycle_scoreboard(
    backend: StateBackend,
    *,
    products_path: Path = PRODUCTS_PATH,
    verify_acceptance_freshness: bool = True,
) -> MissionLifecycleScoreboardV1:
    """Read dynamic lifecycle progress and fail closed on stale dependent proof."""

    entries = load_products(products_path)
    registry_sha256 = _canonical_text_sha256(products_path)
    counts = {boundary: 0 for boundary in ORDERED_BOUNDARIES}
    raw_counts = {boundary: 0 for boundary in ORDERED_BOUNDARIES}
    trusted_counts = {boundary: 0 for boundary in TRUSTED_REACHED_STATUSES}
    status_counts: dict[str, int] = {}
    missing: list[str] = []
    stale_facts: dict[str, list[str]] = {}
    stale_acceptance: dict[str, list[str]] = {}
    watermarks: list[str] = []
    org_repos = [entry.org_repo for entry in entries]
    bulk_loader = getattr(backend, "load_many", None)
    states = (
        bulk_loader(org_repos)
        if callable(bulk_loader)
        else {org_repo: backend.load(org_repo) for org_repo in org_repos}
    )
    fact_contracts = (
        {
            entry.org_repo: current_fact_acceptance_contract(entry.ecosystem, entry.family)
            for entry in entries
        }
        if verify_acceptance_freshness
        else {}
    )

    for entry in entries:
        state = states[entry.org_repo]
        lifecycle = state.readme_poc_lifecycle if state is not None else None
        if not isinstance(lifecycle, (ReadmePocLifecycleStateV1, ReadmePocLifecycleStateV2)):
            missing.append(entry.org_repo)
            status = "DISCOVERED"
        else:
            status = lifecycle.status
            watermarks.append(lifecycle.updated_at)
        status_counts[status] = status_counts.get(status, 0) + 1
        if (
            isinstance(lifecycle, ReadmePocLifecycleStateV2)
            and lifecycle.content_assurance == "trusted_inherited"
        ):
            for boundary, reached_statuses in TRUSTED_REACHED_STATUSES.items():
                if status in reached_statuses:
                    trusted_counts[boundary] += 1
        for boundary in ORDERED_BOUNDARIES:
            if status in REACHED_STATUSES[boundary]:
                raw_counts[boundary] += 1
                counts[boundary] += 1

        facts_are_current = True
        if verify_acceptance_freshness and status in REACHED_STATUSES["FACTS_READY"]:
            source_revision = getattr(lifecycle, "source_revision", None)
            org, repo = entry.org_repo.split("/", maxsplit=1)
            bundle_dir = paths.readme_poc_repository_dir(
                org,
                repo,
                source_revision or "0" * 40,
            )
            fact_decision = evaluate_lifecycle_fact_freshness(
                state,
                bundle_dir,
                current_contract=fact_contracts.get(entry.org_repo),
                current_local_verification_hash=local_verification_contract_hash(entry.ecosystem),
                ecosystem=entry.ecosystem,
                family=entry.family,
            )
            facts_are_current = fact_decision.reusable
            if not facts_are_current:
                stale_facts[entry.org_repo] = fact_decision.mismatch_reasons
                for boundary in ORDERED_BOUNDARIES:
                    if status in REACHED_STATUSES[boundary]:
                        counts[boundary] -= 1

        if (
            facts_are_current
            and verify_acceptance_freshness
            and isinstance(lifecycle, ReadmePocLifecycleStateV2)
            and lifecycle.content_assurance == "repository_verified"
            and status in REACHED_STATUSES["AGENT_APPROVED"]
        ):
            from readme_agent.supervisor.convergence import compute_control_plane_fingerprint
            from readme_agent.supervisor.local_poc_cache import (
                evaluate_approved_local_poc_cache,
                evaluate_completed_local_poc_cache,
            )

            org, repo = entry.org_repo.split("/", maxsplit=1)
            bundle_dir = paths.readme_poc_repository_dir(
                org,
                repo,
                lifecycle.source_revision or "0" * 40,
            )
            evaluator = (
                evaluate_approved_local_poc_cache
                if status == "AGENT_APPROVED"
                else evaluate_completed_local_poc_cache
            )
            decision = evaluator(
                state,
                bundle_dir,
                current_source_revision=lifecycle.source_revision,
                current_control_plane_fingerprint=compute_control_plane_fingerprint(
                    entry.policy_profile
                ),
                ecosystem=entry.ecosystem,
                family=entry.family,
            )
            if not decision.reusable:
                stale_acceptance[entry.org_repo] = decision.mismatch_reasons
                for boundary in ACCEPTANCE_BOUNDARIES:
                    if status in REACHED_STATUSES[boundary]:
                        counts[boundary] -= 1

    denominator = len(entries)
    first_failing: MissionLifecycleBoundary = "MISSION_CLOSED"
    for boundary in ORDERED_BOUNDARIES:
        if counts[boundary] < denominator:
            first_failing = boundary
            break
    return MissionLifecycleScoreboardV1(
        registry_path=products_path.as_posix(),
        registry_sha256=registry_sha256,
        denominator=denominator,
        trusted_facts_extracted=trusted_counts["trusted_facts_extracted"],
        trusted_candidate_generated=trusted_counts["trusted_candidate_generated"],
        trusted_transform_approved=trusted_counts["trusted_transform_approved"],
        trusted_no_op_proven=trusted_counts["trusted_no_op_proven"],
        trusted_pr_open=trusted_counts["trusted_pr_open"],
        facts_ready=counts["FACTS_READY"],
        candidate_generated=counts["CANDIDATE_GENERATED"],
        deterministic_validated=counts["DETERMINISTIC_VALIDATED"],
        agent_approved=counts["AGENT_APPROVED"],
        no_op_proven=counts["NO_OP_PROVEN"],
        human_accepted=counts["HUMAN_ACCEPTED"],
        raw_facts_ready=raw_counts["FACTS_READY"],
        raw_candidate_generated=raw_counts["CANDIDATE_GENERATED"],
        raw_deterministic_validated=raw_counts["DETERMINISTIC_VALIDATED"],
        raw_agent_approved=raw_counts["AGENT_APPROVED"],
        raw_no_op_proven=raw_counts["NO_OP_PROVEN"],
        raw_human_accepted=raw_counts["HUMAN_ACCEPTED"],
        stale_fact_contract_repositories=dict(sorted(stale_facts.items())),
        stale_acceptance_repositories=dict(sorted(stale_acceptance.items())),
        missing_lifecycle_repositories=sorted(missing),
        lifecycle_status_counts=dict(sorted(status_counts.items())),
        first_failing_boundary=first_failing,
        derived_at=max(watermarks, default=f"registry:{registry_sha256}"),
    )


def lifecycle_scoreboard_sha256(scoreboard: MissionLifecycleScoreboardV1) -> str:
    """Stable hash for contribution before/after evidence."""

    payload = scoreboard.model_dump_json(exclude={"derived_at"})
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_task_contribution_evidence(
    task: TaskCardV1,
    evidence_refs: list[str],
    scoreboard: MissionLifecycleScoreboardV1,
) -> tuple[MissionContributionEvidenceV1, TaskCloseoutControlEvidenceV1]:
    """Require one structured, matching, independently verified closeout record."""

    parsed: list[MissionContributionEvidenceV1] = []
    control_receipts: list[TaskCloseoutControlEvidenceV1] = []
    for reference in evidence_refs:
        path = Path(reference)
        if not path.is_file() or path.suffix.lower() != ".json":
            continue
        try:
            parsed.append(
                MissionContributionEvidenceV1.model_validate_json(path.read_text(encoding="utf-8"))
            )
        except (OSError, UnicodeError, ValidationError):
            pass
        try:
            control_receipts.append(
                TaskCloseoutControlEvidenceV1.model_validate_json(path.read_text(encoding="utf-8"))
            )
        except (OSError, UnicodeError, ValidationError):
            pass
    matching = [item for item in parsed if item.task_id == task.task_id]
    if len(matching) != 1:
        raise ConfigError(
            f"closing task {task.task_id!r} requires exactly one valid contribution evidence JSON"
        )
    evidence = matching[0]
    if (
        evidence.stage_goal_id != task.stage_goal_id
        or evidence.campaign_id != task.campaign_id
        or evidence.goal_ids != task.goal_ids
        or evidence.core_contribution != task.core_contribution
    ):
        raise ConfigError(f"task {task.task_id!r} contribution evidence disagrees with the graph")
    if set(evidence.acceptance_checks_passed) != set(task.acceptance_checks):
        raise ConfigError(
            f"task {task.task_id!r} contribution evidence does not cover every acceptance check"
        )
    if not evidence.independently_verified:
        raise ConfigError(f"task {task.task_id!r} contribution was not independently verified")
    current_hash = lifecycle_scoreboard_sha256(scoreboard)
    if evidence.scoreboard_after_sha256 != current_hash:
        raise ConfigError(f"task {task.task_id!r} contribution evidence uses a stale scoreboard")
    portfolio_boundary_changed = (
        evidence.scoreboard_before_sha256 != evidence.scoreboard_after_sha256
        or evidence.first_failing_boundary_before != evidence.first_failing_boundary_after
    )
    task_boundary_changed = (
        evidence.contribution_boundary_before is not None
        and evidence.contribution_boundary_after is not None
        and evidence.contribution_boundary_before != evidence.contribution_boundary_after
    )
    if task.core_contribution.kind == "first_boundary_removal" and not (
        portfolio_boundary_changed or task_boundary_changed
    ):
        raise ConfigError(
            f"task {task.task_id!r} claims boundary removal without a verified boundary delta"
        )
    if not any(Path(reference).exists() for reference in evidence.proof_refs):
        raise ConfigError(f"task {task.task_id!r} contribution proof refs do not exist")
    matching_controls = [item for item in control_receipts if item.task_id == task.task_id]
    if len(matching_controls) != 1:
        raise ConfigError(
            f"closing task {task.task_id!r} requires exactly one closeout control evidence JSON"
        )
    control = matching_controls[0]
    try:
        validate_closeout_control_evidence(task, control)
    except ValueError as exc:
        raise ConfigError(f"task {task.task_id!r} closeout controls failed: {exc}") from exc
    if not all(Path(reference).exists() for reference in control.proof_refs):
        raise ConfigError(f"task {task.task_id!r} closeout control proof refs do not exist")
    return evidence, control


def utc_now_iso() -> str:
    """Clock seam retained for deterministic test patching."""

    return datetime.now(UTC).isoformat()
