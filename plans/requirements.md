# Requirements

## Authority

The normative typed catalog is `plans/requirements/catalog.jsonl`. This file is its compact
human-readable entry point. Every catalog line is one complete `RequirementRecordV1`; stable IDs are
never reused. Requirement status is not completion proof: current evidence and the mapped active task
still govern acceptance.

The catalog contains **514** requirements (2026-08-27 -- this summary drifts from the catalog
between refreshes; it is not mechanically regenerated yet, which is exactly the gap Decision #109
and requirement `GOV-032` exist to close):

- `BACKLOG`: 49
- `DEPRECATED`: 23
- `GOVERNANCE`: 35
- `IMPLEMENTED`: 169
- `PARTIAL`: 104
- `PLANNED`: 128
- `RESEARCH-GATED`: 6

Families: `AGT` 10, `AUTH` 8, `BIZ` 8, `CAP` 9, `CORE` 39, `DEP` 6, `DOC` 10, `ECO` 5, `EFF` 6, `EVID` 6, `FACT` 20, `FRESH` 6, `GAP` 3, `GOV` 31, `INT` 10, `KNOW` 14, `L8` 55, `LLM` 23, `MEM` 5, `MET` 8, `NFR` 14, `ONB` 4, `OPS` 14, `ORC` 9, `OWN` 15, `PIL` 16, `PKG` 6, `PRL` 9, `RDM` 33, `RUN` 10, `SAFE` 21, `SCL` 10, `SURF` 15, `TRP` 23, `VAL` 20, `VER` 13.

## Loading requirements

The active mission graph lists only IDs directly owned by an active task. A task context may load
those records plus declared always-on invariants and must remain at or below 25 records. Full catalog
scans are governance/audit operations, not routine execution context.

Use:

```powershell
.venv/Scripts/python scripts/governance/query_requirement_catalog.py --task-id <TASK-ID>
```

The query fails closed on a missing/duplicate ID, stale graph/catalog hash, more than 25 records, or
an ID not mapped to the requested active task.

## Always-on invariants

Safety, factuality, authorization, recovery, idempotency, evidence integrity, and independent review
remain acceptance invariants even when their detailed rows are not loaded into the task prose context.
Their enforcement lives in registered validators and official checks, not repeated narrative text.

## Current active slice

Run mission `status` before execution and follow its exact immediate goal and repository scope.
Every bounded canary must bind `--mission-task-id` and `--mission-observer` to the unexpired durable
claim; graph drift, scope mismatch, foreign ownership, or an exhausted approach budget fails before
repository work. Aspose.org artifacts may
diagnose development-time contract gaps, but accepted runs must succeed without that checkout and
may not write any product repository. Durable supervisor state remains the sole authority for the
live task; this compact index intentionally does not duplicate a task ID that can become stale.

The current bounded dependency horizon is candidate-first: campaign authority; committed-source
Aspose.org mechanism refresh plus a twice-stable, denominator-reconciled snapshot of its evolving
generated visitor-quality benchmark; independent import/profile qualification;
imported-knowledge-to-bytes and acceptance identity; one complete Aspose.3D Python candidate; 30-point acceptance plus
immediate no-op; minimal graph runner; seven ecosystem canaries; overlapping registry/fact warmup;
the 31/31 processable fleet and adversarial audit; then autonomous source-fresh `PR_ELIGIBLE`
proposal packages for every processable repository. Human content review is not a prerequisite and
the campaign stops before any product effect.
The graph owns the exact task IDs and durable state owns the current cursor.

## Status and history

Generated coverage lives at
`plans/investigations/evidence/level8-requirement-taskcard-coverage/requirement-taskcard-coverage.json`.
Detailed execution history remains in Git, `logs/`, durable state, and checksum-addressed evidence.
No derived report or handover overrides this catalog or durable state.
