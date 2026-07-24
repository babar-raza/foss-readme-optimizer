# Production system reassessment and redesign

Governed by `plans/GOVERNANCE.md`; registered as one mission under the existing
`readme-agent supervise --mission-task-graph` machinery (`DD-REUSE-MISSION-MACHINERY` below) —
this document does not replace `plans/master.md`/`plans/requirements.md`/the
`LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` mission graph; it diagnoses and redesigns that mission's
own execution-control machinery. Companion file: `production-system-redesign.state.json` (machine-
readable taskcard/finding/decision index, kept in lockstep with this document).

## 1. Executive verdict

**REASSESSMENT_COMPLETE, EXECUTION_NOT_AUTHORIZED** (execution begins only as each phase below is
separately worked, per the mission machinery's own evidence-gated transitions). The dominant,
well-evidenced root cause is not "weak prompts" or "fragmented architecture" — it is that this
project's own mission authority was split across three artifacts that structurally could not stay
synchronized (the locked task-graph YAML, the hand-authored handover docs, and the durable CAS
mission state), and its own verification oracle (`run_official_checks.py`) was not itself proven
stable under the concurrent-session conditions the project actually operates under. A second,
independent finding shows the same "build a verifier, forget to wire it in" pattern recurring for a
brand-new capability. Findings below are ranked by blast radius, each tagged with an evidence class.

**Update (2026-07-24, same day, before Phase 0 began execution):** three of the five root causes
below were independently closed as a side effect of an unrelated, urgent correctness fix (a
critical package-acquisition-truth bug — see `logs/2026-07-24.md`, commits `76e88b1`..`1551bab`).
`LOCKED-GRAPH-NEVER-RECONCILED` and `STALE-HANDOVER-VS-GIT-HEAD` were reconciled directly (durable
mission state advanced to version 82; the handover trio was finalized/corrected, commit `40c241c`).
`VERIFIER-BUILT-NOT-WIRED` was closed for the one artifact class it was found on (the README-
proposal bundle verifier is now the producer's real acceptance gate, commit `de7ff3d`) — the
broader `DD-VERIFIER-ENFORCEMENT-PARITY` pattern (generalizing this to a `dispatch_gated_effect`-
style gate for other read-derived-evidence classes) remains open as Phase 2 describes it.

**Second update (2026-07-24/25, PRODSYS-P0-T1 in progress):** two further, materially corrective
findings landed. First, `LOCKED-GRAPH-NEVER-RECONCILED`'s remaining live instance (the active
taskcard's own `status: TODO`/`audit_classification: not_attempted`, still stale after multiple
same-day edits to the surrounding file) was found still current and hand-corrected
(`status: IN_PROGRESS`, `audit_classification: partially_done`) — direct, current confirmation the
mechanism-not-automatic gap (`PRODSYS-P1-T3`) is real, not historical. Second, and more
significantly, `OFFICIAL-CHECKS-NONDETERMINISM`'s original 4-attempt historical incident was
independently re-examined and re-verified directly against raw git history and log files: the tree
was never actually frozen during those attempts (ruff-format's own file count climbed
377→378→379 mid-sequence) and the commit cited as "the unchanged tree under test" was made 68
seconds *after* the last attempt finished, not before the first. This is now `PROVEN`, not
`STRONGLY_INFERRED` — see the finding's own updated section below, which also folds in a
controlled, single-process reproduction (7 of 10 planned attempts completed before an unrelated
host restart interrupted the run; all 7 agreed exactly) that is consistent with, though does not by
itself prove, the corrected explanation. A related, newly-surfaced finding
(`MISSION-CLAIM-NO-LEASE-PARITY`) is added on the same pass. `LOG-LAGS-GIT-HEAD`'s test-suite-scoped
remainder and the generalized verifier-enforcement pattern remain open and are this document's
primary remaining scope, now joined by the corrected official-checks fix (evidence-precondition
recording, not a concurrency lock) and claim-lease parity.

## 2. Scope and authority

In scope: the mission-authority/state-binding layer, the taskcard/state-machine layer, the
verification-oracle layer, and the handover/log-currency layer of the
`LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` mission's own execution control. Out of scope: this pass
proposes no change to `docs/safety-model.md`'s two named safety properties (push-blocking,
allow-list), no change to `src/readme_agent/readme/*` presentation logic itself, and no production
credential/GitHub App work (`plans/idea.md`'s own `L8-014` local→act→staging sequencing is
unaffected). Authority for this plan: explicit user request, this session; `plans/master.md`'s
`GOV-023` gate is not touched by this plan (no edit to `master.md` is proposed here).

## 3. Evidence and confidence standard

`PROVEN` / `STRONGLY_INFERRED` / `CLAIMED_UNVERIFIED` / `CONTRADICTED` / `STALE` / `UNKNOWN`,
applied per finding, each with a direct citation.

## 4. Current-system baseline

- **Successful reruns**: commits `76e88b1` (renderer split, byte-identical, all three original
  candidate hashes reproduced) and `ff77c5f`/`de7ff3d` (independent bundle verifier, built then
  wired) — each closed a named blocker cleanly with focused tests. `PROVEN`.
- **Weak/inconsistent rerun**:
  `plans/investigations/evidence/level8-local-immutable-snapshot-and-facts-2026-07-24/official-checks{,-attempt-2,-attempt-3,-attempt-4}.log`
  — 4 consecutive `run_official_checks.py` runs against the same committed tree: attempt 1 fails
  ruff-format on one file and one pytest test; attempt 2 passes clean; attempt 3 fails ruff-format
  on a *different* file, pytest passes; attempt 4 passes clean. `PROVEN` (direct log read + `git
  log` confirms no source drift between attempts). A further, directly-observed instance this same
  session: a `run_official_checks.py` invocation launched alongside one concurrent live-network
  background process took materially longer (order of 15-20 minutes vs. the usual ~2) before
  completing successfully — consistent with, though not itself proof of, the concurrency
  hypothesis below. `STRONGLY_INFERRED` (single additional data point, not a controlled
  reproduction).
- **Rerun/resume path**: `plans/codex/handover/{HANDOVER.md,CONTINUE.md,state.json}` — the designed
  mechanism for a new session to resume the mission. As of this document's own drafting, both were
  stale-on-arrival (citing HEAD `c3dcdc7` and two blockers as `OPEN` that were already closed) —
  now reconciled (commit `40c241c`, dated amendment banners + corrected `state.json`).
- **Current relevant implementation**: `src/readme_agent/supervisor/mission_control.py` — a real,
  CAS-backed (`StateBackend.save`/`load` with optimistic-concurrency retry,
  `mission_control.py:167-192`), evidence-gated (`transition_task()` rejects a transition into
  `IMPLEMENTED`/`VERIFIED`/`SCORED`/`CLOSED` with no `evidence_refs`) task state machine, driven by
  the declarative, git-tracked `plans/investigations/control/level8-autonomous-mission-task-
  graph.yaml`. Confirmed directly this session: the durable state lives on `origin` as
  `refs/readme-agent-state/mission__LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`, fetched on demand by
  `GitStateBackend` (not a local ref — an earlier local-only `for-each-ref` check wrongly suggested
  it was missing before this was traced to ground).
- **Expected vs. actual**: expected — one queryable, current source of truth for "what has this
  mission actually completed." Actual (at the point this reassessment began) — three disagreeing
  surfaces (see `LOCKED-GRAPH-NEVER-RECONCILED`/`STALE-HANDOVER-VS-GIT-HEAD` below); partially
  resolved same-day as a side effect of unrelated work, general mechanism still not durable.

## 5. Root causes

### `LOCKED-GRAPH-NEVER-RECONCILED` — P0, `PROVEN`, **reconciled 2026-07-24 for this snapshot; mechanism still not durable**

- **Symptom**: the locked task-graph YAML's `requirement_coverage` block and per-taskcard
  `status:`/`audit_classification:` fields are seeded once and never mechanically re-synced after
  `plans/requirements.md` changes, even though the file is the project's own declared "audit
  record."
- **Immediate cause**: `mission_control.py::_load_or_initialize()` reads each taskcard's `status`
  from the YAML only once, to seed durable state the first time a mission key has no CAS record yet
  (lines 75-113); every subsequent transition mutates only the separate `MissionExecutionStateV1`
  record in the Git-ref CAS backend — nothing ever writes back into the YAML file automatically.
  `requirement_coverage` is a *separate* embedded block, regenerated only by an explicit run of
  `scripts/governance/build_level8_requirement_taskcard_coverage.py` — there is no CI/pre-commit
  gate forcing that regeneration when `requirements.md` changes.
- **Root cause**: the project declared one file "the audit record" *and* built a separate,
  correctly-designed durable state machine for the same data, with no mechanism reconciling the two
  after the first read, and a *second* piece of embedded, requirements.md-derived data
  (`requirement_coverage`) with its own independent, manual regeneration trigger.
- **Structural weakness**: this project has already solved this exact class of problem elsewhere —
  hash-coupled staleness detection (`facts_hash`, `VER-004`) — but had not applied that pattern to
  its own mission-authority artifacts.
- **Why existing controls failed**: `GOV-017` (investigate before overwriting) and `GOV-022` (each
  wave reconciles the prior one) both assume an agent reads the record before trusting it — neither
  requires the record's own producer to prove it's still current, and nothing files an alert when
  the locked YAML and the CAS state diverge.
- **Blast radius**: every future session that "reads the graph to know what to work on" gets a
  wrong answer for any task that has progressed since the graph was authored.
