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

**3/33 Python repositories `NO_OP_PROVEN` (2026-08-19)** — 3D, barcode, and cells-Python, up from
1/33 at session start, via a chain of four same-day root-cause fixes plus their live verification:

1. **S12** (composition-authority): template-mandated Dependencies content — three H3
   sub-headings plus two fixed, non-fact-derived lead-in sentences the same headings render
   with — was never registered as governed template structure in `readme/composition_lineage.py`,
   hard-failing composition-ledger validation for every candidate with a Dependencies section.
   Live-confirmed fully cleared on cells-python, font-python, barcode-python, page-python (two
   corrective passes; the first fix was real but incomplete, caught by rerunning immediately
   rather than trusting one green test). A companion diagnostics-persistence fix now captures a
   blocked attempt's full composition ledger on disk — what made root-causing this possible.
2. **Disposition-context wiring audit**: clearing S12 surfaced that `build_readme_document_
   candidate()`'s independent-rebuild callers mostly never received the disposition client/
   repository_root/ratchet path gate 1 (`document_planner.py`) already resolves, so an accepted
   `excluded_with_reason` claim could reappear as a fresh block at any later independent-rebuild
   gate. Audited all 5 call sites: gate 1 already correct; gates 2 (`readme_factuality.py`), 3
   (`verification/checks.py`), and `idea_candidate.py` fixed and live-confirmed (barcode/cells both
   cleared through to `NO_OP_PROVEN`); `readme_proposal_bundle.py` left as a precisely-scoped lead
   (harder shape, no direct live failure evidence).
3. **Shared claim-disposition ratchet backfill**: an already-corroborated disposition replayed
   from a repo's own ratchet never propagated to the portfolio-shared store (only a fresh model
   acceptance did) — live-observed via note-python's own accepted verdict for a boilerplate claim
   (content hash `7ff54c1da64deecb`) that page-python's source also carries verbatim. Fixed;
   confirmed working (the shared store now genuinely holds the backfilled entry). It surfaced a
   distinct, deeper, **not-yet-fixed** gap: this exact claim's source-stage and candidate-stage
   records (byte-identical text, same content hash, different `expected_disposition`) are not
   linked by the schema's own `equivalent_candidate_claims`/`equivalence_group_id` fields, so
   resolving the source-stage claim alone doesn't close the candidate-stage one — recorded
   precisely in the failure-signature ledger, not guessed at further.
4. **Live proof**: multiple `--retry-blocked` passes (one transient GitHub clone/rate-limit
   hiccup was hit and ruled out via direct `git ls-remote`, unrelated to any code change) confirm
   the complete chain end to end for three repositories.

Mission status (state_version 10, post-verification): `facts_ready` 12/33, `candidate_generated`
3/33, `deterministic_validated` 3/33, `agent_approved` 3/33, **`no_op_proven` 3/33**
(3D-Python, barcode-python, cells-python), `human_accepted` 0/33 — an exact, clean set with no
partial/stuck-in-between member. First failing boundary `FACTS_READY` reflects repositories not
yet reached by a pass, not a regression. Seven real defects fixed and regression-tested this
session. Remaining open Python blockers, precisely diagnosed: email/pdf/slides (one S1
claim-accountability block each, not yet root-caused to a specific fixable mechanism);
font (two claims needing new extraction/matching logic — a real parameter-name reference and a
real private-submodule reference, neither covered by any existing matcher); note/page (the
equivalence-linkage gap above); html/psd/tex (genuine upstream `infra_external` defects, not
locally fixable).

Durable mission state owns the live task, immediate goal, repository scope,
claim, transition history, and current contract-valid numerator. This document deliberately does
not name a mutable active task. Run mission `status`; run mission `evaluate` before claiming work.
Evaluation reconciles closed repository deliverables against current fact and acceptance hashes,
regresses the earliest stale closeout when no later reconciliation task already owns that
repository, and prevents dependants from advancing on historical closure alone.

Current generated views: `plans/status.md`, `plans/roadmap.md`, and `logs/`. They are derived and
never override the mission graph or durable state.

## Decision Ledger

