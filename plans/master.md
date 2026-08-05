# Master Plan

## Mission

Deliver `verified_repository_presentation` for every dynamically discovered and admitted Aspose
FOSS repository. The system derives repository facts from authoritative evidence, produces
repository-specific professional presentation, validates every material claim and protected region,
obtains independent and staged human acceptance, and performs only separately authorized effects.

Python is the first complete platform, followed by .NET, Java, C++, TypeScript, Rust, and Go.
Level 5 and deployable Level 6 are delivery milestones. Level 7 and Level 8 are background
certifications accumulated after deployment, never prerequisites for visible output.

`delivery_complete` means every executable stage through deployable Level 6 is closed.
`certification_complete` means both post-deployment Level-7 and Level-8 observation/audit tracks
are closed. Full `mission_complete` requires both; delivery completion is never called Level 7,
Level 8, or full umbrella-mission closure.

## Status

The project remains pre-POC: current verified acceptance is `0/31` registry-wide. The agile
authority reset is durably closed with independently accepted evidence at
`plans/investigations/evidence/agile-authority-reset-v1/`. Durable mission state owns live status.
The active task is `L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E`, which finalizes Aspose.3D FOSS for Python
as the first current calibration README before any portfolio fan-out.

Current generated views: `plans/status.md`, `plans/roadmap.md`, and `logs/`. They are derived and
never override the mission graph or durable state.

## Decision Ledger

The complete typed ledger contains 98 stable decisions in
`plans/decisions/catalog.jsonl`. This section is the human-readable current decision index; the
catalog preserves the complete text and hashes of every prior decision.

Binding current decisions:

- **#24/#40 — Registry scope and intent gates.** Every admitted repository is relevant to read-only
  research; write permission remains separately allow-listed and authorized.
- **#26 — Canonical runtime.** `readme-agent supervise` is the only production execution path.
- **#33 — Product effects.** No product-repository write occurs without fresh exact what/why/where
  authorization; default branches are never written directly.
- **#78/#85/#88 — Verified POC.** Trusted execution is historical. Verified Python is first, then
  the dynamic portfolio. Independent approval and no-op proof precede human acceptance.
- **#89 — Dependencies.** Required toolchains are provisioned autonomously in disposable isolated
  environments from pinned, verified inputs.
- **#90 — Agile presentation.** Repository transactions pin component versions; later changes
  invalidate only semantic dependants. Non-critical improvements become `VALID_UPDATE_AVAILABLE`.
- **#91 — Staged acceptance.** Facts, presentation, independent review, human acceptance, and
  publication eligibility are separate states. All admitted repositories require final Gate-B
  human acceptance before any product PR.
- **#92 — Just-in-time infrastructure.** Infrastructure enters the critical path only when the next
  visible vertical slice exercises or demonstrably needs it.
- **#93 — Compact authority.** Active authority is query-scoped: no more than 15 active tasks, five
  ready tasks, or 25 requirements in one task context. Stable deferred work remains hashed.
- **#94 — Risk-tiered proof.** Focused proof follows each repair; complete suites and canonical
  evidence occur at declared shared/repository/cohort boundaries.
- **#95 — Adaptive parallelism.** Calibration and shared repair are serial. Repository workers
  scale from two to at most three only after isolation and measured throughput proof.
- **#96 — Background certification.** The 30/90-day windows are `OBSERVATION_RUNNING`, not blocked
  delivery tasks.
- **#97 — Technical judgment.** Agents classify and challenge tactics. Two equivalent failures or
  15 minutes without narrowing require a different causal boundary or mechanism.
- **#98 — First calibration.** Aspose.3D FOSS for Python is first; Note is second; Page/PDF form the
  representative Python cohort.

## Architecture

```text
authorized discovery -> immutable snapshot -> verified ProductFactsV2
  -> repository assessment -> component-versioned document plan
  -> candidate + native patch -> deterministic validation
  -> independent review/repair -> unchanged no-op proof
  -> staged human acceptance -> separately authorized proposal effect
  -> hosted observation and background maturity certification
```

### Authority and state

- `plans/idea.md`: human product outcome and intent.
- `plans/master.md` plus `plans/decisions/catalog.jsonl`: architecture, decisions, and sequence.
- `plans/requirements.md` plus `plans/requirements/catalog.jsonl`: normative obligations.
- Level-8 graph: sole active task/dependency graph.
- Hashed deferred-task catalog: future task records, never executable until promoted into the graph.
- Git-ref supervisor state: sole live claims, transitions, leases, and runtime status.

### Runtime invariants

- One immutable repository snapshot supplies every stage of a logical run.
- Repository README prose is evidence to verify, never truth by itself.
- Every final material claim maps to accepted facts or an explicit disposition.
- Existing content is protected and changed only through authorized, source-spanned operations.
- Product repositories are not touched during local proof; analysis never receives a write token.
- Draft proposals never merge, mark ready, force-push, or write default branches.
- State uncertainty, fact conflict, authorization failure, or evidence corruption fails closed.
- Identical reruns produce no patch, duplicate effect, or unnecessary model call.

### Presentation contract

