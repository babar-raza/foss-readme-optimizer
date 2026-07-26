# Autonomous Agent Handover

## 1. Handover Snapshot

**Verdict: `HANDOVER_READY`.** This is a verified snapshot, not an override of live durable state. A receiving agent must revalidate it before acting.

| Field | Value |
|---|---|
| Repository | `D:/Users/prora/OneDrive/Documents/GitHub/foss-readme-optimizer` |
| Branch / snapshot HEAD | `main` / `6ec3795468a64d35866ee1b90c9200767ca0ff1b` |
| Tree | Clean before this in-place handover refresh; runtime artifacts remain under ignored `runs/`. |
| Mission | `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` |
| Durable state | Version 132; graph SHA-256 `b575c29e6404d8268310756e54a25b0249a374b41a7729c106222261b7ebfa9f` |
| Active task | `L8-LOCAL-FULL-REGISTRY-GATE-A` |
| Mission status | 12 unresolved, one external block, graph drift false, mission complete false |
| Exact next action | Continue the active canonical full-registry worker and repair its first failing boundary; start with [CONTINUE.md](CONTINUE.md). |

The snapshot was produced by `readme-agent supervise --mission-action status`. Any change to the graph, durable state, HEAD, or working tree makes it historical. The supervisor's Git-ref state is the live task-status authority.

## 2. Ultimate Goal

Deliver and prove the autonomous repository-presentation system in `plans/idea.md`: it must derive repository-grounded facts, assess all applicable presentation surfaces, generate bounded repository-specific proposals, independently verify them, safely make authorized draft proposals, recover from failure and duplication, and eventually earn an independent Level-8 award after the required 90-day production period.

The immediate milestone is local-first Gate A: every current `data/products.json` entry must have a checksum-valid, independently agent-approved local README bundle and unchanged-rerun proof. The denominator is always dynamic. Gate A is not Level 5, 7, or 8.

## 3. Authority and Scope

| Reference | Role | Authority |
|---|---|---|
| `AGENTS.md`, `plans/GOVERNANCE.md` | repository, safety, test, commit, and plan rules | binding |
| `plans/idea.md` | intended product outcome and ordered delivery gates | authority |
| `plans/master.md` | architecture, decisions, maturity gates | authority |
| `plans/requirements.md` | normative obligations and acceptance | authority |
| `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` | sole executable task dependency graph | authority |
| supervisor Git-ref mission state | active claim, transitions, actual status | authority over snapshots |
| `plans/codex/idea-fidelity-to-level-8-autonomous-execution-plan.md` | supporting design | reference |
| this directory | transfer snapshot and restart instructions | reference |

Never create or execute a competing controller, queue, mission state, or plan. RPOC/PRODSYS records are diagnostic history only. The former handover's `L8-LOCAL-README-PROPOSAL-PROOF` claim is stale and must not be followed.

Non-goals and hard limits: no auto-merge, readying a draft, force push, target default-branch write, package/release publication, GitHub-generated-surface write, or unapproved product write. GitHub App and production access remain deferred until the ordered pre-production gates pass.

## 4. Evidence-Based Current State

### VERIFIED

- The mission graph names `readme-agent supervise` as the selected mechanism and Git-ref state as governing state (`autonomous_execution_contract`).
- `supervise --help` exposes the canonical local interface:

  ```powershell
  .venv/Scripts/readme-agent supervise --registry data/products.json --execution-profile local_poc
  ```

- The dependency chain through `L8-LOCAL-HETEROGENEOUS-QUALIFICATION` is durably closed; mission
  status version 132 names `L8-LOCAL-FULL-REGISTRY-GATE-A` as active with no graph drift.
- `aspose-3d-foss/Aspose.3D-FOSS-for-Java` reached `NO_OP_PROVEN` in
  `runs/readme-poc/aspose-3d-foss__Aspose.3D-FOSS-for-Java/8de5f467e93138b3605acdc46ca40e93f0364ee8/manifest.json`.
- Commits `42ef68e`, `386562d`, `8cc3906`, `9d4c79e`, `3292e9b`, `f324e67`, `6bdd765`,
  `89b66d8`, `136626b`, `5457d5f`, `052901c`, `b5fa7eb`, `7e1d119`, `ade9929`, and
  `6ec3795` repair the live Gate-A truth
  boundaries: multi-root .NET verification, fail-closed evidence contracts, structured
  repository-bound drafting, malformed-response recovery, truthful repair failure transitions,
  larger/longer inference, and compiler-grounded example repair.
- Focused proof for the latest slices passed: 49 lifecycle/forced-tool tests, 68
  reviewer/prose/specialist tests, 33 product-truth/local-verification/security tests, and 36
  cache/evidence/product-truth tests, plus Ruff and mypy on every changed source seam.
- Existing foundation evidence is inspectable under `level8-wave1-heterogeneous-fail-closed-2026-07-23/`, `level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24/`, and `level8-wave4-local-presentation-plan-foundation-2026-07-23/`.

