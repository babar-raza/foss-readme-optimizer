# Agent Handover

## 1. Handover Snapshot

- Repository: `D:/Users/prora/OneDrive/Documents/GitHub/foss-readme-optimizer`
- Branch/base HEAD: `main` at `883fd30760b17855d5648d29c184ac97ec453336`; the plan commit
  containing this handover follows that content checkpoint.
- Executable authority:
  `plans/investigations/control/level8-autonomous-mission-task-graph.yaml`
- Reconciled graph SHA-256:
  `d380edde56f18a7c2e9e4f98a7b753bc76292d300a7b899acafff42cf94b3310`
- Durable mission state: version 552, no active claim, no graph drift.
- Current phase: trusted POC, LLM-first full-registry README transformation and draft PRs.
- Current/next task: `TRP-00-ASSURANCE-CONTRACT`, status `TODO`.
- Exact next action: claim TRP-00 and implement explicit trusted-versus-verified assurance,
  disjoint lifecycle/counters/cache/manifest/proposal/effect identity, and the additive goal/state
  migration without adding a second runtime.
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
PR. After all trusted PRs exist, resume the ultimate verified mission.

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
8. Live per-repository write access and reviewed authorization.
9. Exactly one disclosed trusted draft PR per current registry repository.

Non-goals: repository-source fact reconciliation inside trusted mode, a second controller/store,
a universal deterministic rewrite engine, fork PR support unless direct access fails and is
separately authorized, GitHub App work, merge/ready/force-push/default-branch effects, or calling a
trusted result verified.

## 4. Authority and Reference Map

| Reference | Role | Authority |
|---|---|---|
| `plans/idea.md` | Product outcome and trusted/verified gate order | Product authority |
| `plans/master.md` decisions #78/#83/#84/#85 | Architecture, goals, sequence, gates | Executable plan |
| `plans/requirements.md` `TRP-001`–`TRP-011` | Normative trusted acceptance | Normative |
| `plans/GOVERNANCE.md` rules 14–20 | Governance and assurance separation | Binding |
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

### Phase T6/T7 — Authority and draft PRs

Check direct write access live, consume reviewed expiring authorizations, and create/update exactly
one disclosed draft PR per repository. Prove update, drift, duplicate delivery, lost response,
expiry, crash recovery, and default-branch byte identity.

### Verified continuation

After `TRP-07`, resume preserved `L8-INTAKE-02`, verified repository facts and reconciliation,
verified Gate A/B/C, `act`, staging, hosted App operation, all surfaces, Level 5, Level 7, and
Level 8. No verified requirement is omitted.

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

The plan amendment starts from clean `main` HEAD `883fd307...`. Durable state was evaluated to
version 552 with `TRP-00` as the sole eligible task and no active claim. The graph uses existing
`GOAL-README`/`GOAL-DELIVERY` bindings for bootstrap; TRP-00 must add the new
`GOAL-TRUSTED-POC` goal to the typed goal guard and graph atomically.

## 8. Remaining Gaps

- `GAP-TRP-ASSURANCE`: no typed assurance separation; first boundary and current task.
- `GAP-TRP-LLM-COMPOSITION`: current LLM chiefly selects deterministic operations rather than
  authoring bounded sections.
- `GAP-TRP-FIDELITY-REVIEW`: current factual reviewer cannot represent deliberate inherited
  assurance; real output has truncated and repair has returned unchanged bytes.
- `GAP-TRP-LONG-DOCUMENT`: largest current README exceeds reliable single-output generation.
- `GAP-TRP-PORTFOLIO`: no full-registry trusted approval/no-op campaign.
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
7. `TRP-06-AUTHORIZATION-ACCESS`
8. `TRP-07-DRAFT-PR-PORTFOLIO`
9. Resume `L8-INTAKE-02` and the complete verified graph.

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
- GitHub App remains behind verified Gate C.
- Every Codex commit includes `Co-Authored-By: Codex <noreply@openai.com>`.

## 11. Tests, Proof, and Evidence

Plan reconciliation currently proves:

- graph loads with 109 taskcards;
- 443 requirement rows map deterministically;
- plan structure passes;
- mission evaluate migrated state to version 551;
- graph drift is false and `TRP-00` is sole eligible.

Implementation, canary, full-registry, access, authorization, and PR proof remain unrun because
this change is a plan amendment, not implementation closure.

## 12. Risks and Uncertainty

- The goal guard needs an additive bootstrap migration before `GOAL-TRUSTED-POC` can become a
  native task goal.
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
10. Continue autonomously through TRP-07 and then the preserved verified mission.

## 14. Closure Standard

The short-term trusted POC closes only when `TRUSTED_PR_OPEN == len(data/products.json)` against a
fresh complete registry revision, with zero undisclosed assurance, duplicate PRs, system failures,
manifest failures, prohibited effects, or default-branch changes.

The complete mission closes only after every mandatory graph task is evidence-backed `CLOSED`,
verified repository presentation passes all local/workflow/staging/delivery/production gates, the
30-day and 90-day windows complete, and an independent audit awards Level 8.
