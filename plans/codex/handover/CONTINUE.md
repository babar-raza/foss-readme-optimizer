# Continue the Level-8 Repository-Presentation Mission

Resume `D:\Users\prora\OneDrive\Documents\GitHub\foss-readme-optimizer` as the sole operator on
`main`. The content checkpoint is `1745abfc0168ee32e48c948aca893a60680b5b4c`; the containing
handover commit follows it. The sole executable plan is
`plans/investigations/control/level8-autonomous-mission-task-graph.yaml`, whose checkpoint SHA-256
is `cbeda937ee0d7a6d45d6fc58507fc68e60d8ccc7fbb98a869983d40d5c719f52`. The durable checkpoint is
state version 550 with no active claim or graph drift.

Repository state and supervisor state are authoritative over this snapshot. Start by reading
`AGENTS.md`, `plans/idea.md`, `plans/master.md` decisions #78/#83/#84,
`plans/requirements.md` rows `L8-035`–`L8-039`, this file, `HANDOVER.md`, and the taskcard for
`L8-INTAKE-02-READONLY-PREFLIGHT-ENROLLMENT`. Run mission `status`; if the graph drifted, run
`evaluate`. Inspect the tree and repository-owned processes before starting any command.

The current task is `L8-INTAKE-02-READONLY-PREFLIGHT-ENROLLMENT`, status `IMPLEMENTED` but not
verified or closed. Do not claim task 03. The exact first action is:

1. Add one public-supervisor integration beginning from an unseen authorized discovery
   observation.
2. Reconcile it into `data/products.json` semantics as disabled/read-only with stable identity,
   without granting write authority.
3. Execute exactly one durable intake in the same logical run.
4. Prove cancellation/resume, duplicate replay, stable source/contract binding, correct lifecycle
   continuation, and zero local/remote target effects.
5. Run focused intake/admission tests, relevant supervisor/allow-list/push-blocking regressions,
   and a real-local-Git live-like proof.
6. Regenerate, in place,
   `plans/investigations/evidence/level8-intake-02-readonly-preflight-enrollment-v1/`; require a
   checksum-valid independent `PASS`.
7. Update `L8-037`, `ONB-002`, `CORE-004`, `OPS-007`, master/status/log/handover, and transition
   the same durable task through `VERIFIED`, `SCORED`, and `CLOSED`.
8. Commit the coherent slice directly to `main` with
   `Co-Authored-By: Codex <noreply@openai.com>`, run `evaluate`, then claim the next ready task.

Preserve the ultimate objective: current-contract, independently agent-approved and no-op-proven
local README bundles for the complete runtime registry; Gate B human acceptance; canonical `act`
proof; disposable staging; Gate C governed Java draft PRs; GitHub App only after Gate C; complete
presentation surfaces and Level 5; 30-day Level 7; 90-day Level 8; final independent audit.
Platform priority is Python, .NET, Java, C++, TypeScript, Rust, Go.

Use this loop continuously:

```text
verify authority and live state
→ reconcile graph drift and claim/continue the exact governed task
→ implement the smallest complete repair at the first failing boundary
→ focused proof
→ integration, regression, safety, recovery, idempotency, and live-like proof
→ independent verification
→ repair failures
→ write checksum-complete redacted evidence
→ update the same task, requirements, status, logs, and handover
→ commit to main
→ rebuild eligibility and continue
```

Do not create another plan, controller, queue, or mission state. Do not stop for a completed
subtask, a failed test, a report, a checkpoint, a token/session boundary, a dirty tree, or
convenience. Documentation cannot keep an inactive chat alive; durable state makes restart safe,
while hosted scheduling is a later Gate-D deliverable. Repair agent-fixable blocks. Stop only when
the full mission is independently proved or a genuine unavailable external authority,
credential, infrastructure, manual UI action, or irrecoverable external fact blocks all eligible
work.

Work only on control-repository `main`; preserve user work; use `.venv`; run one top-level command
tree at a time. Never reset, restore, clean, force-push, weaken safety, write a product repository,
or request the production GitHub App early. A product write always requires fresh exact
what/why/where authorization. `plans/master.md` may be truthfully synchronized without fresh
section approval under `GOV-023` and governance rule 12.

The present scoreboard is 31 admitted repositories; 8 facts/candidates/deterministic, 0
agent-approved, 0 no-op-proven, 0 human-accepted. The live 8/31 Python intake slice made zero
provider calls and zero target effects, but it is not Gate A and not eight finalized READMEs.
