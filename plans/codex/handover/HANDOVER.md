# Autonomous Agent Handover

## 1. Handover Snapshot

**Verdict: `HANDOVER_READY`.** This is a verified snapshot, not an override of live durable state. A receiving agent must revalidate it before acting.

| Field | Value |
|---|---|
| Repository | `D:/Users/prora/OneDrive/Documents/GitHub/foss-readme-optimizer` |
| Branch / snapshot HEAD | `main` / `c6b824d3817482666ed547427076fa6eb1c78629` |
| Tree | Only the three canonical handover files were dirty while this snapshot was refreshed. |
| Mission | `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` |
| Durable state | Version 94; graph SHA-256 `8db1168d8a5a84eaa1b5fc057c1cb22b16651cc70f44bfbe2e0c33de1cb3b09b` |
| Active task | `L8-LOCAL-PORTFOLIO-PRODUCT-TRUTH` |
| Mission status | 16 unresolved, one external block, graph drift false, mission complete false |
| Exact next action | Run and repair the seven-ecosystem live product-truth proof; start with [CONTINUE.md](CONTINUE.md). |

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

- `L8-LOCAL-PORTFOLIO-RUNTIME` is durably closed with evidence under
  `runs/level8-local-portfolio-runtime-verification/`; the graph now has
  `L8-LOCAL-PORTFOLIO-PRODUCT-TRUTH` active.
- Commits `922c960` and `c6b824d` bind one immutable `ProductFactsV2` graph through rendering and
  independent review, add C++/Rust verification, and normalize the .NET drafting contract.
- Focused current-tree proof passed: 105 product-truth/lifecycle/reviewer/security tests, six
  local-POC supervisor/write-gate tests, and 27 mission-control/portfolio-tool tests.
- Existing foundation evidence is inspectable under `level8-wave1-heterogeneous-fail-closed-2026-07-23/`, `level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24/`, and `level8-wave4-local-presentation-plan-foundation-2026-07-23/`.

### IMPLEMENTED_BUT_UNVERIFIED

- The active product-truth implementation is committed and offline-proven, but its required
  Java/.NET/Python/TypeScript/C++/Go/Rust live representative proof has not yet completed from the
  stable committed tree. The proof command is the exact next action.

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

1. `L8-LOCAL-PORTFOLIO-PRODUCT-TRUTH`: finish live representative proof for the committed
   snapshot-grounded `ProductFactsV2` flow, acquisition/example verification, and conflict handling.
2. `L8-LOCAL-README-ASSESSMENT-COMPOSITION`: fact-cited source-span plans, protected content, candidate README, and native patch.
3. `L8-LOCAL-INDEPENDENT-REVIEW-REPAIR`: mandatory deterministic validation, independent review, durable reviewer state, bounded repair, revalidation, and no-op proof.
4. `L8-LOCAL-HETEROGENEOUS-QUALIFICATION`: representative ecosystem controls, 100% deterministic validation, and 100 governed agentic evaluations across three sessions at >=95%.
5. `L8-LOCAL-FULL-REGISTRY-GATE-A`: every dynamically loaded entry approved with a complete manifest and no-op proof.
7. Gate B human review of already approved bundles; rejection re-enters repair.
8. Canonical workflow proof under `act`.
9. Disposable GitHub staging.
10. Gate C Java draft-PR proof with fresh what/why/where approval per product push.
11. Gate D GitHub App and hosted runtime, only after Gate C.
12. Controlled Level 5, heterogeneous Level 7 with 30 clean days, then Level 8 with 90 clean days and an independent reproducible award.

The current first boundary is `L8-LOCAL-PORTFOLIO-PRODUCT-TRUTH`: execute
`.venv/Scripts/python plans/investigations/tools/prove_local_portfolio_product_truth_representatives.py`,
repair each agent-fixable lane at its first failure, verify all seven representative graphs and
their exact renderer consumption, then capture a stable-tree checksum inventory and independent
review. Do not transition on offline tests alone.

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
