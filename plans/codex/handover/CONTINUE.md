# Continuation Prompt: Resume the Corrected Level-8 Mission

Resume `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` in:

```text
D:/Users/prora/OneDrive/Documents/GitHub/foss-readme-optimizer
```

The product goal is the complete autonomous repository-presentation system in `plans/idea.md`,
ending only after the independently reproducible 90-day Level-8 proof. Do not create another
plan, controller, queue, state store, branch, or completion narrative.

## Authority

Read and obey:

1. `AGENTS.md` and `plans/GOVERNANCE.md`;
2. `plans/idea.md`;
3. `plans/master.md`;
4. `plans/requirements.md`;
5. `plans/investigations/control/level8-autonomous-mission-task-graph.yaml`;
6. the supervisor Git-ref mission state;
7. `plans/codex/idea-fidelity-to-level-8-autonomous-execution-plan.md` and this handover as
   derived explanations only.

The verified snapshot is `main` at
`8737a702ba3a30a7e3dcdc9e1d0222850eb688eb`, mission state version 152, graph
`2dc10819cddaf6ab96770665fa02b850f67fff57c7b44e3cb1fb332f28c86bcc`, with
`L8-TRUTH-01-STAGE-LIMIT` active. Re-read live state; never let this snapshot override it.

## What Changed

Git history was not lost. Commits `f8b83a4`, `a7ac331`, `f89da60`, `80432cc`, and `a6db18c` are
all ancestors of the snapshot HEAD. The lost continuity was in derived records:

- the former handover still named HEAD `e454f7f`, state 132, and Gate A;
- four bundles were labeled `NO_OP_PROVEN`, but replaying the current fact contract left only
  Java `FACTS_READY`; Python, TypeScript, and BarCode Python reopened as
  `BLOCKED_MISSING_EVIDENCE`;
- the Java candidate's claim map omitted material inherited parity, performance,
  proprietary-format, and no-rewrite claims;
- repository and dependency build commands were running on the operator host despite credential
  filtering not being an OS sandbox;
- synthetic reviewer/qualification success did not prevent obvious real-output false accepts.

The durable graph therefore regressed the broad composition, review, qualification, and Gate-A
tasks and rerouted product truth into atomic `L8-TRUTH-*` children. Do not restore the former
full-registry fan-out.

## Startup

1. Inspect branch, HEAD, status, recent history, active writers, and relevant diffs. Preserve all
   work; never reset, restore, clean, force-push, or overwrite concurrent/user-owned changes.
2. Run:

   ```powershell
   .venv/Scripts/readme-agent supervise `
     --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
     --mission-action status `
     --mission-observer "<agent-identity>"
   ```

3. If graph drift is reported, use `--mission-action evaluate`. Never steal a live claim; reclaim
   only through the existing lease mechanism.
4. Read the complete `L8-TRUTH-01-STAGE-LIMIT` taskcard and requirement `L8-015`; its typed
   implementation is committed and its real read-only proof remains open.
5. Reconcile its allowed paths and the public `supervise` runtime before editing.

## First Task

Run and inspect the committed typed stage-limit contract on the existing canonical interface:

```powershell
.venv/Scripts/readme-agent supervise `
  --registry data/products.json `
  --execution-profile local_poc `
  --max-readme-poc-stage FACTS_READY
```

Required proof:

- CLI/profile unit tests;
- heterogeneous fixture-registry integration;
- public supervisor reaches `FACTS_READY`;
- composition, candidate generation, review, repair, and no-op capabilities have zero calls;
- a stage-limited run cannot claim `AGENT_APPROVED` or Gate A;
- relevant supervisor, lifecycle, profile, allow-list, and push-blocking regressions;
- one real read-only representative with command, HEAD, summary, call inventory, and checksums.

Do not run repository or dependency build scripts on the operator host as acceptance proof.
`L8-TRUTH-03A-ISOLATED-EXECUTOR` must close first.

After closure, claim the graph-selected successor. The critical local order begins:

```text
L8-TRUTH-01-STAGE-LIMIT
-> L8-TRUTH-01A-FACT-CONTRACT
-> L8-TRUTH-02-ROOT-ROLES
-> L8-TRUTH-03-CLAIM-POLARITY
-> L8-TRUTH-03A-ISOLATED-EXECUTOR
-> acquisition/examples/visitor views/seven-ecosystem truth
-> composition with complete inherited-and-generated claim accountability
-> split independent review and effective repair/no-op proof
-> real heterogeneous qualification and frozen campaign
-> bounded full-registry Gate A
-> Gate B human review -> act -> staging -> Gate C Java draft-PR proof
-> Gate D GitHub App/hosted runtime -> Levels 5, 7, and 8
```

No GitHub App request occurs before the ordered local, human-review, `act`, staging, and Gate-C
conditions. No product write occurs without fresh exact what/why/where approval.

## Autonomous Loop

```text
verify authority and live state
-> reconcile graph drift and claim lease
-> claim/reclaim only the highest-priority ready task
-> implement the smallest complete behavior
-> focused proof
-> integration, regression, safety, and live-like proof
-> independent verification
-> repair the first failing boundary
-> write redacted checksum-complete evidence
-> update the same task, requirements, and logs
-> commit coherent work directly to main
-> rebuild eligibility
-> continue
```

Do not stop for a completed subtask, failed test, token/session boundary, report, checkpoint,
dirty tree, restart, or convenience. Repair agent-fixable failures or reroute them within the
same governed graph. Stop only when every mandatory task is closed with complete evidence and an
independent Level-8 award, or when every remaining task is genuinely blocked by unavailable
external authority/infrastructure and its exact unblock condition is recorded.

Documentation cannot keep an inactive chat alive. Durable state provides restart continuity;
hosted unattended scheduling is a later Gate-D deliverable.