### IMPLEMENTED_BUT_UNVERIFIED

- Gate A remains incomplete. Java is `NO_OP_PROVEN`; .NET was correctly
  `BLOCKED_MISSING_EVIDENCE` because its drafted example did not compile. The compiler-diagnostic
  repair is proven to reach the next model turn, and the v5 prompt now requires a six-statement
  self-contained example. Python exposed a separate 8,000-token `finish_reason='length'`; the v5
  contract now caps result cardinality and code size. Both v5 live reruns remain pending. No
  complete `portfolio-summary.json` exists yet.

### PARTIAL OR CONTRADICTED

- `level8-portfolio-readme-proposals-2026-07-25/portfolio-proof-manifest.json` covers 28 non-pilot repositories; it reports 27 mechanically produced candidates, zero verified, one error, and `cross_portfolio_specificity_verified: false`. It is diagnostic evidence, not Gate A.
- `L8-002` is `IMPLEMENTED` in `plans/requirements.md`, while the implementation truth matrix flags it among semantic-closure gaps. Preserve the requirement status but require fresh task-specific proof for changed paths.
- Earlier handovers named older HEADs/state versions and the local-runtime task; all are historical
  and contradicted by the live snapshot above.

### Current Risks and Blocks

- Inspect relevant diffs and history before touching an overlapping file. Never reset, restore,
  clean, force-push, or silently overwrite user-owned work.
- Any live representative product-truth failure is agent-fixable unless it is positively
  classified as unavailable external evidence or infrastructure. Repair its first failing
  boundary rather than reporting a partial result as success.
- Production credentials, product-write authority, and App provisioning are intentionally deferred. They are not blockers to current local implementation.

## 5. Exact Plan and Queue

The supervisor must select the highest-priority dependency-ready task. The intended dependency sequence is:

1. `L8-LOCAL-FULL-REGISTRY-GATE-A`: execute the canonical profile over the runtime-loaded registry,
   repair every agent-fixable failure, and repeat unchanged sweeps until every entry is
   agent-approved and no-op-proven with a valid manifest.
7. Gate B human review of already approved bundles; rejection re-enters repair.
8. Canonical workflow proof under `act`.
9. Disposable GitHub staging.
10. Gate C Java draft-PR proof with fresh what/why/where approval per product push.
11. Gate D GitHub App and hosted runtime, only after Gate C.
12. Controlled Level 5, heterogeneous Level 7 with 30 clean days, then Level 8 with 90 clean days and an independent reproducible award.

The current command is
`.venv/Scripts/readme-agent supervise --registry data/products.json --execution-profile local_poc`.
At snapshot time its resume-9 process tree was active and logging to
`runs/level8-local-full-registry-gate-a-live-resume-9/`. Do not launch a duplicate while that
worker is alive. The first pending proof is that the new compiler-grounded repair regenerates and
verifies the .NET example; then continue every remaining registry entry and run unchanged sweeps.
Gate A closes only when `approved == len(data/products.json)`, `system_failed == 0`,
`unprocessed == 0`, and `manifest_failures == 0`.

## 6. Continuous Execution Contract

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

Do not stop for a completed subtask, test failure, session/token boundary, report, evidence bundle, checkpoint, dirty tree, restart, or convenience. Agent-fixable failures are repaired or rerouted to a governed resolver task. Only unavailable external authority, credentials, infrastructure, or irrecoverable external facts may be `BLOCKED_EXTERNAL`; unrelated ready work continues.

Documentation cannot keep an inactive chat session running. The durable mission state makes a restart safe; hosted autonomous scheduling is a later Gate D outcome and must not be claimed now.

## 7. Receiving-Agent Startup and Closure

1. Read `AGENTS.md`, governance, idea, master, requirements, this handover, the supporting plan, and the complete mission graph.
2. Inspect branch, HEAD, status, relevant history, active writers, and authority hashes.
3. Run mission `status`; if graph drift is reported, run `evaluate`.
4. Do not steal an unexpired claim. Use `claim` only when the lease is expired or the current agent owns it; let supervisor recovery record the transition.
5. Reconcile the taskcard, preceding gate, current diff, tests, and evidence before editing.
6. Work only in taskcard-allowed paths, use `.venv/Scripts/`, and preserve safety invariants.
7. Capture reproduction commands, inputs, outputs, checksums, and independent-verifier results.
8. Transition mission state only with evidence refs; refresh these same three handover files after every transition, coherent commit, external block, or deliberate safe checkpoint.
9. Continue until every mandatory task is closed with sufficient evidence, or all remaining work is genuinely external with exact unblock conditions.

Mission closure requires all mandatory durable tasks closed, truthful requirement status, complete local/workflow/staging/publication/production/recovery/idempotency/safety evidence, the 30-day and 90-day windows, and an independent reproducible Level-8 award. Code, tests, candidates, or reports alone never close the mission.
