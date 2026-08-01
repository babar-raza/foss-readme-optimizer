# Agent Handover

## 1. Handover Snapshot

- Repository: `D:/Users/prora/OneDrive/Documents/GitHub/foss-readme-optimizer`
- Branch: `main`
- Content checkpoint: `fe285db4551f8282b33ca1237c0b24b61a8c3070`
- Upstream relation at capture: `main` is two commits ahead of `origin/main` and not behind.
- Working tree at capture: clean.
- Executable authority: `plans/investigations/control/level8-autonomous-mission-task-graph.yaml`
- Graph SHA-256: `d5a99e705688404887d36d107ab822dd8283e44f7b9b5b21664447b8b8941eb7`
- Durable state: version 678, no graph drift.
- Active goal: `GOAL-V1-VERIFIED-TRUTH`.
- Active task: `L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP`, `IN_PROGRESS`, claimed by `Codex`.
- Portfolio boundary: mission status reports a raw/unreconciled 17/31 facts ready; freshness-aware
  reconstruction found every prior Python result stale and the new Note canary now establishes
  exactly 1/12 current Python `FACTS_READY`. Current approvals and no-op proofs remain 0/31.
- Exact next action: reclaim the expired Wave 3 lease, log and repair `IV-PFR-001` (freshness-aware
  mission facts count) and `IV-PFR-002` (facts-stage manifest provenance), then requalify Page and
  PDF Python without rerunning the unchanged Note canary.
- Overall status: `PARTIAL`. A bounded throughput/control slice is committed and accepted by an
  independent verifier, but Wave 3, Gate A, and the Level-8 mission are not closed.

This document is a historical restart snapshot. Live Git and supervisor state override it after
every task transition or commit.

## 2. Ultimate Goal

Deliver the system described in `plans/idea.md`: an autonomous, evidence-first repository-
presentation manager that derives product truth from repository/package/test evidence, creates
professional and consistent repository-specific presentation, proposes only authorized draft
changes, recovers durably, and earns independently reproducible Level 5, Level 7, and Level 8
proof.

The immediate visible horizon is verified README management. It requires complete, current,
independently approved and unchanged-no-op-proven local bundles for the dynamic registry. Python
has first platform priority, followed by .NET, Java, C++, TypeScript, Rust, and Go. A partial batch
is development evidence, never the POC.

## 3. Current Mission and Scope

Mission ID: `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`.

Current mission:

1. Complete repository-derived `ProductFactsV2` and ownership safety for every required claim.
2. Advance each repository through immutable snapshot, verified facts, assessment, structured
   plan, candidate, deterministic validation, independent review, repair, and no-op proof.
3. Close full-registry local Gate A, then human Gate B.
4. Prove the same canonical runtime under `act`, disposable staging, and governed draft-PR effects.
5. Add hosted GitHub App operation only after its upstream gates, then complete all presentation
   surfaces and the elapsed Level 7/8 evidence windows.

Non-goals for the current task are product-repository writes, default-branch changes, merges,
package/release writes, production App installation, a competing controller, and a rewrite of the
working supervisor/capability/state/evidence foundations.

Completion requires actual evidence, not code presence or plan prose. Every mandatory durable
task must be `CLOSED`, every normative requirement must have current proof, all safety/recovery/
idempotency gates must pass, and an independent audit must award the claimed maturity level.

## 4. Authority and Reference Map

| Reference | Role and relevant key | Authority/status |
|---|---|---|
| `plans/idea.md` | Product outcome and ordered README gates | Highest product authority; current |
| `plans/master.md` | Mission, decisions #81-#88, architecture, build/verification gates | Governed execution design; current |
| `plans/requirements.md` | Normative obligations including `GOV-030`, `FACT-017`, `L8-006`, `CORE-023`, `L8-036`, `L8-038` | Acceptance authority; mixed statuses are intentional |
| `plans/GOVERNANCE.md` | Rules 18-20, especially rule 19 multi-agent execution | Binding governance; current |
| `AGENTS.md` | One coordinator, safety, verification, platform order | Binding operator instructions; current |
| `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` | Sole executable task graph; current task at `L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP` | Executable authority; current hash above |
| Supervisor Git-ref state | Version 678 claim/task/lifecycle authority | Live authority; always re-read |
| `plans/codex/idea-fidelity-to-level-8-autonomous-execution-plan.md` | Detailed route and coordinator/worker protocol | Supporting design; not a second controller |
| `runs/multi-agent/L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP/execution-plan.json` | Current task lane dispositions and leases | Runtime record; current for the completed slice, update before the next slice |
| `plans/investigations/evidence/level8-registry-throughput-multi-agent-v1/` | Committed bounded slice evidence | Current supporting proof; explicitly not task closure |
| `runs/verification/pytest-full-latest.json` | Latest complete non-live suite receipt | Current candidate-tree proof; not a clean-HEAD closure proof |
| Old trusted/VPY handover text | Earlier route and counters | Superseded; must not override live state |