The complete typed ledger contains 107 stable decisions in
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
- **#91 — Staged platform acceptance.** Facts, presentation, independent review, human acceptance,
  transport qualification, and publication eligibility are separate states. A complete platform
  cohort may enter separately authorized draft-PR operation after every repository in that platform
  is accepted; this does not satisfy full-registry Gate A/B or authorize another platform.
- **#92 — Just-in-time infrastructure.** Infrastructure enters the critical path only when the next
  visible vertical slice exercises or demonstrably needs it.
- **#93 — Compact authority.** Active authority is query-scoped: no more than 15 active tasks, five
  ready tasks, or 25 requirements in one task context. Stable deferred work remains hashed.
- **#94 — Risk-tiered proof.** Focused proof follows each repair; complete suites and canonical
  evidence occur at declared shared/repository/cohort boundaries.
- **#95 — Adaptive parallelism.** Calibration and shared repair are serial. Python may use two and
  later at most three disjoint repository workers after transaction isolation, but no non-Python
  goal or worker is eligible before Python production admission.
- **#96 — Background certification.** The 30/90-day windows are `OBSERVATION_RUNNING`, not blocked
  delivery tasks.
- **#97 — Enforced execution focus.** Every visible-delivery task declares one small immediate goal,
  repository scope, permitted change classes, retry/stall budget, next goal, and visible-output
  boundary. A bounded canary must bind to the current durable claim. Two equivalent failures or
  15 minutes without narrowing mechanically reject another equivalent execution until a recorded
  first-principles replan changes the causal approach.
- **#98 — Python-first production sequence.** A contract defect reopens only presentation-dependent
  stages. Note is the current contract reference; the complete Python cohort, human acceptance,
  transport, and production admission close before any non-Python task becomes eligible.
- **#99 — Working-condition presentation, generate-verify split.** Every admitted repository gets a
  visible candidate or an evidence-backed blocker. A candidate is not delivered or qualified until
  deterministic validation and independent review both accept it. Unsupported public content is
  omitted with explicit accounting plus a per-repo `UPSTREAM-DEFECTS.md` for the product agent.
  At 200-repo scale interpretive prose is LLM-authored and validator-grounded; per-family curated
  modules and hand-written policy product-truth blocks are transitional and must be retired.
  Deterministic forever: extraction, coordinates/URLs, install/build and example proofs, the
  presentation shape contract, and the hide-and-log policy.
- **#100 — One reproducible repository transaction.** `supervise` is the sole acceptance and
  production runtime. `readme-agent poc` is diagnostic unless it routes through that complete
  transaction and cannot independently issue delivery, approval, or transaction-no-op states.
  Same-process recomposition proves only
  `RENDER_REPRODUCIBLE`. `TRANSACTION_NO_OP_PROVEN` requires a fresh-process replay of the complete
  transaction with byte-identical artifacts, no new provider work, and no duplicate lifecycle
  effects. Changed component hashes invalidate only dependent stages.
- **#101 — Working-condition-presentation exceptions.** A human may explicitly accept a specific
  poc-delivered README, per repository, when the strict pipeline cannot currently pass because of
  a genuine upstream defect — recorded in `data/working_condition_exceptions.json` and promoted by
  `scripts/governance/promote_working_condition_exceptions.py` into a tree kept structurally
  separate from the `NO_OP_PROVEN` cohort, always labeled `HUMAN_ACCEPTED_WORKING_CONDITION_
  EXCEPTION`, never counted toward Gate A/B or full-registry closure. A repository whose source
  itself is non-importable or missing does not qualify; its defect goes to
  `report/findings/<family>/<platform>/upstream-issues.md` for the owning product team instead.
- **#102 — Typed external-blocker dispositions satisfy a platform-cohort gate task for
  downstream-sequencing only.** A gate task (e.g. `L8-VPY-03-ALL-PYTHON-VERIFIED-POC`) may close,
  solely to unlock the dependency graph's `CLOSED` check on later tasks, once every repository in
  its scope is `NO_OP_PROVEN` or carries an accepted, human-reviewed typed disposition (a #101
  exception, or a deferred/excluded external-blocker record with owner, evidence, and resume
  predicate). This never reclassifies a typed-disposition repository as `NO_OP_PROVEN` and never
  satisfies Gate A/B or full-registry closure; each independently returns to the strict lane on its
  own resume predicate. Applying this to a specific gate task requires updating that task's own
  `closeout_rules`/`acceptance_checks` text in place so its closure evidence asserts something
  true.
