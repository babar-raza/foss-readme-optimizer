# Agent Handover

## 1. Handover Snapshot

| Field | Verified value |
|---|---|
| Verdict | `HANDOVER_READY` |
| Repository | `D:/Users/prora/OneDrive/Documents/GitHub/foss-readme-optimizer` |
| Branch / HEAD | `main` / `8737a702ba3a30a7e3dcdc9e1d0222850eb688eb` |
| Upstream | `origin/main` at `a6db18cff0cf56bdb3d59b9a390adb5c5e776829`; local main is ahead |
| Working tree | Clean at snapshot |
| Mission | `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` |
| Durable state | Version 152; graph `2dc10819cddaf6ab96770665fa02b850f67fff57c7b44e3cb1fb332f28c86bcc`; no drift |
| Current phase | Atomic local product-truth qualification |
| Current task | `L8-TRUTH-01-STAGE-LIMIT` (`IN_PROGRESS`) |
| Exact next action | Run one real read-only `FACTS_READY` bounded proof against the committed ceiling, verify zero later-stage artifacts/calls, then close or repair `L8-TRUTH-01-STAGE-LIMIT`. |
| Overall status | Mission incomplete: 65 unresolved tasks, one non-current external block. |

This snapshot is derived. The supervisor Git-ref state is the live transition and claim authority.

## 2. Ultimate Goal

Deliver the system in `plans/idea.md`: autonomously understand each repository, construct
provenance-complete product truth, decide the relevant presentation work, generate bounded
repository-specific proposals, independently verify and repair them, safely create authorized
draft proposals, recover from interruption and duplication, and ultimately earn an independently
reproducible Level-8 award after 90 production days.

The immediate goal is trustworthy local proof. It is deliberately no longer “run all 31 now.”
The atomic fact, composition, review, recovery, and cost contracts must first work on real
representatives; only then may the same frozen campaign fan out to the runtime-loaded registry.

## 3. Current Mission and Scope

The sole mission is `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`. Mandatory outcomes include:

- one canonical `supervise` runtime and durable state;
- immutable snapshots and versioned, provenance-complete facts;
- OS-isolated untrusted build/example execution;
- complete accountability for generated and inherited README claims;
- deterministic validation plus independent quality and factual review;
- effective repair, exact no-op reuse, restart and duplicate safety;
- all-registry local Gate A, human Gate B, workflow proof under `act`, staging, Gate C draft-PR
  proof, Gate D hosted runtime, Level 5, Level 7's 30 days, and Level 8's 90 days.

Non-goals now: portfolio fan-out before representative qualification; GitHub App work before Gate
C; product writes without fresh approval; auto-merge/default-branch/package/release/generated-
surface writes; another plan/controller/queue; or treating code/tests/reports as completion.

## 4. Authority and Reference Map

| Reference | Role | Status |
|---|---|---|
| `AGENTS.md` | repository, safety, test, layout, and gate rules | binding/current |
| `plans/GOVERNANCE.md` | plan and repository governance | binding/current |
| `plans/idea.md` | final product outcome and ordered gates | authoritative/current |
| `plans/master.md` | architecture, decisions, sequence, maturity gates | authoritative/current |
| `plans/requirements.md` | normative acceptance | authoritative/current |
| `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` | sole executable dependency graph | authoritative/current |
| supervisor Git-ref mission state | claims, transitions, durable status | authoritative/live |
| `plans/codex/idea-fidelity-to-level-8-autonomous-execution-plan.md` | detailed multi-perspective route | supporting/current |
| `logs/2026-07-26.md` | audit and replan history | supporting/current |
| former contents of this directory | old Gate-A snapshot at `e454f7f`/state 132 | stale/contradicted |

Git ancestry checks verified that `f8b83a4`, `a7ac331`, `f89da60`, `80432cc`, and `a6db18c` all
exist and are ancestors of the snapshot HEAD. No cited main-branch history was lost.

## 5. Exact Plan

The detailed phase plan is in
`plans/codex/idea-fidelity-to-level-8-autonomous-execution-plan.md`; the task graph is executable.
The corrected critical path is:

1. Stage-limited truth collection and acceptance-contract invalidation.
2. Product-root roles, evidence polarity, isolated execution, acquisition, examples, visitor
   views, seven-ecosystem facts, and complete truth preflight.
