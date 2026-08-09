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

The project remains pre-POC until the current dynamic Python denominator is independently approved
and no-op-proven. Durable mission state owns the live task, immediate goal, repository scope,
claim, transition history, and current contract-valid numerator. This document deliberately does
not name a mutable active task. Run mission `status`; run mission `evaluate` before claiming work.
Evaluation reconciles closed repository deliverables against current fact and acceptance hashes,
regresses the earliest stale closeout when no later reconciliation task already owns that
repository, and prevents dependants from advancing on historical closure alone.

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
- **#97 — Enforced execution focus.** Every visible-delivery task declares one small immediate goal,
  repository scope, permitted change classes, retry/stall budget, next goal, and visible-output
  boundary. A bounded canary must bind to the current durable claim. Two equivalent failures or
  15 minutes without narrowing mechanically reject another equivalent execution until a recorded
  first-principles replan changes the causal approach.
- **#98 — Evidence-derived Python sequence.** Preserve completed evidence without manufacturing a
  historical order. The graph stores the stable repository-focus chain; durable evaluation selects
  its earliest dependency-ready or regressed boundary and never takes the current task from prose.
- **#99 — Working-condition presentation, generate-verify split.** Every admitted repository gets a
  delivered README presenting only deterministically verified functionality; unverifiable content
  is hidden with explicit accounting plus a per-repo `UPSTREAM-DEFECTS.md` for the product agent.
  At 200-repo scale interpretive prose is LLM-authored and validator-grounded; per-family curated
  modules and hand-written policy product-truth blocks are transitional and must be retired.
  Deterministic forever: extraction, coordinates/URLs, install/build and example proofs, the
  presentation shape contract, and the hide-and-log policy.
- **#100 — Reproducible idempotent machinery only.** No hand-rolled tasks: every delivery action is
  a committed parameterized entrypoint (`readme-agent poc`), cache-keyed by revision plus
  component/prompt hashes, and idempotent — unchanged inputs re-converge to byte-identical output
  with zero new provider calls; changed components invalidate exactly the affected caches.
  Composition plans should be cached by input hash so identical reruns reuse them.

Aspose.org remains a development-only comparative corpus, never a deployed dependency or factual
authority. Repository order may change only through the durable dependency graph; changing a
preference cannot silently enlarge the current task or invalidate unrelated accepted stages.

## Architecture

