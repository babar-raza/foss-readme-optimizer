"""Durable, cross-runner run state (Wave 4, `MEM-001`/`RUN-001`) -- distinct
from `evidence/`'s run-id-scoped audit trail, which stays exactly as it is
and never doubles as a compare-and-swap target. V1-first per
`[[conventions-and-feedback]]`: `RunStateV1`, not a bare `RunState` implying
a future v2 that doesn't exist yet. Mirrors `capabilities/schema.py`'s
pydantic style -- a validated, serialized external contract, not an internal
return value.
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class HandoffFindingV1(BaseModel):
    """One-way handoff finding for a product-agent-owned surface (class D:
    releases, packages -- `OWN-004`/`OWN-013`) -- Wave 7c, decision #41
    addendum. Deliberately NOT a bidirectional ack/reject/rerun state
    machine: the only existing reference to that shape
    (`docs/repository-presentation-surface-model.md`) describes a real
    receiving counterparty this project doesn't have -- decision #37 already
    reversed this exact "product agent as an addressable system" framing,
    for exactly this reason (`plans/master.md`). A plain finding record
    routed to a human maintainer, with no dispatch-side code expecting a
    reply; `DOC-006`'s full handoff schema stays `RESEARCH-GATED` until a
    real receiving system exists to design the other half against.

    Embedded as a plain dict (via `.model_dump(mode="json")`) inside the
    owning specialist's `DomainStateV1.details["handoff_findings"]` list --
    validated at construction time by this model, not a new top-level
    `RunStateV1` field.
    """

    surface: str
    anomaly: str
    evidence: dict = Field(default_factory=dict)
    detected_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class CapabilityOutputCacheEntry(BaseModel):
    """One cached capability result, keyed by `fingerprint` -- a hash of the
    capability's declared `idempotency_inputs` (`capabilities/schema.py`).
    This is the same value `requirements.md`'s `EFF-001`
    (`capability-dispatch-production-readiness.md`) calls an idempotency
    key: an existing entry for a given `fingerprint` is `EFF-002`'s "does
    this effect already exist?" reconciliation check.

    `status` (Wave 5, `EFF-002`) makes this a two-phase record: `pending` is
    written *before* the executor runs, `applied` only after it returns
    successfully -- so a process killed mid-effect leaves a `pending` record
    behind rather than nothing, and a resumed run can tell "never started"
    (no entry) apart from "started, unknown outcome" (`pending`) apart from
    "done" (`applied`). Default `"applied"` preserves the shape for anything
    that isn't going through the two-phase path. See
    `capabilities/effect_ledger.py`.
    """

    capability_id: str
    fingerprint: str
    result: dict
    status: Literal["pending", "applied"] = "applied"
    cached_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class DomainStateV1(BaseModel):
    """One specialist domain's accepted result within a shared `RunStateV1`
    record (`MEM-004`, Decision #34). Mirrors `RunStateV1`'s own flat
    accepted-result fields, one level down -- exists because `RunStateV1`
    was designed to answer "did *the* run for this repo produce an accepted
    result," singular, for a single producer; once Wave 6+ specialists each
    produce their own accepted result within one run against the same
    `org_repo` record, that assumption breaks (verified directly against
    `git_backend.py::save()`'s whole-blob-replace mechanics -- see
    `plans/investigations/specialist-domain-isolation-production-readiness.md`).
    Keyed by domain name in `RunStateV1.domain_states`, matching
    `capabilities/domains.py::KNOWN_DOMAINS`.
    """

    domain: str
    accepted_facts_hash: str | None = None
    accepted_status: str | None = None
    upstream_revision_at_accept: str | None = None
    # Wave 6's `readme_reconciliation` domain specifically: whether the owned
    # `resources` span was present in the README at accept time. Needed
    # because `remove_span` is a no-op when a span is already absent -- a
    # span that existed at last-accept and is gone now can otherwise produce
    # the *same* stripped-content hash as before, silently misclassifying a
    # real `OWNED_SPAN_LOST` as `NO_CHANGE`. Generic on this model (any
    # domain may use or ignore it), per `DomainStateV1`'s own
    # each-domain-gives-it-meaning convention.
    owned_span_present_at_accept: bool = False
    last_run_id: str | None = None
    last_run_timestamp: str | None = None
    # Wave 7: a generic structured-payload escape hatch, matching the
    # plain-dict convention `CapabilityOutputCacheEntry.result`/
    # `SupervisorStateV1.task_graph_snapshot` already use two models away in
    # this same file -- `DomainStateV1` was the one record type that didn't
    # have one, only because its sole consumer so far (`readme_
    # reconciliation`) never needed richer output than a status enum. Every
    # Wave 7+ specialist with real structured findings (proposed metadata
    # values, a package/release handoff payload, a specific inconsistency
    # list, a soft-failure detail) uses this one shared field rather than
    # each inventing its own incompatible workaround.
    details: dict = Field(default_factory=dict)
    # Wave 8 (`VER-002`/production-reliability pass): a per-domain failure
    # runs a real risk of failing closed *correctly* (no bad write) but not
    # *safely* -- `ERROR:`-prefixed state is never durably persisted, so the
    # domain's accepted baseline never advances, and an unchanged upstream
    # keeps re-triggering the identical work (including a real LLM call for
    # domains that render) every single run, forever, indistinguishable from
    # ordinary transient noise. These two fields, populated by `state/
    # domain_state.py::record_failure_or_reset()`, let a specialist's own
    # record-adjacent logic tell "failed once" apart from "has failed
    # identically N times in a row and nothing is fixing it" -- additive,
    # safe pydantic defaults, so a record written before these fields existed
    # deserializes cleanly as "no failure history yet."
    consecutive_failure_count: int = 0
    last_failure_reason: str | None = None
    # Wave 8.6 (`ORC-003` reversal prerequisite): whether this domain's own
    # detection dispatch was skipped this run (an LLM-gated decision,
    # `supervisor/specialist_selection.py`) rather than actually executed.
    # `accepted_status`/`accepted_facts_hash`/`upstream_revision_at_accept`
    # are deliberately left untouched by a skip -- nothing about this
    # domain's accepted baseline was reclassified, so none of it may honestly
    # advance. `consecutive_skip_count` bounds how many runs in a row a
    # domain may be skipped before it is forced to run regardless of any
    # planner's judgment (`state/domain_state.py::mark_domain_skipped()`).
    # Additive, safe pydantic defaults -- a record written before these
    # fields existed deserializes cleanly as "never skipped."
    skipped_this_run: bool = False
    consecutive_skip_count: int = 0


class SurfaceFreshnessContractV1(BaseModel):
    """Wave 9.7 (`FRESH-001`+, behavior in `state/freshness_contract.py`):
    per-surface freshness for a surface the git-SHA-based coarse
    `supervisor.convergence` shortcut cannot see at all -- description/
    homepage/topics, package/release state, GitHub-generated audits, and
    the visual/social-preview surface are none of them git-tracked, so an
    unchanged upstream commit says nothing about whether any of them
    changed. `last_checked_at`/`ttl_seconds` record when this surface was
    last actually observed by its owning specialist and for how long that
    observation may be trusted before the coarse shortcut must defer to a
    real specialist-tier run again."""

    surface_id: str
    authoritative_source: str
    ttl_seconds: int
    last_checked_at: str | None = None
    observed_hash: str | None = None


class SupervisorStateV1(BaseModel):
    """Wave 5's own accepted record within a shared `RunStateV1` (`MEM-001`,
    `ORC-001`) -- deliberately separate from the flat `accepted_facts_hash`/
    `accepted_status`/`upstream_revision_at_accept` fields (owned by
    `orchestrator.generate_repo()`'s pipeline) and from `domain_states`
    (Wave 6+ specialists). A third independent producer writing into either
    would reintroduce the exact single-slot-for-multiple-writers bug
    decisions #32/#34 already found and fixed, one level up.

    `last_observed_upstream_revision` is the cheap freshness check
    `supervisor.convergence` uses to skip planning entirely on an unchanged
    rerun (`VER-003`) -- one clone HEAD comparison, not a `facts_hash`
    recomputation (that's `generate_repo()`-specific and not meaningful
    without a capability that renders something). `task_graph_snapshot`/
    `capability_gaps`/`repair_history` are terminal-run-end snapshots only
    (`MEM-001`'s "task graph, capability outputs, repair history, capability
    gaps") -- not designed for mid-run resume (`SCL-003`, out of scope).
    """

    last_observed_upstream_revision: str | None = None
    last_status: str | None = None
    last_run_id: str | None = None
    last_run_timestamp: str | None = None
    task_graph_snapshot: dict | None = None
    capability_gaps: list[dict] = Field(default_factory=list)
    repair_history: list[dict] = Field(default_factory=list)
    # Wave 8 (production-reliability pass, external-review triage
    # 2026-07-21): `is_fresh()` compared only `last_observed_upstream_
    # revision` (the upstream commit SHA) -- a match short-circuited the
    # entire supervised run to `CONVERGED_NO_CHANGE` *before* the specialist
    # tier ever ran, so a policy/prompt/capability-manifest-version change
    # with no new upstream commit was invisible to a rerun, even though the
    # older CLI path's own `facts_hash` already accounts for policy/prompt
    # hashes. A hash of the currently-loaded control-plane inputs (policy
    # content, prompt content, registered capability versions), recorded
    # alongside the upstream revision, closes that gap: a control-plane
    # change now correctly invalidates the coarse shortcut. `None` on any
    # record written before this field existed -- a mismatch against a fresh
    # fingerprint on the very next run is the correct, expected one-time
    # re-validation, the same accepted pattern decision #38 already
    # established for `upstream_content_fingerprint_at_accept`.
    control_plane_fingerprint: str | None = None
    # TC-23 (decision #46/#48, Phase 13 §13.1's precise `VER-005` boundary):
    # written by `state/domain_state.py::mark_specialist_tier_started()`
    # immediately BEFORE the specialist loop begins -- not after, unlike
    # every other field on this model -- and cleared by the next normal
    # `_record_supervisor_state()` write once the loop actually finishes.
    # `VER-004`'s self-heal already catches a specialist that raises a real
    # Python exception (the `except Exception` in `loop.py`'s own domain
    # loop always runs, producing a synthetic `ERROR:` state); this closes
    # the one class it structurally cannot: a hard process/runner kill
    # *during* `run_domain()`, which prevents that `except` block, and
    # therefore every downstream write, from ever executing at all.
    # `in_flight_run_id` staying non-`None` on the NEXT run's `prior` read is
    # the detectable "started, never finished" signal `VER-005`'s row named
    # as absent -- distinguished from "genuinely nothing needed to happen."
    in_flight_run_id: str | None = None
    in_flight_domains: list[str] = Field(default_factory=list)
    # `VER-005` (found live, Wave 8e full-registry pass, 2026-07-21): a prior
    # run whose upstream revision and control-plane fingerprint both matched
    # could still have left `domain_states` incomplete -- some (not all)
    # domains crashed, lost a race, or were never reached before the process
    # died, with no exception ever bubbling up to mark the run itself as
    # anything but successful. `is_fresh()`'s coarse shortcut had no way to
    # see this, so an incomplete repo got permanently frozen at whatever it
    # last recorded, for as long as upstream stayed unchanged. Computed fresh
    # after the specialist tier completes (`set(specialists.all_domains()) <=
    # set(domain_states.keys())`), recorded here, and checked by `is_fresh()`
    # the same way `control_plane_fingerprint` already is: `None` (any record
    # written before this field existed) or `False` forces one honest full
    # specialist-tier retry, never a silent, permanent freeze.
    domain_coverage_complete: bool | None = None
    # Wave 9.7 (`FRESH-002`): keyed by domain (`GITHUB_GENERATED_SURFACE_AUDIT`/
    # `PACKAGE_RELEASE_AUDIT`/`METADATA_PRESENTATION`/`VISUAL_PREPARATION` --
    # the four non-git-tracked surfaces; README/community files are already
    # covered by `last_observed_upstream_revision` above). Refreshed only when
    # the specialist tier actually runs (`state/freshness_contract.py::
    # refresh_surface_contracts()`); carried forward unchanged on the cheap
    # pre-clone probe shortcut, which never runs the tier. Additive -- a
    # record written before this field existed deserializes cleanly as "every
    # surface due for an immediate recheck," the correct conservative default.
    surface_freshness: dict[str, SurfaceFreshnessContractV1] = Field(default_factory=dict)


class ModelRouteStatusV1(BaseModel):
    """Wave 8.6 (`OPS-011` extension): one LLM job route's enabled/disabled
    status, driven by `golden_set`'s own measured metrics -- the genuinely
    untracked half of `OPS-011` this project's own reconciliation found:
    the measurement side was already tracked, the enforcement action was
    not. Never a silent model substitution (a degraded default route might
    be equally degraded) -- `status="disabled"` blocks the run outright
    (`supervisor/loop.py`'s own `model_route_disabled:<job>:<reason>` check)
    until an explicit, human-authored re-enable."""

    job: str
    status: Literal["enabled", "disabled"] = "enabled"
    reason: str | None = None
    disabled_at: str | None = None
    evidence_ref: str | None = None
    re_enabled_by: str | None = None
    re_enabled_at: str | None = None


class ModelRouteRegistryV1(BaseModel):
    """The global (not per-`org_repo`) durable record -- the first one this
    codebase has; every other `RunStateV1`/lock ref is keyed per-repo. One
    record covers every job route, CAS-versioned the same way `RunStateV1`
    is."""

    state_version: int = 0
    routes: dict[str, ModelRouteStatusV1] = Field(default_factory=dict)


class ProfileCacheV1(BaseModel):
    """Decision #40/Part B: `profile_repository`/`get_product_facts` always
    re-clone + re-walk from scratch today, even when nothing changed
    upstream (measured ~258s on a real ~1GB registry repo). This caches the
    last computed `RepositoryProfile` (as its serialized dict, mirroring
    `CapabilityOutputCacheEntry.result`) keyed by the remote HEAD commit SHA
    at the time it was built (`gitsafety.clone.remote_head_sha()` -- a cheap
    `git ls-remote`, no clone) -- a cache hit means the upstream commit is
    unchanged, so re-cloning and re-walking would produce the identical
    result.

    Deliberately its own field on `RunStateV1`, not reusing
    `upstream_revision_at_accept` (owned by `generate_repo()`'s pipeline,
    and itself still unpopulated) or `supervisor_state` -- the same
    single-slot-for-multiple-writers bug decisions #32/#34 already found and
    fixed applies here too, one level up."""

    upstream_revision: str
    profile_result: dict
    cached_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class TriggerRecordV1(BaseModel):
    """Wave 9.5 (2026-07-22 convergence-sprint plan, `RUN-006`): a durable record of one accepted
    trigger event, keyed by a natural dedup identity so equivalent events (a re-run of the same
    `workflow_dispatch`, a duplicate `schedule` firing) do not silently re-execute already-accepted
    work. This is the trigger-identity half of `RUN-006`; the durable, checkpointed intake queue
    the row's full text also asks for is a larger, separate undertaking not built this pass -- see
    `logs/` for exactly what this phase does and does not close.

    `dedup_key()` is the identity a caller checks before accepting a new trigger: prefer
    `manual_request_id` (an operator-supplied idempotency token) when given, else
    `workflow_run_id` (GitHub's own per-run identity, stable across retries of the *same* run),
    else `(event_type, delivery_id)` (a webhook's own delivery identity), else fall back to
    `(org_repo, event_type, schedule_window)` for a bare `schedule` firing with none of the above.
    """

    org_repo: str
    event_type: Literal["workflow_dispatch", "schedule", "repository_dispatch", "cli_manual"] = (
        "cli_manual"
    )
    workflow_run_id: str | None = None
    delivery_id: str | None = None
    source_revision: str | None = None
    product_change_id: str | None = None
    schedule_window: str | None = None
    manual_request_id: str | None = None
    status: Literal["accepted", "processing", "completed", "deduplicated"] = "accepted"
    accepted_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def dedup_key(self) -> str:
        if self.manual_request_id:
            return f"manual:{self.manual_request_id}"
        if self.workflow_run_id:
            return f"run:{self.workflow_run_id}"
        if self.delivery_id:
            return f"delivery:{self.event_type}:{self.delivery_id}"
        return f"schedule:{self.org_repo}:{self.event_type}:{self.schedule_window}"


class OpenProposalV1(BaseModel):
    """`PRL-002` (decision #46): tracks one real, currently-open PR proposed
    against a target repo -- a state shape neither of this project's two
    existing effect models can honestly represent. The effect ledger's
    `pending`/`applied` pair (`CapabilityOutputCacheEntry.status`) means
    "crashed, unresolved" and "durably landed" respectively; an open PR is
    neither -- it is the intended, correct steady state of a proposal
    awaiting human review under the PR-merge-as-approval model (decision
    #46), not a crash signature, and recording it as `applied` would be
    false (the change hasn't landed; nothing has merged it yet).

    Added ahead of `open_presentation_pr` (`TC-08`) so that capability had a
    real state shape to target instead of retrofitting one later. The
    capability now exists but deliberately remains stateless; a specialist
    record node still needs to populate this model (`PRL-002`, PARTIAL).
    Keyed by domain in a new `RunStateV1.open_proposals` dict,
    mirroring `domain_states`'s own per-domain-producer convention -- more
    than one domain (README content, metadata, community files) may each
    open its own independent PR against the same repo."""

    domain: str
    pr_number: int | None = None
    pr_url: str | None = None
    branch_name: str | None = None
    state: Literal["open", "merged", "closed", "superseded"] = "open"
    facts_hash: str | None = None
    opened_at: str | None = None


class RunStateV1(BaseModel):
    """The durable record of what has been accepted for one `org/repo`.
    Exists specifically so idempotency ("run twice, second run makes zero
    LLM calls") survives an ephemeral GitHub Actions runner being wiped
    after every job (`RUN-001`) -- `paths.work_dir()`'s persistent local
    clone (decision #12) still exists and is still checked first, but is no
    longer the *only* place that memory can live.

    `state_version` is the compare-and-swap counter (`MEM-002`) -- the
    backend increments it on every accepted write and it is never reused;
    `expected_version=None` is only valid for the first-ever write for a new
    `org_repo`.
    """

    org_repo: str
    state_version: int = 0
    accepted_facts_hash: str | None = None
    accepted_status: str | None = None
    # The commit SHA the accepted state was computed against -- `MEM-002`'s
    # "compare-and-swap against the current upstream revision". Not yet
    # populated by orchestrator.py (no caller resolves the baseline's commit
    # SHA today); left `None` rather than faked.
    upstream_revision_at_accept: str | None = None
    # Content-level fingerprint (`readme/facts.py::compute_tracked_content_hash`)
    # of the tracked surfaces (README/LICENSE/community files) as they existed
    # when this record was accepted -- decision #38. Gates
    # `orchestrator.py`'s durable-skip fast path: `accepted_facts_hash`
    # matching alone is not sufficient, since `facts_hash` deliberately
    # excludes README content (decision #11) and is therefore blind to a real
    # upstream content edit on its own. `None` on any record written before
    # this field existed -- a mismatch against a fresh fingerprint on the very
    # next run is the correct, expected one-time re-validation, not a bug.
    upstream_content_fingerprint_at_accept: str | None = None
    last_run_id: str | None = None
    last_run_timestamp: str | None = None
    capability_outputs: list[CapabilityOutputCacheEntry] = Field(default_factory=list)
    # Per-domain accepted results (`MEM-004`, Decision #34) -- additive
    # alongside the flat fields above, which are NOT deprecated: they remain
    # whatever a single top-level (pre-Wave-6) producer writes.
    # `domain_states` is what Wave 6+ specialists write into independently,
    # via `save_domain()` (state/domain_state.py), never by mutating this
    # dict directly through a raw `save()` call.
    domain_states: dict[str, DomainStateV1] = Field(default_factory=dict)
    # Wave 5's own accepted record -- deliberately separate from the flat
    # accepted_facts_hash/accepted_status/upstream_revision_at_accept fields
    # above (owned by orchestrator.generate_repo()'s pipeline) and from
    # domain_states (Wave 6+ specialists). A third independent producer
    # writing into either would reintroduce the exact single-slot-for-
    # multiple-writers bug decisions #32/#34 already found and fixed, one
    # level up -- caught before implementation, not after.
    supervisor_state: SupervisorStateV1 | None = None
    # Decision #40/Part B -- own slot, same reasoning as supervisor_state
    # above: a fourth independent producer (profile/cached.py), never
    # sharing another producer's field.
    profile_cache: ProfileCacheV1 | None = None
    # `PRL-002` (decision #46): keyed by domain, mirroring `domain_states`'s
    # own per-domain-producer convention -- see `OpenProposalV1`'s own
    # docstring for why this cannot reuse `capability_outputs`'s pending/
    # applied model. Additive/optional, same safe-default pattern every
    # other field added to this model after its initial Wave 4 shipment
    # already uses -- a record written before this field existed
    # deserializes cleanly as "no open proposals recorded."
    open_proposals: dict[str, OpenProposalV1] = Field(default_factory=dict)
    # Wave 9.5 (`RUN-006`): keyed by `TriggerRecordV1.dedup_key()`, bounded (see
    # `state/trigger.py::record_trigger()`'s own pruning) so this dict cannot grow unbounded across
    # a long-lived repo's history. Additive -- a record written before this field existed
    # deserializes cleanly as "no trigger history recorded yet."
    trigger_records: dict[str, TriggerRecordV1] = Field(default_factory=dict)
