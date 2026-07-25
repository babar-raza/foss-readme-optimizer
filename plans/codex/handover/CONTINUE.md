# Continuation Prompt: Execute the Existing Level-8 Mission

You are resuming the single mission `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` in:

```text
D:/Users/prora/OneDrive/Documents/GitHub/foss-readme-optimizer
```

Do not create a competing plan, controller, queue, state store, branch, or completion narrative. Use `readme-agent supervise` and the existing Git-ref durable mission state as the only execution authority.

## Non-Negotiable Authority

Read and obey, in order:

1. `AGENTS.md` and `plans/GOVERNANCE.md`.
2. `plans/idea.md` for the product outcome and local-first gate ordering.
3. `plans/master.md` and `plans/requirements.md` for governed architecture and acceptance.
4. `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` for executable task dependencies and acceptance checks.
5. Durable mission state for the active task, claim, transitions, and completion status.
6. `plans/codex/handover/HANDOVER.md`, `state.json`, and `plans/codex/idea-fidelity-to-level-8-autonomous-execution-plan.md` as supporting snapshots.

The handover snapshot was `main` at `c6b824d3817482666ed547427076fa6eb1c78629`, state
version 94, graph hash `8db1168d8a5a84eaa1b5fc057c1cb22b16651cc70f44bfbe2e0c33de1cb3b09b`,
with `L8-LOCAL-PORTFOLIO-PRODUCT-TRUTH` active. These are not a substitute for live verification.

## Mandatory Startup

1. Inspect `git branch --show-current`, `git rev-parse HEAD`, `git status --short`, relevant recent history, and active processes. Preserve all current work; never reset, restore, clean, force-push, or overwrite concurrent/user-owned changes.
2. Recompute the hashes recorded in `state.json`.
3. Run:

   ```powershell
   .venv/Scripts/readme-agent supervise `
     --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
     --mission-action status `
     --mission-observer "<agent-identity>"
   ```

4. If the command reports graph drift, run the same command with `--mission-action evaluate`. Treat the resulting durable state as authoritative.
5. If an unexpired task claim belongs to another active writer, do not steal it. If it expired, call `--mission-action claim --mission-observer "<agent-identity>"`; recovery is append-only.
6. Reconcile the claimed task's taskcard, its preceding gate, current diff, and current evidence before editing. Then work only within its allowed paths.

## Execute Continuously

Perform this loop without asking a human to tell you to continue:

```text
verify authority and live state
→ reconcile graph drift and claim lease
→ claim/reclaim only the highest-priority ready task
→ implement the smallest complete task slice
→ focused proof
→ integration, regression, safety, and live-like proof
→ independent verification
→ repair the first failing boundary
→ write redacted checksum-complete evidence
→ update the same task, requirements, and logs
→ commit coherent work directly to main
→ rebuild eligibility
→ continue
```

Do not stop for a completed subtask, test failure, token/session boundary, report, evidence bundle, checkpoint, dirty tree, restart, or convenience. A failure that can be fixed by an agent is `agent_fixable`: repair it at the first failing boundary or create/reopen a governed resolver task and continue unrelated ready work. Only unavailable external authority, credentials, infrastructure, or irrecoverable external facts may be `BLOCKED_EXTERNAL`, with a precise unblock condition.

Refresh `HANDOVER.md`, this file, and `state.json` after every durable transition, coherent commit, external block, or deliberate safe checkpoint. Update the same files in place; never create dated or duplicate handover documents.

## First Task Now

The expected live task is `L8-LOCAL-PORTFOLIO-PRODUCT-TRUTH`. The canonical local runtime task is
already durably closed. The first boundary now is the committed seven-ecosystem live proof:

```powershell
.venv/Scripts/python `
  plans/investigations/tools/prove_local_portfolio_product_truth_representatives.py
```

Repair each agent-fixable Java, .NET, Python, TypeScript, C++, Go, or Rust lane at its first failure.
Require the exact prepared fact graph to reach the renderer, retain visible narrow fact blocks, and
write redacted checksum-complete evidence. Then run the focused product-truth/lifecycle/security
tests plus supervisor integration/regression proof and independently review the evidence. Do not
transition on offline tests alone.

The succeeding chain is fixed by dependencies:

```text
L8-LOCAL-PORTFOLIO-PRODUCT-TRUTH
→ L8-LOCAL-README-ASSESSMENT-COMPOSITION
→ L8-LOCAL-INDEPENDENT-REVIEW-REPAIR
→ L8-LOCAL-HETEROGENEOUS-QUALIFICATION
→ L8-LOCAL-FULL-REGISTRY-GATE-A
→ Gate B human review → act → staging → Gate C Java PR proof
→ Gate D GitHub App/hosted runtime → Levels 5, 7, and 8
```

Gate C and GitHub App work cannot begin before full-registry local proof. No product-repository write occurs without a fresh, explicit what/why/where approval. Never auto-merge, force-push, write a default branch, publish packages/releases, or write GitHub-generated surfaces.

Documentation cannot run while no agent or workflow is active. The durable state makes a restart safe; real hosted autonomous scheduling is a later Gate D outcome. Do not misrepresent this handover as a substitute for that infrastructure.

## Completion Rule

You may stop only when every mandatory task is `CLOSED` with the required local, workflow, staging, production, safety, recovery, idempotency, 30-day, and 90-day evidence, and an independent audit awards Level 8; or when every remaining mandatory task is genuinely `BLOCKED_EXTERNAL` and its exact external authority/unblock condition is recorded. Implementation, passing unit tests, or a written report alone never closes the mission.