Document hashes at capture are recorded in `state.json`.

## 5. Exact Plan

### Phase A - Wave 3 product truth and ownership (current)

- Entry: local runtime/foundation tasks exist and the durable graph has selected Wave 3.
- Required work: complete provenance, precedence/conflict behavior, field ownership, protected
  content, isolated package/example verification, prompt-injection resistance, and fact-to-claim
  gating.
- Current progress: mission status reports 17/31 raw facts-stage lifecycle states, but those are not
  freshness-filtered. Independent reconstruction found prior Python bundles stale; Note Python is
  now the first current-contract result at 1/12. Structured minimal-example transport,
  registry grammar, stale-acceptance invalidation, and multi-agent controls were repaired in commit
  `908f9f3b54a93ef12a6eb265e17366b0cb0ac21a`.
- Remaining: resolve the 14 FACTS_READY gaps, starting with Python; obtain representative real
  package/example proof; independently accept the fact graphs; satisfy all Wave 3 exit gates.
- Exit: false coordinates cannot pass, unsupported claims remain blocked, protected content cannot
  disappear, isolated execution is proven, and the independent factuality reviewer accepts the
  representative evidence.

### Phase B - Verified README qualification and Gate A

- Use the finalized global presentation contract and reusable profiles.
- For every runtime registry member: assessment, fact-bound document plan, candidate, native patch,
  deterministic verification, independent review, bounded repair, and unchanged no-op proof.
- Invalidate stale acceptance when source, facts, prompt, template, policy, validator, reviewer, or
  protected-content fingerprints change.
- Exit: current `AGENT_APPROVED == NO_OP_PROVEN == len(data/products.json)`, with zero system
  failures and checksum-complete manifests. Current denominator is 31; always recompute it.

### Phase C - Human review, workflow, staging, and publication proof

- Gate B presents only agent-approved/no-op-proven bundles.
- Reproduce the full workflow under `act`, including recovery, deduplication, isolation, and evidence.
- Use disposable GitHub staging to prove proposal create/update/no-op/drift/lost-response/recovery.
- Gate C uses fresh what/why/where authorization for each product-repository draft PR. Never merge,
  mark ready, force-push, close, or write the default branch.

### Phase D - Hosted operation and maturity

- Request GitHub App organization access only after preceding gates require it.
- Prove token isolation, hosted triggers/checkpoints/recovery/health/dead-man monitoring.
- Complete remaining GitHub presentation surfaces and the controlled Java Level-5 pilot.
- Prove the heterogeneous portfolio and 30-day Level 7 window.
- Prove the 90-day Level 8 self-maintenance window and obtain independent audit acceptance.

## 6. Work Completed

### Verified complete for the latest bounded slice

- `GOV-030` multi-agent protocol is machine-readable in the graph and synchronized in
  `AGENTS.md`, `plans/master.md` decision #81, `plans/GOVERNANCE.md` rule 19, and the supporting
  execution plan. Documentation/State-Sync is proposal-only; the coordinator alone applies shared
  changes.
- Registry naming is centralized in `src/readme_agent/registry/naming.py`: case-insensitive exact
  `Aspose[.-]{Family}-FOSS-for-{Platform}`, no terminal suffix. CSSForge and the MCP-suffixed Go
  repository are excluded; the ordinary Go repository remains admitted.
- Product-fact LLM output uses structured `minimal_example.code_lines[]` and a deterministic
  normalizer. The prompt is version 18.
- Lifecycle summaries separate current from raw/stale acceptance. Slides Python and Words Python
  are explicitly stale rather than counted as current approvals.
