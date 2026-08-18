# L8-HORIZON-01-ACTIVATE-GATE-A — investigation findings and deferral rationale

Claimed 2026-08-13 immediately after `L8-VPY-03-ALL-PYTHON-VERIFIED-POC` closed (it was the
mission controller's own `next_task` recommendation). Investigated fully; deferring rather than
forcing a rushed implementation. This is a `REROUTED` disposition, not a completion and not a
genuine external block — the work is well-defined and agent-fixable, just not needed yet.

## What the task actually requires

`L8-HORIZON-01-ACTIVATE-GATE-A`'s objective: "promote only the next dependency-ready verified task
horizon from the hashed deferred catalog into this same graph," bounded to "at most fifteen tasks
and five ready tasks" (decision 93, compact authority).

## Finding 1: the active graph is exactly at its 15-task cap

`plans/investigations/control/level8-autonomous-mission-task-graph.yaml`'s `taskcards` currently
has exactly 15 entries. There is zero room to add anything without first removing some.

## Finding 2: 10 of the 15 active taskcards are already durably `CLOSED`

`L8-AGILE-AUTHORITY-RESET`, `L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E`, `L8-VPY-01-NOTE-VERIFIED-CANARY`,
`L8-VPY-00-PRESENTATION-CONTRACT-RESET`, `L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES`,
`L8-VPY-03C-PAGE-CURRENT-REFRESH`, `L8-VPY-03D-NOTE-CURRENT-REFRESH`,
`L8-VPY-03E-3D-CURRENT-REFRESH`, `L8-VPY-03-ALL-PYTHON-VERIFIED-POC`, and
`L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES` are all `CLOSED` in durable state but still occupy active
taskcard slots. Retiring them (moving them into `deferred_task_index` as closed/historical
records) is the obvious way to free budget for promotion.

## Finding 3: retirement is blocked by a real referential-integrity gap in the loader

`src/readme_agent/supervisor/mission_graph.py::_validate_graph` builds `by_id` **only** from
`graph.taskcards` (lines 227-268) and rejects any `dependencies` entry not present in that dict
(lines 270-273: `missing = [dependency for dependency in task.dependencies if dependency not in
by_id]`). It does **not** also check `deferred_task_index` for active-task dependency resolution
(that union is only used for validating the deferred catalog's own internal dependencies, lines
196-208 — the opposite direction). Concretely: `L8-VPY-04-PRODUCTION-TRANSPORT` (still active,
`TODO`, and the actual next critical-path task) lists `L8-VPY-03-ALL-PYTHON-VERIFIED-POC` as a
dependency. Removing `L8-VPY-03` from `taskcards` — even though it is durably `CLOSED` and
`_DEPENDENCY_SATISFIED` would still recognize it via durable state — would break graph-load
validation with "unknown dependencies", because the loader's referential-integrity check only
looks at the active taskcard list, not durable state or the deferred index.

The same chain applies transitively to all 10 closed tasks: each one is a dependency (direct or
transitive) of an active task still needed on the near-term critical path
(`L8-VPY-04 -> L8-VPY-05 -> L8-VNET-01 -> L8-VNET-02 -> L8-VPY-02[Java]`). None can be safely
removed today.

**The real fix** is a scoped, legitimate code change: extend the active-task dependency check
(and/or `mission_control.py`'s `_DEPENDENCY_SATISFIED`/`by_id` resolution) to also recognize a
dependency that resolves to a `deferred_task_index` entry whose recorded status is `CLOSED` —
mirroring how the deferred catalog's own dependencies already resolve against the union of both
sets (lines 196, 204). This is genuine, well-scoped `src/readme_agent/supervisor/` work (which is
exactly why this task's `allowed_paths` includes that directory and
`tests/unit/test_mission_control.py`) — not something to improvise inline as a side effect of a
graph-data edit.

## Finding 4: a second, independent anomaly — legacy closures predate the current dependency shape

Durable state carries `CLOSED` for roughly 60 of the 125 deferred-catalog task_ids as well, even
though the catalog still lists them `status: TODO` — evidence the durable-state backend is shared
across an earlier, larger incarnation of this same `mission_id` graph (predating the 2026-08-02
compact-authority migration that split this catalog out). A specific concrete instance:
`L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES` is durably `CLOSED`, yet under the *current* graph it has an
unmet dependency (`L8-VNET-02-PRODUCTION-TRANSPORT`, still `TODO`) — meaning its closure predates
the dependency edge that now points at it. This is a pre-existing data-provenance question, not
something this session introduced or should silently paper over. It does not block the near-term
critical path (nothing currently depends on `L8-VPY-02`'s closure being freshly re-validated), but
it deserves its own dedicated look before any bulk graph-compaction pass relies on "durably closed"
as ground truth.

## Six genuinely dependency-ready deferred candidates (found, not promoted)

All in the `verified-gate-a` activation group (a broader full-registry-qualification campaign,
`CAMP-GATE-A-PORTFOLIO`, distinct from the platform-by-platform delivery campaigns like
`CAMP-PYTHON-PORTFOLIO`): `L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP`, `L8-LOCAL-README-PROPOSAL-PROOF`,
`L8-TRUTH-08-FULL-REGISTRY`, `L8-REVIEW-00-CONTEXT-CORPUS`, `L8-REVIEW-04A-REAL-CORPUS` (plus
`L8-PREPRODUCTION-IDEA-FIDELITY-GATE`, `gate-b-c` group, almost certainly out of scope for a task
literally named "ACTIVATE-GATE-A"). None of these six gate or unlock any part of the actively
requested `.NET -> Java -> C++ -> TypeScript -> Rust -> Go` delivery sequence — that sequence's
next tasks (`L8-VPY-04`, `L8-VPY-05`, `L8-VNET-01`, `L8-VNET-02`) are already present as active
taskcards and require no promotion to proceed.

## Why deferred rather than forced

Decision 92 (just-in-time infrastructure): "Infrastructure enters the critical path only when the
next visible vertical slice exercises or demonstrably needs it." The next visible vertical slice —
the .NET pilot via `L8-VPY-04`/`L8-VPY-05`/`L8-VNET-01` — needs none of this. Implementing the
retirement mechanism correctly (a real `mission_graph.py`/`mission_control.py` change, with its own
focused tests proving the negative control "a dependency-ineligible task must fail activation"
still holds) is real, non-trivial, well-scoped engineering work that deserves its own dedicated
pass, not something to improvise as a rushed side effect while the actually-requested platform
work sits waiting. Forcing a promotion today would also require picking a subset of the six ready
`verified-gate-a` candidates without a clear selection rule beyond "whatever fits" — exactly the
kind of under-specified judgment call this project's governance conventions ask to be deferred
rather than guessed at.

## Resume predicate

Re-attempt once either: (a) a `.NET`/`Java`/later-platform task genuinely needs a currently-deferred
task promoted (decision 92's trigger), or (b) someone deliberately schedules the
`deferred_task_index` retirement-mechanism code change as its own task. At that point, re-run the
dependency-readiness scan (the method used here — computing the durably-closed set and checking
every deferred record's `dependencies` against it, while excluding candidates whose own task_id is
already durably closed or catalog-marked `REROUTED`/`DEFERRED_WITH_REASON` — reproduces cleanly)
and implement the loader extension from Finding 3 before attempting any retirement.