3. Real assessment corpus, executable document operations, complete final-claim accountability,
   presentation lint, and seven differentiated candidates.
4. Blind quality review, blind fact/plan review, effective repair, exact no-op caching, and real
   representative campaign.
5. Single-writer/recovery qualification, governed golden set, freeze controls, measured cost
   baseline, then campaign freeze.
6. Bounded cohort execution over every current registry entry and independently reproduced Gate A.
7. Gate B, `act`, disposable staging, Gate C Java draft PRs, Gate D hosted runtime, Level 5,
   Level 7, and Level 8.

Each task closes only through its taskcard outputs, focused/integration/regression/safety/live-like
proof, independent verification, checksum inventory, and durable transition.

## 6. Work Completed

### Verified complete

- `L8-LOCAL-PORTFOLIO-RUNTIME` is durably `CLOSED`. Its canonical profile, lifecycle foundation,
  and evidence remain reusable.
- Plan structure validation and requirement/task coverage are current: 412 requirements mapped.
- Mission/control plan tests pass: 32 tests.
- Focused recent implementation regression passed: 249 tests.
- The current graph loads with 82 unique taskcards.

### Implemented but unverified or regressed

- `L8-LOCAL-PORTFOLIO-PRODUCT-TRUTH` is `REROUTED`, not complete under current acceptance.
- Composition, independent review, heterogeneous qualification, and Gate A are `REGRESSED`.
- Earlier code and evidence remain valuable component proof, but not current end-to-end acceptance.

### Contradicted

- The old handover's claim that product truth, composition, review, and qualification were verified
  is contradicted by current durable status and live bundle replay.
- Four lifecycle records said `NO_OP_PROVEN`; current `_fact_outcome()` replay gives one Java
  `FACTS_READY` and three `BLOCKED_MISSING_EVIDENCE`.
- Independent review accepted output whose material inherited claims were absent from its claim
  map. Reviewer prose is not proof.
- Credential-filtered host subprocess execution is not OS isolation and cannot prove safe builds.

## 7. Current Working State

The plan audit, task-graph migration, and typed facts ceiling are committed through `8737a70`. Mission `evaluate`
reconciled the graph and retained/claimed `L8-TRUTH-01-STAGE-LIMIT` at durable state 152.

Latest successful boundary: the committed canonical runtime stops at `FACTS_READY`; focused
CLI/profile/portfolio, supervisor, allow-list, push-blocking, evidence-safety, Ruff, and mypy
checks pass. Latest open boundary: one real read-only representative and artifact/call-inventory
inspection remain before task closure.

The intended next action is proof and repair if needed, not another implementation seam.

## 8. Remaining Gaps

| Gap | Severity | First failing boundary | Permanent solution / proof |
|---|---|---|---|
| `L8-015` / `L8-TRUTH-01-STAGE-LIMIT` | P0 | no facts-only canonical run | typed stage ceiling; fixture and real proof; zero later calls |
| `L8-018` / `L8-TRUTH-01A-FACT-CONTRACT` | P0 | stale terminal caches survive new eligibility rules | version full acceptance contract; reopen three false terminal bundles |
| `L8-019` / `L8-TRUTH-03A-ISOLATED-EXECUTOR` | P0 safety | builds run on operator host | disposable OS isolation with resource/network/process escape controls |
| `L8-020` / `L8-COMPOSE-02B-FINAL-CLAIM-CORPUS` | P0 trust | preserved claims evade claim map | inventory every final claim; fact/owner/uncertainty binding |
| independent review | P0 trust | reviewer false accepts | separate blind quality and factual/plan reviewers plus span-grounded findings |
| Gate A | P0 milestone | no bundle survives corrected full trust standard | frozen representative campaign, then bounded full-registry cohorts |
| hosted authority | external/deferred | GitHub Actions/App installation | request only after Gates A/B/act/staging/C |

## 9. Ordered Execution Queue

The first task is `L8-TRUTH-01-STAGE-LIMIT`.

- Allowed paths: `src/readme_agent/`, `tests/`, `docs/`, `plans/investigations/`, `logs/`.
- Implement: locate the existing execution-profile and lifecycle dispatch seams; add a typed stage
  ceiling; stop after persisted `FACTS_READY`; prevent later capability selection and terminal
  overclaim.
