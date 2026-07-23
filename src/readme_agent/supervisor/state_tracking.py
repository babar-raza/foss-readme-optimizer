"""Load and persist durable repository-supervision state."""

import sys

from readme_agent.errors import StateBackendError
from readme_agent.specialists import registry as specialists_registry
from readme_agent.state.backend import StateBackend
from readme_agent.state.domain_state import (
    compute_domain_coverage_complete,
    merge_unrecorded_failures,
)
from readme_agent.state.schema import DomainStateV1, RunStateV1, RunStateV2, SupervisorStateV1


def load_prior_run_state(
    backend: StateBackend | None,
    org_repo: str,
    *,
    strict: bool = False,
) -> RunStateV2 | None:
    """Return prior durable state; local profiles degrade visibly when unavailable."""

    if backend is None:
        return None
    try:
        return backend.load(org_repo)
    except StateBackendError as exc:
        if strict:
            raise
        print(f"warning: durable state read failed, continuing without it: {exc}", file=sys.stderr)
        return None


def load_supervisor_state(
    backend: StateBackend | None,
    org_repo: str,
    *,
    strict: bool = False,
) -> SupervisorStateV1 | None:
    state = load_prior_run_state(backend, org_repo, strict=strict)
    return state.supervisor_state if state else None


def record_supervisor_state(
    backend: StateBackend,
    org_repo: str,
    supervisor_state: SupervisorStateV1,
    *,
    failures: dict[str, DomainStateV1] | None = None,
    strict: bool = False,
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
                if strict:
                    raise StateBackendError(
                        f"strict supervisor state write for {org_repo!r} lost a CAS race"
                    )
                return
    except StateBackendError as exc:
        if strict:
            raise
        print(
            f"warning: durable state write-back failed, continuing without it: {exc}",
            file=sys.stderr,
        )
