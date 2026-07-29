# Agent Handover

## 1. Handover Snapshot

- Repository: `D:/Users/prora/OneDrive/Documents/GitHub/foss-readme-optimizer`
- Branch/base HEAD: `main` at `0607b65ffbb366ff8e6d9f8a2fe0b59a5a0bcc00`; the plan commit
  containing this handover follows that content checkpoint.
- Executable authority:
  `plans/investigations/control/level8-autonomous-mission-task-graph.yaml`
- Reconciled graph SHA-256:
  `5e12d81344498f385487949bc0af44896039d587fb0deca870833b6d975fb21a`
- Durable mission state: version 556, no active claim, no graph drift.
- Current phase: T0 trusted qualification—assurance, goal migration, composition, review, and canaries.
- Current/next task: `TRP-00-ASSURANCE-CONTRACT`, status `TODO`.
- Exact next action: claim TRP-00 and implement explicit trusted-versus-verified assurance,
  disjoint lifecycle/counters/cache/manifest/proposal/effect identity, and the ordered
  stage-goal migration without adding a second runtime.
- Overall status: plan-ready and resumable; implementation of trusted mode has not started.

Live repository and supervisor state override this historical snapshot.

## 2. Ultimate Goal

The ultimate goal is `verified_repository_presentation`: an autonomous system that derives
product truth from repository source, manifests, consumer tooling, tests, examples, releases,
verified registries, and approved policy; reconciles existing README claims; manages every
applicable repository-presentation surface; creates safe authorized proposals; and earns
independently reproducible Level 5, 7, and 8 evidence.

The temporary short-term goal is `trusted_readme_transform`: for every current registry
repository, transform the existing README through an LLM-first pipeline, treating its own claims
as `README_INHERITED` evidence without repository/external fact verification, independently
approve transformation quality and fidelity, prove no-op, and open one clearly disclosed draft
PR through the same `act`, staging, GitHub App, hosted workflow, authorization, and effect
pipeline. After all trusted PRs exist, resume the ultimate verified mission without promoting
their content assurance.

The runtime goal is not a universal mission label. `evaluate` derives exactly one goal in this
order and automatically advances or reactivates it from evidence:

`GOAL-T0-TRUSTED-QUALIFICATION` → `GOAL-T1-TRUSTED-PORTFOLIO` →
`GOAL-T2-WORKFLOW-STAGING` → `GOAL-T3-HOSTED-TRUSTED-DELIVERY` →
`GOAL-V1-VERIFIED-TRUTH` → `GOAL-V2-VERIFIED-GATE-A` →
`GOAL-V3-HUMAN-AND-JAVA-PROOF` → `GOAL-L5-PRESENTATION-PILOT` →
`GOAL-L6-AUTONOMOUS-PORTFOLIO` → `GOAL-L7-HETEROGENEOUS-30D` →
`GOAL-L8-SELF-MAINTAINING-90D`.

## 3. Current Mission and Scope

Mission ID: `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`.

Short-term mandatory outcomes:

1. Explicit `ContentAssuranceV1` and anti-promotion controls.
2. README-derived typed facts/claims with exact source spans.
3. LLM-first inventory, plan, bounded section composition, and repair.
4. Deterministic presentation/safety validation.
5. Independent blind-quality and inheritance-fidelity approval.
6. Real adversarial canary qualification.
7. Full-registry transformation/no-op proof.
8. Actual reusable-workflow proof under `act`.
9. Disposable staging proposal/effect proof.
10. GitHub App and hosted autonomous workflow qualification on staging.
11. Live per-repository write access and reviewed authorization.
12. Exactly one disclosed trusted draft PR per current registry repository.

Non-goals: repository-source fact reconciliation inside trusted mode, a second controller/store,
a universal deterministic rewrite engine, fork PR support unless direct access fails and is
separately authorized, merge/ready/force-push/default-branch effects, or calling a trusted result
verified.

## 4. Authority and Reference Map

| Reference | Role | Authority |
|---|---|---|
| `plans/idea.md` | Product outcome and trusted/verified gate order | Product authority |
| `plans/master.md` decisions #78/#83/#84/#85 | Architecture, goals, sequence, gates | Executable plan |
| `plans/requirements.md` `TRP-001`–`TRP-014` | Normative trusted acceptance | Normative |
| `plans/GOVERNANCE.md` rules 14–21 | Governance and assurance/goal separation | Binding |
| Mission task graph | Sole task/dependency graph | Executable authority |
| Supervisor Git-ref state | Claims and transitions | Live execution authority |
| `AGENTS.md` | One-operator, safety, effect and gate instructions | Binding |
| Codex idea-fidelity plan | Detailed supporting route | Supporting only |

## 5. Exact Plan

### Phase T0 — Assurance separation

Add the typed assurance axis, trusted lifecycle/verdict/proposal/counter identities, dependency
fingerprints, and durable migration. Trusted and verified records must be mechanically disjoint.

