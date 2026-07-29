# Continue the Level-8 Mission

Resume in:

`D:/Users/prora/OneDrive/Documents/GitHub/foss-readme-optimizer`

Mission: `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`.

The content snapshot immediately before the containing handover commit is `main` at
`bb994cf91d3b11e0a1774be092e221a721a0e6f9`, with a clean tree, durable mission state version 527,
graph hash `471a0d29f5e772db2845e51cd5ebe421d1a7813bad72671656f4c189a0a8ab39`,
no active claim, and `L8-REVIEW-00-CONTEXT-CORPUS` as the next eligible task. Re-read live state;
this narrative never overrides it.

## Authority and Goal

Use only this authority chain:

1. `plans/idea.md`
2. `plans/master.md`
3. `plans/requirements.md`
4. `plans/investigations/control/level8-autonomous-mission-task-graph.yaml`
5. supervisor Git-ref mission state
6. `plans/codex/idea-fidelity-to-level-8-autonomous-execution-plan.md` as supporting design

Read `AGENTS.md` and `plans/GOVERNANCE.md` first. Do not create a competing plan, controller,
queue, state store, or branch.

The goal is not implementation-only closure. Continue through full-registry local Gate A, Gate B,
`act`, staging, Gate C, hosted operation, Level 5, Level 7's 30 days, Level 8's 90 days, and final
independent audit.

## Startup

1. Verify branch, HEAD, tree, repository-owned processes, graph hash, and mission status.
2. Run:

   ```powershell
   .venv/Scripts/readme-agent supervise `
     --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
     --mission-action status `
     --mission-observer Codex
   ```

3. If graph drift exists, evaluate. Never steal a live unexpired claim.
4. Read the complete `L8-REVIEW-00-CONTEXT-CORPUS` taskcard and
   `plans/investigations/evidence/level8-review-real-corpus-route-failure-v1/`.
5. Claim the task through the same supervisor.

## First Failing Boundary

The blind role completed on the sealed real C++ candidate. The factual role used about 25,014
prompt tokens and exhausted the fixed 2,400-token completion cap twice, returning truncated JSON
both times. The unchanged retry repeated the structural failure. Fail-closed safety worked, but the
production route is unqualified.

Preserve the separate roles, grounding, deterministic reduction, candidate retention, exact
accounting, and no-write behavior. Build a production-grade bounded-output design:

- bound the factual response contract independently of repository size;
- compact context without dropping fact/plan/claim/evidence grounding;
- classify `finish_reason=length` separately;
- use a bounded deterministic recovery strategy instead of repeating an identical request;
- keep cost and call counts predictable.

Do not merely weaken the schema, remove citations, or increase tokens without a bound.

## Required Proof

Run focused transport/schema/role tests, reviewer integration, lifecycle, allow-list,
push-blocking, and redaction regressions. Then rerun:

```powershell
.venv/Scripts/python plans/investigations/tools/prove_grounded_review_real.py `
  --bundle runs/readme-poc/aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp/3e1edeacd4c1600507009c3fd3bf122d54f5d3a9 `
  --output runs/level8-review-real-corpus-probe/cpp-requalified
```

The canary must produce a complete governed verdict. A semantic rejection is valid; transport
truncation is not. Record exact per-invocation calls, checksums, candidate retention, and zero
remote writes.

After closing the repaired owner task, transition `L8-REVIEW-04A-REAL-CORPUS` from `REROUTED` to
`READY`, claim it, and run the seven real representatives. Acceptance requires zero critical false
accepts and every repairable case to change and resolve its defect.

## Continuous Loop

```text
verify authority and live state
-> claim/reclaim only the graph-selected task
-> implement the smallest complete permanent repair
-> focused proof
-> integration/regression/safety/live-like proof
-> independent verification
-> heal the first failing boundary
-> write redacted checksum-complete evidence
-> update the same task/requirements/log state
-> commit coherently to main with the Codex trailer
-> rebuild eligibility
-> continue
```

Do not stop for a completed subtask, failed test, report, checkpoint, token/session boundary, or
convenience. Stop only for explicit user instruction, actual mission completion, or a genuine
external dependency that blocks every eligible task.

No product write occurs without fresh what/why/where approval. No `plans/master.md` edit occurs
without fresh section-specific approval. No GitHub App request occurs before Gate C.
