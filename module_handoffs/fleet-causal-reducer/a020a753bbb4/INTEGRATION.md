# Integration notes for Codex

## Exact entry point

```python
from readme_agent.supervisor.portfolio_proof_engine.failure_causal_reducer import (
    reduce_fleet_failures,
    FailureObservationV1,
    DependencyFingerprintSnapshotV1,
)

result = reduce_fleet_failures(observations=[...], dependency_snapshot=snapshot_or_None)
```

Not re-exported from `portfolio_proof_engine/__init__.py` (deliberately not edited — see the task's
owned-paths list). Import directly from the submodule, matching every other consumer in this
package (`dashboard.py`, `stage_classifier.py`, `receipt_store.py` all import this way already).

## How to feed it portfolio receipts

For every `ProofStageReceiptV1` with `status == "FAILED"` that the portfolio proof engine already
produces (via `stage_classifier.py`, ideally after `dashboard.py`'s receipt-chain coherence pass —
see Known Limitation 5), wrap it in a `FailureObservationV1`:

```python
FailureObservationV1(
    receipt=failed_receipt,                 # required, must be status="FAILED"
    family=registry_entry.family,            # optional, not on the receipt
    blocked_category=task.blocked_category,  # optional, reused BlockedCategory
    causal_component=...,                    # optional, only if genuinely known -- never guessed
    structured_error_code=...,               # optional, prefer this over free text whenever available
    gate_or_check_id=...,                    # optional, e.g. from dashboard.py's failed_gates tuple
    dependency_fingerprint=...,              # optional, same shape as local_poc_cache's dependency dict
    exception_type=...,                      # optional, fully-qualified exception class name
    evidence_ref=...,                        # optional, relative path only, no ".." segments
    pipeline_source="commands_poc_delivery", # a literal string identifying the CALLING pipeline --
                                              # never inferred by this module
    known_reproducibility_verdict=...,       # optional, only from real noop.json-shaped evidence,
                                              # e.g. "RENDER_REPRODUCIBLE"/"NO_OP_PROVEN" -- never guessed
)
```

Collect all such observations across the fleet pass into one list and call `reduce_fleet_failures`
once. Optionally supply a `DependencyFingerprintSnapshotV1` (built the same way
`retry_policy.py::evaluate_retry` already builds a "current dependencies" dict, via
`local_poc_cache.current_blocked_decision_dependencies()`) if you want tier-5 fingerprinting and
`dependency_changed` signals to be meaningful; without it, both default to conservative
"unknown → not changed" behavior.

## Where it could sit

Between portfolio evidence collection and repair selection: after a fleet pass has produced
`ProofStageReceiptV1` records (and ideally after `dashboard.py`'s coherence pass), but before any
repair-scheduling decision. It complements `retry_policy.py` (which decides *whether one repo*
should retry) by deciding *which repos share a cause*, so a repair effort can target
`representative`/`minimal_proof_cohort` members instead of every affected repo individually.

## Why it must remain read-only

Per the task brief and this repo's own "never a second scoring/execution/promotion system"
convention (already established for `dashboard.py`, `portfolio_scheduler/reducer.py`, and
`portfolio_proof_engine/__init__.py`): this module classifies and prioritizes what is already true,
it never decides what should happen next. Repair execution, retries, and lifecycle transitions
belong to `portfolio_scheduler/reducer.py` and `retry_policy.py`, which already own that authority
and were deliberately not touched, duplicated, or extended by this lane.

## What result fields a future state-machine transition may consume

`clusters[i].classification`, `.confidence`, `.priority_rank`, `.recommended_repair_scope`,
`.required_closure_evidence`, `.representative`, and the top-level `minimal_proof_cohort` are the
fields designed to inform a repair-selection decision. `member_org_repos` and
`estimated_retries_avoided` quantify blast radius/leverage. None of these fields, on their own or
combined, constitute authorization to execute a repair, retry, or promote lifecycle state — that
remains a decision for whatever system consumes this module's output.

## What it does not decide

Repair scope execution, retries, mission/lifecycle transitions, acceptance, publication. It never
writes a receipt, never calls a provider, never touches `ReadmePocLifecycleStateV2` or any registry
file.

## How to invalidate clusters when dependencies or code revisions change

The function is pure: identical input always reproduces identical output (verified live via
`test_input_ordering_does_not_affect_output`, which checks full output equality across a shuffled
input order). There is nothing to invalidate *in-place* — there is no cache, no stored state. The
correct pattern is: rebuild the full `observations` list fresh from current evidence, rebuild
`dependency_snapshot` fresh from current dependency state, and call `reduce_fleet_failures` again.
Given the demonstrated fleet churn documented in `KNOWN_LIMITATIONS.md` (60%+ bucket-membership
change in an 11-hour window during this module's own research), this should happen every fleet pass,
never on a longer cadence, and never be persisted/cached across a code-revision boundary.

## Potential conflicts with changes landed after `BASE_SHA`

One drift commit exists on `main` past this lane's `BASE_SHA` at handoff time
(`d6fbed567aa7d99dd0e065944e3694cb6ebd5ced`, "fix(evidence): resume long-path supersession") — see
`BASE_AND_DRIFT.json`. It touches evidence/long-path handling, not `portfolio_proof_engine/`,
`presentation/`, or anything this lane reads from or owns; no conflict expected, but re-verify
against `main` at integration time given this repo's demonstrated churn rate. Given the volume of
concurrent `fix(review):`/`fix(readme):` activity documented in this handoff's `REPORT.md`, treat
any integration attempt as needing a fresh `git diff main...HEAD` check immediately before merging,
not just at the point this handoff was produced.
