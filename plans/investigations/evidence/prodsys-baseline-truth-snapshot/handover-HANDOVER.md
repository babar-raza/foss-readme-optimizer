# Agent Handover

> **AMENDMENT (2026-07-24, later same day).** Everything below this notice describes state as of
> HEAD `c3dcdc7`. Since then: a continuing agent closed both P0 blockers this document lists as
> `OPEN` (`separate-readme-proposal-verification`, `readme-renderer-responsibility-split`), found
> and fixed a critical package-acquisition-truth bug across the whole pipeline (the Maven resolver
> queried the wrong endpoint and every Java pilot's package was falsely reported unpublished,
> causing correct installs to be stripped), and regenerated evidence through the corrected
> pipeline. Durable mission state is now version 82; HEAD is `265bd97`. **Do not treat the narrative
> below as current** — read `plans/codex/handover/state.json` (freshly corrected) and
> `logs/2026-07-24.md`'s later entries first. This document is not yet regenerated (Plan Y's
> `PRODSYS-P1-T2` — a live-state-sourced generator — replaces this hand-authored format; not built
> yet). Full detail: commits `76e88b1`..`1551bab` and `265bd97`.

## 1. Handover Snapshot

| Field | Exact value |
|---|---|
| Repository | `D:/Users/prora/OneDrive/Documents/GitHub/foss-readme-optimizer` |
| Branch | `main` |
| HEAD at handover verification | `c3dcdc75ec448e410cb9a956379cf451527fd66b` |
| Upstream state | `origin/main` = `f8b83a41506fb22a6884f494f1b16ffb8213076e`; local `main` is 6 ahead, 0 behind |
| Governed specification | `plans/master.md`, SHA-256 `3387c8ede4e87f7c022c267c77fd82478a3fc90e4e6bb6057f5132002a822eca` |
| Normative requirements | `plans/requirements.md`, SHA-256 `2fdf55ff4c880966c19afa539bc8ca23091164783adad938ebabdf1f1672e4cd` |
| Locked execution plan | `plans/investigations/control/level8-autonomous-mission-task-graph.yaml`, SHA-256 `2ea570475bd6afbe733338e9b4ef3b87e42ede59a9f13140903772b18db0db82` |
| Durable mission | `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`, state version `81` |
| Current phase | Pre-production Gate A: direct local idea-fidelity proof |
| Current task | `L8-LOCAL-README-PROPOSAL-PROOF` = `IN_PROGRESS` |
| Exact next action | Split src/readme_agent/readme/document_renderer.py by responsibility without changing the three committed candidate hashes, then implement a separate verifier that independently reproduces the three proposal bundles before running the canonical supervisor proof. |
| Overall mission status | `PARTIAL`; mission is not locally complete, production-ready, Level 7, or Level 8 |
| Handover verdict | `HANDOVER_READY` |

Do not claim another task. The durable active claim is:

```text
task: L8-LOCAL-README-PROPOSAL-PROOF
claim_id: 7fe22ed54ab14e89bfd412eeabe73f7a
claimed_by: Codex
claimed_at: 2026-07-24T09:55:42.134252+00:00
```

## 2. Ultimate Goal

The user wants the autonomous central repository-presentation system described in
`plans/idea.md` to work in reality, be honestly presentable, and eventually earn Level 8 through
production evidence.

The finished system must continuously:

- monitor every repository in `data/products.json`;
- obtain one immutable repository view for each run;
- reconcile product truth from source, manifests, examples, tests, documentation, history,
  releases, and package registries;
- assess every applicable GitHub presentation surface;
- produce product-specific, fact-backed README and surface plans;
- generate bounded, protected, independently verified proposals;
- create or update draft PRs under reviewed authorization;
- recover durably from duplicate triggers, crashes, state outages, drift, and lost responses;
- expose health, backlog, proposal age, drift, and blocked work;
- operate without routine human initiation; and
- preserve factuality, repository ownership, and safety over referral goals.

README health is the first mandatory product outcome. A repository visitor must quickly
understand what the product does, what problems it solves, its capabilities and formats, how to
acquire and use it, its maintenance/license/support/limitations truth, and only then its
commercial/FOSS relationship.

Final success is not “the code exists.” Level 8 requires the quantitative 90-day production
proof in `plans/master.md` decision 76 and requirements `L8-010` through `L8-012`, followed by an
independent reproducible award.

## 3. Current Mission and Scope

### Mission

`LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` incrementally implements and proves the Level-8 system
through the existing `readme-agent supervise` authority. The selected mechanism is locked in the
task graph under `autonomous_execution_contract`.

### Current mission slice

The immediate mission is the user-directed local-first pre-production sequence in requirement
`L8-014`:

```text
direct local proof
  -> complete current workflow under act
  -> isolated GitHub staging
  -> production App/access and production pilots later
```

The current child must prove three reviewer-ready Java README proposals before broader local
multi-surface or workflow work.

### Mandatory outcomes

- `supervise` remains the sole production runtime (`L8-002`, decision 73).
- Every technical claim is provenance-complete (`L8-006`).
- Every candidate is fact-cited, source-span bounded, ownership-safe, and protected
  (`L8-007`).
- Draft effects are verified, authorized, drift-safe, and exactly once (`L8-008`).
- No auto-merge, force push, target default-branch write, package/release publication, or
  generated-surface write occurs (`L8-009`).
