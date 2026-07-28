"""Run, isolate, retry, and summarize the registered specialist tier."""

import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION, README_PRESENTATION
from readme_agent.errors import StateBackendError
from readme_agent.evidence.redaction import redact
from readme_agent.evidence.writer import generate_run_id
from readme_agent.llm.planner_client import PlannerClient
from readme_agent.specialists import registry as specialists_registry
from readme_agent.state.backend import StateBackend
from readme_agent.state.domain_state import (
    mark_domain_skipped,
    mark_specialist_tier_started,
    save_domain_with_failure_tracking,
)
from readme_agent.state.schema import DomainStateV1
from readme_agent.supervisor import specialist_selection
from readme_agent.supervisor.models import DecisionSummary
from readme_agent.supervisor.stage_limit import ReadmePocStageLimitV1


@dataclass
class SpecialistTierResult:
    domains: list[str]
    results: dict[str, DomainStateV1]
    unrecorded_failures: dict[str, DomainStateV1]
    escalation_alerts: list[DecisionSummary]
    retry_alerts: list[DecisionSummary]


def _is_retryable_execution_failure(result: DomainStateV1) -> bool:
    """Retry an invocation failure, never a deterministic or agentic verdict."""

    return (result.accepted_status or "").startswith("ERROR:execution_error:")


def run_specialist_tier(
    *,
    org_repo: str,
    baseline_path: Path,
    state_backend: StateBackend | None,
    current_revision: str | None,
    enable_specialist_skip: bool,
    specialist_selection_client: PlannerClient | None,
    escalation_alert_threshold: int,
    fail_closed_on_state_failure: bool = False,
    readme_poc_stage_limit: ReadmePocStageLimitV1 | None = None,
) -> SpecialistTierResult:
    """Run every registered domain while one domain's failure remains isolated."""

    skip_plan = specialist_selection.SkipPlan()
    if enable_specialist_skip and state_backend is not None and current_revision is not None:
        try:
            prior_full_state = state_backend.load(org_repo)
        except StateBackendError:
            if fail_closed_on_state_failure:
                raise
            prior_full_state = None
        skip_plan = specialist_selection.decide_skips(
            org_repo=org_repo,
            baseline_path=baseline_path,
            prior_domain_states=(
                prior_full_state.domain_states if prior_full_state is not None else {}
            ),
            current_revision=current_revision,
            specialist_selection_client=specialist_selection_client,
        )

    domains = (
        [README_PRESENTATION]
        if readme_poc_stage_limit in {"CANDIDATE_GENERATED", "DETERMINISTIC_VALIDATED"}
        else specialists_registry.all_domains()
    )
    results: dict[str, DomainStateV1] = {}
    if state_backend is not None:
        mark_specialist_tier_started(
            state_backend,
            org_repo,
            generate_run_id(),
            domains,
            strict=fail_closed_on_state_failure,
        )

    for domain in domains:
        if domain in skip_plan.skip_domains:
            assert state_backend is not None
            assert current_revision is not None
            results[domain] = mark_domain_skipped(
                state_backend,
                org_repo,
                domain,
                current_revision,
                skip_reason=skip_plan.reasons[domain],
                max_consecutive_skips=specialist_selection.MAX_CONSECUTIVE_SKIPS,
            )
            continue
        try:
            result = specialists_registry.run_domain(
                domain, org_repo, state_backend, current_revision=current_revision
            )
        except Exception as exc:  # noqa: BLE001 -- one domain cannot abort its siblings
            if fail_closed_on_state_failure and isinstance(exc, StateBackendError):
                raise
            print(
                f"warning: specialist domain {domain!r} raised, continuing with the others: {exc}",
                file=sys.stderr,
            )
            result = DomainStateV1(
                domain=domain,
                accepted_status=f"ERROR:execution_error:{exc}",
                details={
                    "error": redact(str(exc)),
                    "failure_envelope": {
                        "schema_version": 1,
                        "domain": domain,
                        "failure_reason": "execution_error",
                        "error_type": type(exc).__name__,
                        "message": redact(str(exc)),
                        "stage": readme_poc_stage_limit,
                        "attempt": 1,
                        "source_revision": current_revision,
                        "occurred_at": datetime.now(UTC).isoformat(),
                    },
                },
            )
            if state_backend is not None and domain == README_PRESENTATION:
                save_domain_with_failure_tracking(
                    state_backend,
                    org_repo,
                    domain,
                    result,
                    current_revision=current_revision,
                )
        if result is not None:
            results[domain] = result

    retry_alerts: list[DecisionSummary] = []
    for domain in [
        key for key, result in results.items() if _is_retryable_execution_failure(result)
    ]:
        try:
            retry_result = specialists_registry.run_domain(
                domain, org_repo, state_backend, current_revision=current_revision
            )
        except Exception as exc:  # noqa: BLE001 -- retain the original visible error
            if fail_closed_on_state_failure and isinstance(exc, StateBackendError):
                raise
            print(
                f"warning: specialist domain {domain!r} retry raised, "
                f"keeping the original error: {exc}",
                file=sys.stderr,
            )
            if state_backend is not None and domain == README_PRESENTATION:
                retry_failure = DomainStateV1(
                    domain=domain,
                    accepted_status=f"ERROR:execution_error:{exc}",
                    details={
                        "error": redact(str(exc)),
                        "failure_envelope": {
                            "schema_version": 1,
                            "domain": domain,
                            "failure_reason": "execution_error",
                            "error_type": type(exc).__name__,
                            "message": redact(str(exc)),
                            "stage": readme_poc_stage_limit,
                            "attempt": 2,
                            "source_revision": current_revision,
                            "occurred_at": datetime.now(UTC).isoformat(),
                        },
                    },
                )
                save_domain_with_failure_tracking(
                    state_backend,
                    org_repo,
                    domain,
                    retry_failure,
                    current_revision=current_revision,
                )
            continue
        if retry_result is None:
            continue
        recovered = not (retry_result.accepted_status or "").startswith("ERROR:")
        retry_alerts.append(
            DecisionSummary(
                turn=0,
                kind="specialist_retry",
                detail=(
                    f"{domain!r} reported an error on its first classify attempt this run; "
                    f"retried once, {'recovered' if recovered else 'still failing'} "
                    f"({retry_result.accepted_status!r})"
                ),
            )
        )
        results[domain] = retry_result

    unrecorded_failures = {
        domain: result
        for domain, result in results.items()
        if domain != README_PRESENTATION and (result.accepted_status or "").startswith("ERROR:")
    }
    independent = results.get(INDEPENDENT_VERIFICATION)
    failure_escalations = (
        independent.details.get("failure_escalations", {}) if independent is not None else {}
    )
    escalation_alerts = [
        DecisionSummary(
            turn=0,
            kind="escalation_alert",
            detail=(
                f"{domain!r} has failed {info['consecutive_failure_count']} consecutive runs "
                f"for the same reason ({info['last_failure_reason']!r}) -- human attention needed"
            ),
        )
        for domain, info in failure_escalations.items()
        if info["consecutive_failure_count"] >= escalation_alert_threshold
    ]
    return SpecialistTierResult(
        domains=domains,
        results=results,
        unrecorded_failures=unrecorded_failures,
        escalation_alerts=escalation_alerts,
        retry_alerts=retry_alerts,
    )
