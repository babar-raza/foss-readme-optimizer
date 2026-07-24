# Current state and worktree boundaries

## Git state at handover preparation

```text
branch: main
local HEAD before the handover package: ab8a54d9e68eefe25a030498e217a9a62c64c302
origin/main: f8b83a41506fb22a6884f494f1b16ffb8213076e
divergence: local main is 5 commits ahead and 0 behind
```

The five local-only commits are:

| Commit | Purpose |
|---|---|
| `946081e81c670d84d49604b1fefb712226eb886c` | Truthful terminal semantics, WorkLedgerV1, guarded stopping, prompt loading, pre-production child taskcards |
| `05589be23d37a398231975c9d72abc893980a2c2` | Checksum-addressed truthful-baseline proof |
| `5e31f9c11e7a54d9acc8638b23e1f85fc799ed9a` | Immutable repository snapshots and complete three-pilot ProductFactsV2 |
| `5d2256b559890353d1a1b3e380cb848f2c831b15` | Complete-document README planning/rendering/validation foundation |
| `ab8a54d9e68eefe25a030498e217a9a62c64c302` | Three-pilot README proposal evidence checkpoint |

This handover package will add one more local commit. A different checkout that sees only
`origin/main` will not contain this work. If the new agent is not using this same workspace, the
human must make the control-repository commits available on `main` or transfer the complete
workspace. Do not reconstruct these commits manually from this document.

No control-repository push was performed during the work documented here. No product repository
was written.

## User-owned uncommitted paths

These paths existed before the current Codex work and were intentionally excluded from every
commit:

| Path | State | SHA-256 at handover inspection |
|---|---|---|
| `AGENTS.md` | modified | `a5e0d1ae527e2d6013d6b30f7c4939e0ff5917b73a1749b5f97a38cd7ea82b34` |
| `plans/idea.md` | modified | `a5d68a7a2f09659ea9b2cc3f50761b2fecb748e265fe71199e45cee7ae16da9e` |
| `plans/changelog.md` | untracked | `33b853f30426f6d2c3777554d5583bd2da74757d7cd329e9e59a9c177ded1884` |
| `plans/roadmap.md` | untracked | `5888f9265aa3399baa8346664a6b7ce2eb3c84b2fe41b93cd5eeffe8f0e779d0` |
| `plans/status.md` | untracked | `9308f94b39a2c46d044052f4321f3bb018a23071cf3b660667521bdda0c9b7b1` |

Before staging any future commit:

```powershell
git status --short
git diff --cached --name-only
```

The five paths above must not appear in the staged list unless the user separately directs their
disposition after an explicit content/history review.

## Durable mission state

The durable state is stored in the control repository remote ref:

```text
refs/readme-agent-state/mission__LEVEL8-CENTRAL-REPOSITORY-PRESENTATION
```

At the handover inspection:

```text
schema version: 2
state version: 81
graph SHA-256: 2ea570475bd6afbe733338e9b4ef3b87e42ede59a9f13140903772b18db0db82
active task: L8-LOCAL-README-PROPOSAL-PROOF
claim ID: 7fe22ed54ab14e89bfd412eeabe73f7a
claimed at: 2026-07-24T09:55:42.134252+00:00
claimed by: Codex
mission complete: false
```

Durable statuses:

| Task | Durable status |
|---|---|
| `L8-MISSION-CONTROL-CONSUMER` | `CLOSED` |
| `L8-REQUIREMENT-TO-TASKCARD-COVERAGE` | `CLOSED` |
| `L8-WAVE0-PLAN-TRUTH-RECONCILIATION` | `REROUTED` |
| `L8-WAVE0-MASTER-STRUCTURAL-AMENDMENT` | `CLOSED` |
| `L8-WAVE0-SEMANTIC-CLOSURE-EVIDENCE` | `CLOSED` |
| `L8-WAVE0-CANDIDATE-ARTIFACT-DISPOSITION` | `CLOSED` |
| `L8-WAVE0-FRESH-CLONE-HEAD-REPRODUCTION` | `CLOSED` |
| `L8-WAVE1-CANONICAL-SAFETY-SPINE` | `CLOSED` |
| `L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME` | `BLOCKED_EXTERNAL` |
| `L8-WAVE3-LOCAL-PRODUCT-TRUTH-FOUNDATION` | `CLOSED` |
| `L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP` | `TODO` |
| `L8-WAVE4-LOCAL-PRESENTATION-PLAN-FOUNDATION` | `CLOSED` |
| `L8-WAVE4-PRESENTATION-INTELLIGENCE` | `TODO` |
| `L8-PREPRODUCTION-IDEA-FIDELITY-GATE` | `REROUTED` |
| `L8-PREPRODUCTION-TRUTHFUL-BASELINE` | `CLOSED` |
| `L8-LOCAL-IMMUTABLE-SNAPSHOT-AND-FACTS` | `CLOSED` |
| `L8-LOCAL-README-PROPOSAL-PROOF` | `IN_PROGRESS` |
| `L8-LOCAL-CENTRAL-AGENT-RESILIENCE` | `TODO` |
| `L8-ACT-CANONICAL-WORKFLOW-PARITY` | `TODO` |
| `L8-STAGING-VERIFIED-PROPOSAL-PROOF` | `TODO` |
| `L8-WAVE5-VERIFIED-PROPOSAL-LIFECYCLE` | `TODO` |
| `L8-WAVE6-CONTROLLED-JAVA-PILOT` | `TODO` |
| `L8-WAVE7-HETEROGENEOUS-PORTFOLIO` | `TODO` |
| `L8-WAVE8-NINETY-DAY-SELF-MAINTENANCE` | `TODO` |

The graph file's static `status:` fields are bootstrap declarations and are stale for several
tasks. The durable state is the execution-state authority.

## Known authoritative-source drift

### Master status versus current local-first execution

`plans/master.md` still says Wave 2 is the active implementation wave. The later user-directed
local-first sequence is committed in requirement `L8-014`, the task graph, investigation reports,
and durable state. This is an acknowledged synchronization gap, not permission to edit
`master.md` without fresh section-specific approval.

Before changing the master's Status, Build Checklist, Verification Checklist, or another section,
the next agent must state exactly which sections and why, then obtain fresh approval.

### Requirement rows lag the latest README implementation

The README proposal implementation and producer evidence moved ahead of several normative rows.
For example, at this checkpoint:

- `RDM-008` still says insertion into independently accepted proposals is open;
- `RDM-025` still says document-plan correction is the next task;
- `RDM-018` remains `PLANNED`;
- `L8-014` describes the immutable-facts child as the latest completed child.

This lag is intentional at the checkpoint because the latest evidence has not yet been
independently reproduced. Reconcile these rows after, not before, the missing verification gates
pass.

## Mechanical sequencing defect to repair

The durable controller treats a `REROUTED` dependency as satisfied. The parent
`L8-PREPRODUCTION-IDEA-FIDELITY-GATE` is `REROUTED`, while
`L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME` depends on that parent rather than on the last staging
child. Therefore, the graph does not mechanically prove that all local, `act`, and staging
children are closed before Wave 2 can be externally reopened.

The active task and the existing `BLOCKED_EXTERNAL` status prevent accidental progress today,
but this is not a sufficient long-term guard.

Before reopening Wave 2:

1. inspect task-graph history and the transition semantics;
2. make Wave 2 depend on `L8-STAGING-VERIFIED-PROPOSAL-PROOF`, or add an equivalent explicit
   dependency that cannot be satisfied by merely rerouting the parent;
3. update requirement-task coverage;
4. add a negative test proving Wave 2 is not eligible after only the parent reroute;
5. persist a graph evaluation and verify the active/eligible set.

Do not use this defect as a reason to skip the current README child or begin production work.