- Local, `act`, and staging proof precede production credentials (`L8-014`).
- Level 5, heterogeneous Levels 6-7, and 90-day Level 8 meet `L8-010` and `L8-011`.
- Deterministic validation remains 100%, agentic accuracy reaches at least 95%, and regressed
  routes disable automatically (`L8-012`).

### Non-goals

- Rewriting the system from scratch.
- Creating a competing controller, plan, task queue, or mission state.
- Auto-merging or writing target default branches.
- Publishing packages/releases.
- Treating GitHub-generated surfaces as writable.
- Enabling newly discovered repositories for writes without authorization.
- Requesting production GitHub App access before pre-production gates pass.
- Calling a controlled three-Java pilot heterogeneous.

### Completion conditions

The mission may close only when all mandatory taskcards are closed, the durable supervisor finds
no remaining mandatory work, the Level-8 acceptance metrics have elapsed and passed, and an
independent audit reproduces the evidence. A report, implementation commit, unit suite, proposal
bundle, or one completed sprint is not mission closure.

## 4. Authority and Reference Map

The project uses one mission with distinct authority surfaces; these are not competing plans.

| Reference | Role and relevant key | Authority | Truth status |
|---|---|---|---|
| Current user instruction | Requires this exact three-file handover; does not authorize unrelated implementation | Highest for this task | CURRENT |
| `plans/idea.md` | Product vision, “Production-Readiness Standard,” “Operating Model,” responsibility boundaries | Vision authority; user-owned dirty candidate | CURRENT but uncommitted |
| `plans/master.md` | Governed current specification; Mission, decisions 73-76, Architecture, Waves 0-8 | Specification authority; edit-gated | PARTLY STALE: “Wave 2 active” predates local-first execution |
| `plans/requirements.md` | Normative obligation register; especially `L8-001`-`014`, `RDM-*`, `FACT-*`, `VER-*` | Normative acceptance authority | CURRENT except latest README integration rows intentionally lag pending independent proof |
| `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` | Locked mechanism, taskcards, dependencies, allowed paths, acceptance | Execution-plan authority | CURRENT hash matches durable state; static task `status:` fields are bootstrap/stale |
| Durable Git ref `refs/readme-agent-state/mission__LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` | Claims, transitions, current task statuses | Execution-state authority | VERIFIED at state 81 |
| `plans/investigations/preproduction-idea-fidelity-gate-2026-07-24.md` | Clause matrix and local -> `act` -> staging sequence | Supporting execution rationale | CURRENT |
| `plans/investigations/control/preproduction-idea-fidelity-restart-checkpoint-2026-07-24.md` | Earlier state-68 restart narrative | Historical support | STALE for current state; useful for defect history only |
| `logs/2026-07-24.md` | Dated execution history and test/evidence claims | Supporting history | CURRENT, but a log assertion is not raw proof |
| `docs/architecture.md` | Current module map and implemented pipeline | Current implementation documentation | CURRENT through commit `5d2256b` |
| `docs/safety-model.md` | Push-blocking and allow-list properties | Binding safety documentation | CURRENT |
| `AGENTS.md` | Repository commands, structure, safety, governance | Binding agent instructions | CURRENT user-owned dirty candidate |
| `plans/codex/handover/state.json` | Machine-readable continuation snapshot | Handover index only | CURRENT when its focused checks pass |

### Material authority conflicts

1. `plans/master.md` Status says Wave 2 is active. Requirement `L8-014`, the later task graph,
   durable state, and the user's explicit local-first direction put execution in local Gate A.
   Classification: the master Status statement is **STALE**, not authority to begin production.
2. The task graph's static statuses show many `TODO` rows that durable state has closed.
   Classification: static statuses are **STALE bootstrap values**; durable state wins.
3. `L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME` depends on the pre-production parent, but the parent is
   `REROUTED`, which the controller counts as dependency-satisfied. This does not mechanically
   enforce closure of the final staging child. Classification: **VERIFIED control gap**; repair
   before Wave 2 is reopened.
4. Latest README proposal evidence labels its producer-written review “independent.”
   Classification: **CLAIMED_BUT_UNVERIFIED** independent acceptance.

## 5. Exact Plan

### Phase 0: truthful and reproducible baseline

- Purpose: eliminate false-success execution and establish reproducible state.
- Entry: prior runtime could converge despite unresolved findings.
- Steps: truthful terminal classifier, `WorkLedgerV1`, guarded stop, cwd-independent prompts,
  official checks, checksum evidence.
- Outputs: commits `946081e` and `05589be`.
- Validation: focused runtime tests, prior/after pilot evidence, official checks.
- Exit: no unresolved finding can report successful no-change.
- Status: **VERIFIED complete** as bounded child
  `L8-PREPRODUCTION-TRUTHFUL-BASELINE`.
- Remaining: none in this child; later full mission gates remain.

### Phase 1: immutable snapshots and pilot truth

- Purpose: ensure all facts and proposal stages consume one revision.
- Entry: truthful baseline closed.
- Steps: `RepositorySnapshotV1`, repository/policy ingestion, live registry checks, disposable
  source builds and examples, conflict behavior, independent factuality verification.
- Outputs: commit `5e31f9c`, three current and three historical pilot proofs.
- Validation: separate verifier, checksum inventory, official checks.
- Exit: three pilots have accepted core README facts and false Maven claims are rejected.
- Status: **VERIFIED complete** as
  `L8-LOCAL-IMMUTABLE-SNAPSHOT-AND-FACTS`.
- Remaining: portfolio and production fact proof belongs to Wave 3.

### Phase 2: three reviewer-ready README proposals

