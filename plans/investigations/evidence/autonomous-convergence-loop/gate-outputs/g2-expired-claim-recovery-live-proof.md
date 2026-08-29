# G2 — expired-claim recovery proven on authoritative state

The repair is `persist_evaluation()` now calling `_recover_expired_claim()` (see
`g1-verification-baseline-root-causes.md`, RC-A/RC-C context). This file records the live
before/after against the real `origin`-backed mission record, not a fixture.

## Before (state_version 1791)

Read directly from `refs/readme-agent-state/mission__LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`:

```
active_task_id:     L8-PF-05-SEVEN-ECOSYSTEM-CANARIES
claimed_by:         codex-portfolio-resume
claim_expires_at:   2026-08-28T08:33:24.670776+00:00      <- expired ~23 hours earlier
L8-PF-05 status:    IN_PROGRESS
```

`supervise --mission-action status` reported `eligible_tasks: -`. Repeated `evaluate` calls did
not change that: before the fix, `evaluate` updated only `mission_complete` and `last_evaluated_at`.

## After (state_version 1792) — one `--mission-action evaluate`

```
state_version:           1792
active_task:             -
eligible_tasks:          L8-PF-02-COMPLETE-CANDIDATE-SEAM
next_task:               L8-PF-02-COMPLETE-CANDIDATE-SEAM
graph_drift:             false
first_failing_boundary:  FACTS_READY
```

The stale lease was released through the same append-only `mission-claim-recovery` transition
`claim` already used, and the controller immediately surfaced the correct dependency-ready task.

## Why this is the load-bearing repair

`evaluate_mission()` computes `eligible = [] if active else _ready_tasks(...)`. Any set
`active_task_id` suppresses eligibility regardless of lease validity. So a worker dying mid-claim
left the mission permanently reporting "no eligible work" to every reader of the documented
`evaluate` -> `status` sequence, while the underlying graph was in fact ready to proceed. No amount
of re-running `evaluate` recovered it; only an explicit `claim` would, and an operator following
the documented order had no reason to issue one.

Independently verified by reproducing the pre-fix behaviour in
`test_evaluate_recovers_an_expired_claim_and_restores_eligibility` (fails before the change) and by
`test_evaluate_leaves_an_unexpired_claim_untouched` (negative control: a live lease is never stolen
by a routine evaluation).

## Correct next work, per the controller itself

`L8-PF-02-COMPLETE-CANDIDATE-SEAM` is `REGRESSED`, not `TODO`. Its own transition history records
why: it closed at 2026-08-28T08:02:46Z and regressed at 2026-08-28T10:16:15Z with
"repository deliverable became stale for aspose-3d-foss/Aspose.3D-FOSS-for-Python:
presentation_component_safety_changed". `status` additionally reports 22 repositories with stale
fact contracts, which is why every contract-valid lifecycle counter reads 0/34 while
`raw_lifecycle_progress` still reads facts_ready=22, candidate_generated=3,
deterministic_validated=2, agent_approved=1, no_op_proven=1.
