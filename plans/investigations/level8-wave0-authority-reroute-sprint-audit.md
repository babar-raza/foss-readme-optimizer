# Level-8 Wave 0 Authority-Reroute Sprint Audit

Date: 2026-07-23

## Outcome

The broad Wave 0 task was decomposed without treating a plan-governance gate as mission-wide
failure. The supervisor can now reroute the parent task into three executable children and one
explicitly blocked child. Wave 1 depends on every child, so the reroute cannot manufacture false
progress past the unresolved structural amendment.

## External authority boundary

`plans/master.md` requires fresh, section-specific approval before structural edits. Three
materially distinct authority checks were exhausted and recorded on
`L8-WAVE0-MASTER-STRUCTURAL-AMENDMENT`:

1. The original implementation instruction was tested against the plan's own later-approval
   reservation.
2. The continuous-autonomy instruction was tested against the requirement to name the exact
   sections.
3. Decision 44's standing-directive exception was tested against the structural nature of the
   requested replacement.

None crosses the first failing boundary. The exact action that resumes the task is a fresh user
message approving edits to Mission, Status, Decision Ledger, Architecture, Build Checklist, and
Verification Checklist.

## Hardening

The graph loader now rejects `BLOCKED_EXTERNAL` taskcards unless they contain at least three
sequential, materially distinct attempts plus an exact external action and resume condition.
Dependency evaluation treats `REROUTED` as satisfied for child work, while Wave 1 directly depends
on all four Wave 0 children. This preserves both forward progress and fail-closed sequencing.

## Verification

The focused controller suite passed 13 tests. The combined supervise/mission CLI selection passed
34 tests with 33 unrelated cases deselected. Ruff, mypy, the 376-row requirement coverage check,
and plan-structure validation passed. The machine-readable record is
`plans/investigations/evidence/level8-wave0-authority-reroute/wave0-authority-reroute-verification.json`.

No product repository was written, `plans/master.md` was not edited by this change, and all
pre-existing candidate artifacts remain untouched.