```text
authorized discovery -> immutable snapshot -> verified ProductFactsV2
  -> native fact selection + conflict reconciliation
  -> repository assessment -> semantic graph + component-versioned document plan
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

All READMEs use a consistent professional header, product-specific title and opening, one useful
badge row, list-form navigation, verified installation and examples, a detailed fact-backed semantic
Mermaid graph, action-led search-oriented capabilities, curated hub APIs, complete applicable documentation,
user-relevant limitations, maintainer guidance, MIT-license prose when applicable, and a separate
third-party-notices section with normally styled repository-relative link text. The Mermaid graph
uses vertically arranged Core capabilities and exactly one product-to-capabilities and one applicable
capabilities-to-outputs relationship; it never fans out one edge per capability. Additional examples
preview their named workflows before the disclosure and never publish internal verification state or
numbered duplicate headings. No comments, emoji, process narration, raw export dumps, duplicate
sections, or dangling fragments are emitted. Aspose.com and Aspose.org links are natural,
contextual, policy-capped, and selected from governed catalogs; `products.*` destinations have
priority. Commercial products are called **Enterprise Edition**.

Template structure is reusable but prose and facts remain repository-specific. Dense examples and
reference material may use accessible collapsible sections. Later style changes create component
deltas rather than global invalidation.

### Execution and concurrency

The coordinator owns shared state, plans, integration, commits, and closure. Calibration and shared
repairs are serial. After transaction/cache/cancellation/aggregation isolation passes, two disjoint
repository workers may run; a third is admitted only while speedup is at least 1.5x and coordination
overhead at most 25 percent. Independent verification never authors accepted work.

### Small-goal execution and anti-drift

The umbrella mission never directly authorizes implementation. The controller selects one stage,
one task, and one `TaskExecutionFocusV1`. Visible work is admitted only when the repository matches
that focus, the named observer owns an unexpired durable claim, the graph hash is current, and the
approach budget remains open. Nonblocking discoveries become backlog; they cannot enlarge the task.

The stable small-goal catalog is:

1. `DELIVERY-PY-PDF-CURRENT` — show current PDF Python plus independent and no-op proof.
2. `DELIVERY-PY-PAGE-CURRENT` — reconcile and show Page using valid cached receipts.
3. `DELIVERY-PY-NOTE-CURRENT` — reconcile and show Note without sibling runtime dependence.
4. `DELIVERY-PY-3D-CURRENT` — reconcile and show Aspose.3D using valid cached receipts.
5. `DELIVERY-PY-REMAINING-COHORT` — finalize and expose each remaining Python README individually.
6. `DELIVERY-POST-PYTHON-DOTNET-JAVA` — prove .NET first, then Java, after Python closes.

The exact current goal and repository scope are printed only by mission `status`. Mission
`evaluate` first reconciles closed-task freshness; if an accepted repository becomes stale and no
pending repository-specific refresh already owns it, the same closed task becomes `REGRESSED` and
blocks its dependants. A broad suite follows the declared cohort/shared-code boundary; it does not
delay showing an already accepted README.

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
Release data and approved documentation follow. During development, matching Aspose.org knowledge
and reports may expose gaps in Repo Presenter's extraction, selection, composition, graph, and
review behavior. Those lessons must be generalized into this repository's native versioned
contracts. Deployed and acceptance runs never read or depend on the sibling repository, its reports,
skills, scripts, or caches.

## Build Checklist

- [ ] **Agile authority reset:** compact catalogs and active graph, reconcile durable state, prove
  lossless stable-ID/dependency/coverage migration, and commit one control-only slice.
- [ ] **Comparative Note regression:** use the revision-matched Aspose.org report during development
  to expose native contract gaps, then regenerate Note without an Aspose.org runtime dependency and
  pass factual, editorial, semantic-graph, review, repair, promotion, and unchanged no-op proof.
- [ ] **Current PDF deliverable:** finish, independently approve, show, promote, and no-op-prove
  PDF Python before any broad suite or unrelated machinery work.
- [ ] **Reference reconciliation:** reconcile and show Page, Note, and Aspose.3D as three separate
  cached small goals under the same current contract.
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
- [ ] Every active visible-delivery task has one typed execution focus and mission `status` exposes
  its exact immediate outcome and repository scope.
- [ ] A bounded canary fails before repository work when its task, repository, observer, claim,
  graph hash, or approach budget does not match the current execution focus.
- [ ] Two equivalent ineffective attempts or 15 minutes without material narrowing prevent another
  equivalent run until a recorded first-principles replan changes the approach fingerprint.
- [ ] Accepted README output is shown before a deferred broad regression boundary begins.
- [ ] Every original requirement, decision, task, dependency, status, and evidence pointer is preserved
  in a typed active or deferred record with verified hashes.
- [ ] Current task loads at most 25 requirements plus always-on invariants.
- [ ] Cosmetic changes do not invalidate facts or unrelated accepted components.
- [ ] Factual/safety/acceptance changes reopen the earliest affected stage.
- [ ] No README proceeds without deterministic and independent acceptance and no-op proof.
- [ ] Acceptance and deployed runs succeed with the Aspose.org checkout unavailable; no sibling
  report, raw knowledge record, skill, script, or cache is a runtime input or factual proof.
- [ ] Mermaid validation proves semantic topology, not syntax alone, and independent review rejects
  a correct-but-unhelpful document.
- [ ] Every admitted repository is human-accepted before Gate-C product effects.
- [ ] No local/`act` run writes a product remote and no effect writes a default branch.
- [ ] Recovery, deduplication, drift, lost-response, authorization, and corruption controls pass.
- [ ] Full-registry evidence is checksum-complete and independently reproducible.
- [ ] Level 7/8 observations run after deployment without blocking deliverables.

## Changelog

History lives in `logs/`; decisions retain stable IDs in `plans/decisions/catalog.jsonl`.