- Invalidated candidates are preserved under checksum-addressed `superseded/` storage with
  collision validation.
- Commit `908f9f3b54a93ef12a6eb265e17366b0cb0ac21a` contains the integrated slice. Independent verdict:
  accepted for the bounded slice, no Wave 3/Gate A/mission closure.

### Verification performed

- Focused integrated matrix: 288 passed in 102.95 seconds.
- Complete non-live suite after fixture repairs: 2639 passed in 259.95 seconds; zero leaked
  repository-owned processes.
- Ruff check, Ruff format check, mypy, plan structure, requirement coverage, semantic
  traceability, verifier enforcement, prompt hygiene, actionlint, and `git diff --check` passed.
- Independent replay: 130 representative tests passed in 25.03 seconds; 12 high-risk nodes passed
  in 1.60 seconds; static/governance/actionlint checks accepted.

### Partial or implemented but unverified

- `CORE-023`, `L8-036`, and `L8-038` are correctly `PARTIAL`: code enforces the revised registry
  grammar, but a fresh authenticated all-visibility `RegistryRevisionV1` proof for the 31-member
  set and explicit exclusions is still absent.
- Wave 3 foundations exist. The 17/31 mission numerator is raw/unreconciled; only 1/12 Python
  repositories has been requalified against the current fact contract.
- Nine current candidates are deterministically validated, but none has a current independent
  approval/no-op pair. Two older raw pairs are stale and cannot count.
- Latest full-suite receipt was made on the integrated candidate tree before commit; it is strong
  regression evidence but not a clean-HEAD task-closure receipt.

### Contradicted or stale claims

- Any 33-repository denominator is stale. Current admitted registry count is 31.
- Any claim of 13 current no-op-proven repositories is contradicted by current lifecycle
  reconstruction: current count is zero.
- Any handover selecting `GOAL-V0-VERIFIED-PYTHON-POC` or `L8-VPY-00-GOLDEN-TEMPLATE` is stale.
- CSSForge and `Aspose-PDF-FOSS-for-Go-MCP` are observations/exclusions, not portfolio members.

## 7. Current Working State

The tree was clean at `908f9f3b54a93ef12a6eb265e17366b0cb0ac21a` before this handover refresh.
The active Wave 3 claim was reclaimed as `Codex`, producing durable state version 678, but its lease
expired at this checkpoint. The current task lane record describes the completed
`python-facts-ready-recovery-01` slice and must be updated before a new implementation wave. All
worker lanes and repository-owned command trees are stopped.

Latest successful boundary: Note Python requalified at current `FACTS_READY` with one provider call;
its immediate identical rerun made zero provider calls, added no lifecycle transition or effect,
and reused the same revision bundle. Independent verification accepted this bounded slice. HTML
Python was independently confirmed fail-closed on invalid upstream PEP 517 backend metadata.

Latest unresolved boundary: mission facts-stage counts are not freshness-filtered (`IV-PFR-001`),
and facts-stage RunManifestV3 omits known immutable source fields (`IV-PFR-002`). HTML Python has an
invalid upstream build backend; TeX remains agent-fixable until its current requalification proves
otherwise. These are facts/evidence problems and must not be papered over with generic prose.

## 8. Remaining Gaps

