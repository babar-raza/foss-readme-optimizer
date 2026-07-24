# Continuation Prompt for the Receiving Agent

> **AMENDMENT (2026-07-24, later same day).** See `plans/codex/handover/HANDOVER.md`'s own
> amendment banner: both P0 blockers this document lists as still-required-work are closed, a
> critical package-acquisition-truth bug is fixed end-to-end and live-verified, and evidence is
> regenerated. Durable mission state version is 82 (was 81); HEAD is `265bd97`. Read
> `plans/codex/handover/state.json` and `logs/2026-07-24.md` for current truth before following the
> "First task to execute now" section below, which describes the renderer-split/verifier work that
> is now already done.

You are taking over the `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` mission in:

```text
D:/Users/prora/OneDrive/Documents/GitHub/foss-readme-optimizer
```

Operate as the primary strong reasoning agent. Do not launch parallel agents unless a genuinely
independent, necessary investigation cannot be completed efficiently by you.

## Bound authority and current state

Repository snapshot:

```text
branch: main
HEAD at handover verification: c3dcdc75ec448e410cb9a956379cf451527fd66b
origin/main: f8b83a41506fb22a6884f494f1b16ffb8213076e
local divergence: 0 behind, 6 ahead
mission: LEVEL8-CENTRAL-REPOSITORY-PRESENTATION
durable state version: 81
current phase: Pre-production Gate A: direct local idea-fidelity proof
active task: L8-LOCAL-README-PROPOSAL-PROOF
active status: IN_PROGRESS
graph hash: 2ea570475bd6afbe733338e9b4ef3b87e42ede59a9f13140903772b18db0db82
```

Authority roles:

- Vision: `plans/idea.md`.
- Governed specification: `plans/master.md`, SHA-256
  `3387c8ede4e87f7c022c267c77fd82478a3fc90e4e6bb6057f5132002a822eca`.
- Normative obligations: `plans/requirements.md`, SHA-256
  `2fdf55ff4c880966c19afa539bc8ca23091164783adad938ebabdf1f1672e4cd`.
- Locked execution plan:
  `plans/investigations/control/level8-autonomous-mission-task-graph.yaml`, SHA-256
  `2ea570475bd6afbe733338e9b4ef3b87e42ede59a9f13140903772b18db0db82`.
- Current execution state: the durable mission Git ref.
- Complete transfer truth: `plans/codex/handover/HANDOVER.md`.
- Machine-readable queue: `plans/codex/handover/state.json`.

These are one mission with different roles. Do not select, create, merge, or substitute a
competing plan.

There is a documented conflict: `plans/master.md` still says Wave 2 is active, but the later
user-directed requirement `L8-014`, locked task graph, and durable state require local README,
complete local resilience, `act`, and staging before production. Follow the durable local-first
execution state and request fresh section-specific approval before correcting master Status or
checklists.

## Ultimate goal

Deliver and prove the autonomous repository-presentation system described in `plans/idea.md`.
It must continuously reconcile repository-grounded product truth, produce product-specific
fact-backed presentation improvements, independently verify bounded proposals, operate safely and
idempotently through `supervise`, recover durably, and eventually earn:

- Level 5 through the controlled three-Java production-like pilot;
- Levels 6-7 through heterogeneous portfolio proof and 30 clean production days; and
- Level 8 only after 90 clean production days and an independent reproducible award.

Implementation, a passing unit test, or a report is not closure.

## Startup sequence

1. Read completely:
   - `AGENTS.md`;
   - `plans/GOVERNANCE.md`;
   - `plans/idea.md`;
   - `plans/master.md`;
   - `plans/requirements.md`;
   - `plans/investigations/control/level8-autonomous-mission-task-graph.yaml`;
   - `plans/codex/handover/HANDOVER.md`;
   - `plans/codex/handover/state.json`;
   - `docs/architecture.md`; and
   - `docs/safety-model.md`.
2. Verify repository root, `main`, HEAD, upstream divergence, and working tree.
3. Recompute the three authority hashes above.
4. Run:

   ```powershell
   .venv/Scripts/readme-agent supervise `
     --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
     --mission-action status `
     --mission-observer "<your-agent-name>"
   ```

