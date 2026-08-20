"""FAILED-ONLY retry policy: require an explicit causal fingerprint change before retry, and
classify REASSESS_REQUIRED after two consecutive same-fingerprint failures.

Reuses the existing `blocked_decision_cache.py` record (org_repo, blocked_reason, dependencies,
`consecutive_count`) and `local_poc_cache.py::current_blocked_decision_dependencies()` fingerprint
-- never a new counter or a second failure-tracking store.
"""

from __future__ import annotations

from dataclasses import dataclass

from readme_agent import paths
from readme_agent.registry.models import ProductEntry
from readme_agent.supervisor.blocked_decision_cache import (
    BlockedDecisionRecordV1,
    load_blocked_decision,
)
from readme_agent.supervisor.convergence import compute_control_plane_fingerprint
from readme_agent.supervisor.local_poc_cache import current_blocked_decision_dependencies

REASSESS_THRESHOLD = 2


@dataclass(frozen=True)
class RetryDecisionV1:
    eligible: bool
    reason: str
    reassess_required: bool
    record: BlockedDecisionRecordV1 | None


def evaluate_retry(
    entry: ProductEntry,
    *,
    current_source_revision: str | None = None,
) -> RetryDecisionV1:
    """A previously-BLOCKED repository is retried only once an explicit causal fingerprint
    (source revision, control-plane, policy) actually changed -- never merely reattempted.

    `current_source_revision` is injectable so tests never need a live network probe; production
    callers omit it and this resolves the real remote HEAD.
    """

    org, repo = entry.org_repo.split("/", maxsplit=1)
    record = load_blocked_decision(paths.readme_poc_blocked_decision_path(org, repo))
    if record is None:
        return RetryDecisionV1(
            eligible=True,
            reason="no prior blocked decision on file",
            reassess_required=False,
            record=None,
        )
    if record.consecutive_count >= REASSESS_THRESHOLD:
        return RetryDecisionV1(
            eligible=False,
            reason=(
                f"{record.consecutive_count} consecutive failures with the same approach "
                "fingerprint -- REASSESS_REQUIRED, not another equivalent retry"
            ),
            reassess_required=True,
            record=record,
        )
    if current_source_revision is None:
        from readme_agent.gitsafety.clone import remote_head_sha

        current_source_revision = remote_head_sha(entry.clone_url)
    current_dependencies = current_blocked_decision_dependencies(
        org_repo=entry.org_repo,
        source_revision=current_source_revision,
        control_plane_fingerprint=compute_control_plane_fingerprint(entry.policy_profile),
        ecosystem=entry.ecosystem,
        family=entry.family,
    )
    changed = [
        key
        for key in sorted(set(record.dependencies) | set(current_dependencies))
        if record.dependencies.get(key) != current_dependencies.get(key)
    ]
    if not changed:
        return RetryDecisionV1(
            eligible=False,
            reason=(
                "no dependency fingerprint changed since the last failure -- refusing an "
                "equivalent retry without a causal repair/version change"
            ),
            reassess_required=False,
            record=record,
        )
    return RetryDecisionV1(
        eligible=True,
        reason=f"fingerprint changed: {', '.join(changed)}",
        reassess_required=False,
        record=record,
    )
