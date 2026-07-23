"""Load and persist durable repository-supervision state."""

import sys

from readme_agent.errors import StateBackendError
from readme_agent.specialists import registry as specialists_registry
from readme_agent.state.backend import StateBackend
from readme_agent.state.domain_state import (
    compute_domain_coverage_complete,
    merge_unrecorded_failures,
)
from readme_agent.state.schema import DomainStateV1, RunStateV1, SupervisorStateV1


def load_prior_run_state(backend: StateBackend | None, org_repo: str) -> RunStateV1 | None:
    """Return prior durable state; local profiles degrade visibly when unavailable."""

    if backend is None:
        return None
    try:
        return backend.load(org_repo)
    except StateBackendError as exc:
        print(f"warning: durable state read failed, continuing without it: {exc}", file=sys.stderr)
        return None


def load_supervisor_state(backend: StateBackend | None, org_repo: str) -> SupervisorStateV1 | None:
    state = load_prior_run_state(backend, org_repo)
    return state.supervisor_state if state else None


def record_supervisor_state(
    backend: StateBackend,
    org_repo: str,
    supervisor_state: SupervisorStateV1,
    *,
    failures: dict[str, DomainStateV1] | None = None,
) -> None:
    """Best-effort CAS write-back for local profiles and terminal evidence."""

    try:
        current = backend.load(org_repo)
        expected_version = current.state_version if current else None
        base = current or RunStateV1(org_repo=org_repo)
        if failures:
            base = merge_unrecorded_failures(
                base,
                failures,
                current_revision=supervisor_state.last_observed_upstream_revision,
            )
        domain_coverage_complete = compute_domain_coverage_complete(
            base,
            specialists_registry.all_domains(),
            supervisor_state.last_observed_upstream_revision,
        )
        new_state = base.model_copy(
            update={
                "supervisor_state": supervisor_state.model_copy(
                    update={"domain_coverage_complete": domain_coverage_complete}
                )
            }
        )
        result = backend.save(org_repo, new_state, expected_version)
        if result.outcome == "stale":
            reloaded = backend.load(org_repo)
            if reloaded is None or (
                reloaded.supervisor_state
                and reloaded.supervisor_state.last_run_id != supervisor_state.last_run_id
            ):
                return
    except StateBackendError as exc:
        print(
            f"warning: durable state write-back failed, continuing without it: {exc}",
            file=sys.stderr,
        )
