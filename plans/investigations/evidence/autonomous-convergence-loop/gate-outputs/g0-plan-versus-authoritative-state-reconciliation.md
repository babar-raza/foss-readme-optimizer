# G0 reconciliation — session plan vs. authoritative mission state

Recorded: 2026-08-29. Method: read the authoritative mission-execution record from the
`origin`-backed state ref (`refs/readme-agent-state/mission__LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`,
`state.json`), which `supervisor/mission_command.py::_mission_state_backend_for_args()` binds
unconditionally to `default_state_backend()` regardless of execution profile.

## Correction to method (recorded because it changed a conclusion)

The first read targeted `runs/local-poc-state/state.git`. That store holds repository-lifecycle
state, not mission authority; its `mission_execution` block reports `active_task_id: None` and
`state_version: None`. Reading it produced a wrong conclusion about claims. The authoritative
store is `origin`. This is the failure mode the project's own `local_poc` state-location note
warns about.

## Conflict 1 — taskcard statuses (PROVEN)

The session plan asserted "all 10 taskcards are TODO, none READY". False.

| Taskcard | Graph file | Authoritative durable state |
|---|---|---|
| L8-PF-00-CAMPAIGN-AUTHORITY-RECONCILIATION | TODO | **CLOSED** |
| L8-PF-01-KNOWLEDGE-ACCEPTANCE-IDENTITY | TODO | **CLOSED** |
| L8-PF-01A-QWEN-SECTION-ENGINE-INTEGRATION | TODO | **CLOSED** |
| L8-PF-02-COMPLETE-CANDIDATE-SEAM | TODO | **REGRESSED** |
| L8-PF-03-SEALED-CANDIDATE-NO-OP | TODO | **CLOSED** |
| L8-PF-04-MINIMAL-GRAPH-RUNNER | TODO | **CLOSED** |
| L8-PF-05-SEVEN-ECOSYSTEM-CANARIES | TODO | **IN_PROGRESS (expired claim)** |
| L8-PF-06-REGISTRY-FREEZE-AND-FACT-WARMUP | TODO | TODO |
| L8-PORT-01-LOCAL-README-PORTFOLIO-ASPOSE-PARITY | TODO | **REGRESSED** |
| L8-PF-07-AUTONOMOUS-PUBLICATION-READINESS | TODO | TODO |

The graph file's committed `status:` field is not live truth; durable state is. This matches the
project's own authority model and the discrepancy `plans/master.md` already flags for
`L8-PF-03-SEALED-CANDIDATE-NO-OP`.

## Conflict 2 — "no eligible task" has a different cause than assumed (PROVEN)

`evaluate`/`status` print `eligible_tasks: -`. Cause is not "everything is TODO". It is:

- `mission_execution.active_task_id = L8-PF-05-SEVEN-ECOSYSTEM-CANARIES`
- `claimed_by = codex-portfolio-resume`, `claim_expires_at = 2026-08-28T08:33:24Z` — expired ~23h
- `evaluate_mission()` computes `eligible = [] if active else _ready_tasks(...)`, so any set
  `active_task_id` suppresses eligibility regardless of lease validity.

Reproduced directly against the real code with the real graph and the real state: with the
expired claim ignored, `_derive_goal_selection` returns `GOAL-V0A-FIRST-VERIFIED-README` and
`_ready_tasks` returns `['L8-PF-02-COMPLETE-CANDIDATE-SEAM']`. The controller is therefore
correct; the expired claim is what blocks it.

## Conflict 3 — expired-claim recovery is unreachable from the documented path (PROVEN DEFECT)

`plans/master.md` states: "mission `evaluate` reconciles graph drift, claims, lifecycle freshness,
and component hashes."

Actual: `_recover_expired_claim()` (`supervisor/mission_control.py:166`) has exactly one caller,
line 756, inside `claim_next_task()`. `persist_evaluation()` updates only `mission_complete` and
`last_evaluated_at`. So `evaluate` does **not** reconcile claims.

Consequence for autonomy: an operator or loop that runs the documented `evaluate` -> `status`
sequence sees "no eligible work" and stops, while the true cause is a stale lease that only the
`claim` action can clear. This is a genuine autonomy-blocking defect: documented behaviour and
actual behaviour disagree.

## Conflict 4 — L8-PF-04 is CLOSED against unreachable machinery (PROVEN UNSUPPORTED CLOSURE)

`L8-PF-04-MINIMAL-GRAPH-RUNNER` is `CLOSED` in durable state. Its deliverable is
`src/readme_agent/supervisor/proven_transaction_runner/`. Verified:

- production importers outside the package: **NONE**
- `run_proven_transaction` callers: only `pf04_evidence.py` (same package) and tests
- references in `cli.py` / `commands*.py`: **NONE**

The subtree is unreachable from every production entry point. The closure is therefore not
supported by an integrated capability.

## Conflict 5 — live regression cause (PROVEN, matches predicted mechanism)

`L8-PF-02` transitioned `CLOSED -> REGRESSED` at 2026-08-28T10:16:15Z with reason
"repository deliverable became stale for aspose-3d-foss/Aspose.3D-FOSS-for-Python:
presentation_component_safety_changed". `status` additionally reports 22 repositories with stale
fact contracts, which is why every contract-valid lifecycle counter reads 0/34 while
`raw_lifecycle_progress` still reads facts_ready=22, candidate_generated=3,
deterministic_validated=2, agent_approved=1, no_op_proven=1.

This is the global-invalidation mechanism (Decision #111 / plan RC5) observed live.

## Amendments required to the session plan

1. Replace the "all taskcards TODO" premise with the table above.
2. Replace the "nothing is READY because nothing is promoted" diagnosis with Conflict 2/3.
3. Add expired-claim recovery on the `evaluate` path as a defect repair (Conflict 3).
4. Add L8-PF-04 closure reconciliation (Conflict 4) — either integrate or reopen.
5. Recognise the live critical path is `L8-PF-02-COMPLETE-CANDIDATE-SEAM`, not a fresh G2.
