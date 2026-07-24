# Codex handover: Level-8 repository-presentation mission

Handover prepared: 2026-07-24
Repository root:
`D:\Users\prora\OneDrive\Documents\GitHub\foss-readme-optimizer`

This directory is a transfer snapshot for the next implementation agent. It is deliberately
descriptive, not a second execution authority. The authoritative sources remain:

1. the user-owned vision in `plans/idea.md`;
2. the current architecture and sequence in `plans/master.md`, subject to its edit gate;
3. the normative obligations in `plans/requirements.md`;
4. the executable taskcards in
   `plans/investigations/control/level8-autonomous-mission-task-graph.yaml`;
5. the durable mission state stored in the control repository's
   `refs/readme-agent-state/mission__LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` Git ref; and
6. committed evidence under `plans/investigations/evidence/`.

Where those sources disagree, do not silently choose the most optimistic statement. Inspect the
code and evidence, preserve the stricter safety boundary, and reconcile the authoritative
surfaces through their governance process.

## Start here

The next agent should read these files in order:

1. [`mission-goals-and-nonnegotiable-boundaries.md`](mission-goals-and-nonnegotiable-boundaries.md)
2. [`current-state-and-worktree-boundaries.md`](current-state-and-worktree-boundaries.md)
3. [`completed-work-and-evidence.md`](completed-work-and-evidence.md)
4. [`active-readme-proof-completion-plan.md`](active-readme-proof-completion-plan.md)
5. [`remaining-autonomous-execution-program.md`](remaining-autonomous-execution-program.md)
6. [`continuous-sprint-operating-runbook.md`](continuous-sprint-operating-runbook.md)
7. [`reference-and-evidence-index.md`](reference-and-evidence-index.md)

## Exact resume identity

```text
mission: LEVEL8-CENTRAL-REPOSITORY-PRESENTATION
durable state version: 81
durable graph SHA-256: 2ea570475bd6afbe733338e9b4ef3b87e42ede59a9f13140903772b18db0db82
active task: L8-LOCAL-README-PROPOSAL-PROOF
active task status: IN_PROGRESS
active claim ID: 7fe22ed54ab14e89bfd412eeabe73f7a
claimed by: Codex
branch policy: control repository main only
local HEAD before this handover package: ab8a54d9e68eefe25a030498e217a9a62c64c302
origin/main at handover inspection: f8b83a41506fb22a6884f494f1b16ffb8213076e
local divergence before this handover commit: 0 behind, 5 ahead
```

Do not claim a new task. Resume the already-active README proposal task.

## Immediate resume command

From the repository root:

```powershell
.venv/Scripts/readme-agent supervise `
  --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
  --mission-action status `
  --mission-observer "<new-agent-name>"
```

Expected result before any transition:

```text
state_version: 81
active_task: L8-LOCAL-README-PROPOSAL-PROOF
unresolved_tasks: 10
blocked_external_tasks: 1
mission_complete: false
```

The next implementation action is not production authentication and not `act`. It is completing
the local README proof honestly:

1. split the 474-line README document renderer;
2. add a genuinely separate evidence verifier and cross-pilot clone/prose review;
3. prove the new path through the canonical supervisor against all three pilots;
4. reproduce no-op behavior and negative controls;
5. reconcile requirements and durable task state only after the evidence passes.

## Truthful maturity statement

The system is not Level 7, Level 8, production-ready, or even fully locally proven yet.

What is proven:

- truthful terminal classification and deterministic remaining-work enforcement;
- immutable pilot snapshots and fact graphs for three Java repositories;
- source-build acquisition and minimal Java example verification for those pilots;
- deterministic candidate bundles for three pilot READMEs;
- zero product-remote writes in the recorded local work.

What is not yet proven:

- independent reproduction of the latest three README proposal bundles by a separately
  implemented verifier;
- the latest proposal path through a complete canonical supervisor run;
- complete local multi-surface behavior and recovery;
- complete workflow execution under `act`;
- isolated GitHub staging;
- production GitHub App operation;
- Level-5 production pilot, heterogeneous Level 6/7, or the 90-day Level-8 window.

Any agent that reports more than this before producing new evidence is overclaiming.
