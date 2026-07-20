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