- **2026-07-24 reconciliation (this snapshot only, not a durable fix)**: `requirements.md` gained a
  new row (`FACT-014`) as an unrelated side effect of the package-truth correction; a hard-coded
  `test_mission_control.py` assertion (`total_requirement_rows == 391`) then failed real
  `run_official_checks.py`, correctly catching the staleness this finding describes.
  `build_level8_requirement_taskcard_coverage.py --check`/(no flag) was run, confirming and then
  curing the drift (392 rows, mandatory unchanged at 368); `supervise --mission-action evaluate`
  was then run to push the reconciled `graph_sha256` into durable state (version 81 → 82). This
  proves the *existing* tools work correctly when run — it does not yet make running them
  *automatic* on every `requirements.md`/graph edit, which is this root cause's real remaining
  scope (`PRODSYS-P1-T3`).

### `STALE-HANDOVER-VS-GIT-HEAD` — P0, `PROVEN`, **corrected 2026-07-24 for this snapshot; mechanism still hand-authored**

- **Symptom**: `plans/codex/handover/state.json`/`HANDOVER.md`/`CONTINUE.md` presented themselves
  as current against HEAD `c3dcdc7`, with two blockers marked `OPEN`, while real git history
  (`76e88b1`, `ff77c5f`) had already closed exactly those two blockers before a continuing session
  began working from them. A second, independent discovery this same session: the entire handover
  trio had never actually been committed at all — it existed only as untracked working-tree files,
  despite the authoring commit's own message claiming it "replaces" the prior eight-file set.
- **Immediate cause**: hand-authored Markdown/JSON files with no generation timestamp check against
  `git rev-parse HEAD`, no hash binding to the mission's own durable CAS state, and (compounding)
  no commit ever actually landing the intended replacement.
- **Root cause**: same class as `LOCKED-GRAPH-NEVER-RECONCILED` — a second, independently
  hand-maintained "authoritative snapshot" artifact with no enforced freshness contract, this time
  authored by a human/agent narrative process rather than a declarative input file, and in this
  instance not even reliably *committed*.
- **Structural weakness**: this repo already names the general failure mode in `plans/master.md`
  decision #37 ("no responsive counterparty will ever arrive to resolve a conflict... recon is the
  primary arbiter") but had not applied it to its own handover artifacts.
- **Blast radius**: a session trusting the handover docs as the fast path (rather than querying real
  state) inherits stale blocker status and could re-attempt already-closed work, or worse, report a
  blocker as open in a new plan — this nearly happened this same session before direct `git`/CAS
  verification caught it.
- **2026-07-24 reconciliation (this snapshot only)**: the trio was actually committed for the first
  time (`40c241c`), `state.json` was corrected (HEAD, authority hashes, durable state version,
  resolved/open blockers, evidence paths), and `HANDOVER.md`/`CONTINUE.md` each got a dated
  amendment banner pointing to `state.json`/`logs/` rather than a full hand-rewrite of the ~800-line
  narrative bodies (judged disproportionate and itself staleness-prone — see `DD-SINGLE-AUTHORITY`
  below, which replaces the hand-authored format entirely rather than re-authoring it repeatedly).

### `LOG-LAGS-GIT-HEAD` — P1, `PROVEN`, **partially closed this session, pattern remains**

- **Symptom**: `logs/2026-07-24.md`'s entries can lag real commits by a session or more if a session
  ends without appending one. Directly observed and corrected twice this same session (a catch-up
  entry for `76e88b1`/`ff77c5f`, commit `c57423c`; and routine per-phase entries for every
  subsequent commit through `40c241c`) — proving the discipline is followable when actively
  practiced, not proving it is enforced.
- **Root cause**: same reconciliation gap as the two findings above, at a third independent layer —
  `logs/README.md`'s own text calls this "the authoritative dated history," but nothing enforces
  that a shard is appended in the same commit/session as the work it describes.
- **Structural weakness**: the *third* place the same "declared authoritative, not mechanically kept
  current" pattern recurs (graph YAML, handover docs, dated log) — strong evidence this is a
  systemic pattern in the mission's bookkeeping design, not three unrelated slips.
- **Blast radius**: lower than the two above (the log is consulted for narrative context, not the
  primary resume mechanism), but undermines its own stated purpose if not cross-checked against
  `git log` directly.

### `OFFICIAL-CHECKS-NONDETERMINISM` — P0, `PROVEN` (occurrence and, now, cause) — **corrected 2026-07-24/25; root cause is evidence mislabeling, not concurrency**

- **Symptom (original)**: 4 consecutive `run_official_checks.py` runs against a tree claimed to be
  "unchanged, already-committed" produced 4 different results (see §4).
- **Corrected root cause (`PROVEN`, re-verified directly against raw git history and log files,
  not merely quoted from a prior pass)**: the tree was never actually frozen during those 4
  attempts. `ruff format --check .`'s own reported file-scan total climbed mid-sequence — 377 files
  (attempt 2) → 378 files, one reformatted (attempt 3) → 379 files (attempt 4) — meaning real `.py`
  files materialized in the tree *between* attempts. The commit later cited as "the unchanged tree
  under test" (`5e31f9c1`) has timestamp `2026-07-24T14:53:31+05:00`; attempt 4's own log file has
  mtime `14:52:23+05:00` — the commit was made **68 seconds after the last attempt finished**, not
  before the first one started. `run_official_checks.py` has no concept of "the tree must be
  clean/committed before this run counts as evidence" and never records `git status --porcelain` at
  invocation time — so a dirty, actively-edited-mid-run tree produced a log that was later cited as
  proof about a specific commit it never actually tested. The two `ruff format` failures map exactly
  onto files that were genuinely being edited in that window, not to flaky tooling.
- **Concurrency verdict for this specific incident**: `DISCONFIRMED`. The edit/re-run gaps are
  tight-but-plausible within one continuous single-session working pattern (down to 44 seconds
  apart); no other session's commit falls inside the window. Concurrency remains real and
  documented elsewhere in this repo's history (a Decision Ledger number collision, an uncommitted
  cross-session edit breaking another session's tests — `logs/2026-07-22.md`), and remains a
  plausible **amplifier** for a *future* incident of this same class, but it was not the cause of
  *this* one.
- **Corroborating, not confirmatory, further evidence**: a controlled, single-process reproduction
  (`PRODSYS-P0-T1`, this same pass) ran the real official-checks suite repeatedly with no concurrent
  session activity; 7 of the planned 10 attempts completed before an unrelated host restart
  interrupted the run, and all 7 agreed exactly (`exit 0`, identical pytest counts every time — see
  `plans/investigations/evidence/prodsys-official-checks-nondeterminism/reproduction-verdict.json`).
  This is consistent with "the checks are stable when the tree is genuinely stable," matching the
  corrected explanation, but a 7/10 partial run does not by itself prove the general case, and is
  recorded honestly as partial, not padded to a false 10/10.
- **What remains genuinely open (not resolved by this correction)**: one pytest failure in the
  original attempt 1 (`test_specialists.py::TestCommunityFilesPresentationSpecialist::
  test_first_run_...`) traces through code that is byte-identical between the pre-attempt-1 state
  and the final commit — ruling out "a committed code fix" as the explanation, but not distinguishing
  an edit-then-revert cycle mid-session from a genuine transient test-isolation issue. The
  intermediate dirty-tree state that would resolve this no longer exists; recorded as `UNKNOWN`, not
  assumed either way. The controlled reproduction's own elapsed-time swing (400.9s-535.4s, ~33.5%
  across the 7 completed attempts) is a separate, secondary, still-real finding — wall-clock is not
  perfectly stable even where pass/fail correctness is.
- **Structural weakness (revised)**: not "the oracle is unstable under concurrent sessions" as
  originally framed — the oracle's own real defect is narrower and cheaper to fix: **it never records
  its own preconditions**, so a run against an unstable tree cannot be told apart, after the fact,
  from a run against a stable one. `GOV-007`/`GOV-018`'s assumption that a green run "means what it
  says" fails specifically when nobody checks whether the tree was clean at invocation time, not
  because the checks themselves are unreliable.
- **Blast radius**: same as originally assessed (every downstream `IMPLEMENTED`/`VERIFIED` claim
  gated on this oracle), but the fix is now known to be a cheap, targeted precondition-recording
  change (`DD-RECORD-EVIDENCE-PRECONDITIONS`), not a heavier concurrency-control mechanism that the
  disconfirmed hypothesis would have motivated building.

### `MISSION-CLAIM-NO-LEASE-PARITY` — P2, `PROVEN`, new finding this pass

- **Symptom**: live durable mission state (fetched from the real `origin` ref, version 83 as of this
  pass) shows a `claimed_by`/`claimed_at` pair from an earlier session, while multiple commits
  co-authored under a different agent identity did the actual claimed work afterward — the claim
  field never updated to reflect who was really working the task.