All READMEs use a consistent professional header, product-specific title and description, balanced
badges, list-form navigation, verified installation and examples, detailed fact-backed Mermaid
overview, capability/format/platform information, support/community context, MIT-license prose when
applicable, and a separate third-party-notices section. No comments or emoji are emitted. Aspose.com
and Aspose.org links are natural, contextual, policy-capped, and selected from governed catalogs;
`products.*` destinations have priority. Commercial products are called **Enterprise Edition**.

Template structure is reusable but prose and facts remain repository-specific. Dense examples and
reference material may use accessible collapsible sections. Later style changes create component
deltas rather than global invalidation.

### Execution and concurrency

The coordinator owns shared state, plans, integration, commits, and closure. Calibration and shared
repairs are serial. After transaction/cache/cancellation/aggregation isolation passes, two disjoint
repository workers may run; a third is admitted only while speedup is at least 1.5x and coordination
overhead at most 25 percent. Independent verification never authors accepted work.

### Verification tiers

1. Touched static and focused checks during implementation.
2. Impacted integration, safety, recovery, and idempotency proof at coherent slices.
3. Per-repository facts, candidate, diff, deterministic validation, independent review, repair,
   no-op, LLM ledger, and checksum-valid manifest.
4. Complete non-live suite at shared-code, Python-platform, Gate-A, and declared delivery boundaries.
5. One independently reconstructed canonical evidence package per repository and cohort.

## Registry & Policy Config

`data/products.json` is the hard allow-list, not proof of discovery completeness. Organization-wide,
paginated, all-visibility discovery produces a revisioned observation set; exclusions and inaccessible
sources remain visible. New matching repositories enter disabled/read-only preflight. Platform priority
comes from `data/platform_priorities.json`.

Aspose link destinations come only from `data/aspose_com_links.json` and
`plans/aspose_org_links.json`. Configured link slots override automatic size-based allocation.

## Validator Registry

Validators are registered, typed, deterministic where judgment is unnecessary, and bound into the
candidate dependency manifest. They cover factual claims, package coordinates, examples, protected
content, Markdown structure, links, badges, Mermaid facts, license/notices, branding consistency,
promotion balance, ownership, safety, no-op behavior, and evidence integrity.

## LLM Contract

Models organize and write repository-specific prose and independently review quality where rules
cannot express judgment. Deterministic code remains authoritative for facts, permissions, source spans,
component versions, link ceilings, schemas, examples, validation, and effects. Author and reviewer
contexts, prompts, identities, caches, and evidence are separate. Every call records job, route, model,
input/output hashes, latency, retry, and repository without secrets.

## CI & Safety

All Python commands use `.venv`. Official control checks are Ruff, Ruff formatting, mypy, the bounded
complete non-live pytest runner, plan/coverage/authority validation, actionlint, and `git diff --check`.
Push-blocking, the allow-list, evidence redaction, isolated repository execution, short-lived effect
credentials, authorization, and default-branch protection are non-negotiable.

## Reference Data

Repository/package/test evidence outranks README prose. Approved policy owns subjective positioning.
Release data and approved documentation follow. Aspose.org may locate facts or reusable ecosystem
techniques but never substitutes for repository-bound verification.

## Build Checklist

- [ ] **Agile authority reset:** compact catalogs and active graph, reconcile durable state, prove
  lossless stable-ID/dependency/coverage migration, and commit one control-only slice.
- [ ] **First calibration:** finalize Aspose.3D FOSS for Python and show it immediately.
- [ ] **Python representative cohort:** rebuild Note, then Page/PDF, with targeted feedback updates.
- [ ] **Python platform POC:** finalize every dynamically admitted Python repository.
- [ ] **Post-Python slices:** prove one current .NET and one current Java vertical slice.
- [ ] **Discovery and verified Gate A:** reconcile the complete source denominator, then finalize all
  repositories in .NET, Java, C++, TypeScript, Rust, and Go order.
- [ ] **Gate B:** independently approved portfolio package and explicit human acceptance per repository.
- [ ] **Workflow/staging/Gate C:** prove `act`, disposable GitHub staging, and authorized draft proposals.
- [ ] **Hosted system:** GitHub App token isolation, recovery, health, backlog, alerts, and dead-man monitor.
- [ ] **Level 5 and deployable Level 6:** complete presentation surfaces and autonomous portfolio operation.
- [ ] **Background certification:** observe and independently award Level 7 and Level 8 after deployment.

## Verification Checklist

- [ ] Active graph has at most 15 tasks, at most five ready, and no competing controller.
- [ ] Every original requirement, decision, task, dependency, status, and evidence pointer is preserved
  in a typed active or deferred record with verified hashes.
- [ ] Current task loads at most 25 requirements plus always-on invariants.
- [ ] Cosmetic changes do not invalidate facts or unrelated accepted components.
- [ ] Factual/safety/acceptance changes reopen the earliest affected stage.
- [ ] No README proceeds without deterministic and independent acceptance and no-op proof.
- [ ] Every admitted repository is human-accepted before Gate-C product effects.
- [ ] No local/`act` run writes a product remote and no effect writes a default branch.
- [ ] Recovery, deduplication, drift, lost-response, authorization, and corruption controls pass.
- [ ] Full-registry evidence is checksum-complete and independently reproducible.
- [ ] Level 7/8 observations run after deployment without blocking deliverables.

## Changelog

History lives in `logs/`; decisions retain stable IDs in `plans/decisions/catalog.jsonl`.
