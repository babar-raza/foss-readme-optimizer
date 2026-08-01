# Continue the Level-8 Repository-Presentation Mission

Resume `D:\Users\prora\OneDrive\Documents\GitHub\foss-readme-optimizer` as the accountable
coordinator on `main`. The historical checkpoint for this prompt is
`908f9f3b54a93ef12a6eb265e17366b0cb0ac21a`, but live Git and supervisor state always override it.

## Authority

Use exactly this order:

1. `plans/idea.md` - product outcome.
2. `plans/master.md` - architecture, decisions, sequencing, maturity gates.
3. `plans/requirements.md` - normative acceptance.
4. `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` - sole executable graph.
5. Supervisor Git-ref durable state - actual task/claim/transition authority.
6. `plans/codex/idea-fidelity-to-level-8-autonomous-execution-plan.md` - supporting detail only.

Do not select or create a competing plan, controller, queue, or mission state. Do not use this
narrative file to override durable state.

At capture, durable state was version 678 with graph hash
`d5a99e705688404887d36d107ab822dd8283e44f7b9b5b21664447b8b8941eb7`, active goal
`GOAL-V1-VERIFIED-TRUTH`, and active task `L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP`. The scoreboard was
17/31 facts ready, 9/31 candidates and deterministic validations, and 0/31 current independent
approvals/no-op proofs. Two raw approval/no-op pairs for Slides Python and Words Python were stale
and must not count.

## Startup

```powershell
git status --short --branch
git rev-parse HEAD
.venv/Scripts/readme-agent supervise `
  --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
  --mission-action status `
  --mission-observer Codex `
  --durable-state
```

If graph drift is reported, run `evaluate`. If the claim lease expired, reclaim through
`--mission-action claim`; never steal an unexpired claim or edit state manually. Inspect
repository-owned processes before any long campaign and run only one top-level integrated
test/proof/supervisor tree at a time.

## Immediate task

Continue `L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP` at the first `FACTS_READY` boundary. Reconcile the
existing committed implementation and current runtime bundles, identify the next Python failure,
and make the smallest permanent producer or ecosystem repair. Known leads are the invalid HTML
Python build backend and TeX Python's source/package verification failure; verify the live first
failing boundary before choosing one.

Before implementation, update
`runs/multi-agent/L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP/execution-plan.json`. Disposition all five
required roles:

- Repair: a bounded failing producer/ecosystem path.
- Advancement: a different dependency-ready repository or independent read-only qualification.
- Validator/Evidence: read-only scoreboard, cache, lifecycle, and evidence reconstruction.
- Documentation/State-Sync: proposal only under `runs/multi-agent/`; never direct plan/state edits.
- Independent Verification: only after coordinator integration; cannot author implementation.

At most three workers run beside the coordinator. Every active worker gets an exclusive non-shared
path lease, forbidden shared paths, focused tests, and an evidence destination. A role with no real
independent work is `not_applicable` with a task-specific reason; do not spawn ceremonial agents.
The coordinator alone owns shared files, integration, state transitions, commits, official checks,
final evidence, and product effects.

Run focused facts/ecosystem/security checks and then the bounded canonical proof:

```powershell
.venv/Scripts/readme-agent supervise `
  --registry data/products.json `
  --execution-profile local_poc `
  --max-readme-poc-stage FACTS_READY
```

Independently reconstruct lifecycle counts and verify that no remote write occurred. Do not close
Wave 3 merely because one repository or one test passes.

## Continuous loop

```text
verify authority and live state
-> reconcile graph drift and claim lease
-> update the task-lane plan and lease disjoint work
-> implement the smallest complete task slice
-> focused proof
-> integration, regression, safety, recovery, idempotency, and live-like proof
-> coordinator integration
-> independent verification
-> repair the first failing boundary
-> checksum-complete redacted evidence
-> update the same task, requirements, logs, and handover
-> commit coherent work directly to main
-> evaluate, rebuild eligibility, and continue
```

Do not stop for a completed subtask, test failure, report, evidence bundle, commit, dirty tree,
session/token boundary, or convenience. An agent-fixable failure is repaired or rerouted to its
governed resolver. After two ineffective attempts or 15 minutes at the same boundary, perform a
first-principles review before trying a third approach. Stop only when the entire mission is
proved or all remaining progress requires unavailable external authority/infrastructure.

## Ordered outcomes

1. Complete Wave 3 product truth and ownership, Python first, then .NET, Java, C++, TypeScript,
   Rust, and Go.
2. Produce current deterministic, independent, repaired, no-op-proven bundles for every dynamic
   registry member; close Gate A only when all 31 current entries pass (recompute the denominator).
3. Present Gate B only after full agent approval.
4. Prove the canonical workflow under `act`.
5. Prove disposable staging proposal lifecycle.
6. Create product-repository draft PRs only after exact fresh what/why/where approval.
7. Request/install GitHub App access only at the governed hosted gate.
8. Complete all presentation surfaces, Level 5, the 30-day Level 7 proof, and the 90-day Level 8
   proof with final independent review.

## Non-negotiable controls

- Existing README content is valuable evidence but not automatically factual.
- Preserve the global presentation contract: no comments, no emojis, consistent professional
  header, detailed useful Mermaid, full product names outside APIs/packages, natural contextual
  links with budgets, and `Enterprise Edition` terminology.
- `data/products.json` is the allow-list. CSSForge and the MCP-suffixed Go repository are excluded;
  ordinary `Aspose-PDF-FOSS-for-Go` remains admitted.
- No reset, restore, clean, force-push, default-branch write, merge, package/release write, or
  silent overwrite.
- No product write without fresh exact what/why/where authorization.
- Use `.venv` only. Preserve push-blocking, allow-list, redaction, isolation, and independent
  verifier guarantees.
- Every AI-authored commit includes `Co-Authored-By: Codex <noreply@openai.com>`.

Implementation is not closure. A result is complete only after focused, integration, regression,
safety, live-like/E2E, recovery, idempotency, consumer/pilot proof as applicable, checksum-complete
evidence, independent acceptance, task/requirement reconciliation, and final mission reevaluation.