- Purpose: produce visible, product-specific proof of the system.
- Entry: immutable facts child closed.
- Required steps:
  1. split the oversized document renderer;
  2. preserve candidate bytes/hashes through the refactor;
  3. implement a separate evidence verifier;
  4. independently reconstruct candidates, validate Git patches, facts, protected content, and
     cross-pilot specificity;
  5. run the path through canonical `supervise` for Cells, 3D, and PDF Java;
  6. prove unchanged reruns create no diff, duplicate proposal, or unnecessary LLM call;
  7. capture negative controls and official checks;
  8. reconcile affected requirements, architecture, logs, and durable state.
- Outputs: accepted three-pilot evidence with original/candidate/patch/facts/plan/verifier files.
- Validation: separate verifier plus focused, integration, regression, local-live, and no-op
  proofs.
- Exit: all three pass deterministic and independent verification and need no manual prose
  repair.
- Status: **IMPLEMENTED_BUT_UNVERIFIED / IN_PROGRESS**.
- Remaining: all steps above except initial implementation and producer bundles.

### Phase 3: complete local central-agent resilience

- Purpose: prove all locally testable surfaces and recovery in one canonical run.
- Entry: README proposal task closed.
- Steps: README, metadata, community, visual/manual handoff, package/release audit, generated
  signals, cross-surface validation; no-op/change/overwrite/malformed/injection/fact
  conflict/duplicate/outage/checkpoint/specialist-failure/evidence-corruption scenarios.
- Outputs: `LocalProofManifestV1` and consolidated acceptance report.
- Validation: local E2E, fault injection, independent evidence reproduction, all safety tests.
- Exit: every applicable `idea.md` obligation is terminal and reproducible; no product remote
  touched.
- Status: **NOT STARTED** (`L8-LOCAL-CENTRAL-AGENT-RESILIENCE`).

### Phase 4: complete workflow under `act`

- Purpose: prove actual Actions-compatible orchestration.
- Entry: local resilience closed.
- Steps: isolated auth provider/remotes, full planning/supervise/recovery/evidence/health jobs,
  dispatch/dedup/recovery/matrix isolation.
- Outputs: raw Docker/`act` logs, versions, job results, checksums.
- Validation: real `act`, actionlint, official checks.
- Exit: every applicable workflow job reaches honest terminal state; planning-only is failure.
- Status: **NOT STARTED** (`L8-ACT-CANONICAL-WORKFLOW-PARITY`).

### Phase 5: disposable GitHub staging

- Purpose: prove exactly-once draft PR effects without touching production.
- Entry: full `act` gate closed.
- Steps: disposable repositories, staging credential, `VerifiedPresentationCandidateV1`,
  `VerifiedProposalV1`, `OpenProposalV2`, create/no-op/update/drift/dedup/lost-response/
  expiry/crash matrix.
- Outputs: staging PR/effect/reconciliation evidence.
- Validation: independent proposal review; default branch byte-identical.
- Exit: exactly one correct draft state for each scenario.
- Status: **NOT STARTED** (`L8-STAGING-VERIFIED-PROPOSAL-PROOF`).

### Phase 6: production runtime, truth, presentation, and proposals

- Purpose: close parent Waves 2-5 under real authorization.
- Entry: all pre-production gates closed and dependency guard repaired.
- Steps:
  - Wave 2: App auth, hosted recovery, health, dead-man, terminal manifests.
  - Wave 3: portfolio facts, ownership, conflicts, protected content, isolated verification.
  - Wave 4: complete surfaces/archetypes and governed golden set.
  - Wave 5: exactly-once verified draft proposal lifecycle.
- Outputs: hosted production-like evidence for each parent taskcard.
- Validation: live authorized checks, no token-boundary violations, independent reproduction.
- Exit: every Wave 2-5 taskcard passes its explicit closeout rules.
- Status: **PARTIAL foundation only**; Wave 2 is `BLOCKED_EXTERNAL`, Waves 3-5 `TODO`.

### Phase 7: controlled Level-5 Java pilot

- Purpose: prove the complete production-like lifecycle on 3D, Cells, and PDF Java.
- Entry: Wave 5 closed and fresh per-push authorization available.
- Steps: baseline, facts, every surface, verified draft PR, no-op, targeted change, overwrite,
  resume, duplicate, failure, evidence, independent review.
- Outputs: complete pilot bundles and Level-5 reviewer decision.
- Validation: real governed pilot, read-only reconciliation, checksum replay.
- Exit: independent Level-5 award.
- Status: **NOT STARTED** (`L8-WAVE6-CONTROLLED-JAVA-PILOT`).

### Phase 8: heterogeneous Levels 6-7

- Purpose: prove the active portfolio and one lifecycle per ecosystem.
- Entry: Level 5.
- Steps: all-registry observe/proposal, Java/.NET/Python/TypeScript/C++/Go/supported Rust
  lifecycle, health/alerts/recovery, 30-day clean window.
- Outputs: portfolio manifests and 30-day series.
- Validation: daily reconciliation and independent portfolio audit.
- Exit: Level 6 autonomous operation and Level 7 30-day acceptance.
- Status: **NOT STARTED** (`L8-WAVE7-HETEROGENEOUS-PORTFOLIO`).

### Phase 9: 90-day Level 8

- Purpose: prove sustained self-maintenance.
- Entry: Level 7.
- Steps: weekly full/incremental audits, discovery proposals, route disablement, dependency/SBOM/
  vulnerability monitoring, authorization expiry, migrations, freshness, dead-man, quality and
  traffic reports.