| ID | Severity/status | First failing boundary | Permanent solution and proof |
|---|---|---|---|
| `FACT-017`, `L8-006` | P1/P0, open | Agent-drafted product truth is not fully mechanically grounded | Repair each producer/verification boundary; require citations, deterministic checks, isolated consumer proof, conflict controls, and independent factuality acceptance |
| `L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP` | P0, in progress | Raw 17/31; current Python 1/12 | Repair freshness/provenance defects, requalify Python, then remaining platforms; close only after every Wave 3 acceptance check passes |
| `IV-PFR-001` | P1, agent-fixable | Mission facts numerator ignores stale fact contracts | Apply the per-repository fact-cache freshness predicate or label a separate raw count; prove stale/current controls and status output |
| `IV-PFR-002` | P1, agent-fixable | Facts-stage RunManifestV3 omits captured revision/snapshot | Populate immutable trigger/upstream/snapshot fields from the captured snapshot and prove checksum-complete semantic manifests |
| `CORE-023`, `L8-036`, `L8-038` | P0, partial | Current all-visibility registry proof absent | Generate a fresh authenticated `RegistryRevisionV1` proving 31 admissions, 12 Python members, explicit CSSForge/MCP exclusions, zero unexplained observations, recovery, and no-op |
| Current lifecycle acceptance | P0, 0/31 | Stale approval fingerprints | Rebuild only invalidated dependent stages; rerun deterministic review, independent review, repair, and no-op proof |
| TeX Python truth | P0 for Python cohort | Source/package consumer verification | Determine whether repository syntax/build state permits a supported evidence path; record a narrow external fact block only if no locally recoverable authoritative route exists |
| HTML Python truth | P0 for Python cohort | Invalid setuptools backend/acquisition | Correct ecosystem detection or source-build metadata interpretation, then rerun isolated acquisition and facts gates |
| `L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME` | `BLOCKED_EXTERNAL` in durable state | Hosted/production-like proof | Do not let it block independent local truth work; revisit at the plan's `act`/hosted gate with required infrastructure |
| `L8-VPY-03-ALL-PYTHON-VERIFIED-POC` | `BLOCKED_EXTERNAL` in durable state | Old Python goal route | Reconcile its dependency/status only through the same graph; it cannot substitute for the current Wave 3 claim |

## 9. Ordered Execution Queue

1. `L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP` - reclaim its expired lease and update its task-lane record;
   repair `IV-PFR-001` and `IV-PFR-002`; run focused mission/manifest/security tests and independent
   verification. Preserve the accepted Note evidence.
2. Requalify Page and PDF Python, then the remaining Python repositories, followed by .NET, Java, C++, TypeScript,
   Rust, and Go. Reuse content-addressed valid stages; do not rerun unchanged work.
3. Generate the fresh authenticated all-visibility registry revision and restore `CORE-023`,
   `L8-036`, and `L8-038` only when its evidence passes.
4. Complete current independent approval and no-op proof for each repository; stale raw verdicts
   must be regenerated, not relabeled.
5. Close full-registry Gate A and prepare Gate B only when the dynamic denominator is complete.
6. Proceed in dependency order through `act`, staging, Gate C, GitHub App/hosted runtime, Level 5,
   Level 7, and Level 8.

For each task the coordinator must write one `runs/multi-agent/<task-id>/execution-plan.json`,
disposition all five roles, lease disjoint paths, integrate serially, run required regression/
safety proof, then launch an implementation-independent verifier. At most three workers may run
beside the coordinator; roles run in waves when needed.

## 10. Decisions and Constraints

- One accountable coordinator. Workers never own shared plans/state, integration, commits, closure,
  final evidence, or product effects.
- Required roles: Repair, Advancement, Validator/Evidence, Documentation/State-Sync, Independent
  Verification. Spawn only roles with useful independent work; always disposition all five.
- Documentation/State-Sync writes proposals under `runs/multi-agent/`; the coordinator applies them.
- Work directly on control-repository `main`. Do not create control branches.
- Preserve user/concurrent work; no reset, restore, clean, destructive history, or force-push.
- Use `.venv/Scripts/python` and `.venv/Scripts/readme-agent`; never the global Python toolchain.
- `supervise` is the sole production runtime. `data/products.json` is the allow-list.
- Existing README text is valuable evidence, not automatically true. Every material final claim
  needs accepted facts, authority, or an explicit uncertainty/correction disposition.
- No comments in generated READMEs, no emojis, standard consistent header, detailed non-directional
  Mermaid, full product names outside API/package identifiers, natural contextual links, link-budget
  controls, and the phrase `Enterprise Edition` for aspose.com products.
- No product remote write without fresh exact what/why/where confirmation. Never merge or write a
  target default branch.
- Safe local commands are pre-authorized. Ask only for genuine external authority, secrets,
  infrastructure, manual UI, or an explicitly gated external effect.
- After two ineffective attempts or 15 minutes at the same failing boundary, stop repeating the
  same approach and perform a first-principles redesign of that boundary.

## 11. Tests, Proof, and Evidence

Primary evidence:

- `plans/investigations/evidence/level8-registry-throughput-multi-agent-v1/README.md`
- `plans/investigations/evidence/level8-registry-throughput-multi-agent-v1/verification.json`
- `plans/investigations/evidence/level8-registry-throughput-multi-agent-v1/independent-verification.md`
- `plans/investigations/evidence/level8-registry-throughput-multi-agent-v1/sha256sums.txt`
- `runs/multi-agent/L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP/execution-plan.json`
- `runs/verification/pytest-full-latest.json`
- `runs/multi-agent/independent-verification/python-facts-ready-01/REPORT.md`
- `runs/multi-agent/independent-verification/python-facts-ready-01/verification.json`

The exact 288-test command and all static commands are recorded in the committed evidence README.
The latest independent report records 60 acquisition tests and 98 current README-operation tests
passing; the older literal 88-test count is stale. Tests still required before Wave 3 closure are
real isolated package/example execution for affected ecosystems, current representative facts,
prompt-injection/false-coordinate/protected-content negative controls, and a clean committed-tree
official campaign at the task boundary.

No product remote effect was performed by the latest slice.

## 12. Risks and Uncertainty

- Live repository/package state can change; current facts and registry visibility require fresh
  revision-bound evidence.
- Python repositories differ materially. A shared parser or prompt fix may not repair broken
  upstream source/build metadata; keep failures repository-bound.
- Latest regression receipt binds a dirty pre-commit tree, not the exact current commit.
- The two durable `BLOCKED_EXTERNAL` tasks are real recorded state, but unrelated local Wave 3 work
  remains available, so the mission itself is not globally blocked.
- The active claim has a lease. Re-read it on restart and never steal an unexpired claim.
- Runtime files under `runs/` are disposable and may not exist on another machine; committed
  evidence and durable Git-ref state are the cross-session authorities.

## 13. Receiving Agent Startup Steps

1. Start in `D:\Users\prora\OneDrive\Documents\GitHub\foss-readme-optimizer`.
2. Read `AGENTS.md`, `plans/idea.md`, relevant current sections of `plans/master.md`,
   `plans/requirements.md`, `plans/GOVERNANCE.md`, and the current task in the mission graph.
3. Run `git status --short --branch`, `git rev-parse HEAD`, and inspect upstream divergence.
4. Run mission `status` below. If graph drift is true, run `evaluate`. Reclaim only an expired
   claim through `--mission-action claim`; never overwrite durable state manually.
5. Reclaim the expired Wave 3 claim and verify the Note evidence; do not rerun it unless a dependency
   fingerprint changed. Start the next slice with `IV-PFR-001` and `IV-PFR-002`.
6. Update the same task-lane record, disposition all five roles, and grant disjoint paths. Use
   Repair for the producer defect, Advancement for a separate unaffected repository, Validator/
   Evidence for read-only reconstruction, Documentation/State-Sync for proposal-only changes, and
   Independent Verification only after integration.
7. Implement the smallest complete permanent repair through public seams.
8. Run focused tests, relevant safety/regression tests, then this bounded canonical proof:

```powershell
.venv/Scripts/readme-agent supervise `
  --registry data/products.json `
  --execution-profile local_poc `
  --max-readme-poc-stage FACTS_READY
```

9. Capture revision, inputs, hashes, lifecycle transitions, LLM calls, validations, failures, and
   reproduction commands in redacted evidence.
10. Integrate serially, run independent verification, update the same requirements/task/log/
    handover state, commit a coherent slice directly to `main` with the Codex trailer, evaluate,
    rebuild eligibility, and continue without waiting for another prompt.

Mission status command:

```powershell
.venv/Scripts/readme-agent supervise `
  --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
  --mission-action status `
  --mission-observer Codex `
  --durable-state
```

## 14. Closure Standard

The receiving agent may not declare this mission complete until:

- every mandatory graph task is `CLOSED` with current evidence;
- every normative requirement is truthfully reconciled;
- the dynamic registry has complete current verified bundles and no-op proof;
- local, `act`, staging, proposal, hosted, recovery, safety, idempotency, and evidence-corruption
  gates pass;
- no unauthorized/default-branch/package/release/GitHub-generated-surface write occurred;
- the 30-day Level 7 and 90-day Level 8 windows complete;
- an implementation-independent audit reproduces the evidence and awards Level 8; and
- reevaluation finds no mandatory ready, in-progress, agent-fixable blocked, reopened, regressed,
  or unresolved task.

Current verdict: `HANDOVER_READY` for continuation, not mission completion.