- **#103 — Continuous progress.** No agent idles while a dependency is in flight and safe eligible
  work remains; idling is recorded with its blocker and resume condition only when genuinely none
  does.
- **#104 — Aspose.org corpus parity review.** Every repository's first promoted candidate (and any
  later content change) gets a qualitative comparison against aspose.org's real corpus, logged to
  `candidate-quality-gap-list.md`; systemic gaps become deterministic template/fact/composition
  fixes, never one-off prose edits or silent drops. Diagnostic and improvement-driving, not an
  additional promotion gate — Gate A's own AGENT_APPROVED/NO_OP_PROVEN definition is unchanged.
- **#105 — Dependency-bound blocked decisions; ratcheting acceptances.** A BLOCKED canonical
  outcome persists with the exact dependency fingerprints current at that moment and is not
  re-executed until a bound fingerprint changes (or `--retry-blocked`); a deterministically
  corroborated LLM acceptance persists per claim-content hash and replays through the same
  corroboration — regression only when evidence stops holding, never from a re-rolled model call
  (qwen3-next tool arguments are live-proven nondeterministic at temperature 0).
- **#106 — Native knowledge-application layer.** `facts/aspose_knowledge_claims.py`/
  `aspose_knowledge_selection.py` load, freshness-gate, and bound-select the full imported
  aspose.org claim corpus (all 12 kinds, not only `dependency`) into `ProductFactsV2`; the corpus
  is one checksum-bound unit (`data/imported/knowledge_manifest.json`) feeding a new
  `imported_knowledge` fact-acceptance component; a per-run `knowledge-application.json`
  (`facts/knowledge_application_evidence.py`) records considered/selected/rejected claims. The
  vendored 89-check battery is classified into four buckets
  (`data/aspose_check_classification.json`) and 11 empirically-validated checks are now blocking
  acceptance gates (raised from 10 by the 2026-08-19 post-landing course-correction commits
  `2608f1257`..`cbccb8623`, "Gate R1"–"Gate R6a": wall-clock removal from hashed contracts,
  fail-closed corpus accountability and real per-claim corroboration, genuine multi-signal
  relevance selection, reproducible fixture-backed check classification plus a
  `check_no_excluded_domain_links` root-cause link-hygiene fix, truthful
  considered/selected/influenced/rendered evidence staging, and an attribution-only SEO-keyword
  citation into Key Capabilities lineage — same decision, no separate ledger entry recorded for
  these fixes yet). See `KNOW-001`..`KNOW-013`; `KNOW-007`–`010` remain open (BACKLOG); `KNOW-011`
  remains open but now covers 2 (not 3) unresolved false-positive checks —
  `check_no_excluded_domain_links` was fixed and promoted to blocking by Gate R4; `KNOW-012` is now
  `IMPLEMENTED`, resolved by that same fix; `KNOW-013` (new fact fields need a renderer/composition
  consumer that affects rendered candidate bytes) remains open — Gate R6a gave
  `aspose.relevant_seo_keywords` a narrow, attribution-only evidence-lineage consumer, but no field
  yet shapes rendered wording.