5. Confirm state 81 and active `L8-LOCAL-README-PROPOSAL-PROOF`. Do not call `claim`.
6. Preserve without staging or rewriting:

   ```text
   AGENTS.md
   plans/idea.md
   plans/changelog.md
   plans/roadmap.md
   plans/status.md
   ```

7. Reconcile the immediately preceding child using:

   ```text
   plans/investigations/evidence/
     level8-local-immutable-snapshot-and-facts-2026-07-24/
   ```

   Use its existing separate verifier; do not regenerate sufficient evidence.

## First task to execute now

Exact next action: Split src/readme_agent/readme/document_renderer.py by responsibility without
changing the three committed candidate hashes, then implement a separate verifier that
independently reproduces the three proposal bundles before running the canonical supervisor proof.

Complete `L8-LOCAL-README-PROPOSAL-PROOF`.

The implementation foundation is in:

```text
commit 5d2256b559890353d1a1b3e380cb848f2c831b15
commit ab8a54d9e68eefe25a030498e217a9a62c64c302
plans/investigations/evidence/level8-local-readme-proposals-2026-07-24/
```

Current truth:

- complete candidates exist for Cells Java, 3D Java, and PDF Java;
- producer checks and 29 artifact checksums pass;
- the durable task remains correctly open;
- the producer authored its own `independent-review.json`;
- `document_renderer.py` is 474 lines;
- complete candidates have not been captured through canonical supervisor E2E;
- cross-pilot/no-manual-repair proof is inadequate;
- the logged 1,344-test result lacks a committed raw log in the latest bundle.

Execute in this order:

1. Inspect `src/readme_agent/readme/document_renderer.py`, related modules/tests, and Git history.
2. Split structure parsing, templates, operation application, and orchestration into coherent
   public modules before adding behavior.
3. Preserve these candidate hashes:

   ```text
   Cells: 43fae20ac1561fbe3ba094310be514b1d3d5bf21ea474a1f9d88ea35af5d7fba
   3D:    9ed32c5eeabfb70f6e0fc98c607b337dbb1944b1fb2eb5dc0d7cdef971ccee8b
   PDF:   1dc2ffd5ffb692f5239fd910f755de1704400f64a931656e37bc982c0bdb4030
   ```

4. Update `docs/architecture.md` and split mirrored tests.
5. Implement a separate verifier, preferably:

   ```text
   src/readme_agent/verification/readme_document_candidate.py
   plans/investigations/tools/verify_local_readme_proposal_evidence.py
   ```

6. The verifier must consume finished artifacts without trusting the producer review. It must
   validate schemas/checksums/hashes/facts, reconstruct operations, use native Git patch checks,
   enforce protected-content corrections, and compare cross-pilot specificity.
7. Add negative controls for tampered candidate, fact, operation, checksum, fake accepted review,
   protected loss, and a copied/name-substituted candidate.
8. Run the canonical supervisor for all three pilots in `local_dry_run`, focused first on
   `readme_presentation`, then the required integrated scope. Capture selected capabilities, work
   ledger, hashes, verifier, terminal status, exit code, and zero product writes.
9. Prove identical reruns produce zero diff, no duplicate proposal/effect, and no unnecessary LLM
   call.
10. Produce a new checksum-complete acceptance evidence directory. Do not overwrite
    `level8-local-readme-proposals-2026-07-24/`.
11. Reconcile only proven clauses in `RDM-003`, `RDM-004`, `RDM-007`, `RDM-008`, `RDM-018`,
    `RDM-025`, `L8-007`, and `L8-014`. Keep portfolio/production clauses open.
12. Regenerate requirement/task coverage, update logs through the governance script, and run
    plan validation.

Allowed paths for this task:

```text
src/readme_agent/
tests/
prompts/
templates/
docs/
plans/investigations/
logs/
```

`plans/master.md` and `plans/idea.md` are forbidden for this task absent fresh authority.

## Verification standard

Run focused tests after the smallest complete change. Then run:

```powershell
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m ruff format --check .
.venv/Scripts/python -m mypy src
.venv/Scripts/python -m pytest -q
.venv/Scripts/python scripts/governance/validate_plan_structure.py
actionlint
```