- Outputs: 90-day manifest/health series and independent audit.
- Validation: daily/weekly reconciliation and final full replay.
- Exit: every decision-76 metric passes and independent audit awards Level 8.
- Status: **NOT STARTED** (`L8-WAVE8-NINETY-DAY-SELF-MAINTENANCE`).

## 6. Work Completed

### Verified complete

| Task/requirement | Work and affected paths | Verification/evidence | Limitation |
|---|---|---|---|
| `L8-MISSION-CONTROL-CONSUMER` | Durable mission schema, loader, selection, transitions in `src/readme_agent/supervisor/mission_*` | `plans/investigations/evidence/level8-autonomous-mission-control/mission-control-verification.json`; durable transitions | Mission graph still has the Wave-2 dependency gap |
| `L8-REQUIREMENT-TO-TASKCARD-COVERAGE` | Requirement inventory and mapping | `plans/investigations/evidence/level8-requirement-taskcard-coverage/requirement-taskcard-coverage.json` | Must regenerate after future task/requirement edits |
| Wave 0 bounded gates | Candidate preservation, semantic closure, master consolidation, fresh-clone reproduction | commits `146d81d`, `9376436`; `plans/investigations/evidence/level8-wave0-*` | Master Status later became stale |
| `L8-WAVE1-CANONICAL-SAFETY-SPINE` / `L8-002` / `VER-009` | Canonical runtime, typed capability contracts, fail-closed classifications, cancellation cleanup | `plans/investigations/evidence/level8-wave1-heterogeneous-fail-closed-2026-07-23/`; durable `CLOSED` | Later production credentials and hosted proof remain open |
| `L8-PREPRODUCTION-TRUTHFUL-BASELINE` | `finding_status.py`, `work_ledger.py`, convergence/stop/prompt fixes | commits `946081e`, `05589be`; `plans/investigations/evidence/level8-preproduction-truthful-baseline-2026-07-24/` | Does not prove complete product presentation |
| `L8-LOCAL-IMMUTABLE-SNAPSHOT-AND-FACTS` / local scope of `L8-006` | Snapshot, policy/repository ingestion, source builds, examples | commit `5e31f9c`; separate verifier and evidence in `plans/investigations/evidence/level8-local-immutable-snapshot-and-facts-2026-07-24/` | Three Java pilots only |

### Implemented but unverified

| Item | Existing implementation | Evidence | Missing proof |
|---|---|---|---|
| `L8-LOCAL-README-PROPOSAL-PROOF` foundation | `readme/document_plan.py`, 474-line `document_renderer.py`, `document_validation.py`, `idea_candidate.py`, `presentation/document_planner.py`, templates and capability wiring | commit `5d2256b`; bundles at `plans/investigations/evidence/level8-local-readme-proposals-2026-07-24/` | Separate verifier, supervisor E2E, cross-pilot/editorial proof, compliant module split |
| Three candidate outcomes | Cells false Maven install corrected; 3D opening promotion removed; PDF badge/version corrected; all get verified acquisition/example | `local-proof-manifest-v1.json` and per-pilot artifacts | Producer authored its own acceptance |
| 1,344-test result at `5d2256b` | Recorded in `logs/2026-07-24.md` | Log assertion and observed prior session | No committed raw test log in latest proposal evidence; rerun/capture required |

### Partial

- `L8-003` through `L8-005`: lifecycle/checkpoint/health/manifest contracts exist locally, but
  hosted interruption, external monitor, retention, and complete production proof remain open.
- `L8-007`: typed plan and protected-content foundation exists, but complete surfaces,
  archetypes, golden-set threshold, and portfolio proof remain open.
- `L8-008`: existing PR opener/OpenProposalV1 are insufficient for the required V2 lifecycle.
- `L8-012`: golden-set and route-disable foundations exist, but 100 evaluations across three
  sessions and production monitoring remain open.
- `L8-014`: truthful baseline and immutable facts are closed; README, complete local, `act`, and
  staging remain open.

### Claimed but unverified

- Each latest per-pilot `independent-review.json` claims
  `deterministic-independent-local-proposal-reviewer`, but
  `plans/investigations/tools/collect_local_readme_proposal_evidence.py` creates both candidate
  and verdict. It is a producer self-check.
- `local-proof-manifest-v1.json` says `accepted: true`; this proves the producer's internal gates,
  not the task's independent acceptance.

### Stale or contradicted

- **STALE:** `plans/master.md` Status “Wave 2 active” versus durable local README task.
- **STALE:** static taskcard `status:` declarations versus durable state 81.
- **STALE:** earlier state-68 checkpoints as current-state descriptions.
- **CONTRADICTED:** any claim that the current `act` proof exercises the complete workflow;
  `plans/investigations/preproduction-idea-fidelity-gate-2026-07-24.md` records that it ran only
  matrix planning.
- **CONTRADICTED:** any claim that the system is Level 7/8 or production-ready; required staging,
  production, heterogeneous, 30-day, and 90-day evidence does not exist.

## 7. Current Working State

### Work being performed when handover was requested

The active child was implementing complete-document README proposals. The previous agent:

1. committed the document planning/rendering foundation at `5d2256b`;
2. generated the three proposal bundles;
3. committed them at `ab8a54d`;
4. deliberately left the durable task `IN_PROGRESS`;
5. documented the remaining verifier, renderer, supervisor, and editorial gates; and
6. stopped without production work.

### Relevant working tree

Before this canonical handover rewrite, the only non-handover changes were user-owned:

```text
 M AGENTS.md
 M plans/idea.md
?? plans/changelog.md
?? plans/roadmap.md
?? plans/status.md
```

They must not be staged, normalized, reset, deleted, or treated as execution authority without
explicit user disposition.

This handover task replaces the previously committed eight overlapping files under
`plans/codex/handover/` with only `HANDOVER.md`, `CONTINUE.md`, and `state.json`. Those are the
only agent-owned current worktree changes.

### Current execution boundary

- Last verified successful boundary:
  `L8-LOCAL-IMMUTABLE-SNAPSHOT-AND-FACTS = CLOSED`.
- Current boundary:
  `L8-LOCAL-README-PROPOSAL-PROOF = IN_PROGRESS`.
- Latest implementation:
  `5d2256b`.
- Latest evidence checkpoint:
  `ab8a54d`.
- Latest handover-only HEAD:
  `c3dcdc7`.

### Latest unresolved boundary and root cause

The proposal output exists but independent acceptance does not. Root cause is known:

- the evidence producer also writes the review verdict;
- the renderer violates code-organization constraints;
- complete candidates were not replayed through canonical supervisor E2E;
- cross-pilot/editorial specificity checks are inadequate.

The next step is the renderer split followed by the separate verifier—not `act`, staging,
production authentication, or another plan.

## 8. Remaining Gaps

### `readme-renderer-responsibility-split`

- Requirement: `plans/GOVERNANCE.md`, “Code organization: no monoliths.”
- Severity: P0 for active-task acceptance.
- Evidence: `src/readme_agent/readme/document_renderer.py` = 474 lines.
- First failing boundary: implementation maintainability/governance.
- Root cause: structure parsing, templates, value formatting, operation construction/application,
  and orchestration accumulated in one non-wiring module.
- Permanent solution: split into public responsibility modules; suggested seams are document
  structure, templates, operations, and orchestration.
- Exact next action: inspect file/history, split without behavioral changes, update module map
  and mirrored tests.
- Required proof: three candidate hashes unchanged; focused tests and full official checks pass.

### `separate-readme-proposal-verification`

- Affected requirements: `VER-001`, `L8-007`, active task closeout.
- Severity: P0.
- Evidence: producer function `_pilot_bundle()` creates candidate and `independent-review.json`.
- First failing boundary: independent verification.
- Root cause: reviewer identity is a label, not an independently executed consumer.
- Permanent solution: production verification seam plus
  `plans/investigations/tools/verify_local_readme_proposal_evidence.py`.
- Exact next action: validate schemas/checksums, reconstruct operations, Git-apply patch, recompute
  facts/template/candidate hashes, inspect protected losses, and issue separate verdict.
- Required proof: accepted originals plus tampered candidate/fact/plan/checksum/fake-review
  negatives.

### `cross-pilot-editorial-specificity`

- Affected requirement: active task “repository-specific and no manual prose repair.”
- Severity: P0.
- Evidence: current producer checks only product identity plus deterministic booleans.
- First failing boundary: reviewer acceptance.
- Root cause: no robust cross-pilot similarity, wrong-product-token, or editorial assessment.
- Permanent solution: deterministic wrong-product/similarity checks plus independent editorial
  review after factual gates.
- Exact next action: compare audience/problem/capability/format/example/import/coordinates and
  normalized prose across all three.
- Required proof: reject a copied candidate with name substitution; accept real product-specific
  candidates without unsupported prose.

### `canonical-supervisor-proposal-proof`

- Affected requirement: active task verification and `L8-014`.
- Severity: P0.
- Evidence: producer invokes contracts directly; no committed post-`5d2256b` supervisor bundle.
- First failing boundary: canonical runtime integration.
- Root cause: evidence generation stopped at deterministic contract layer.
- Permanent solution: run `readme-agent supervise` against each pilot in `local_dry_run`, first
  focused on `readme_presentation`, then required integrated scope.
- Exact next action: after verifier passes, execute and capture selected capabilities, work
  ledger, facts/plan hashes, terminal state, exit code, and zero product writes.
- Required proof: first run proposal-ready; identical rerun no-op/no duplicate/no unnecessary LLM.

### `preproduction-wave2-dependency-gate`

- Affected requirement: `L8-014`.
- Severity: P0 before production unblock.
- Evidence: graph dependency and `mission_control.py::_DEPENDENCY_SATISFIED` include `REROUTED`.
- First failing boundary: task eligibility.
- Root cause: Wave 2 depends on rerouted parent rather than final staging child.
- Permanent solution: add dependency on `L8-STAGING-VERIFIED-PROPOSAL-PROOF` or equivalent explicit
  gate and negative test.
- Exact next action: fix only after the current README task, before reopening Wave 2; regenerate
  coverage and persist evaluation.
- Required proof: Wave 2 cannot become eligible after only parent reroute.

### `production-github-app-and-authority`

- Affected requirements: `L8-001`, `L8-008`, `L8-009`.
- Severity: external but intentionally deferred.
- Evidence: durable Wave 2 `BLOCKED_EXTERNAL`; no production App secrets are required now.
- Unblock condition: local, `act`, and staging gates pass; agent provides exact permissions,
  installation scope, secret names, and resume test.
- Human action: register/install App and provide secrets/authorizations at that later gate.
- Required proof: fresh short-lived tokens, no PAT fallback, analysis/effect token isolation.

## 9. Ordered Execution Queue

### Critical path