- **#107 — Control-repo auto-push.** This repository's own landed commits are pushed to its own
  `origin` automatically and immediately, with no separate confirmation, mechanically enforced by a
  `post-commit` hook (`scripts/governance/post_commit_push.py`) that never force-pushes. The
  product-repo write path (`open_presentation_pr`, `AUTH-004`, `GOV-018`, decision #69) is entirely
  unchanged — this decision was scoped, on request, to this control repository's own remote only.

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

The transaction above is implemented once and exposed through three control lanes: rapid local
candidate delivery, verified qualification/replay, and governed production supervision. Lanes may
choose scope and stop boundary; they may not duplicate facts, rendering, validation, review, cache,
or lifecycle semantics. Portfolio aggregation is serialized even when isolated repository
transactions later run concurrently.

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
third-party-notices section with normally styled repository-relative link text. All selected Key
Capabilities and every material limitation remain visible. Development and Testing remains visible,
shows representative assets, and ends with a complete-inventory repository link when detail is omitted;
only additional examples and long API inventories may collapse. Every code fence is language-tagged,
language-valid, and normalized without repeated empty-line runs. The Mermaid graph uses one compact
vertical Core column through five capabilities or exactly two balanced, equally spaced vertical columns
above five, renders uniformly wrapped endpoint boxes, and has exactly one product-to-capabilities and one
applicable capabilities-to-outputs relationship; it never fans out one edge per capability. Additional
examples preview their named workflows before the disclosure and never publish internal verification
state or numbered duplicate headings. The deterministic gate renders each non-empty diagram through the
pinned official Mermaid CLI, inspects the resulting SVG geometry for compact landscape shape, adaptive
Core columns, non-overlap, uniform peer endpoint widths, and the required semantic connectors, and caches
only a source-hash-bound passing proof. Source grammar checks alone cannot approve a diagram.
No comments, emoji, process narration, raw export dumps, duplicate sections, repeated workflows, or
dangling fragments are emitted. Aspose.com and Aspose.org links are natural,
contextual, policy-capped, and selected from governed catalogs; `products.*` destinations have
priority. Commercial products are called **Enterprise Edition**.

Template structure and public tone are reusable but prose and facts remain repository-specific.
Validated source information maps exactly once to a canonical candidate section, evidence-backed
correction, or justified omission; source tone and layout are not preservation obligations. Dense
additional examples and reference material may use accessible collapsible sections. Later style
changes create component deltas rather than global invalidation.

### Execution and concurrency

The coordinator owns shared state, plans, integration, commits, and closure. Calibration and shared
repairs are serial. Python is the sole executable platform until its complete dynamic cohort is
independently approved, fresh-transaction-no-op-proven, human-accepted, transport-qualified, and
production-admitted. After transaction/cache/cancellation/aggregation isolation passes, two disjoint
Python repository workers may run; a third is admitted only while speedup is at least 1.5x and
coordination overhead at most 25 percent. No non-Python concurrent goal or worker is eligible before
Python production admission. Independent verification never authors accepted work.

### Small-goal execution and anti-drift

The umbrella mission never directly authorizes implementation. The controller selects one stage,
one task, and one `TaskExecutionFocusV1`. Visible work is admitted only when the repository matches
that focus, the named observer owns an unexpired durable claim, the graph hash is current, and the
approach budget remains open. Nonblocking discoveries become backlog; they cannot enlarge the task.

The stable small-goal catalog is:

1. `DELIVERY-PY-CONTRACT-CURRENT` — correct the global contract and show current Note as the
   independently accepted reference without preserving source tone.
2. `DELIVERY-PY-PDF-CURRENT` — reconcile and show PDF under that exact contract.
3. `DELIVERY-PY-PAGE-CURRENT` — reconcile and show Page under that exact contract.
4. `DELIVERY-PY-3D-CURRENT` — reconcile and show Aspose.3D under that exact contract.
5. `DELIVERY-PY-REMAINING-COHORT` — finalize and expose each remaining Python README individually.
6. `DELIVERY-PY-PLATFORM-ACCEPTANCE` — independently reconstruct and obtain explicit human
   acceptance for the complete current Python denominator.
7. `DELIVERY-PYTHON-PRODUCTION-TRANSPORT` — prove the complete accepted Python platform through
   the canonical workflow, `act`, disposable staging, hosted GitHub App transport, and recovery.
8. `DELIVERY-PYTHON-PRODUCTION-ADMISSION` — admit only the accepted Python cohort to hosted
   operation and separately authorized draft-PR effects.
9. `DELIVERY-DOTNET-LOCAL-NO-OP` — qualify .NET only after Python production admission.
10. `DELIVERY-DOTNET-PRODUCTION-TRANSPORT` — reuse the Python-proven transport for .NET.
11. `DELIVERY-JAVA-FIRST-CURRENT` — prove the first Java repository after .NET admission.

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

The accelerated POC resolves only repository-declared distribution routes. Active registry lookup
is limited to pip/PyPI for declared Python packages, NuGet, Maven, npm, Go modules/proxy, and
Cargo/crates.io. Conan and vcpkg are outside the active POC path: their existing code may remain,
but it is not invoked, extended, or treated as required evidence. C++ uses verified repository
source/CMake acquisition unless a supported declared route exists.

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

- [x] **Post-Claude baseline adoption:** preserve the clean `69b2af21d` candidate/evidence set by
  hash and classify its lifecycle claims without regenerating accepted work.
- [x] **Portfolio candidate visibility:** produce a local reviewable candidate for all 32 active
  entries, including disabled/read-only PSD, without granting product-write authority.
- [ ] **Python shared-cause qualification:** repair source-claim placement, component lineage, and
  recurring presentation-validation families once, then replay only the eight affected Python
  repositories until all 13 are deterministically and independently accepted.
- [ ] **Concurrent .NET local qualification:** after transaction isolation, project existing .NET
  evidence through a disjoint lane and qualify all six repositories through fresh-transaction no-op.
- [ ] **Complete-transaction no-op:** prove fresh-process byte stability, zero new provider work,
  recovery, and non-duplication separately from renderer recomposition.
- [ ] **Canonical-state reconciliation:** make rapid POC and `supervise` consume the shared
  transaction and import checksum-valid accelerated artifacts into durable lifecycle state.
- [ ] **Python production transport:** prove the accepted Python platform through the canonical
  workflow, `act`, disposable staging, hosted App isolation, recovery, and effect reconciliation.
- [ ] **.NET production transport:** reuse the same production system for the accepted .NET cohort.
- [ ] **Remaining-platform qualification:** continue Java, C++, TypeScript, Rust, and Go in priority
  order; preserve every candidate during repair.
- [ ] **Verified Gate A:** reconcile source discovery and qualify every current admitted repository.
- [ ] **Post-.NET Java slice:** prove one current Java vertical slice before Java cohort expansion.
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
- [ ] Candidate visibility, deterministic qualification, independent acceptance, renderer
  reproducibility, and complete-transaction no-op are reported as separate lifecycle facts.
- [ ] A same-process `_compose()` replay can satisfy only `RENDER_REPRODUCIBLE`; fresh-process replay
  of the shared transaction is required for `TRANSACTION_NO_OP_PROVEN`.
- [ ] Acceptance and deployed runs succeed with the Aspose.org checkout unavailable; no sibling
  report, raw knowledge record, skill, script, or cache is a runtime input or factual proof.
- [ ] Mermaid validation proves semantic topology and official-rendered SVG geometry, not syntax alone,
  and independent review rejects a correct-but-unhelpful document.
- [ ] Contract validation rejects collapsed selected capabilities, collapsed material limitations,
  fully collapsed development/testing guidance, untagged or whitespace-corrupt code fences, more
  than two Core columns, unequal endpoint presentation, semantic block/workflow repetition, and any
  merged source unit without one non-empty canonical destination.
- [ ] No non-Python goal is eligible until the complete Python cohort is current, independently
  accepted, fresh-transaction-no-op-proven, human-accepted, transport-qualified, and production-admitted.
- [ ] Every product effect is limited to a complete, independently approved, explicitly human-accepted
  platform cohort under fresh what/why/where authorization; platform publication cannot promote
  another platform or satisfy full-registry Gate A/B.
- [ ] A concurrent repository-local-write lane is admitted only after transaction isolation, under
  disjoint paths, with no shared-state, aggregate, transition, commit, or effect authority.
- [ ] No local/`act` run writes a product remote and no effect writes a default branch.
- [ ] Recovery, deduplication, drift, lost-response, authorization, and corruption controls pass.
- [ ] Full-registry evidence is checksum-complete and independently reproducible.
- [ ] Level 7/8 observations run after deployment without blocking deliverables.

## Changelog

History lives in `logs/`; decisions retain stable IDs in `plans/decisions/catalog.jsonl`.
