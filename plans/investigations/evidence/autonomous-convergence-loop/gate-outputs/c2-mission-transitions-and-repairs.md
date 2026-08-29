# Cycle 2 — repairs landed and mission transitions recorded

## Repairs

### Traceability closure citations (commit `99a1ad007`)

`traceability_matrix.py --check` — one of the ten official checks — had exited 1 on three
`IMPLEMENTED` P1 rows citing neither a concrete pytest node nor a committed artifact. All three
predate this sprint (`3e4da1b88`, `67f66f6d9`, `f1efd83a2`) and all three describe real landed work
at length; only a machine-checkable citation was missing. Each row was matched to the test that
actually proves its behaviour, and **every cited node was collected and run green (12 passed)
before being cited**:

- `LLM-023` → `test_capabilities.py::TestVerifyProseQuality::test_execute_reuses_a_cached_verdict_with_zero_new_calls`
  plus `tests/unit/test_prose_quality_cache.py`
- `CORE-041` → `test_evidence_writer.py::test_atomic_write_survives_a_destination_beyond_windows_max_path`
- `CORE-042` → `test_portfolio_worker_integration.py::test_nonzero_exit_worker_with_an_exit_code_consistent_receipt_is_trusted`,
  with `test_failed_current_worker_cannot_reuse_a_stale_success_receipt` as its negative control

Cost one cycle to a Windows trap worth recording: the first run used `Path.write_text()`, which
translates every `\n` to `\r\n`. The git diff stayed correct at 3 changed lines while the file's
bytes changed for all 523 records — and the pinned catalog/coverage hashes are computed over those
bytes, so `validate_pinned_hashes.py` called the coverage report stale against a catalog the builder
had just regenerated from it. Anything that rewrites a pinned file wholesale needs `newline=""`.

### VER-012: the reviewer double answered for a reviewer that never ran (commit `af09e2ca8`)

Both failing tests patched `separated_readme_review.build_live_merged_review_client`, but
`run_merged_readme_review` routes to the bounded/separated reviewer for every candidate carrying a
document plan (`6591c6cc2`) — which is every candidate the `project` fixture builds. The override
hit a reviewer that never executed; the fixture's own always-accepting `_fake_accepting_role_clients`
stayed in charge; the candidate was accepted on the first round; the repair loop under test was
never entered (`statuses.count("AGENT_REVIEWING") == 1`, not 2).

A previous cycle had tried rewiring to `build_live_role_review_clients` alone and correctly reverted
it: that alone moves the failure to `independent_review_exception:StopIteration`, because the double
was written for the merged reviewer, which sees the whole candidate in one call. Bounded review
sends one packet per section, so "reject on call 1" meant "reject whichever section is packed
first", and `next(... startswith("```mermaid"))` raised the moment that section held no diagram.

The double now selects the packet that actually contains the mermaid anchor rather than a call
ordinal, and rejects exactly once. That target is load-bearing: `build_repair_receipt` only marks a
finding `addressed_pending_rereview` when the finding's own section text changes, a bound operation
changes, and its quoted span stops occurring — and `_RepairAwareCompositionForcedToolClient` is what
makes all three true by re-planning that diagram.

Assertions moved to the bounded contract. Finding ids are packet-namespaced
(`pkt.visitor.0002.at.a.glance.9c47a37ecc7c.quality.generic-overview`); asserting the namespace
alongside the id is strictly stronger than the old bare equality, because it also proves the
rejection landed on the at-a-glance packet. Per-round call literals were replaced by the
relationships they stood for — a fixed number there encodes today's section packing, not the
contract.

**Non-vacuity proved** by restoring the pre-fix wiring in place: both tests fail with it, both pass
with the migration.

### Composition truncation retry — RDM-033's second call site (commit `37b7a7517`)

RDM-033 already required that a forced tool call must not fail closed on
`LLMTruncatedResponseError`, and its recorded fix for `section_cluster_authoring.py` was exactly
"reuse the established repair-hint rebuild with a write-more-concisely instruction". That landed at
one site. The sibling-site sweep this sprint's plan mandates found the other.

`plan_readme_composition` does catch the error, but answered it with `_repair_hints()`, which
appends the full section-decision, phrase-option and diagram-role vocabularies. So the single retry
`MAX_AUTHORING_ATTEMPTS = 2` permits was **strictly longer** than the attempt that had already
overrun the client's 6000-token output ceiling, with nothing asking for brevity.

Measured blast radius: 3 repositories blocked at
`presentation_plan:execution_error:LLMTruncatedResponseError`, truncating at 5184, 7402 and 10698
characters of tool arguments.

One design point is recorded because the first draft got it wrong: the authoritative diagram role
vocabulary is deliberately **kept** on the retry. Dropping it would have saved prompt space by
trading a truncation failure for a grounding failure on invented labels. The assertion that exposed
this was `len(retry) <= len(first)`, which failed by 151 characters and forced the question of what
was actually being removed. Non-vacuity proved by disabling the branch in place.

`test_readme_composition_module_boundaries.py` caps `agentic_composition.py` at 300 lines and the
fix pushed it to 308, so the hint builder moved to `agentic_composition_inputs.py`. The guard was
respected, not relaxed.

## Mission transitions

Both performed through the controller, never by editing durable state.

**`L8-PF-02-COMPLETE-CANDIDATE-SEAM` → `BLOCKED`** (agent_fixable), `state_version 1801`, with the
root cause from the scope-mismatch artifact and an exact resume condition recorded on the
transition. Preferred over leaving an expiring claim on a task that cannot progress.

**`L8-PF-04-MINIMAL-GRAPH-RUNNER` → `REOPENED`**, `state_version 1802`. It was `CLOSED` against
`supervisor/proven_transaction_runner/`. Verified at HEAD `37b7a7517`: zero production importers
outside its own package, no `run_proven_transaction` caller outside `pf04_evidence.py` and tests,
and no reference from `cli.py` or `commands*.py`. Deliberately **not** integrated — that would
duplicate the supervise runtime, which Decision #26 makes the sole runtime.

The controller refused the PF-04 transition while PF-02 was active
(`cannot transition while 'L8-PF-02-COMPLETE-CANDIDATE-SEAM' is active`), which is the
single-active-task discipline working correctly; PF-02 was closed out first.

**Consequence, stated rather than hidden:** `eligible_tasks` is now empty, because `L8-PF-05`
depended on `L8-PF-04`. Before these transitions the controller would have offered `L8-PF-05` as
ready work resting on an unreachable deliverable. An empty eligible list that is true is better than
a populated one that is not.

It is **not** mission completion: `mission_complete: false`, 49 unresolved tasks, contract-valid
`no_op_proven` 0/34, `graph_drift: false`.
