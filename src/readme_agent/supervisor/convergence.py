"""Convergence / stop-condition logic (`AGT-004`): "MUST NOT stop on an
arbitrary global iteration limit; it stops only on defined convergence,
safe-proposal, missing-permission, or genuine-blocker conditions." Honestly
scoped to what Wave 5's actual capability surface (four read-only
capabilities, no mutation registered yet) can produce -- see
`plans/foamy-brewing-moonbeam.md`'s "Convergence" section for the full
reasoning this module implements.

`TaskGraph.is_converged()` (all current tasks terminal) is *not* by itself a
stop signal: it is trivially true after any single synchronous dispatch,
before the planner has ever been asked whether more work is worth
discovering. The real stop signal is the planner's own explicit turn with no
tool call (found live, via a smoke test: an earlier design checked
`is_converged()` at the top of every turn and stopped after the bootstrap
observation alone, never consulting the planner at all). This module
therefore splits into two independent checks: `check_repair_exhausted()`
(a bug-detector bound, evaluated every turn) and `final_status()` (classifies
the ending state, called only once the loop has actually stopped).
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from readme_agent.errors import ConfigError
from readme_agent.state.schema import (
    CapabilityOutputCacheEntry,
    DomainStateV1,
    OpenProposalV1,
    RunStateV1,
    TriggerRecordV1,
)
from readme_agent.supervisor.task import TaskGraph

SuperviseStatus = Literal[
    "CONVERGED_NO_CHANGE",
    "CONVERGED_APPLIED",
    "PARTIAL_WITH_CAPABILITY_GAP",
    "BLOCKED",
    # Wave 6 (decision #39): the coarse `is_fresh()` check below found the
    # upstream commit had moved, but every registered specialist domain's
    # fine-grained classification came back NO_CHANGE (nothing tracked --
    # README/community files -- actually changed). Constructed directly in
    # `loop.py::supervise_repo()`, not via `final_status()` -- listed here
    # for the status vocabulary's own documentation completeness.
    "CONVERGED_NO_TRACKED_CHANGE",
]


@dataclass
class ConvergenceOutcome:
    status: SuperviseStatus
    blocked_reason: str | None = None


def is_fresh(
    recorded_revision: str | None,
    current_revision: str | None,
    *,
    recorded_control_plane_fingerprint: str | None = None,
    current_control_plane_fingerprint: str | None = None,
    recorded_domain_coverage_complete: bool | None = None,
    check_domain_coverage: bool = False,
) -> bool:
    """The cheap pre-planning freshness check (`VER-003`): if the durable
    record's last-observed upstream revision equals the baseline clone's
    current HEAD, nothing has changed since the last converged run -- skip
    planning entirely. One clone-HEAD comparison, not a `facts_hash`
    recomputation (that's `generate_repo()`-specific and not meaningful
    without a capability that renders something).

    Wave 8 (production-reliability pass, external-review triage
    2026-07-21): the upstream-revision comparison alone is blind to a
    control-plane change (a policy/prompt/capability-manifest-version edit)
    with no new upstream commit -- and since this function's own match
    short-circuits `supervise_repo()` *before* the specialist tier (whose own
    facts_hash comparisons *are* control-plane-aware) ever runs, that
    blindness was total, not just partial. `current_control_plane_
    fingerprint` is keyword-only and defaults to `None`, preserving every
    existing caller's exact behavior when it isn't supplied (skips this
    check entirely) -- backward compatible, not a breaking signature change.
    A recorded fingerprint of `None` (every record written before this field
    existed) never matches a real current fingerprint, forcing one honest
    re-validation, the same accepted pattern decision #38 already
    established for `upstream_content_fingerprint_at_accept`.

    `VER-005` (found live, Wave 8e full-registry pass, 2026-07-21): even a
    genuinely unchanged upstream + control plane says nothing about whether
    the *prior* run's own `domain_states` coverage was actually complete --
    a domain that crashed, lost a race, or was never reached before the
    process died leaves no trace the coarse check above can see, so an
    incomplete repo got permanently frozen at whatever it last recorded.
    `check_domain_coverage` is keyword-only, defaults to `False` -- preserves
    every existing caller's exact behavior when not passed. A caller that
    opts in (passes `check_domain_coverage=True`, `recorded_domain_coverage_
    complete` read from `SupervisorStateV1`) additionally requires that
    value to be exactly `True`; `None` (every record written before this
    field existed) or `False` forces one honest full specialist-tier retry,
    the same self-healing pattern as the control-plane fingerprint above."""
    revision_matches = (
        recorded_revision is not None
        and current_revision is not None
        and recorded_revision == current_revision
    )
    if not revision_matches:
        return False
    if current_control_plane_fingerprint is not None and (
        recorded_control_plane_fingerprint is None
        or recorded_control_plane_fingerprint != current_control_plane_fingerprint
    ):
        return False
    if check_domain_coverage and recorded_domain_coverage_complete is not True:
        return False
    return True


def compute_control_plane_fingerprint(policy_profile: str | None) -> str:
    """A hash of the parts of the control plane that can change a
    supervised run's output with no new upstream commit at all: every
    registered capability's declared `version` (`capabilities/registry.py::
    list_all()`, in-memory, no I/O), the shared LLM prompt content (`llm/
    prompts.py::prompt_content_hash()`, already the canonical hash for this
    exact concern elsewhere in this codebase), the validation ruleset
    version (`VER-004`: a rule-code change with no new upstream commit is
    exactly this kind of control-plane change too -- without this, `is_fresh
    ()`'s own coarse shortcut would keep skipping the specialist tier
    entirely after a rule edit, never giving `orchestrator.py`'s own
    `durable_skip` check inside it a chance to notice), and -- if the repo
    has a configured `policy_profile` -- that policy file's own content. A
    repo with no `policy_profile` configured (22/25 real registry entries,
    confirmed by direct inspection of `data/products.json`) still gets a
    real, capability-version/prompt-aware fingerprint; only the
    policy-specific slice is absent for those, degrading honestly rather
    than raising -- the same "no policy_profile yet" tolerance `get_product_
    facts` already extends elsewhere.

    GOV-024/Wave 8.5: hashes via `prompt_registry.content_hash()` -- every
    registered prompt file, including the supervisor's own `supervisor_turn`
    prompt -- not `llm.prompts.prompt_content_hash()`, which stays narrowly
    scoped to `relationship_explained` only (that one also feeds
    `RepositoryFacts`' facts-hash; widening it here would make an unrelated
    supervisor-prompt edit force every README to look stale)."""
    from readme_agent.capabilities import registry
    from readme_agent.llm import prompt_registry
    from readme_agent.registry.loader import load_policy
    from readme_agent.validation.registry import VALIDATION_RULESET_VERSION

    capability_versions = {m.capability_id: m.version for m in registry.list_all()}
    policy_content = None
    if policy_profile is not None:
        try:
            policy = load_policy(policy_profile)
            policy_content = json.dumps(
                policy.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            )
        except ConfigError:
            policy_content = None  # unresolvable policy -- fingerprint degrades honestly

    canonical = json.dumps(
        {
            "capability_versions": capability_versions,
            "prompt_registry_content_hash": prompt_registry.content_hash(),
            "validation_ruleset_version": VALIDATION_RULESET_VERSION,
            "policy_content": policy_content,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def has_pending_effect(capability_outputs: list[CapabilityOutputCacheEntry]) -> bool:
    """Condition 3 of 7 (`FRESH-007`): an effect that crashed mid-apply
    (`EFF-002`'s own `pending` record) must never be silently papered over
    by the coarse `NO_CHANGE` shortcut -- it needs `reconciliation_check()`
    or a real retry, never a skip that leaves it stuck forever."""
    return any(entry.status == "pending" for entry in capability_outputs)


def has_open_proposal_needing_reconciliation(open_proposals: dict[str, OpenProposalV1]) -> bool:
    """Condition 4 of 7 (`FRESH-008`): an open, unmerged proposal (`PRL-002`)
    may have been merged/closed/superseded on the remote side independent
    of anything this project tracks -- the coarse shortcut cannot know
    without a real check. Currently always vacuous in production: `PRL-002`
    is still `PARTIAL` (no specialist populates `RunStateV1.open_proposals`
    yet), so this can never actually block a real run today -- built now so
    the gate is already correct the moment a specialist starts populating
    it, not retrofitted later."""
    return any(proposal.state == "open" for proposal in open_proposals.values())


def has_unfinished_trigger(trigger_records: dict[str, TriggerRecordV1]) -> bool:
    """Condition 7 of 7 (`FRESH-009`): a trigger accepted but never marked
    `completed`/`deduplicated` (`RUN-006`, Wave 9.5) means the run it
    represents may still be in flight or may have died before recording its
    own outcome -- the coarse shortcut must not treat that as settled."""
    return any(record.status in ("accepted", "processing") for record in trigger_records.values())


def no_change_gate_holds(
    prior: RunStateV1 | None,
    current_revision: str | None,
    current_control_plane_fingerprint: str | None,
    *,
    now: datetime,
) -> bool:
    """Wave 9.7 (`FRESH-010`): the full 7-condition `NO_CHANGE` gate --
    `is_fresh()`'s original 3 conditions (Git revision, control-plane
    fingerprint, domain coverage) plus the 4 this phase adds (external
    surfaces within TTL, no pending effect, no open proposal needing
    reconciliation, no unfinished trigger). Replaces the bare `is_fresh()`
    call at `supervisor/loop.py`'s post-clone coarse-shortcut call site,
    which has the full `RunStateV1` on hand -- `is_fresh()` itself is
    untouched (still directly unit-tested, still the right tool for the
    cheap pre-clone probe shortcut, which has no full `RunStateV1` to
    inspect and only ever needs the Git-revision-level question)."""
    from readme_agent.state.domain_state import effective_domain_coverage_complete
    from readme_agent.state.freshness_contract import any_surface_due_for_recheck

    supervisor_state = prior.supervisor_state if prior is not None else None
    if not is_fresh(
        supervisor_state.last_observed_upstream_revision if supervisor_state else None,
        current_revision,
        recorded_control_plane_fingerprint=(
            supervisor_state.control_plane_fingerprint if supervisor_state else None
        ),
        current_control_plane_fingerprint=current_control_plane_fingerprint,
        recorded_domain_coverage_complete=effective_domain_coverage_complete(supervisor_state),
        check_domain_coverage=True,
    ):
        return False
    if prior is None:
        return True
    if any_surface_due_for_recheck(
        supervisor_state.surface_freshness if supervisor_state else {}, now
    ):
        return False
    if has_pending_effect(prior.capability_outputs):
        return False
    if has_open_proposal_needing_reconciliation(prior.open_proposals):
        return False
    if has_unfinished_trigger(prior.trigger_records):
        return False
    return True


def check_repair_exhausted(turns_taken: int, max_turns: int) -> ConvergenceOutcome | None:
    """A **bug detector**, not the normal stop path: if the loop is still
    going after `max_turns`, that is itself evidence of a stuck planner (a
    genuine-blocker condition, `AGT-004`'s own wording), recorded as a
    distinct `BLOCKED` reason -- never a silent, arbitrary stop."""
    if turns_taken >= max_turns:
        return ConvergenceOutcome(status="BLOCKED", blocked_reason="repair_exhausted")
    return None


def final_status(
    graph: TaskGraph,
    *,
    applied_any_effect: bool,
    specialist_results: dict[str, DomainStateV1] | None = None,
) -> ConvergenceOutcome:
    """Classifies the graph's ending state once the loop has actually
    stopped (the planner's own explicit turn with no tool call, or
    `check_repair_exhausted()` firing). Never called mid-loop to decide
    *whether* to stop -- only to decide *what happened* once it has."""
    specialist_errors = sorted(
        (
            domain,
            result.accepted_status,
        )
        for domain, result in (specialist_results or {}).items()
        if (result.accepted_status or "").startswith("ERROR:")
    )
    if specialist_errors:
        domain, status = specialist_errors[0]
        return ConvergenceOutcome(
            status="BLOCKED",
            blocked_reason=f"specialist_failed:{domain}:{status}",
        )

    blocked = [t for t in graph.tasks.values() if t.state == "BLOCKED"]
    if blocked:
        has_gap = any(t.gap is not None for t in blocked)
        if has_gap and any(t.state == "PASSED" for t in graph.tasks.values()):
            # GAP-001's "continue independent supported work": at least one
            # branch genuinely converged despite the gap.
            return ConvergenceOutcome(status="PARTIAL_WITH_CAPABILITY_GAP")
        return ConvergenceOutcome(
            status="BLOCKED", blocked_reason=blocked[0].blocked_reason or "blocked"
        )

    return ConvergenceOutcome(
        status="CONVERGED_APPLIED" if applied_any_effect else "CONVERGED_NO_CHANGE"
    )