- **Immediate cause**: `MissionExecutionStateV1`'s `claim_id`/`claimed_by`/`claimed_at`
  (`src/readme_agent/state/schema.py:399-401`, directly re-read and confirmed this pass) are plain
  nullable strings with **no lease/expiry field** — contrast the sibling per-repo lock
  (`state/git_backend.py`'s `Lock` dataclass, `PRESERVE-REPO-LOCK-LEASE`), which **does** carry
  `leased_until` and a real lease-based compare-and-swap release. `claim_next_task()` silently
  no-ops if a task is already claimed rather than detecting or flagging staleness.
- **Root cause**: the correct pattern (lease + expiry) already exists in this exact codebase, one
  layer down, for a sibling concept (the per-repo lock) — it was just never applied to the
  mission-level claim. An inconsistency within an otherwise-sound pattern, not a missing pattern.
- **Structural weakness**: the mission claim is the one durable-state field this whole redesign
  otherwise treats as trustworthy (`PRESERVE-MISSION-CAS`) — but its own "who is working this and
  since when" field can silently go stale exactly like the handover docs and the task-graph status
  field did, for the identical underlying reason (no freshness contract).
- **Blast radius**: low today (the CAS write path already prevents a literal race at the write
  instant; this is about the claim *field* lying about who/when, not about losing a real write) but
  grows with session count and duration.

### `VERIFIER-BUILT-NOT-WIRED` — P1, `PROVEN` — **closed for the one artifact class found; pattern-generalization remains open**

- **Symptom (as found)**: commit `ff77c5f` built `verification/readme_proposal_bundle.py::
  verify_readme_proposal_bundle()` specifically to close "producer writes its own independent-
  review.json" — but at the time, `grep -rn "verify_readme_proposal_bundle"` across
  `src/readme_agent/supervisor/`, `orchestrator.py`, `commands*.py`, `cli.py` returned zero matches.
  Reachable only from its own unit test and a standalone script.
- **Root cause**: this project has an established, structurally-enforced pattern for exactly this
  problem — `VER-001`'s `verify_readme_candidate`/`commit_readme_write` gate, enforced via
  `dispatch_gated_effect()` so a candidate cannot be committed without passing through the real
  verifier — but the new bundle verifier was built as a plain importable function with no
  equivalent enforced call site.
- **2026-07-24 closure (this artifact class)**: `plans/investigations/tools/
  collect_local_readme_proposal_evidence.py` (the one real caller/producer for this artifact class)
  no longer computes its own `reviewer_checks`/verdict — it writes the core bundle files, then
  calls the real `verify_readme_proposal_bundle()` and persists *that* verdict/checks/failures
  under the real `VERIFIER_IDENTITY` (commit `de7ff3d`). Verified: a smoke test against the
  pre-fix, stale evidence bundle correctly produced `verdict: rejected` (the verifier caught real
  staleness in its own first live exercise) — proof the wiring is load-bearing, not decorative.
- **Remaining, generalized scope** (`PRODSYS-P2`): this closure is scoped to the one producer script
  that existed. The broader pattern this finding names — "a verifier with no *structurally*
  enforced call site, regardless of artifact class" — has no general prevention yet. The next
  read-derived-evidence verifier built in this project could reproduce the same gap unless the
  pattern is generalized (a capability-registry-level convention, mirroring `dispatch_gated_effect`)
  rather than fixed one call site at a time.

### `VER009-REPROOF-OWED` — P2, `PROVEN`, narrower/mostly-closed

- **Symptom**: `logs/2026-07-23.md` — heterogeneous (.NET/Python/C++) runs previously returned
  `CONVERGED_NO_CHANGE`/exit 0 while their `readme_presentation` specialist had recorded a rejected
  candidate. Root-caused to `supervisor/convergence.py::final_status()` only consulting the planner
  task graph, not specialist results outside it; fixed, new `VER-009` added.
- **Current status**: `plans/requirements.md`'s own text says the requirement "remains `PARTIAL`
  until the previously false-success heterogeneous cases are rerun under production-like
  conditions" — an explicitly acknowledged, still-open re-proof obligation, not a currently-active
  defect.
- **Why lower severity here**: the fix is real and unit-tested; this is validation debt (an owed
  re-run), not a live inconsistency generator.

## 6. Capabilities to preserve (must not be weakened by this redesign)

| ID | Behavior | Evidence | Why it matters | Regression risk if mishandled |
|---|---|---|---|---|
| `PRESERVE-TASKGRAPH` | Ordinary capability-dispatch `TaskGraph`/`Task` — proven, tested, unrelated to mission bookkeeping | `task.py`; existing test suite | Powers every non-mission `supervise` run today | A redesign must not conflate this with the separate mission taskcard system |
| `PRESERVE-VER001-GATE` | `dispatch_gated_effect()`-enforced independent verification for `commit_readme_write`/`open_presentation_pr` | `plans/requirements.md` `VER-001` row | The one proven pattern this redesign explicitly extends, not replaces | Do not build a second, incompatible enforcement mechanism |
| `PRESERVE-MISSION-CAS` | CAS-backed, evidence-gated `MissionExecutionStateV1` transitions | `mission_control.py`, directly re-read and exercised this session (`evaluate` calls, version 81→82→83) | Already the correct design for "one durable, race-safe source of truth" | A rewrite-from-scratch would be strictly worse than reusing this |
| `PRESERVE-REPO-LOCK-LEASE` | `state/git_backend.py`'s `leased_until`/CAS-delete per-repo lock (`Lock` dataclass) | Directly re-read this session | The proven lease pattern `MISSION-CLAIM-NO-LEASE-PARITY`'s fix should copy, not reinvent | Don't build a second, incompatible lease mechanism |
| `PRESERVE-RENDERER-SPLIT` | `document_renderer.py` split into focused modules, byte-identical candidate hashes preserved | commit `76e88b1` | Real, already-verified no-monolith fix | Must not be re-touched as part of this redesign |
| `PRESERVE-BUNDLE-VERIFIER-LOGIC` | `verify_readme_proposal_bundle()`'s re-derivation logic (rebuilds candidate from scratch, live ground-truth check) | `readme_proposal_bundle.py`, commits `ff77c5f`/`de7ff3d` | The verification *logic* is sound and now wired for its own artifact class | Generalizing the wiring pattern must reuse this function, not rewrite it |
| `PRESERVE-LOGS-SHARD-TOOLING` | `scripts/governance/append_log_entry.py` + dated shard convention | `logs/README.md`, script source | Good, already-working discipline; the gap is currency, not mechanism | Don't replace the tool — fix when it's invoked |
| `PRESERVE-REQUIREMENT-COVERAGE-TOOL` | `scripts/governance/build_level8_requirement_taskcard_coverage.py`, idempotent, `--check` mode | Directly exercised this session, correctly caught and cured real drift | Already the correct mechanism; the gap is automatic invocation, not the tool | Don't replace it — wire it into a gate |
| `PRESERVE-SAFETY-INVARIANTS` | Push-blocking + allow-list, completely out of scope | `docs/safety-model.md`, `tests/unit/test_gitsafety.py` | Non-negotiable per repo governance | This plan touches neither |

## 7. What must be redesigned

1. Reused, not-yet-automatic reconciliation for `LOCKED-GRAPH-NEVER-RECONCILED` — turn the proven
   manual tools into a gate.
2. A generated, never-hand-edited handover snapshot for `STALE-HANDOVER-VS-GIT-HEAD`.
3. A time-boxed, controlled root-cause investigation (not a guessed fix) for
   `OFFICIAL-CHECKS-NONDETERMINISM`.
4. A generalized, capability-registry-level enforcement pattern for `VERIFIER-BUILT-NOT-WIRED`'s
   class of gap, extending `PRESERVE-VER001-GATE` rather than duplicating it.
5. `VER-009`'s owed heterogeneous re-proof.

## 8. Design decisions

```
design_decision:
  decision_id: DD-SINGLE-AUTHORITY
  problem_addressed: LOCKED-GRAPH-NEVER-RECONCILED, STALE-HANDOVER-VS-GIT-HEAD
  chosen_design: Mission CAS state (mission_control.py) is sole runtime authority; the locked YAML is seed-only, its requirement_coverage kept current by a gate (not a habit); handover docs become generated from live CAS+HEAD, never hand-edited again.
  alternatives_considered: [Keep hand-authored handover docs with a "last verified" convention (rejected -- convention, not enforcement, and this session directly proved the convention alone fails: the trio was stale AND never even committed); make the locked YAML itself the mutated source of truth (rejected -- defeats its own locked/reviewable governance purpose, high merge-conflict risk across concurrent sessions)]
  reason: Reuses an already-correct, already-tested mechanism (proven again this session via a real `evaluate` call); eliminates the staleness class by construction rather than by discipline.
  preserved_behavior: [PRESERVE-MISSION-CAS, PRESERVE-TASKGRAPH]
  tradeoffs: Handover docs lose "written narrative by a thoughtful prior session" texture unless the generator is designed to still produce prose, not just JSON.
  risks: [R-NARRATIVE-LOSS]
  migration_impact: One-time reconciliation of current stale docs is already done for this snapshot (commit 40c241c); the generator itself (PRODSYS-P1-T2) still needs building so future snapshots don't require hand-editing again.
  verification: [T1.1, T1.2, T1.3, T4.1]
  related_finding_ids: [LOCKED-GRAPH-NEVER-RECONCILED, STALE-HANDOVER-VS-GIT-HEAD, LOG-LAGS-GIT-HEAD]
  related_task_ids: [PRODSYS-P1-T1, PRODSYS-P1-T2, PRODSYS-P1-T3, PRODSYS-P4-T1, PRODSYS-P4-T2]

design_decision:
  decision_id: DD-REUSE-MISSION-MACHINERY
  problem_addressed: Avoiding a fourth parallel state-tracking mechanism for this redesign's own progress
  chosen_design: Register this redesign as one mission (or a scoped taskcard set within the existing LEVEL8 mission) in the existing mission_control.py/MissionTaskStatus machinery.
  alternatives_considered: [Build a separate literal state-template schema for this redesign's own tracking (rejected -- GOVERNANCE.md rule 8, recreates the diagnosed root cause)]
  reason: The existing machinery already satisfies every structural need (CAS durability, evidence-gated transitions, explicit reopen/regress, no-implicit-completion).
  preserved_behavior: [PRESERVE-MISSION-CAS]
  tradeoffs: none material
  risks: []
  migration_impact: none -- additive
  verification: Tracked live via `supervise --mission-action status`
  related_finding_ids: []
  related_task_ids: [PRODSYS-P1-T1]

design_decision:
  decision_id: DD-VERIFIER-ENFORCEMENT-PARITY
  problem_addressed: VERIFIER-BUILT-NOT-WIRED (generalized pattern, beyond the one already-closed instance)
  chosen_design: A capability-registry-level convention -- any capability whose manifest declares it consumes/produces "independent_verification"-class evidence must be dispatched only through a wrapper mirroring dispatch_gated_effect()'s precheck/ledger shape, not a bespoke ad hoc gate per artifact class.
  alternatives_considered: [Fix each future instance one call site at a time as found (rejected as the sole strategy -- this is the second occurrence of the identical gap; a third is a process failure, not bad luck); a lint rule flagging any new verify_* function with no detected call site (kept as a cheap interim Phase-2 measure, not a substitute for the structural fix)]
  reason: Reuses a proven, already-live pattern (PRESERVE-VER001-GATE) instead of inventing a second enforcement mechanism, and prevents recurrence structurally rather than by vigilance.
  preserved_behavior: [PRESERVE-VER001-GATE, PRESERVE-BUNDLE-VERIFIER-LOGIC]
  tradeoffs: Heavier lift than a per-instance fix; staged accordingly (cheap lint/CI gate first, full registry-level wiring later).
  risks: [R-HIDDEN-DEFECTS-SURFACE]
  migration_impact: none for the already-closed instance (de7ff3d); future verifier additions must declare and route through the new convention.
  verification: [T2.1, T2.2, T5.1]
  related_finding_ids: [VERIFIER-BUILT-NOT-WIRED]
  related_task_ids: [PRODSYS-P2-T1, PRODSYS-P2-T2]

design_decision:
  decision_id: DD-INVESTIGATE-BEFORE-LOCKING
  problem_addressed: OFFICIAL-CHECKS-NONDETERMINISM
  chosen_design: Time-boxed, controlled-reproduction root-cause investigation (Phase 0) before designing any concurrency-control mechanism.
  alternatives_considered: [Assume concurrency and build a lock immediately (rejected -- would have been the WRONG fix, confirmed after investigation: the concurrency hypothesis is now DISCONFIRMED for the historical incident that motivated it)]
  reason: This plan's own evidence-class standard forbids treating an inferred cause as proven -- vindicated by outcome, not just by principle.
  preserved_behavior: run_official_checks.py itself is not replaced, only its invocation discipline
  tradeoffs: Delayed a fix until RCA completed; the delay was worth it -- a concurrency lock would have added real complexity to fix a cause that turned out not to be the real one.
  risks: []
  migration_impact: none
  verification: [T0.1]
  related_finding_ids: [OFFICIAL-CHECKS-NONDETERMINISM]
  related_task_ids: [PRODSYS-P0-T1]

design_decision:
  decision_id: DD-RECORD-EVIDENCE-PRECONDITIONS
  problem_addressed: OFFICIAL-CHECKS-NONDETERMINISM (corrected root cause)
  chosen_design: run_official_checks.py records `git status --porcelain` (clean/dirty + file list) at invocation start into its own log output; a dirty-tree run is explicitly labeled as such and must never be cited as evidence about a specific commit's state.
  alternatives_considered: [A full concurrency lock over official-checks invocations (rejected -- the concurrency hypothesis was DISCONFIRMED for the incident that motivated it; building heavy machinery for a disconfirmed cause would be exactly the "solve the wrong problem" failure mode DD-INVESTIGATE-BEFORE-LOCKING exists to avoid. If a genuinely concurrent double-run is later observed with real evidence, a lock can be added then.)]
  reason: Directly targets the PROVEN mechanism (a labeling gap -- evidence not recording its own preconditions), not a plausible-but-disconfirmed one.
  preserved_behavior: run_official_checks.py's actual check logic is unchanged; only its logged preconditions gain a new field.
  tradeoffs: none material -- cheap, additive, low-risk.
  risks: []
  migration_impact: none -- new log field only.
  verification: [T3.1]
  related_finding_ids: [OFFICIAL-CHECKS-NONDETERMINISM]
  related_task_ids: [PRODSYS-P3-T1]

design_decision:
  decision_id: DD-CLAIM-LEASE-PARITY
  problem_addressed: MISSION-CLAIM-NO-LEASE-PARITY
  chosen_design: Add `leased_until` to MissionExecutionStateV1's claim fields, mirroring git_backend.py's own Lock dataclass; make claim_next_task() detect an expired or clearly-stale claim and either reassign with a logged warning or surface staleness explicitly instead of silently no-op-ing.
  alternatives_considered: [A full session-identity/mutex system across agent tools (rejected -- heavier than the evidence calls for; the existing CAS write-path already prevents a literal race at the write instant, this only closes the "claim field lies for hours/days" gap)]
  reason: Copies an already-proven, already-in-this-exact-codebase pattern (the per-repo lock's lease) rather than inventing a new one -- GOVERNANCE.md rule 8.
  preserved_behavior: [PRESERVE-MISSION-CAS, PRESERVE-REPO-LOCK-LEASE]
  tradeoffs: none material.
  risks: []
  migration_impact: Schema addition to MissionExecutionStateV1; existing durable state without the field defaults to no-lease (treated as always-stale-checkable, never a hard break).
  verification: [T1.4]
  related_finding_ids: [MISSION-CLAIM-NO-LEASE-PARITY]
  related_task_ids: [PRODSYS-P1-T4]
```

## 9. Phased implementation plan

```
phase: PRODSYS-P0 -- Baseline and safety net
  objective: Establish a documented, reproducible before-state and investigate the verification oracle before trusting it further.
  root_causes_addressed: [OFFICIAL-CHECKS-NONDETERMINISM]
  preserved_capabilities: [PRESERVE-MISSION-CAS, PRESERVE-TASKGRAPH]
  entry_conditions: [This plan approved]
  task_ids: [PRODSYS-P0-T1, PRODSYS-P0-T2]
  exit_conditions: [official-checks non-determinism root-caused (DONE -- evidence mislabeling, not concurrency, PROVEN) or bounded+documented; a frozen snapshot of all three current "truth" artifacts exists]
  rollback_conditions: [N/A -- read-only investigation phase]
  status: PRODSYS-P0-T1_SUBSTANTIALLY_COMPLETE

phase: PRODSYS-P1 -- Authority, contracts, and state
  objective: Make mission CAS state the sole runtime authority; demote the locked YAML's requirement_coverage to a gated-regeneration artifact; register this redesign under the existing mission machinery; close the mission-claim lease gap.
  root_causes_addressed: [LOCKED-GRAPH-NEVER-RECONCILED, STALE-HANDOVER-VS-GIT-HEAD, MISSION-CLAIM-NO-LEASE-PARITY]
  preserved_capabilities: [PRESERVE-MISSION-CAS, PRESERVE-REQUIREMENT-COVERAGE-TOOL, PRESERVE-REPO-LOCK-LEASE]
  task_ids: [PRODSYS-P1-T1, PRODSYS-P1-T2, PRODSYS-P1-T3, PRODSYS-P1-T4]
  exit_conditions: [A generated handover snapshot command exists and passes against live state; the coverage-regeneration tool runs automatically (not just manually) on requirements.md/graph drift; the mission claim field has lease/expiry parity with the sibling repo lock]
  rollback_conditions: [Revert new diagnostic/generator commands only -- no schema changes to roll back]
  status: NOT_STARTED

phase: PRODSYS-P2 -- Verifier-enforcement generalization
  objective: Turn the one already-closed VERIFIER-BUILT-NOT-WIRED instance into a structural, registry-level convention that prevents recurrence for the next verifier built.
  root_causes_addressed: [VERIFIER-BUILT-NOT-WIRED]
  preserved_capabilities: [PRESERVE-VER001-GATE, PRESERVE-BUNDLE-VERIFIER-LOGIC]
  task_ids: [PRODSYS-P2-T1, PRODSYS-P2-T2]
  exit_conditions: [A capability declaring independent_verification-class evidence cannot be dispatched outside the enforced wrapper; the existing readme-proposal-bundle wiring is migrated to the same wrapper for consistency, not left as a bespoke exception]
  rollback_conditions: [Feature-flag the new gate off if it blocks unrelated in-flight work unexpectedly]
  status: NOT_STARTED

phase: PRODSYS-P3 -- Validation, evidence, and recovery
  objective: Resolve or bound OFFICIAL-CHECKS-NONDETERMINISM for real; close the VER-009 re-proof debt.
  root_causes_addressed: [OFFICIAL-CHECKS-NONDETERMINISM, VER009-REPROOF-OWED]
  task_ids: [PRODSYS-P3-T1, PRODSYS-P3-T2]
  exit_conditions: [10 consecutive official-checks runs against one unchanged tree agree; VER-009's heterogeneous cases re-run clean under production-like conditions]
  rollback_conditions: [If RCA inconclusive, ship containment (retry-with-quarantine) rather than block indefinitely]
  status: NOT_STARTED

phase: PRODSYS-P4 -- Migration and compatibility
  objective: Confirm DD-SINGLE-AUTHORITY holds for the general case, not just this one snapshot -- prove the generator reproduces what was hand-corrected this session.
  root_causes_addressed: [LOCKED-GRAPH-NEVER-RECONCILED, STALE-HANDOVER-VS-GIT-HEAD, LOG-LAGS-GIT-HEAD]
  task_ids: [PRODSYS-P4-T1, PRODSYS-P4-T2]
  exit_conditions: [The PRODSYS-P1-T2 generator, run against current real state, produces a handover snapshot matching state.json's own hand-corrected content from commit 40c241c in every field that is mechanically derivable]
  rollback_conditions: [Pure doc correction -- trivially revertible]
  status: NOT_STARTED

phase: PRODSYS-P5 -- E2E, pilots, and rollout
  objective: Live-prove the unified authority and the concurrency-safety finding.
  task_ids: [PRODSYS-P5-T1, PRODSYS-P5-T2]
  exit_conditions: [Live `supervise --mission-action status` output independently cross-checked against direct git/CAS inspection and matches; a deliberate overlapped-rerun pilot no longer reproduces OFFICIAL-CHECKS-NONDETERMINISM]
  rollback_conditions: [Roll back P0-P3 changes if pilot disproves the design]
  status: NOT_STARTED

phase: PRODSYS-P6 -- Final reconciliation and closure
  objective: Independent adversarial review; reconcile requirements.md L8-0xx rows and master.md against real delivered state.
  task_ids: [PRODSYS-P6-T1, PRODSYS-P6-T2]
  exit_conditions: [Independent review passes with no material finding; GOV-022-style reconciliation recorded]
  rollback_conditions: [N/A -- closure phase]
  status: NOT_STARTED
```

## 10. Taskcard ledger (16 taskcards, each tied to a named root cause)

*(Corrected from the reviewed draft's "12" — the phase table above and the dependency graph in §11
both reference 16 distinct task IDs (15 from the original authoring pass, plus `PRODSYS-P1-T4`
added when `MISSION-CLAIM-NO-LEASE-PARITY` was found); this is the accurate count, not a
re-scoping.)*

```
taskcard:
  task_id: PRODSYS-P0-T1
  phase_id: PRODSYS-P0
  title: Reproduce and root-cause official-checks non-determinism under controlled conditions
  objective: Determine whether OFFICIAL-CHECKS-NONDETERMINISM is caused by concurrent-workspace access, a ruff/pytest cache defect, or a Windows filesystem-ordering issue -- with direct evidence, not inference.
  root_cause_ids: [OFFICIAL-CHECKS-NONDETERMINISM]
  design_decision_ids: [DD-INVESTIGATE-BEFORE-LOCKING, DD-RECORD-EVIDENCE-PRECONDITIONS]
  requirements: []
  owner_role: implementer
  reviewer_role: independent-verifier
  allowed_paths: [plans/investigations/evidence/prodsys-official-checks-nondeterminism/, plans/investigations/tools/measure_official_checks_reproducibility.py]
  forbidden_paths: [src/readme_agent/]
  dependencies: []
  preconditions: [This plan approved]
  implementation_steps: [DONE for the root-cause half -- direct re-examination of the 4 original historical logs plus git history (file-count climb 377->378->379, commit timestamp 68s after the last attempt) independently confirmed the cause is evidence mislabeling (dirty tree, uncaptured), not concurrency. PARTIAL for the fresh-reproduction half -- measure_official_checks_reproducibility.py built and run for 10 sequential single-process attempts; 7 completed (all agreeing exactly) before an unrelated host restart killed the run. Remaining, optional: a full clean 10/10 rerun would strengthen but is not required to close this taskcard, since the corrected root cause does not depend on it]
  schemas_or_contracts: []
  migration_steps: []
  focused_tests: []
  integration_tests: []
  regression_tests: []
  negative_controls: [A run with a second process deliberately writing to the same tree mid-check, to test whether that alone reproduces the symptom -- not yet run, now lower priority given the disconfirmed concurrency hypothesis]
  e2e_or_pilot_proof: [7/7 completed single-process attempts agreed exactly (partial, not the full 10x target)]
  observability_and_evidence: [plans/investigations/evidence/prodsys-official-checks-nondeterminism/reproduction-verdict.json (honest partial result, interruption cause recorded), partial-run-2026-07-24-interrupted-by-restart.log, plans/investigations/tools/measure_official_checks_reproducibility.py]
  rollback: N/A -- investigation only, no code change
  acceptance_criteria: [A named cause is PROVEN or the hypothesis is explicitly left STRONGLY_INFERRED/UNKNOWN with a documented containment recommendation]
  proof_target: 10/10 consistent single-process runs (achieved 7/10 before interruption; root cause independently PROVEN via a separate, direct historical-log re-examination that does not depend on the full 10x completing)
  current_state: IMPLEMENTED
  next_transition: VERIFIED once an independent reviewer (not this pass's own author) re-confirms the git-timestamp/file-count evidence chain

taskcard:
  task_id: PRODSYS-P0-T2
  phase_id: PRODSYS-P0
  title: Freeze a checksummed snapshot of the three current "truth" artifacts before touching any of them
  objective: Establish a before-state so every later phase's diff is provable, not asserted.
  root_cause_ids: [LOCKED-GRAPH-NEVER-RECONCILED, STALE-HANDOVER-VS-GIT-HEAD, LOG-LAGS-GIT-HEAD]
  design_decision_ids: [DD-SINGLE-AUTHORITY]
  requirements: []
  owner_role: implementer
  reviewer_role: independent-verifier
  allowed_paths: [plans/investigations/evidence/prodsys-baseline-truth-snapshot/]
  forbidden_paths: [plans/investigations/control/, plans/codex/handover/]
  dependencies: []
  preconditions: [This plan approved]
  implementation_steps: [Copy the current level8-autonomous-mission-task-graph.yaml, the handover trio, and a `supervise --mission-action status` capture into the evidence directory with SHA-256 checksums and a timestamp]
  schemas_or_contracts: []
  migration_steps: []
  focused_tests: []
  integration_tests: []
  regression_tests: []
  negative_controls: []
  e2e_or_pilot_proof: []
  observability_and_evidence: [plans/investigations/evidence/prodsys-baseline-truth-snapshot/*, sha256sums.txt]
  rollback: N/A -- read-only snapshot
  acceptance_criteria: [Snapshot exists, checksummed, referenced by every later phase's before/after diff]
  proof_target: One complete, checksummed snapshot
  current_state: TODO
  next_transition: READY on plan approval

taskcard:
  task_id: PRODSYS-P1-T1
  phase_id: PRODSYS-P1
  title: Register this redesign's own progress under the existing mission machinery
  objective: Avoid inventing a fourth parallel tracking mechanism for this plan's own execution.
  root_cause_ids: []
  design_decision_ids: [DD-REUSE-MISSION-MACHINERY]
  requirements: []
  owner_role: implementer
  reviewer_role: independent-verifier
  allowed_paths: [plans/investigations/control/level8-autonomous-mission-task-graph.yaml]
  forbidden_paths: [plans/master.md]
  dependencies: []
  preconditions: [PRODSYS-P0-T2 snapshot exists]
  implementation_steps: [Add the PRODSYS-* taskcards as a governed extension to the existing locked graph's taskcard list, or as a clearly-scoped sibling file consumed by the same mission_control.py loader -- decide based on whether the existing "mechanism_locked" contract permits additive taskcards without a full re-lock; document the choice inline]
  schemas_or_contracts: [MissionTaskGraphV1, TaskCardV1 -- no schema change, additive data only]
  migration_steps: []
  focused_tests: [New: the extended graph still loads via load_mission_graph() and passes its existing schema/acyclic validation]
  integration_tests: []
  regression_tests: [Existing test_mission_control.py suite unaffected]
  negative_controls: [A malformed additive taskcard is rejected by the same validation that rejects any other malformed taskcard]
  e2e_or_pilot_proof: [supervise --mission-action status reflects the new taskcards]
  observability_and_evidence: [Updated graph file itself, a diff against the P0-T2 snapshot]
  rollback: Revert the graph-file diff
  acceptance_criteria: [PRODSYS taskcards are visible to and manageable by the existing mission controller, no second controller introduced]
  proof_target: One clean load + status query showing the new taskcards
  current_state: TODO
  next_transition: READY after PRODSYS-P0-T2

taskcard:
  task_id: PRODSYS-P1-T2
  phase_id: PRODSYS-P1
  title: Replace hand-authored handover docs with a generated, real-state-sourced snapshot command
  objective: Eliminate STALE-HANDOVER-VS-GIT-HEAD structurally -- a snapshot can never be stale-on-arrival because it is derived, not authored, at read time.
  root_cause_ids: [STALE-HANDOVER-VS-GIT-HEAD]
  design_decision_ids: [DD-SINGLE-AUTHORITY]
  requirements: []
  owner_role: implementer
  reviewer_role: independent-verifier
  allowed_paths: [src/readme_agent/supervisor/mission_command.py, plans/codex/handover/]
  forbidden_paths: [src/readme_agent/readme/, src/readme_agent/gitsafety/]
  dependencies: [PRODSYS-P0-T1 not required, but recommended first]
  preconditions: []
  implementation_steps: [Add a `--format handover` output mode to the existing mission-action status command, sourcing every field (head, blockers, current_task) from a live git + CAS read at invocation time; regenerate plans/codex/handover/ from it once; delete the hand-authored variant]
  schemas_or_contracts: [Reuses MissionEvaluation, MissionExecutionStateV1 -- no new schema]
  migration_steps: [One-time regeneration of the 3 current handover files, replacing the 2026-07-24 hand-correction (commit 40c241c) with a generated equivalent]
  focused_tests: [New test: generated snapshot's head field always equals git rev-parse HEAD at generation time]
  integration_tests: [Generate against the real repo, diff against the current hand-corrected state.json, confirm every mechanically-derivable field matches]
  regression_tests: [Existing mission_command.py tests unaffected]
  negative_controls: [A hand-edit to the generated file is detectable/overwritten on next generation, never silently trusted]
  e2e_or_pilot_proof: [Live regeneration matching the hand-corrected baseline]
  observability_and_evidence: [Regenerated plans/codex/handover/ files themselves are the evidence]
  rollback: Revert to the commit-40c241c hand-corrected files if the generator has a defect
  acceptance_criteria: [Generated snapshot matches live state; no field is hand-edited afterward]
  proof_target: One clean regeneration matching real git HEAD and real CAS state
  current_state: TODO
  next_transition: READY after PRODSYS-P1-T1 (diagnostic groundwork)

taskcard:
  task_id: PRODSYS-P1-T3
  phase_id: PRODSYS-P1
  title: Gate requirement-coverage regeneration on requirements.md/graph drift instead of relying on manual invocation
  objective: Turn the proven-correct build_level8_requirement_taskcard_coverage.py tool into an enforced check, not a habit -- close LOCKED-GRAPH-NEVER-RECONCILED's remaining automatic-invocation gap.
  root_cause_ids: [LOCKED-GRAPH-NEVER-RECONCILED]
  design_decision_ids: [DD-SINGLE-AUTHORITY]
  requirements: []
  owner_role: implementer
  reviewer_role: independent-verifier
  allowed_paths: [scripts/governance/run_official_checks.py, .github/workflows/ci.yml]
  forbidden_paths: [plans/requirements.md]
  dependencies: []
  preconditions: [PRODSYS-P0-T2 snapshot exists]
  implementation_steps: [Add `build_level8_requirement_taskcard_coverage.py --check` as a step in run_official_checks.py, mirroring validate_plan_structure.py's own placement; warn-only first (matching this repo's own established GOV-009 staged-rollout precedent), promoted to blocking after N clean runs]
  schemas_or_contracts: []
  migration_steps: [None -- the tool and its --check mode already exist and were proven this session]
  focused_tests: [New: a deliberately-stale requirement_coverage block is caught by the new check step]
  integration_tests: [run_official_checks.py end-to-end with the new step present]
  regression_tests: [Existing official-checks suite unaffected on an already-current tree]
  negative_controls: [A requirements.md edit with no matching coverage regeneration fails the new check]
  e2e_or_pilot_proof: [A real requirements.md edit (like this session's FACT-014 addition) is caught automatically, not by a downstream test failure as happened this session]
  observability_and_evidence: [run_official_checks.py output showing the new step; a dated log entry]
  rollback: Remove the new step from run_official_checks.py
  acceptance_criteria: [The exact drift this session found by accident (a hard-coded test assertion catching it) is instead caught directly and immediately by this new step]
  proof_target: One deliberately-introduced drift caught by the new gate before it reaches pytest
  current_state: TODO
  next_transition: READY after PRODSYS-P0-T2

taskcard:
  task_id: PRODSYS-P1-T4
  phase_id: PRODSYS-P1
  title: Add lease/expiry parity to the mission claim, mirroring the sibling repo-lock pattern
  objective: Close MISSION-CLAIM-NO-LEASE-PARITY -- a stale claim currently lies silently about who is working a task and since when.
  root_cause_ids: [MISSION-CLAIM-NO-LEASE-PARITY]
  design_decision_ids: [DD-CLAIM-LEASE-PARITY]
  requirements: []
  owner_role: implementer
  reviewer_role: independent-verifier
  allowed_paths: [src/readme_agent/state/schema.py, src/readme_agent/supervisor/mission_control.py]
  forbidden_paths: [src/readme_agent/state/git_backend.py]
  dependencies: []
  preconditions: []
  implementation_steps: [Add an optional `leased_until` field to MissionExecutionStateV1's claim fields, defaulting to None for backward compatibility with existing durable state; update claim_next_task() to treat a claim with an expired (or absent, for pre-migration state) lease as reclaimable, logging a warning naming the prior claimant rather than silently no-op-ing]
  schemas_or_contracts: [MissionExecutionStateV1 -- additive field only, no breaking change]
  migration_steps: [None required -- existing durable state without the field is handled by the None-default path]
  focused_tests: [New: an expired-lease claim is detected and reassigned with a logged warning; a live-lease claim is correctly left alone; a pre-migration claim with no lease field is handled without raising]
  integration_tests: [claim_next_task() against real durable state with each of the three cases above]
  regression_tests: [Existing test_mission_control.py suite unaffected for every other claim/transition path]
  negative_controls: [A claim leased 1 second in the future is correctly NOT reassigned]
  e2e_or_pilot_proof: [One real claim/expire/reclaim cycle against the durable mission state]
  observability_and_evidence: [Test output, dated log entry]
  rollback: Revert the schema addition -- no data loss, field is additive
  acceptance_criteria: [An expired claim is detected and reassignable, matching the sibling repo-lock's own proven lease behavior]
  proof_target: One passing expired-claim reassignment test plus one passing live-claim non-reassignment test
  current_state: TODO
  next_transition: READY on plan approval

taskcard:
  task_id: PRODSYS-P2-T1
  phase_id: PRODSYS-P2
  title: Cheap interim gate -- CI/lint check that every verify_* function has a detected call site
  objective: A fast, low-risk first layer of defense against VERIFIER-BUILT-NOT-WIRED recurring, shippable before the full registry-level wiring.
  root_cause_ids: [VERIFIER-BUILT-NOT-WIRED]
  design_decision_ids: [DD-VERIFIER-ENFORCEMENT-PARITY]
  requirements: []
  owner_role: implementer
  reviewer_role: independent-verifier
  allowed_paths: [scripts/governance/]
  forbidden_paths: [src/readme_agent/verification/]
  dependencies: []
  preconditions: []
  implementation_steps: [Add a small static-analysis script that greps for public verify_* function definitions and confirms each has at least one non-test call site in src/readme_agent/; wire into run_official_checks.py as a warn-only step]
  schemas_or_contracts: []
  migration_steps: []
  focused_tests: [New test: a synthetic unwired verify_* function is flagged]
  integration_tests: []
  regression_tests: [The already-wired verify_readme_proposal_bundle passes cleanly]
  negative_controls: [A verifier called only from its own test file is correctly flagged, not silently passed]
  e2e_or_pilot_proof: [Run against the real current tree with zero unexpected flags]
  observability_and_evidence: [Script output, dated log entry]
  rollback: Remove the script from the official-checks chain
  acceptance_criteria: [The script would have caught the original VERIFIER-BUILT-NOT-WIRED gap if run at the time]
  proof_target: Zero false positives against the current tree; the original gap reproduced against a synthetic fixture
  current_state: TODO
  next_transition: READY on plan approval

taskcard:
  task_id: PRODSYS-P2-T2
  phase_id: PRODSYS-P2
  title: Registry-level enforced-verification wrapper, mirroring dispatch_gated_effect()
  objective: The durable, structural fix -- any capability declaring independent_verification-class evidence must route through the same precheck/ledger shape as the write-path gate.
  root_cause_ids: [VERIFIER-BUILT-NOT-WIRED]
  design_decision_ids: [DD-VERIFIER-ENFORCEMENT-PARITY]
  requirements: []
  owner_role: implementer
  reviewer_role: independent-verifier
  allowed_paths: [src/readme_agent/capabilities/, src/readme_agent/verification/]
  forbidden_paths: [src/readme_agent/effects/]
  dependencies: [PRODSYS-P2-T1]
  preconditions: [PRODSYS-P2-T1 shipped and stable]
  implementation_steps: [Design and implement dispatch_gated_verification(), the read-path structural sibling to dispatch_gated_effect(); migrate the already-wired readme-proposal-bundle case to it for consistency, not as a special exception]
  schemas_or_contracts: [New: VerificationDispatchRecord or equivalent, mirroring EffectLedger's shape]
  migration_steps: [Migrate the one existing wired case; no other migrations needed yet since no other verifier exists]
  focused_tests: [New unit tests for the wrapper's precheck/dispatch/record paths]
  integration_tests: [The migrated readme-proposal-bundle path still produces the same verdicts as before migration]
  regression_tests: [Full existing verification test suite]
  negative_controls: [A capability that tries to bypass the wrapper and call the verifier function directly is either structurally prevented or flagged by PRODSYS-P2-T1's lint]
  e2e_or_pilot_proof: [One real producer run through the new wrapper, verdict matches direct-call baseline]
  observability_and_evidence: [Evidence bundle showing wrapper dispatch records]
  rollback: Feature-flag the wrapper off, fall back to the pre-migration direct call
  acceptance_criteria: [No verifier in the codebase is reachable only from its own test file]
  proof_target: 100% of declared verify_* functions have an enforced call site
  current_state: TODO
  next_transition: READY after PRODSYS-P2-T1

taskcard:
  task_id: PRODSYS-P3-T1
  phase_id: PRODSYS-P3
  title: Ship the evidence-precondition-recording fix identified by PRODSYS-P0-T1 (corrected from a concurrency lock)
  objective: Close OFFICIAL-CHECKS-NONDETERMINISM's real, proven mechanism -- evidence not recording its own preconditions -- per DD-RECORD-EVIDENCE-PRECONDITIONS, not the originally-hypothesized (now disconfirmed) concurrency cause.
  root_cause_ids: [OFFICIAL-CHECKS-NONDETERMINISM]
  design_decision_ids: [DD-RECORD-EVIDENCE-PRECONDITIONS]
  requirements: []
  owner_role: implementer
  reviewer_role: independent-verifier
  allowed_paths: [scripts/governance/run_official_checks.py]
  forbidden_paths: [src/readme_agent/]
  dependencies: [PRODSYS-P0-T1]
  preconditions: [PRODSYS-P0-T1 IMPLEMENTED -- satisfied]
  implementation_steps: [Add a `git status --porcelain` capture at the start of run_official_checks.py's main(); print a clear "TREE DIRTY" / "TREE CLEAN" label with the dirty file list (if any) at both the start and end of the log output; document in the script's own docstring that a dirty-tree run must never be cited as evidence about a specific commit]
  schemas_or_contracts: []
  migration_steps: []
  focused_tests: [New: a deliberately dirty tree produces the TREE DIRTY label with the correct file list]
  integration_tests: [A clean-tree run produces the TREE CLEAN label; existing official-checks suite unaffected]
  regression_tests: [Existing official-checks suite unaffected]
  negative_controls: [A run against a tree dirtied mid-execution (a file touched between the start-of-run and end-of-run precondition capture) is still distinguishable after the fact from a genuinely stable run]
  e2e_or_pilot_proof: [One real dirty-tree run and one real clean-tree run, both correctly labeled]
  observability_and_evidence: [Updated run_official_checks.py output showing the new label; a dated log entry]
  rollback: Revert the new logging step -- no behavior change to the checks themselves
  acceptance_criteria: [A rerun of the exact historical scenario (edits landing mid-sequence) would now be correctly labeled dirty in its own log, preventing the original mislabeling from recurring]
  proof_target: Dirty and clean tree states both correctly and visibly labeled in the official-checks log
  current_state: TODO
  next_transition: READY (dependency already satisfied)

taskcard:
  task_id: PRODSYS-P3-T2
  phase_id: PRODSYS-P3
  title: Re-run VER-009's owed heterogeneous false-success re-proof under production-like conditions
  objective: Close the acknowledged, still-open re-proof obligation named in plans/requirements.md's VER-009 row.
  root_cause_ids: [VER009-REPROOF-OWED]
  design_decision_ids: []
  requirements: [VER-009]
  owner_role: implementer
  reviewer_role: independent-verifier
  allowed_paths: [plans/investigations/evidence/prodsys-ver009-reproof/]
  forbidden_paths: [src/readme_agent/supervisor/convergence.py]
  dependencies: [PRODSYS-P3-T1]
  preconditions: [Official-checks oracle stabilized (PRODSYS-P3-T1) so this re-proof's own results are trustworthy]
  implementation_steps: [Re-run the previously false-success .NET/Python/C++ heterogeneous cases under the same production-like conditions that originally exposed the bug; confirm each now correctly reports BLOCKED, not CONVERGED_NO_CHANGE]
  schemas_or_contracts: []
  migration_steps: []
  focused_tests: []
  integration_tests: [Existing test_convergence.py suite]
  regression_tests: []
  negative_controls: [A deliberately-reintroduced version of the original bug is caught by the re-proof]
  e2e_or_pilot_proof: [All previously-false-success cases now report correctly]
  observability_and_evidence: [plans/investigations/evidence/prodsys-ver009-reproof/*, updated plans/requirements.md VER-009 row status]
  rollback: N/A -- proof-only, no code change expected
  acceptance_criteria: [VER-009 moves from PARTIAL to IMPLEMENTED with real re-proof evidence]
  proof_target: All named heterogeneous cases re-run clean
  current_state: TODO
  next_transition: READY after PRODSYS-P3-T1

taskcard:
  task_id: PRODSYS-P4-T1
  phase_id: PRODSYS-P4
  title: Confirm the PRODSYS-P1-T2 generator reproduces the hand-corrected commit-40c241c baseline
  objective: Prove DD-SINGLE-AUTHORITY holds generally, not just for this one hand-corrected snapshot.
  root_cause_ids: [STALE-HANDOVER-VS-GIT-HEAD, LOG-LAGS-GIT-HEAD]
  design_decision_ids: [DD-SINGLE-AUTHORITY]
  requirements: []
  owner_role: implementer
  reviewer_role: independent-verifier
  allowed_paths: [plans/investigations/evidence/prodsys-generator-baseline-match/]
  forbidden_paths: [plans/codex/handover/]
  dependencies: [PRODSYS-P1-T2]
  preconditions: [PRODSYS-P1-T2 shipped]
  implementation_steps: [Run the generator against current state; diff every field against the hand-corrected commit-40c241c content; document any field the generator cannot mechanically derive (e.g. narrative prose) as an explicit, accepted gap, not a silent omission]
  schemas_or_contracts: []
  migration_steps: []
  focused_tests: []
  integration_tests: []
  regression_tests: []
  negative_controls: []
  e2e_or_pilot_proof: [Generated output matches the hand-corrected baseline in every mechanically-derivable field]
  observability_and_evidence: [plans/investigations/evidence/prodsys-generator-baseline-match/diff.txt]
  rollback: N/A -- proof-only
  acceptance_criteria: [No mechanically-derivable field diverges between generated and hand-corrected]
  proof_target: One clean diff run
  current_state: TODO
  next_transition: READY after PRODSYS-P1-T2

taskcard:
  task_id: PRODSYS-P4-T2
  phase_id: PRODSYS-P4
  title: Reconcile the pre-production/Wave-2 dependency-gating gap named in the original handover
  objective: Close the separately-named control-plane gap (Wave 2 currently depends on a parent whose REROUTED status counts as dependency-satisfied instead of the final staging child) while the mission-graph machinery is already being touched by this redesign.
  root_cause_ids: []
  design_decision_ids: []
  requirements: []
  owner_role: implementer
  reviewer_role: independent-verifier
  allowed_paths: [plans/investigations/control/level8-autonomous-mission-task-graph.yaml]
  forbidden_paths: [plans/master.md]
  dependencies: [PRODSYS-P1-T1]
  preconditions: []
  implementation_steps: [Change Wave 2's dependency to require L8-STAGING-VERIFIED-PROPOSAL-PROOF's own closure, either directly or via a parent-state computation that only counts CLOSED (never REROUTED) as satisfying a staging-gate dependency; add a regression test]
  schemas_or_contracts: []
  migration_steps: [Durable-state migration/reconciliation, not a schema change]
  focused_tests: [New: Wave 2 cannot become eligible after only its parent's REROUTED transition]
  integration_tests: [mission_control.py's own ready-task computation with the corrected dependency]
  regression_tests: [Existing mission_control.py suite unaffected for every other taskcard's dependency logic]
  negative_controls: [The original bug's exact shape -- parent REROUTED, staging child still open -- is proven to keep Wave 2 ineligible]
  e2e_or_pilot_proof: [supervise --mission-action status confirms Wave 2 stays ineligible until staging genuinely closes]
  observability_and_evidence: [Updated graph, dated log entry, new test]
  rollback: Revert the dependency-graph edit
  acceptance_criteria: [Wave 2 cannot become ready via a rerouted parent alone]
  proof_target: One passing negative-control test plus one live status confirmation
  current_state: TODO
  next_transition: READY after PRODSYS-P1-T1

taskcard:
  task_id: PRODSYS-P5-T1
  phase_id: PRODSYS-P5
  title: Live cross-check -- supervise --mission-action status output vs. direct git/CAS inspection
  objective: Prove the reconciled authority chain (DD-SINGLE-AUTHORITY) matches ground truth under real conditions, not just in unit tests.
  root_cause_ids: [LOCKED-GRAPH-NEVER-RECONCILED, STALE-HANDOVER-VS-GIT-HEAD]
  design_decision_ids: [DD-SINGLE-AUTHORITY]
  requirements: []
  owner_role: implementer
  reviewer_role: independent-verifier
  allowed_paths: [plans/investigations/evidence/prodsys-live-cross-check/]
  forbidden_paths: []
  dependencies: [PRODSYS-P1-T1, PRODSYS-P1-T2, PRODSYS-P1-T3, PRODSYS-P4-T1, PRODSYS-P4-T2]
  preconditions: [All PRODSYS-P1/P4 tasks closed]
  implementation_steps: [Run supervise --mission-action status; independently re-derive the same facts via direct git log/git ls-remote on the durable-state ref and a manual read of requirements.md/the graph file; confirm agreement]
  schemas_or_contracts: []
  migration_steps: []
  focused_tests: []
  integration_tests: []
  regression_tests: []
  negative_controls: []
  e2e_or_pilot_proof: [Independent re-derivation matches the tool's own output exactly]
  observability_and_evidence: [plans/investigations/evidence/prodsys-live-cross-check/*]
  rollback: N/A -- proof-only
  acceptance_criteria: [Zero discrepancies between tool output and independent manual re-derivation]
  proof_target: One clean cross-check
  current_state: TODO
  next_transition: READY after PRODSYS-P1/P4 tasks close

taskcard:
  task_id: PRODSYS-P5-T2
  phase_id: PRODSYS-P5
  title: Deliberate overlapped-rerun pilot proving the concurrency fix
  objective: Prove PRODSYS-P3-T1's fix actually prevents OFFICIAL-CHECKS-NONDETERMINISM under the exact overlapped-session conditions this document's own evidence observed.
  root_cause_ids: [OFFICIAL-CHECKS-NONDETERMINISM]
  design_decision_ids: [DD-INVESTIGATE-BEFORE-LOCKING]
  requirements: []
  owner_role: implementer
  reviewer_role: independent-verifier
  allowed_paths: [plans/investigations/evidence/prodsys-overlapped-rerun-pilot/]
  forbidden_paths: []
  dependencies: [PRODSYS-P3-T1]
  preconditions: [PRODSYS-P3-T1 shipped]
  implementation_steps: [Deliberately run two official-checks invocations concurrently (or one official-checks run alongside a heavy live-network background task, mirroring this session's own observed slowdown) and confirm the fix either serializes them safely or the results remain consistent]
  schemas_or_contracts: []
  migration_steps: []
  focused_tests: []
  integration_tests: []
  regression_tests: []
  negative_controls: [Without the fix, re-confirm the symptom reproduces (control condition)]
  e2e_or_pilot_proof: [The overlapped condition that previously caused instability/slowdown now behaves predictably]
  observability_and_evidence: [plans/investigations/evidence/prodsys-overlapped-rerun-pilot/*]
  rollback: N/A -- proof-only
  acceptance_criteria: [The exact overlapped condition observed during this session's own Phase E1 work no longer produces divergent results]
  proof_target: One successful overlapped-run pilot, with-fix vs. without-fix comparison
  current_state: TODO
  next_transition: READY after PRODSYS-P3-T1

taskcard:
  task_id: PRODSYS-P6-T1
  phase_id: PRODSYS-P6
  title: Independent adversarial review of the whole redesign
  objective: A reviewer distinct from every implementer above re-examines every finding, decision, and taskcard for material gaps before closure.
  root_cause_ids: []
  design_decision_ids: []
  requirements: []
  owner_role: independent-verifier
  reviewer_role: independent-verifier
  allowed_paths: [plans/investigations/evidence/prodsys-independent-review/]
  forbidden_paths: [src/readme_agent/]
  dependencies: [PRODSYS-P0-T1, PRODSYS-P1-T1, PRODSYS-P1-T2, PRODSYS-P1-T3, PRODSYS-P2-T1, PRODSYS-P2-T2, PRODSYS-P3-T1, PRODSYS-P3-T2, PRODSYS-P4-T1, PRODSYS-P4-T2, PRODSYS-P5-T1, PRODSYS-P5-T2]
  preconditions: [All prior phases closed]
  implementation_steps: [Re-verify every acceptance_criteria above against its own cited evidence path, independently; flag any claim not actually supported]
  schemas_or_contracts: []
  migration_steps: []
  focused_tests: []
  integration_tests: []
  regression_tests: []
  negative_controls: []
  e2e_or_pilot_proof: []
  observability_and_evidence: [plans/investigations/evidence/prodsys-independent-review/verdict.md]
  rollback: N/A -- review only
  acceptance_criteria: [No material (severity >= 4 of 5) finding remains open]
  proof_target: A clean independent review verdict
  current_state: TODO
  next_transition: READY after all prior phases close

taskcard:
  task_id: PRODSYS-P6-T2
  phase_id: PRODSYS-P6
  title: Reconcile plans/requirements.md and plans/master.md against real delivered state; close
  objective: GOV-022-style reconciliation -- update the normative register and (under a fresh GOV-023 approval) master.md to reflect what this redesign actually delivered, then close the mission taskcard set.
  root_cause_ids: []
  design_decision_ids: []
  requirements: []
  owner_role: implementer
  reviewer_role: independent-verifier
  allowed_paths: [plans/requirements.md, plans/master.md]
  forbidden_paths: []
  dependencies: [PRODSYS-P6-T1]
  preconditions: [PRODSYS-P6-T1 clean verdict; fresh GOV-023 approval obtained before any master.md edit]
  implementation_steps: [Add/update the requirements.md rows this redesign's mechanisms warrant; request and apply a scoped master.md Decision Ledger entry recording the redesign; run build_level8_requirement_taskcard_coverage.py to keep coverage current; transition every PRODSYS taskcard to CLOSED with real evidence_refs]
  schemas_or_contracts: []
  migration_steps: []
  focused_tests: []
  integration_tests: [validate_plan_structure.py, run_official_checks.py]
  regression_tests: [Full official-checks suite]
  negative_controls: []
  e2e_or_pilot_proof: [supervise --mission-action evaluate reports every PRODSYS taskcard CLOSED]
  observability_and_evidence: [Final dated log entry, updated requirements.md/master.md, final evidence bundle]
  rollback: N/A -- closure phase, individual prior-phase rollbacks already covered their own risk
  acceptance_criteria: [Every PRODSYS taskcard CLOSED with evidence_refs; requirements.md/master.md/durable state agree]
  proof_target: mission_complete-eligible state for this taskcard subset
  current_state: TODO
  next_transition: READY after PRODSYS-P6-T1
```

## 11. Dependency graph and critical path

```
PRODSYS-P0-T1 -> PRODSYS-P1-T1 (mission registration) -> PRODSYS-P1-T2 (handover generator) ->
PRODSYS-P4-T1 (generator-baseline match) -> PRODSYS-P1-T3 (coverage-gate) ->
PRODSYS-P4-T2 (Wave-2 dependency reconciliation) -> PRODSYS-P2-T1 -> PRODSYS-P2-T2 (verifier wiring) ->
PRODSYS-P3-T1 (official-checks RCA fix, parallelizable with P1/P2) -> PRODSYS-P3-T2 (VER-009 re-proof) ->
PRODSYS-P5-T1 -> PRODSYS-P5-T2 (live pilots) -> PRODSYS-P6-T1 -> PRODSYS-P6-T2 (independent review, reconciliation, close)
```

**Critical path**: `PRODSYS-P0-T1 -> P1-T1 -> P1-T2 -> P4-T1 -> P2-T1 -> P2-T2 -> P5-T1 -> P6-T1 -> P6-T2`.

## 12. Validation and regression strategy

Layered per the mission's own conventions: schema/transition validation reuses `mission_control.py`'s
existing enforcement (`DD-REUSE-MISSION-MACHINERY` — no new schema layer needed); focused/integration
tests are named per-taskcard above; regression controls explicitly re-run
`test_supervisor_loop.py`/`test_convergence.py`/`test_mission_control.py` to prove nothing preserved
(§6) regresses; production-shaped proof is Phase 5's live pilots, not mocked.

## 13. Migration and rollout

Incremental, matching this repo's own established convention (new checks start warn-only before
promotion — `GOV-009`, and this session's own directly-observed `build_level8_requirement_
taskcard_coverage.py --check` precedent): `PRODSYS-P1-T3`'s coverage gate ships warn-only first; the
verifier-enforcement wrapper (`PRODSYS-P2-T2`) ships after its own cheap lint precursor
(`PRODSYS-P2-T1`) is stable. No feature flags needed beyond that staging — this is docs/tooling and
mission-machinery hardening, not a live production surface change.

## 14. Observability and evidence

Every taskcard's evidence lands under `plans/investigations/evidence/prodsys-<taskcard-slug>/`, per
this repo's own `GOVERNANCE.md` naming/organization rules (self-explanatory, no enumerated names).

## 15. Risks, tradeoffs, and limits

| ID | Description | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| `R-NARRATIVE-LOSS` | Generated handover snapshots could read as dry/mechanical vs. hand-written prose | Medium | Low | Generator emits human-readable Markdown, not just JSON |
| `R-RCA-INCONCLUSIVE` | Official-checks flakiness may not reproduce under controlled single-process conditions | Medium | Medium | Ship containment (documented retry/quarantine) if RCA is genuinely inconclusive after a time-boxed attempt |
| `R-HIDDEN-DEFECTS-SURFACE` | Wiring a verifier into an enforced gate may reveal previously-hidden defects in what it verifies | Medium | Medium (desired outcome, budgeted for) | Explicit repair-cycle budget in Phase 2/5, not treated as a surprise blocker |
| `R-FALSE-POSITIVE-DRIFT-GATE` | The new coverage/verifier-wiring gates could false-positive on legitimate in-progress work | Low-Medium | Low (warn-only rollout) | Ships warn-only first, matching this repo's own established rollout precedent |

Explicitly: this redesign does not claim to eliminate model/agent variability — it targets the proven
bookkeeping and oracle-stability root causes. Any remaining variability in LLM-driven planning itself
is out of scope.

**Rejected alternatives**: a fourth, bespoke state-tracking mechanism for this redesign's own progress
(rejected — `GOVERNANCE.md` rule 8, would recreate the diagnosed pattern); fixing `VERIFIER-BUILT-NOT-
WIRED` one call site at a time indefinitely (rejected as the sole strategy — this is the second
occurrence of the identical gap); assuming the concurrency hypothesis and building a lock without
controlled reproduction (rejected — the evidence standard this plan itself sets forbids treating an
inferred cause as proven).

## 16. Final assessment

**PRODUCTION_HARDENING_REQUIRED**, partially delivered as an unplanned side effect of unrelated,
urgent work (see §1's update). The core architecture is sound and should not be redesigned: the
fingerprint/idempotency discipline, the "prove it in production" governance model, and the CAS-backed
mission state machine are all correctly designed for the problems they were built to solve — this
session's own direct exercise of `mission_control.py` (a real `evaluate` call reconciling state
version 81 → 82) proved the mechanism works exactly as designed the moment it is actually invoked.
What remains is making that invocation automatic rather than incidental, generalizing the one already-
closed verifier-wiring gap into a structural convention, and root-causing the official-checks oracle's
observed instability before building anything further on top of it.

**Confidence**: High on root-cause identification for four of the six findings (`LOCKED-GRAPH-
NEVER-RECONCILED`, `STALE-HANDOVER-VS-GIT-HEAD`, `VERIFIER-BUILT-NOT-WIRED`'s closed instance, and
now `OFFICIAL-CHECKS-NONDETERMINISM`), each with direct before/after evidence independently
re-verified against raw git history and log files, not merely asserted. `OFFICIAL-CHECKS-
NONDETERMINISM` moved from `STRONGLY_INFERRED` to `PROVEN` this same pass — the concurrency
hypothesis that motivated the original Phase 0 design is `DISCONFIRMED` for the incident that
produced it; the actual, cheaper fix (`DD-RECORD-EVIDENCE-PRECONDITIONS`) is now well-justified.
`MISSION-CLAIM-NO-LEASE-PARITY` is a new, directly-confirmed finding from the same pass. Medium
confidence remains on two narrower points: whether a residual, unrelated cause explains the one
still-`UNKNOWN` pytest flip inside the original 4-attempt incident, and on the achievable xdist/
concurrency-tuning figures this document does not itself estimate.