### Phase T1 — README-derived evidence

Capture immutable README bytes and let the LLM extract a typed source inventory/fact graph. Every
inherited fact cites exact README spans and `README_INHERITED`; approved standard additions use
`CONFIGURED_STANDARD`. Make zero repository/package/external fact-verification calls.

### Phase T2 — LLM-first composition

The LLM performs transformation planning and authors one or more bounded section drafts.
Deterministic code only parses/assembles Markdown and enforces contracts, provenance, safety,
links, headers, Mermaid, terminology, caching, and effects.

### Phase T3 — Independent review and repair

Require deterministic validation, separate blind-quality and inheritance-fidelity reviewers,
grounded findings, changed-candidate section repair, and exact LLM call/cache accounting.

### Phase T4 — Canary qualification

Serially prove Python, .NET, ordinary Java, malformed/prompt-injected content, and the largest
current README. Fan-out is prohibited until all pass recovery, no-op, and no-effect controls.

### Phase T5 — Full-registry transformation

Run two-to-four supervisor-owned isolated lanes in platform priority. Close only when every
current registry entry is trusted-approved/no-op-proven with a checksum-valid PR-ready bundle.

### Phase T6 — Actual workflow under `act`

Run the same supervisor/lifecycle through the actual reusable workflow. Prove dispatch variants,
matrix isolation, deduplication, checkpoint resume, recovery, evidence upload, health aggregation,
and production-token fallback rejection without a product write.

### Phase T7 — Disposable staging

Prove create/no-op/update/drift/dedup/lost-response/expired-authorization/crash reconciliation
against disposable GitHub repositories. Default branches remain byte-identical and analysis jobs
never receive a write token.

### Phase T8 — GitHub App and hosted staging qualification

Only after `act` and staging pass, request the exact App authority and secrets. Prove fresh
short-lived tokens, analysis/effect isolation, hosted triggers, recovery, leases, backlog, health,
alerts, dead-man monitoring, and terminal manifests on staging.

### Phase T9/T10 — Authority and draft PRs

Check direct write access live, consume reviewed expiring authorizations, and create/update exactly
one disclosed draft PR per repository. Prove update, drift, duplicate delivery, lost response,
expiry, crash recovery, and default-branch byte identity.

### Verified continuation

After `TRP-07`, resume preserved `L8-INTAKE-02`, verified repository facts and reconciliation,
verified Gate A/B/C, all surfaces, Level 5, Level 6, Level 7, and Level 8. Reuse prior operational
proof only when its hashes and environment remain current. No verified requirement is omitted.

## 6. Work Completed

Verified reusable foundations include source-complete observation (`L8-INTAKE-00`), provider-stable
registry identity (`L8-INTAKE-01`), canonical `supervise`, immutable snapshots, durable lifecycle,
leases/CAS, evidence redaction/checksums, LLM call ledger/cache, deterministic presentation
contracts, blind-review machinery, allow-list, push blocking, authorization, and effect ledger.

`L8-INTAKE-02` is implemented but unverified. Its missing combined
discovery → disabled admission → one intake public-path proof is preserved behind TRP-07.

No TRP task is implemented. Existing 8/31 verified fact/candidate/deterministic artifacts are
reusable where their hashes remain valid, but they provide zero trusted PRs and zero verified
agent approvals/no-ops.

## 7. Current Working State

The plan amendment starts from clean `main` HEAD `0607b65f...`. Durable state was evaluated to
version 556 with `TRP-00` as the sole eligible task and no active claim. The graph uses the legacy
universal/subordinate bindings only for parser bootstrap; TRP-00 must atomically migrate to the
ordered T0/T1/T2/T3/V1/V2/V3/L5/L6/L7/L8 goal catalog. The immediate target is
`GOAL-T0-TRUSTED-QUALIFICATION`, not the displayed legacy universal goal.

## 8. Remaining Gaps

- `GAP-TRP-ASSURANCE`: no typed assurance separation; first boundary and current task.
- `GAP-TRP-LLM-COMPOSITION`: current LLM chiefly selects deterministic operations rather than
  authoring bounded sections.
- `GAP-TRP-FIDELITY-REVIEW`: current factual reviewer cannot represent deliberate inherited
  assurance; real output has truncated and repair has returned unchanged bytes.
- `GAP-TRP-LONG-DOCUMENT`: largest current README exceeds reliable single-output generation.
- `GAP-TRP-PORTFOLIO`: no full-registry trusted approval/no-op campaign.
- `GAP-TRP-WORKFLOW`: no complete canonical trusted run under the actual reusable workflow.
- `GAP-TRP-STAGING`: no trusted remote proposal/recovery matrix in disposable GitHub staging.
- `GAP-TRP-HOSTED`: App authentication, hosted recovery, health, and dead-man behavior are unproved.
- `GAP-TRP-AUTHORITY`: owner intends to obtain remaining write access, but live access and reviewed
  authorization are not yet complete.