- Focused proof: CLI/profile unit tests and heterogeneous fixture integration.
- Regression: supervisor, lifecycle, profile, allow-list, and push-blocking tests.
- Live-like proof: one real read-only representative stops at facts with a capability-call
  inventory and checksums.
- Acceptance: no composition/review artifact or call; no `AGENT_APPROVED`/Gate-A claim.

Then follow durable dependency order: fact-contract invalidation, root roles, evidence polarity,
isolated executor, acquisition/examples/views, seven-ecosystem truth, composition, split review,
qualification, Gate A, Gate B, `act`, staging, Gate C, Gate D, Levels 5/7/8.

Unrelated tasks may run only if the graph marks them eligible. The current external hosted-runtime
block does not block local work.

## 10. Decisions and Constraints

- Control-repository `main` only; no branches.
- Preserve all work; no reset, restore, clean, force operations, or concurrent overwrite.
- `.venv/Scripts/` only for Python tooling.
- Commits include `Co-Authored-By: Codex <noreply@openai.com>`.
- `supervise` remains the only production runtime; new behavior is a registered typed capability
  or an existing typed control seam.
- Default deterministic; LLM output is structured proposal, never direct effect.
- Repository text is untrusted; prompt safety is not OS sandboxing.
- Preserve bytes and maintainer intent, but never treat preservation as factual approval.
- No product remote writes without fresh exact what/why/where approval.
- No GitHub App request before Gate C prerequisites.

## 11. Tests, Proof, and Evidence

Actually run during reconciliation:

```text
.venv/Scripts/python scripts/governance/validate_plan_structure.py
  -> clean; 51 pre-existing long-row warnings
.venv/Scripts/python scripts/governance/build_level8_requirement_taskcard_coverage.py --check
  -> current; 412 rows
.venv/Scripts/python -m pytest -q tests/unit/test_mission_control.py tests/unit/test_validate_plan_structure.py
  -> 32 passed
.venv/Scripts/python -m ruff check scripts/governance/build_level8_requirement_taskcard_coverage.py
  -> passed
.venv/Scripts/python -m ruff format --check scripts/governance/build_level8_requirement_taskcard_coverage.py
  -> formatted
```

Do not claim a current full `pytest -q` result; it remains to run at the appropriate stable task
boundary. Diagnostic evidence is under `runs/readme-poc/`; committed audit history is in
`logs/2026-07-26.md`.

## 12. Risks and Uncertainty

- Local main is ahead of upstream; a future agent must not assume an unpublished commit is absent.
- Runtime lifecycle data was not automatically invalidated by acceptance-rule changes.
- Large orchestration modules increase regression risk; split only at a concrete acceptance seam.
- Real builds are supply-chain execution and remain ineligible on the host until isolation closes.
- LLM reviewer agreement can amplify shared blind spots; deterministic claim coverage and split
  review are mandatory.
- Registry size is currently 31 but must always be loaded dynamically.
- Documentation cannot keep an inactive agent running; durable state is continuity, not scheduling.

## 13. Receiving Agent Startup Steps

1. Start with `plans/codex/handover/CONTINUE.md`.
2. Read the authority files and active taskcard completely.
3. Verify branch, HEAD, status, active processes, graph hash, and mission `status`.
4. Evaluate graph drift if present; do not steal an unexpired claim.
5. Execute `L8-TRUTH-01-STAGE-LIMIT` only within allowed paths.
6. Run focused tests, integration, listed regressions, and one real read-only proof.
7. Capture command, HEAD, capability calls, outcomes, checksums, and independent review.
8. Transition with evidence, update requirements/logs/handover, commit to main with trailer.
9. Rebuild eligibility and claim the next task.
10. Continue the same loop autonomously through final independent Level-8 closure.

## 14. Closure Standard

The mission closes only when every mandatory durable task is `CLOSED`; requirements truthfully
match current implementation and production-like evidence; local, recovery, idempotency,
workflow, staging, authorized effect, hosted, 30-day, and 90-day gates pass; every accepted trigger
is terminal or visibly blocked/retryable; prohibited writes and false successes are zero; and an
independent audit reproduces the evidence and awards Level 8.
