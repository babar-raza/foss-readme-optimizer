# Level-8 autonomous mission-control sprint audit

Date: 2026-07-23

Mission: `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`

Task: `L8-MISSION-CONTROL-CONSUMER`

Verdict: `PLAN_HARDENED_FROM_AUDIT_READY_FOR_EXECUTION`

## Evidence inspected

- The raw repository state and dirty-tree inventory at HEAD
  `79c7beadbc0072714198e03a8f58b46c431d3a4a`.
- The complete user-supplied continuous-autonomy protocol.
- `plans/GOVERNANCE.md`, the supervisor task graph, state schema/backend, CLI, and current module
  map.
- The committed mission source:
  `plans/investigations/control/level8-autonomous-mission-task-graph.yaml`.
- The live Git-ref state
  `refs/readme-agent-state/mission__LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`.
- Focused test, lint, formatting, type-check, plan-validator, semantic-truth-matrix, and full-suite
  output summarized in
  `plans/investigations/evidence/level8-autonomous-mission-control/mission-control-verification.json`.

## What we achieved

- Locked the run to the existing `readme-agent supervise` authority; no cycle controller or
  competing supervisor was activated.
- Added a strict V1 schema for the protocol's taskcards and authority records.
- Added deterministic dependency/cycle validation in a dedicated graph module, dependency-ready
  selection, CAS-backed claim and transition handling, evidence-required closure stages, and
  mission-aware stop evaluation.
- Reused the existing Git-ref `GitStateBackend`; no second state or continuation mechanism was
  introduced.
- Added a mutually exclusive `supervise --mission-task-graph` target beside `--repo`, keeping both
  under the same command and controller.
- Proved a real durable claim and inspected it from the remote ref.
- Found and repaired a no-op idempotency defect during verification: repeated competing claims
  initially advanced the state version even though they could not replace the claim. Unchanged
  CAS saves are now elided; repeated claims remained at version 5 with the original claim ID.

## What this proves

Finding `LEVEL8-MISSION-CONTROL-CONSUMER`:

- Requirement or task: `L8-MISSION-CONTROL-CONSUMER`
- Classification: `completed_verified`
- Proof level: `end_to_end_proof`
- Direct evidence:
  - live state ref with active task and stable claim ID;
  - focused negative-control tests;
  - no-op repeated-claim proof;
  - full official regression checks.
- Verified behavior: task source → validation → mission evaluation → existing claim observation →
  durable state update → reevaluation occurs through the selected supervisor.
- Limitation: arbitrary implementation work is still performed by bounded workers after the
  supervisor claims it; the supervisor, not a worker, remains responsible for selection, state,
  and stop evaluation.
- Remaining risk: requirement-to-taskcard coverage is not yet complete.
- Effect on final outcome: removes the first broken producer-consumer boundary and makes automatic
  next-task selection testable and durable.
- Action required: close this card through the governed status ladder, then claim
  `L8-REQUIREMENT-TO-TASKCARD-COVERAGE`.
- Priority: P0.
- Proposed owner lane: mission-control.

Finding `LEVEL8-REQUIREMENT-COVERAGE-MISSING`:

- Requirement or task: `L8-REQUIREMENT-TO-TASKCARD-COVERAGE`
- Classification: `partially_done`
- Proof level: `partial_validation`
- Direct evidence: `plans/requirements.md` has 376 rows; the current graph has 11 wave/control
  cards.
- Verified behavior: all Level-8 waves are represented and dependency ordered.
- Limitation: each mandatory normative row is not yet mapped to exactly one primary taskcard.
- Remaining risk: the stop evaluator cannot yet prove complete normative coverage.
- Effect on final outcome: blocks mission completion, not continued execution.
- Action required: generate and validate stable per-requirement coverage while preserving verified
  closures and reopening the 85 semantic contradictions.
- Priority: P0.
- Proposed owner lane: mission-control.

Finding `LEVEL8-MASTER-STRUCTURAL-GATE`:

- Requirement or task: `L8-WAVE0-PLAN-TRUTH-RECONCILIATION`
- Classification: `final_outcome_blocker`
- Proof level: `end_to_end_proof`
- Direct evidence: `plans/GOVERNANCE.md` rule 12 and the dirty master diff.
- Verified behavior: structural amendments to Mission, Status, Decision Ledger, Architecture,
  Build Checklist, and Verification Checklist require the applicable explicit gate.
- Limitation: the current directive does not name those sections as a fresh approval response.
- Remaining risk: the master cannot yet become the sole active Level-8 sequence.
- Effect on final outcome: caps Wave 0, but safe mission-control and coverage work remains eligible.
- Action required: continue independent work; preserve an exact approval request and resume
  condition in task state.
- Priority: P0.
- Proposed owner lane: governance-truth.

## Effect on the final outcome

The mission remains incomplete. This sprint made continuation real and durable, rather than a
documentary claim, and it exposed the next dependency-ready P0 task. It did not implement or prove
Waves 0-8.

## Uncertainty and limitations

- The remote state proves one real project-state ref, not multi-runner concurrency under GitHub
  Actions.
- The wave cards deliberately remain coarse until the next task expands all normative
  requirements.
- The full Level-8 outcome still depends on reviewed GitHub App credentials, authorization records,
  heterogeneous write-capable pilots, a 30-day Level-7 run, a 90-day Level-8 run, and an independent
  reviewer.
- The dirty master/roadmap/status/changelog candidate was preserved and not silently legitimized.

## Findings requiring plan amendments

- Expand all mandatory requirements into stable taskcards and record requirement-to-card coverage.
- Keep the master structural amendment blocked until its exact governance gate is satisfied.
- Preserve the current drastic-action freeze: do not add unrelated capability/specialist
  abstractions while correctness and runtime consolidation work is open.

## Plan hardening and adversarial validation

The active control plan now encodes authority, mission, baseline, task dependencies, allowed and
forbidden paths, verification, negative controls, evidence, recovery, and closeout rules. Two
validation-repair loops ran:

1. Focused tests found the graph-count assertion was stale; it was corrected and rerun.
2. Live repeated-claim inspection found redundant no-op state writes; the CAS path was repaired,
   focused tests were strengthened, and the real claim was rerun twice.

All material quality dimensions score at least 4/5. The next eligible task is
`L8-REQUIREMENT-TO-TASKCARD-COVERAGE`; no audit or plan artifact is treated as a stop condition.