```text
L8-LOCAL-README-PROPOSAL-PROOF
  -> L8-LOCAL-CENTRAL-AGENT-RESILIENCE
  -> L8-ACT-CANONICAL-WORKFLOW-PARITY
  -> L8-STAGING-VERIFIED-PROPOSAL-PROOF
  -> repair/reconcile pre-production parent and Wave-2 dependency
  -> L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME
  -> L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP
  -> L8-WAVE4-PRESENTATION-INTELLIGENCE
  -> L8-WAVE5-VERIFIED-PROPOSAL-LIFECYCLE
  -> L8-WAVE6-CONTROLLED-JAVA-PILOT
  -> L8-WAVE7-HETEROGENEOUS-PORTFOLIO
  -> L8-WAVE8-NINETY-DAY-SELF-MAINTENANCE
```

The parent `L8-PREPRODUCTION-IDEA-FIDELITY-GATE` and
`L8-WAVE0-PLAN-TRUTH-RECONCILIATION` are `REROUTED`. They eventually require governed
reconciliation to `CLOSED`, because `evaluate_mission()` requires every task closed for
`mission_complete=true`.

### Task 1: `L8-LOCAL-README-PROPOSAL-PROOF` — execute now

- Objective: independently accepted, reviewer-ready Cells/3D/PDF Java README proposals.
- Allowed paths: `src/readme_agent/`, `tests/`, `prompts/`, `templates/`, `docs/`,
  `plans/investigations/`, `logs/`.
- Dependency: immutable snapshot/facts child is closed.
- Implementation:
  1. predecessor evidence recheck;
  2. renderer responsibility split;
  3. separate verifier and negative controls;
  4. cross-pilot/editorial checks;
  5. canonical supervisor three-pilot run;
  6. unchanged reruns;
  7. new immutable evidence root;
  8. requirements/docs/log reconciliation.
- Focused proof: document structure/template/operations/plan/verifier tests.
- Integration/regression: capabilities, specialists, supervisor, safety, official checks.
- E2E: three `local_dry_run` supervisor runs plus no-op reruns.
- Acceptance: taskcard closeout rules both true.

### Task 2: `L8-LOCAL-CENTRAL-AGENT-RESILIENCE`

- Objective: complete local multi-surface behavior and fault recovery.
- Allowed paths: `src/readme_agent/`, `tests/`, `config/`, `docs/`,
  `plans/investigations/`, `logs/`.
- Dependency: Task 1 closed.
- Implementation: all surfaces and named no-op/change/overwrite/injection/conflict/duplicate/
  outage/checkpoint/specialist/evidence scenarios.
- Focused proof: each surface and failure producer.
- Integration/regression: one-command local pipeline, complete safety suite.
- E2E: three pilots, all applicable surfaces, independent manifest reproduction.
- Acceptance: every local `idea.md` obligation terminal; no product remote touched.

### Task 3: `L8-ACT-CANONICAL-WORKFLOW-PARITY`

- Objective: full current workflow in Docker/`act`.
- Allowed paths: `src/readme_agent/`, `tests/`, `.github/workflows/`, `docs/`,
  `plans/investigations/`, `logs/`.
- Dependency: Task 2 closed.
- Implementation: isolated auth/state/targets, all jobs/triggers, recovery and matrix isolation.
- Focused proof: workflow contract and actionlint.
- Integration/regression: real `act`, official checks.
- E2E: planning through supervise/evidence/health; plan-only is rejection.
- Acceptance: every applicable workflow job terminal and reproducible.

### Task 4: `L8-STAGING-VERIFIED-PROPOSAL-PROOF`

- Objective: exactly-once draft proposals in disposable staging.
- Allowed paths: `src/readme_agent/`, `tests/`, `.github/workflows/`, `config/`, `docs/`,
  `plans/investigations/`, `logs/`.
- Dependency: Task 3 closed.
- Implementation: candidate/proposal/open-proposal contracts and lifecycle matrix.
- Focused proof: local bare-remote scenarios.
- Integration/regression: real disposable GitHub staging.
- E2E: create/no-op/update/drift/dedup/lost-response/expiry/crashes.
- Acceptance: one correct draft state; default branch byte-identical.
- External input: staging target/credential only when reached.

### Task 5: Wave 2 and pre-production reconciliation

- Objective: mechanically gate and complete restartable hosted runtime.
- Allowed paths: taskcard Wave-2 paths plus task graph/coverage for dependency repair.
- Dependencies: staging proof and fresh production authority.
- Implementation: dependency negative control, App auth, hosted checkpoints/recovery/health/
  dead-man/manifest retention.
- Verification: fault injection, hosted workflow, state outage, duplicate/matrix isolation.
- Acceptance: every accepted trigger terminal/visible and all Wave-2 exit gates pass.

### Task 6: `L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP`

- Objective: portfolio-wide provenance and ownership.
- Allowed paths: `src/readme_agent/`, `tests/`, `config/policies/`, `docs/`, evidence.
- Dependencies: Wave 2 and closed local facts foundation.
- Implementation: all repositories/ecosystems, conflicts, protected content, prompt injection,
  isolated acquisition/examples.
- Verification: false-coordinate/conflict/protected-loss negative controls and real checks.
- Acceptance: Wave-3 closeout.

### Task 7: `L8-WAVE4-PRESENTATION-INTELLIGENCE`

