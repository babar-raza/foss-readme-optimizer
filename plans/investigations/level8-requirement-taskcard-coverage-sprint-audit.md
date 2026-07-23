# Level-8 requirement-to-taskcard coverage sprint audit

Date: 2026-07-23

Mission: `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`

Task: `L8-REQUIREMENT-TO-TASKCARD-COVERAGE`

Verdict: `PLAN_HARDENED_FROM_AUDIT_READY_FOR_EXECUTION`

## Evidence inspected

- The complete current `plans/master.md`, including all 72 decisions, Architecture, both active
  checklist tracks, and the Verification Checklist.
- All 376 well-formed normative rows in `plans/requirements.md`.
- The semantic implementation-truth matrix at
  `plans/investigations/evidence/implementation-truth-matrix-2026/matrix.json`.
- The generated coverage report at
  `plans/investigations/evidence/level8-requirement-taskcard-coverage/requirement-taskcard-coverage.json`.
- The live mission state after graph reconciliation:
  `refs/readme-agent-state/mission__LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`, version 11.
- Focused schema/graph tests and the deterministic generator's `--check` result.

## What we achieved

- Mapped every one of 376 requirement IDs to exactly one primary Level-8 taskcard and lane.
- Classified 348 rows as mandatory mission coverage.
- Excluded 28 `BACKLOG` rows from mandatory execution without deleting their traceability.
- Preserved 65 `IMPLEMENTED` rows whose semantic matrix has no high-confidence contradiction.
- Reopened 85 `IMPLEMENTED` rows as `reopened_semantic_evidence_gap`; none can be silently
  preserved while its semantic findings remain.
- Kept 33 always-active governance requirements explicit and classified 165 other open normative
  rows as mandatory work.
- Added deterministic generation and check-mode tooling, source hashes, duplicate/unmapped
  controls, taskcard-count reconciliation, and graph-loader enforcement.
- Reconciled the changed graph into the existing live state. The same task and claim remained
  active; a competing claim caused no state-version change.

## What this proves

Finding `LEVEL8-REQUIREMENT-COVERAGE-COMPLETE`:

- Requirement or task: `L8-REQUIREMENT-TO-TASKCARD-COVERAGE`
- Classification: `completed_verified`
- Proof level: `end_to_end_proof`
- Direct evidence:
  - 376 unique mappings;
  - zero duplicate requirement IDs;
  - zero unmapped requirement IDs;
  - requirements-source SHA-256 verified by the graph test;
  - live state reload at graph hash
    `2cd9c5306ca15dfd2b901b674c804127db4a23a5b93da2d14eebc3fdf2899973`.
- Verified behavior: requirements source → semantic closure classification → stable task/lane
  mapping → graph validation → durable state reconciliation.
- Limitations: mapping proves complete governance of the work; it does not prove any reopened
  requirement is implemented.
- Remaining risk: the 85 reopened closure claims must be either evidenced correctly or downgraded
  in the normative register.
- Effect on final outcome: the stop evaluator now has complete normative coverage and cannot
  report completion by overlooking a requirement row.
- Action required: advance this task through the evidence ladder and consume
  `L8-WAVE0-PLAN-TRUTH-RECONCILIATION`.
- Priority: P0.
- Proposed owner lane: mission-control.

Finding `LEVEL8-REOPENED-CLOSURE-DEBT`:

- Requirement or task: 85 mapped `reopened_semantic_evidence_gap` requirements.
- Classification: `claimed_unproven`
- Proof level: `partial_validation`
- Direct evidence: each mapping contains its semantic matrix finding.
- Verified behavior: the graph loader rejects an `IMPLEMENTED` row with semantic findings if its
  disposition is changed to `preserved_verified`.
- Limitations: many findings are missing exact test-node or committed-evidence citations rather
  than known behavior defects; each still needs individual disposition.
- Remaining risk: aggregate `IMPLEMENTED` counts continue to overstate semantically closed work.
- Effect on final outcome: blocks truthful Wave 0 closure and any Level-8 award.
- Action required: preserve genuine implementations, add exact evidence where it exists, downgrade
  claims where it does not, and rerun the matrix.
- Priority: P0/P1 according to the underlying row.
- Proposed owner lane: the mapped Level-8 wave.

Finding `LEVEL8-PARALLEL-PLAN-TRACKS`:

- Requirement or task: `L8-WAVE0-PLAN-TRUTH-RECONCILIATION`
- Classification: `final_outcome_blocker`
- Proof level: `end_to_end_proof`
- Direct evidence: the complete master read shows Sprint Waves 0-9 and legacy Phases 0-26 both
  remain active checklists; the new Level-8 Waves 0-8 are not yet the master Build Checklist.
- Verified behavior: the graph correctly assigns governance/business truth work to Wave 0.
- Limitations: the structural master amendment remains gated by `GOVERNANCE.md` rule 12.
- Remaining risk: repository readers still face contradictory current execution sequences.
- Effect on final outcome: prevents Wave 0 closure, but is now represented rather than hidden.
- Action required: use the exact bounded master-section gate and preserve all independent work.
- Priority: P0.
- Proposed owner lane: governance-truth.

## Effect on the final outcome

This sprint closes the coverage blind spot, not the Level-8 mission. The mission remains at Wave 0
with 10 unresolved taskcards and no external-blocker classification in durable state.

## Uncertainty and limitations

- Prefix-to-wave routing is explicit policy, not proof that every requirement is already optimally
  decomposed. A requirement may be split into child cards when its owning wave begins, while its
  primary mapping remains stable.
- `BACKLOG` rows remain visible but are not treated as accepted mandatory scope.
- No `DEPRECATED` rows currently exist; the generator and schema still handle that status.
- The current plan candidates under `plans/roadmap.md`, `plans/status.md`, and
  `plans/changelog.md` remain uncommitted and are not silently accepted by this mapping.

## Findings requiring plan amendments

- Replace the two active historical execution tracks with the approved Level-8 Waves 0-8.
- Correct or evidence all 85 semantically reopened closure claims.
- Add the new Level-7 30-day and Level-8 90-day requirements after the master/requirements
  synchronization gate is satisfied.
- Keep `idea.md` vision-only and move generated status/future sequencing only to governance-approved
  homes.

## Plan hardening and adversarial validation

The generator fails on an unknown requirement prefix or target task, and the graph loader rejects
duplicate mappings, missing tasks, taskcard/mapping disagreement, executable backlog/deprecated
rows, and unsupported `IMPLEMENTED` preservation. Validation-repair loops:

1. The first generated graph mapped all 376 rows and exposed the exact 348/28 mandatory/excluded
   split; focused loader tests passed.
2. An adversarial negative test changed a reopened `IMPLEMENTED` mapping back to preserved; the
   loader rejected it. The deterministic `--check` rerun then confirmed no stale output.

Material quality scores: correctness 5/5, safety 5/5, coverage 5/5, evidence 4/5,
maintainability 4/5. The active plan is ready to return to Wave 0 execution.