- `GAP-TRP-EFFECT`: no assurance-specific trusted proposal and full-registry PR reconciliation.

## 9. Ordered Execution Queue

1. `TRP-00-ASSURANCE-CONTRACT`
2. `TRP-01-README-DERIVED-FACTS`
3. `TRP-02-LLM-FIRST-COMPOSITION`
4. `TRP-03-INDEPENDENT-FIDELITY-REVIEW`
5. `TRP-04-CANARY-QUALIFICATION`
6. `TRP-05-FULL-REGISTRY-TRANSFORM`
7. `TRP-05A-ACT-WORKFLOW-PARITY`
8. `TRP-05B-STAGING-EFFECT-PROOF`
9. `TRP-05C-GITHUB-APP-HOSTED-QUALIFICATION`
10. `TRP-06-AUTHORIZATION-ACCESS`
11. `TRP-07-DRAFT-PR-PORTFOLIO`
12. Resume `L8-INTAKE-02` and the complete verified graph.

Every taskcard contains exact allowed paths, dependencies, implementation outputs, focused and
regression verification, negative controls, evidence, recovery, and closure rules.

## 10. Decisions and Constraints

- One operator and one top-level command tree.
- Work directly on control-repository `main`; preserve user work.
- No second plan, controller, queue, state backend, or execution profile.
- LLM-first trusted composition; deterministic code remains the safety/contract envelope.
- README content is trusted data but untrusted instruction.
- No comments in candidate READMEs.
- Preserve header/badges, Mermaid, natural contextual links, configurable link budgets,
  product-subdomain priority, and exact Enterprise Edition terminology.
- Platform priority: Python, .NET, Java, C++, TypeScript, Rust, Go.
- Serial through canaries; two-to-four isolated lanes only after qualification.
- Every LLM call/retry/cache reuse is attributed per README.
- Expected write access is not current authority.
- Draft PR only; no merge, ready transition, force-push, or default-branch write.
- Trusted evidence never promotes into verified evidence.
- App authority is requested after trusted `act` and staging proof, then qualified on staging
  before trusted product PR effects.
- Exactly one stage goal is derived automatically; no operator or narrative file selects it.
- Every Codex commit includes `Co-Authored-By: Codex <noreply@openai.com>`.

## 11. Tests, Proof, and Evidence

Plan reconciliation currently proves:

- graph loads with 114 taskcards;
- 447 requirement rows map deterministically;
- plan structure passes;
- mission evaluate migrated state to version 556;
- graph drift is false and `TRP-00` is sole eligible.
- focused mission/plan/CLI tests pass: 69 passed, 53 deselected;
- the pre-commit full official gate passed Ruff, format, mypy, 2,183 non-live tests, plan
  structure, verifier wiring, prompt hygiene, coverage, traceability, and semantic closure;
  `actionlint` was unavailable and explicitly skipped. The official wrapper correctly withheld
  committed-state proof because the plan tree had not yet been committed.

Implementation, canary, full-registry, access, authorization, and PR proof remain unrun because
this change is a plan amendment, not implementation closure.

## 12. Risks and Uncertainty

- The goal guard needs an additive bootstrap migration before the stage-goal catalog becomes
  native durable state; current universal-goal status is explicitly stale after this plan change.
- LLM output envelopes are not yet qualified against the largest current README.
- Existing README claims may be stale or wrong; trusted PRs must disclose this.
- Direct write access is promised but not yet live-proven for every repository.
- A one-day full-registry campaign is a target only after the implementation and canaries pass.
- Human reviewers may reject transformed inherited content; later verified reconciliation may
  correct claims even if a trusted PR was accepted.

## 13. Receiving Agent Startup Steps

1. Read authority and run mission status.
2. Verify main/HEAD/tree/processes and graph hash.
3. Claim `TRP-00-ASSURANCE-CONTRACT`.
4. Implement only its declared assurance/goal/state boundary.
5. Run focused schema/migration/lifecycle/cache/effect tests.
6. Run relevant integration, regression, safety, recovery, and idempotency checks.
7. Capture redacted checksum-complete evidence and independent verification.
8. Update the same requirements/task/log/handover and commit to main.
9. Evaluate and claim TRP-01.
10. Continue autonomously through TRP-05A/05B/05C, TRP-06/07, and then the preserved verified
    mission.

## 14. Closure Standard

The short-term trusted POC closes only when `TRUSTED_PR_OPEN == len(data/products.json)` against a
fresh complete registry revision, with zero undisclosed assurance, duplicate PRs, system failures,
manifest failures, prohibited effects, or default-branch changes. The same closure also requires
current `act`, disposable-staging, GitHub App, hosted-recovery, and health proof.

The complete mission closes only after every mandatory graph task is evidence-backed `CLOSED`,
verified repository presentation passes all local/workflow/staging/delivery/production gates, the
30-day and 90-day windows complete, and an independent audit awards Level 8.
