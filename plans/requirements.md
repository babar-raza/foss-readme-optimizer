# Requirements

## Authority

The normative typed catalog is `plans/requirements/catalog.jsonl`. This file is its compact
human-readable entry point. Every catalog line is one complete `RequirementRecordV1`; stable IDs are
never reused. Requirement status is not completion proof: current evidence and the mapped active task
still govern acceptance.

The catalog contains **475** requirements:

- `BACKLOG`: 28
- `DEPRECATED`: 22
- `GOVERNANCE`: 35
- `IMPLEMENTED`: 163
- `PARTIAL`: 98
- `PLANNED`: 123
- `RESEARCH-GATED`: 6

Families: `AGT` 10, `AUTH` 8, `BIZ` 8, `CAP` 9, `CORE` 34, `DEP` 6, `DOC` 10, `ECO` 5, `EFF` 6, `EVID` 5, `FACT` 17, `FRESH` 6, `GAP` 3, `GOV` 30, `INT` 10, `L8` 55, `LLM` 22, `MEM` 5, `MET` 8, `NFR` 14, `ONB` 4, `OPS` 13, `ORC` 9, `OWN` 15, `PIL` 16, `PKG` 6, `PRL` 9, `RDM` 26, `RUN` 10, `SAFE` 19, `SCL` 10, `SURF` 15, `TRP` 23, `VAL` 18, `VER` 11.

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

`L8-AGILE-AUTHORITY-RESET` owns `L8-047` through `L8-054`. It may modify only governance, mission,
state, catalog, validation, test, evidence, and log paths. Product presentation and product-repository
effects are forbidden until this reset closes.

## Status and history

Generated coverage lives at
`plans/investigations/evidence/level8-requirement-taskcard-coverage/requirement-taskcard-coverage.json`.
Detailed execution history remains in Git, `logs/`, durable state, and checksum-addressed evidence.
No derived report or handover overrides this catalog or durable state.