- Objective: complete repository-specific presentation surfaces.
- Allowed paths: `src/`, tests, templates, prompts, docs, evidence, dependencies.
- Dependencies: Wave 3 and local presentation foundation.
- Implementation: ten dimensions, archetypes, surfaces, 100-case/3-session golden set.
- Verification: 100% deterministic and >=95% agentic result.
- Acceptance: no unsupported/template/ownership loss; reviewer needs no prose repair.

### Task 8: `L8-WAVE5-VERIFIED-PROPOSAL-LIFECYCLE`

- Objective: exactly-once verified draft effects.
- Allowed paths: `src/`, tests, workflows, docs, evidence.
- Dependency: Wave 4.
- Implementation: V1/V2 contracts, branch/PR lifecycle, drift/retry/expiry/crash/token isolation.
- Verification: local bare remote and authorized live draft proof.
- Acceptance: every scenario produces one correct state and no pre-effect write token.

### Task 9: `L8-WAVE6-CONTROLLED-JAVA-PILOT`

- Objective: Level 5.
- Allowed paths: runtime evidence, live integration tests, authorized target proposal branches.
- Dependency: Wave 5.
- Implementation/proof: complete three-repository scenario matrix.
- Acceptance: independent Level-5 award.
- External input: fresh what/why/where confirmation for each product push.

### Task 10: `L8-WAVE7-HETEROGENEOUS-PORTFOLIO`

- Objective: Levels 6-7.
- Dependencies: Level 5.
- Implementation: all active repositories, one lifecycle per supported ecosystem, 30-day window.
- Verification: scheduled/event runs, daily reconciliation, independent audit.
- Acceptance: Level 6 automation and Level 7 clean-window gates.

### Task 11: `L8-WAVE8-NINETY-DAY-SELF-MAINTENANCE`

- Objective: Level 8.
- Dependency: Level 7.
- Implementation: monitoring, discovery, route health, dependency/security, expiry, migrations,
  freshness, reports, 90-day series.
- Verification: daily/weekly sampling and final independent replay.
- Acceptance: every quantitative threshold and independent Level-8 award.

No later task is ready while the current task is active. A failing lane may be repaired while
unrelated eligible work continues, but no dependency may be skipped.

## 10. Decisions and Constraints

### User decisions

- Control repository uses `main` only.
- Prove locally, then under `act`, then staging, before production App/secrets.
- Human supplies authority/secrets only when the relevant gate is reached.
- Codex/receiving agent owns planning, implementation, execution, verification, evidence,
  remediation, and continuation.

### Architecture decisions

- `supervise` is the only production runtime (decision 73).
- GitHub Actions is production compute.
- Versioned trigger/checkpoint recovery is mandatory (decision 74).
- `VerifiedProposalV1` is the immutable boundary before effects (decision 75).
- Maturity is awarded by elapsed production evidence (decision 76).
- Git-ref durable state remains unless measured needs justify replacement.
- Agentic results are proposals/actions; deterministic gates retain authority.

### Repository commands and environment

- Use `.venv/Scripts/python` and `.venv/Scripts/readme-agent`; never global Python/pip.
- PowerShell is the current shell.
- Search with `rg`.
- Use `apply_patch` for hand edits.
- Production code belongs in `src/readme_agent/`; tests mirror modules.
- Templates/prompts live only in their governed directories.
- Update `docs/architecture.md` when adding/splitting production modules.

### Safety

- Allow-list before network access, using listed/permitted gate appropriate to side effect.
- Work clones keep push remote disabled and pre-push hook blocking.
- Evidence goes through redaction.
- No product push without fresh exact what/why/where approval.
- No default-branch write, merge, force push, package/release write, or generated-surface write.
- Production App token only in final authorized effect job; no PAT fallback.

### Governance

- Read and investigate history before overwrite/delete.
- `plans/master.md` requires fresh approval naming exact sections.
- `plans/requirements.md` changes must be surgical and evidence-backed.
- Append history through `scripts/governance/append_log_entry.py`.
- Preserve the five user-owned dirty paths.
- Every AI-authored commit needs the correct `Co-Authored-By` trailer.
- New machinery names must be self-explanatory; no vague/enumerated artifacts.
- A new non-blocking gap becomes a `BACKLOG` requirement; a task blocker is fixed first.

### Prohibited shortcuts

- No new plan/controller/queue.
- No task closure from implementation or mocked tests alone.
- No producer self-acceptance called independent.
- No fixture-only replacement for canonical supervisor or workflow proof.
- No generic full-document LLM rewrite.
- No feature branch in the control repository.
- No production access request before staging.
- No test expectation change without inspecting the fixture's real findings.
- No reset/clean/restore/force operations against user work.

## 11. Tests, Proof, and Evidence

### Commands/results directly rechecked for this handover

```powershell
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short
Get-FileHash plans/master.md,plans/requirements.md,
  plans/investigations/control/level8-autonomous-mission-task-graph.yaml,
  plans/idea.md -Algorithm SHA256
.venv/Scripts/readme-agent supervise --mission-task-graph `
  plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
  --mission-action status