Capture raw output, exit codes, exact commit, versions, and checksums. Verify no repository-scoped
git/Python/`act` helper remains. Never print environment-variable values.

Do not close the task until:

- all three candidates pass deterministic and separately executed independent verification;
- protected content is preserved or exactly fact-corrected;
- the three outputs are repository-specific and need no manual prose repair;
- supervisor E2E and unchanged reruns pass;
- official checks pass;
- evidence is reproducible and checksum-complete; and
- requirements/documentation/durable state match the actual proof.

Commit coherent work directly to `main` with the required AI attribution trailer. Transition
legally:

```text
IN_PROGRESS -> IMPLEMENTED -> VERIFIED -> SCORED -> CLOSED
```

Use a verifier observer distinct from the producer and exact commit/evidence references.

Then call the same supervisor's `claim`. Expected next task:

```text
L8-LOCAL-CENTRAL-AGENT-RESILIENCE
```

If another task is selected, inspect and repair task dependencies rather than overriding the
controller manually.

## Continuous autonomous execution

Continue this exact loop:

```text
READ AUTHORITY
-> RECONCILE CURRENT STATE
-> SELECT THE NEXT READY PLAN-BOUND TASK
-> IMPLEMENT THE SMALLEST COMPLETE FIX
-> RUN FOCUSED VERIFICATION
-> RUN REQUIRED INTEGRATION AND REGRESSION PROOF
-> HEAL FAILURES AT THE FIRST FAILING BOUNDARY
-> UPDATE THE SAME PLAN, TASK, REQUIREMENT, LOG, AND EVIDENCE STATE
-> REBUILD THE REMAINING QUEUE
-> CONTINUE
-> RUN END-TO-END AND PILOT PROOF
-> PERFORM FINAL INDEPENDENT REVIEW
-> RECONCILE AND CLOSE
```

Ordered continuation after the current task:

```text
L8-LOCAL-CENTRAL-AGENT-RESILIENCE
-> L8-ACT-CANONICAL-WORKFLOW-PARITY
-> L8-STAGING-VERIFIED-PROPOSAL-PROOF
-> repair the preproduction/Wave-2 dependency gate
-> L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME
-> L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP
-> L8-WAVE4-PRESENTATION-INTELLIGENCE
-> L8-WAVE5-VERIFIED-PROPOSAL-LIFECYCLE
-> L8-WAVE6-CONTROLLED-JAVA-PILOT
-> L8-WAVE7-HETEROGENEOUS-PORTFOLIO
-> L8-WAVE8-NINETY-DAY-SELF-MAINTENANCE
```

Do not stop because one task, test, report, evidence bundle, sprint, or session ended. Continue
until every mandatory outcome is proved or all remaining work is blocked by a true external
authority dependency.

Local difficulty, a failed attempt, a large scope, or incomplete investigation is not an external
blocker. Repair root causes; do not weaken gates or convert them to mocks.

## Human-only boundaries

Ask the human only when the exact gate is reached for:

- fresh section-specific `plans/master.md` edit approval;
- disposable staging repository/access authority;
- production GitHub App registration/installation and secrets after staging;
- fresh what/why/where confirmation before every real product-repository push;
- genuinely manual GitHub UI surfaces;
- analytics/dead-man credentials; or
- final independent elapsed-window acceptance.

The human is not the pipeline operator. You own implementation, execution, testing, remediation,
evidence, monitoring setup, and continuation.

## Safety and prohibited shortcuts

- Keep control work on `main`; no control feature branches.
- Never auto-merge, force-push, or write a target default branch.
- Never publish packages/releases or write GitHub-generated surfaces.
- Never expose a target-write token to analysis, clone, package/example, LLM, or validation.
- Production must reject PAT/`GH_TOKEN` fallback.
- Never push a product repository without fresh exact what/why/where approval.
- Never call producer self-review independent.
- Never replace `supervise` with a fixture controller for acceptance.
- Never create a competing plan/controller/queue.
- Never reset, clean, restore, overwrite, or stage the five user-owned paths.
- Never mark implementation-only or mocked proof complete.

Before final mission closure, run a final independent review, reconcile every task including
rerouted parents, and require durable `mission_complete=true` plus every Level-8 metric in
`HANDOVER.md` section 14.