```

Observed:

- root, branch, HEAD, divergence, and dirty paths match section 1/7;
- master, requirements, graph, and idea hashes match the snapshot;
- mission state version is 81;
- active task is README proposal proof;
- unresolved tasks = 10, blocked external tasks = 1, mission complete = false.

### Truthful baseline proof

```text
plans/investigations/evidence/level8-preproduction-truthful-baseline-2026-07-24/
```

Contains raw focused/official logs, before/after terminal evidence, checksums, and acceptance.

### Immutable facts proof

```text
plans/investigations/evidence/level8-local-immutable-snapshot-and-facts-2026-07-24/
```

Contains a separate verifier, source-build/example results, official checks, and checksums.
Classification: VERIFIED for the bounded three-pilot child.

### Latest proposal proof

```text
plans/investigations/evidence/level8-local-readme-proposals-2026-07-24/
```

The root 29-entry SHA-256 inventory was rechecked successfully during the preceding checkpoint.
The candidate hashes are:

```text
Cells: 43fae20ac1561fbe3ba094310be514b1d3d5bf21ea474a1f9d88ea35af5d7fba
3D:    9ed32c5eeabfb70f6e0fc98c607b337dbb1944b1fb2eb5dc0d7cdef971ccee8b
PDF:   1dc2ffd5ffb692f5239fd910f755de1704400f64a931656e37bc982c0bdb4030
```

Classification: IMPLEMENTED_BUT_UNVERIFIED as independent task acceptance.

### Tests not yet sufficient or not yet run

- No committed raw 1,344-test log for the latest proposal commit.
- No separate finished-bundle verifier for latest proposals.
- No post-`5d2256b` canonical supervisor three-pilot E2E bundle.
- No cross-pilot copied-template negative control.
- No complete local multi-surface/fault proof.
- Existing `act` evidence is planning-only and insufficient.
- No staging proof.
- No production App/hosted recovery/pilot/30-day/90-day proof.

### Required next official gate

```powershell
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m ruff format --check .
.venv/Scripts/python -m mypy src
.venv/Scripts/python -m pytest -q
.venv/Scripts/python scripts/governance/validate_plan_structure.py
actionlint
```

Capture raw logs and checksums against the exact implementation commit.

## 12. Risks and Uncertainty

- The user-owned `plans/idea.md` and `AGENTS.md` are modified but uncommitted. They are current
  local inputs and may be absent from another clone.
- Six mission/handover commits are not on `origin/main`; a remote-only receiving environment will
  miss them.
- Master Status is stale and cannot be edited without fresh approval.
- The Wave-2 dependency graph can be reopened too early unless repaired.
- The mission completion evaluator requires every task `CLOSED`; rerouted parents need eventual
  reconciliation.
- Latest candidate prose may still need editorial repair; current evidence is too weak to prove
  otherwise.
- Renderer refactoring could change byte offsets/hashes; preserve candidate hashes as a negative
  regression boundary.
- Live dynamic planning may expose additional work-ledger/stop defects; repair the first producer
  boundary instead of bypassing it.
- Local `act` may differ from hosted Actions; both proofs remain required.
- Staging repository creation and token scope are future human authority dependencies, not current
  blockers.
- Production App, analytics, dead-man endpoint, product write confirmations, and independent
  elapsed-window reviewer are later external dependencies.

## 13. Receiving Agent Startup Steps

1. Start at
   `D:\Users\prora\OneDrive\Documents\GitHub\foss-readme-optimizer`.
2. Read completely:
   `AGENTS.md`, `plans/GOVERNANCE.md`, `plans/idea.md`, `plans/master.md`,
   `plans/requirements.md`, the locked task graph, `HANDOVER.md`, `CONTINUE.md`, and
   `state.json`.
3. Verify authority hashes from section 1 and confirm the graph hash equals durable state.
4. Run `git status --short`, confirm `main`, verify HEAD, and preserve the five user-owned paths.
5. Run mission `status`; do not `claim` because the README task is active.
6. Recheck the immediately preceding immutable-facts evidence with its existing separate verifier.
7. Execute the first action: split `document_renderer.py` by responsibility while preserving all
   three candidate hashes.
8. Implement the separate finished-bundle verifier and its tamper/copy negative controls.
9. Run focused tests, then canonical three-pilot supervisor and no-op proof, then official checks.
10. Create a new checksum-complete acceptance evidence root; do not overwrite the checkpoint.
11. Reconcile only evidence-supported requirement clauses, architecture, coverage, and logs.
12. Commit coherent changes on `main` with required attribution.
13. Transition the active task one legal state at a time using exact commit/evidence references
    and a verifier identity distinct from the producer.
14. Claim the next ready task only after closure; expected next task is local resilience.
15. Continue through the ordered queue without asking the user for routine operation.
16. Stop only at mission completion or when all remaining work is blocked by proven external
    authority. Log exact unblock conditions.

Resume-status command:

```powershell
.venv/Scripts/readme-agent supervise `
  --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
  --mission-action status `
  --mission-observer "<receiving-agent>"
```

## 14. Closure Standard

The receiving agent may declare the mission complete only when:

- every mandatory requirement is evidence-supported at its full scope;
- every taskcard, including rerouted parents, is reconciled to `CLOSED`;
- the durable evaluator reports no remaining/eligible work and `mission_complete=true`;
- direct local, complete `act`, and isolated staging gates passed in order;
- production App/token isolation and hosted recovery passed;
- the controlled Java pilot earned Level 5;
- every active registry repository and supported ecosystem earned the required Level-6/7 proof;
- the 30-day Level-7 and 90-day Level-8 windows passed with no prohibited writes, duplicate
  effects, or false success;
- every terminal run has a valid checksum-complete manifest;
- eligible autonomous completion is at least 99%;
- outage recovery and proposal visibility meet 24-hour limits;
- deterministic validation is 100% and agentic accuracy at least 95%;
- business/referral reporting is operational without overriding trust; and
- an independent reviewer reproduces the full evidence and explicitly awards Level 8.

Until then, the correct mission status is partial, blocked, retryable, or in progress—never
complete by assertion.
