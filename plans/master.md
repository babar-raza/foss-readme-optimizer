# Master Plan

## Mission

Deliver `verified_repository_presentation` for every dynamically discovered and admitted Aspose
FOSS repository. The immediate campaign is the safest, repeatable, fastest path to complete README
proof for every processable repository in one frozen registry revision. At the reviewed baseline,
that means 31/31 substantive repositories plus two evidence-bound PSD
`NON_PROCESSABLE_NO_IMPLEMENTATION` dispositions. The denominator remains dynamic across later
registry revisions.

Every processable candidate must reach candidate-bound 30/30 acceptance with zero hard
disqualifiers and immediate complete-transaction no-op, pass the portfolio adversarial audit, remain
source-fresh, and receive a validated proposal payload before becoming `PR_ELIGIBLE`. Human content
review is not required. The campaign stops at effect authorization and produces no product effect.
Level 5 and deployable Level 6 remain later delivery milestones; Level
7 and Level 8 remain post-deployment background certifications.

`delivery_complete` means every executable stage through deployable Level 6 is closed.
`certification_complete` means both post-deployment Level-7 and Level-8 observation/audit tracks
are closed. Full `mission_complete` requires both; delivery completion is never called Level 7,
Level 8, or full umbrella-mission closure.

## Status

**Live mission status (2026-08-27, read-only `supervise --mission-action status`): portfolio
denominator 34; `facts_ready` 23/34, `candidate_generated` 2/34, `deterministic_validated` 1/34,
`agent_approved` 1/34, `no_op_proven` 1/34 (Aspose.3D Python), `human_accepted` 0/34; `graph_drift:
false`; no active/eligible/next task; 49 unresolved tasks; 1 externally blocked task; first failing
boundary `FACTS_READY`.** This paragraph replaces the prior 2026-08-24 snapshot below it (0/31, 33
denominator), which had drifted from live truth by the time it was next read — a concrete instance of
the pinned-summary-drift pattern the 2026-08-27 production recovery sprint's Decision #109 now exists
to catch mechanically. See `plans/investigations/production-recovery-sprint-2026-08-27.md` for the full
independently-verified claim ledger, root-cause hierarchy, and Decisions #109-113. The sealed
`L8-PF-03-SEALED-CANDIDATE-NO-OP` evidence bundle (2026-08-24, Aspose.3D-Python, `NO_OP_PROVEN`) remains
the one current no-op proof; changed contracts since have not yet been checked against it component-by-
component (Decision #111's per-repository dependency scoping, once implemented, is what makes that
check cheap enough to run routinely instead of only at full-fleet boundaries). The Level-8 taskcard
`L8-PF-03-SEALED-CANDIDATE-NO-OP` itself remains committed `status: TODO`; per this repo's own
authority model, durable state and sealed evidence — not the graph file's committed status field — are
what is live-authoritative here, but the discrepancy is worth closing explicitly rather than leaving
implicit.

The following retains the prior 2026-08-24 snapshot's own denominator (33) and count basis exactly as
originally written, for its historical narrative value; do not read its raw numbers as current.

The following is a **historical 2026-08-19 snapshot**, retained for traceability and not current
closure evidence: **3/33 Python repositories were then reported `NO_OP_PROVEN`** — 3D, barcode,
and cells-Python, up from
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

The complete typed ledger contains 113 stable decisions in
`plans/decisions/catalog.jsonl`. This section is the human-readable current decision index; the
catalog preserves the complete text and hashes of every prior decision.

Binding current decisions:

- **#24/#40 — Registry scope and intent gates.** Every admitted repository is relevant to read-only
  research; write permission remains separately allow-listed and authorized.
- **#26 — Canonical runtime.** `readme-agent supervise` is the only production execution path.
- **#33 — Product effects.** No product-repository write occurs without fresh exact what/why/where
  authorization; default branches are never written directly.
- **#78/#85/#88/#108 — Verified portfolio POC.** Trusted execution is historical. The immediate
  campaign seals one complete weak-input candidate, automates only that proven transaction, qualifies
  seven ecosystem canaries, and then completes every processable repository. Independent 30/30
  approval and immediate complete-transaction no-op precede autonomous publication-readiness
  reconciliation.
- **#89 — Dependencies.** Required toolchains are provisioned autonomously in disposable isolated
  environments from pinned, verified inputs.
- **#90 — Agile presentation.** Repository transactions pin component versions; later changes
  invalidate only semantic dependants. Non-critical improvements become `VALID_UPDATE_AVAILABLE`.
- **#91 — Staged autonomous acceptance.** Facts, presentation, independent review, no-op, source
  freshness, publication eligibility, effect authorization, and effect execution are separate states.
  Human content review is optional and never gates candidate readiness. A complete portfolio may enter
  separately authorized draft-PR operation only after every processable repository is `PR_ELIGIBLE`;
  readiness never grants effect authority.
- **#92 — Just-in-time infrastructure.** Infrastructure enters the critical path only when the next
  visible vertical slice exercises or demonstrably needs it.
- **#93 — Compact authority.** Active authority is query-scoped: no more than 15 active tasks, five
  ready tasks, or 25 requirements in one task context. Stable deferred work remains hashed.
- **#94 — Risk-tiered proof.** Focused proof follows each repair; complete suites and canonical
  evidence occur at declared shared/repository/cohort boundaries.
- **#95 — Adaptive parallelism.** Calibration, shared repair, aggregation, and transition are serial.
  After one complete repository transaction proves isolation, the coordinator may admit two disjoint
  repository workers and a third only while measured speedup remains at least 1.5x with coordination
  overhead at or below 25 percent. Platform labels never override dependency readiness.
- **#96 — Background certification.** The 30/90-day windows are `OBSERVATION_RUNNING`, not blocked
  delivery tasks.
- **#97 — Enforced execution focus.** Every visible-delivery task declares one small immediate goal,
  repository scope, permitted change classes, retry/stall budget, next goal, and visible-output
  boundary. A bounded canary must bind to the current durable claim. Material progress is only a
  current-hash lifecycle advance, valid finding adjudication, strictly narrower evidenced first
  boundary, proven shared-blocker removal, or accepted/no-op repository; commits, tests, reports,
  provider calls, bundles, evidence references, and elapsed effort do not qualify alone. Every model
  finding is an allegation adjudicated against the exact candidate, accepted facts, deterministic
  contract, and plan before repair. Two equivalent failures or 15 minutes without typed material
  progress reject another equivalent execution until a recorded first-principles replan changes the
  causal approach. One initial transaction, one targeted repair, and one zero-provider replay are
  the normal repository budget.
- **#98 — Candidate-first portfolio sequence.** A contract defect reopens only dependent stages.
  Aspose.3D Python is the first weak-input transaction; one accepted candidate per ecosystem follows
  before processable-portfolio fan-out. Read-only registry/fact warmup may overlap the final canary.
  Production transport remains later than autonomous portfolio readiness and is never a prerequisite
  for local candidates in another ecosystem.
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
- **#104 — Refreshable Aspose.org visitor-quality benchmark.** At campaign freeze, bind the producer
  Git HEAD and dirty-tree fingerprint, then require two identical inventories of the latest complete
  synchronized canonical `repo-presenter-regen-full` generated corpus. Reconcile every candidate,
  disposition, report, receipt, aggregate-audit omission, and current hard-gate result before deriving a
  qualified
  `BenchmarkQualityProfileV1`; a local candidate must meet or exceed every accepted applicable
  information-coverage and visitor-quality dimension as part of its 30-point acceptance. Benchmark
  prose is never copied, benchmark claims are never facts, and a missing/failing sibling result can
  never lower the local bar. Systemic gaps are repaired at extraction, knowledge selection,
  composition, rendering, validation, or review. The snapshot is development-only and deployed
  execution remains sibling-independent. An incomplete or mutating upstream sync remains visible but
  cannot lower acceptance; later semantic improvement becomes `BENCHMARK_REFRESH_AVAILABLE` and is
  adopted only at a declared campaign or cohort boundary.
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
  currently vendored 89-check snapshot is classified into four buckets
  (`data/aspose_check_classification.json`) and 11 empirically-validated checks were promoted to blocking
  acceptance gates (raised from 10 by the 2026-08-19 post-landing course-correction commits
  `2608f1257`..`cbccb8623`, "Gate R1"–"Gate R6a": wall-clock removal from hashed contracts,
  fail-closed corpus accountability and real per-claim corroboration, genuine multi-signal
  relevance selection, reproducible fixture-backed check classification plus a
  `check_no_excluded_domain_links` root-cause link-hygiene fix, truthful
  considered/selected/influenced/rendered evidence staging, and an attribution-only SEO-keyword
  citation into Key Capabilities lineage — same decision, no separate ledger entry recorded for
  these fixes yet). See `KNOW-001`..`KNOW-014`; `KNOW-007`–`010` remain open (BACKLOG); `KNOW-011`
  remains open but now covers 2 (not 3) unresolved false-positive checks —
  `check_no_excluded_domain_links` was fixed and promoted to blocking by Gate R4; `KNOW-012` is now
  `IMPLEMENTED`, resolved by that same fix; `KNOW-013` (new fact fields need a renderer/composition
  consumer that affects rendered candidate bytes) is now `PARTIAL` — Gate R6a first gave
  `aspose.relevant_seo_keywords` a narrow, attribution-only evidence-lineage consumer (no field
  shaped rendered wording), then the same-day R6a repair replaced it with a real one:
  `seo_capability_title()`'s `seo_keyword` parameter lets a relevance-filtered keyword replace a
  capability row's generic fallback wording when grounded in that row's own capability text,
  never cited as evidence either way. The other five imported-knowledge fact fields remain
  unconsumed.
  Gate R2's "real per-claim corroboration" (above) was corroboration-by-cited-file-existence
  only, not content/polarity-aware: the 2026-08-19 owner audit (`plans/investigations/owner_audit/`)
  confirmed against real source that a claim citing a stub `raise NotImplementedError`
  implementation (3D FBX `FbxExporter.save`, Barcode PDF `PdfRenderer.render`) was still accepted
  as corroborating a positive capability claim, and the field-level `verified_any` aggregate could
  let one verified item promote unverified siblings under one fact ID. `d11ac3800` (K1) replaces
  file-existence corroboration with item-level, polarity-aware content verification
  (`facts/knowledge_evidence_verification.py`: resolves `file`/`source_file` evidence safely
  inside the pinned clone, classifies the cited Python region as a real implementation or a proven
  stub) and removes `verified_any` by splitting a mixed field into a verified-authorizing
  `FactRecordV2` and a separate, non-authorizing `aspose-knowledge-supporting` one. `872abdd04`
  (K2) separates symbol presence from capability authorization for `api.public_surface`:
  `curated_python_api_ast.py::member_is_implemented` marks a proven-stub method (confirmed against
  real 3D `NurbsSurface.to_mesh`); `verified_template_api_members.py`'s renderer no longer emits
  "Supports ..." prose for one; a new deterministic `readme/claim_map_capability_validation.py`
  check rejects capability wording for an unimplemented member regardless of which renderer
  produced it; `aspose_detectors.py::detect_api_public_surface`'s hard `reachable` requirement
  (never a discriminating signal in the real 3D/Note/Barcode bundles) is replaced by corpus
  visibility-vocabulary resolution; and `aspose_knowledge_selection.py`'s blanket api*-kind
  rejection as "covered by the structured API surface" is now conditional on that surface actually
  existing and being non-empty for the family/platform.
  `0eadaa622` (K3) adds the missing final post-render accountability pass: it binds the exact
  candidate hash, joins both operation and verified-template provenance, gives every selected item
  exact output spans or a typed reason, and fails acceptance on provisional, stale, missing, or
  inconsistent accountability. Current portfolio proof must still exercise K1/K3 on one real
  candidate, and `L8-PF-01` must add bounded useful-byte consumers for the five remaining fields
  before that candidate can seal.

  The fresh 2026-08-20 development-oracle recon changes the check-battery premise without changing
  the safety model. Committed Aspose.org revision
  `bf9381af81415843a36a8f50cb6415e01f03ad55` contains 103 `check_*` functions: 97 used by the
  ordinary candidate runner and six auxiliary surgical-scope/upstream-issue checks. Fourteen are
  absent from the 89-function local snapshot. The existing classification and its 11 blocking checks
  therefore describe a qualified historical subset, not current parity or complete acceptance.
  `L8-PF-01` must first content-address the committed upstream blobs, diff knowledge/check/schema/data/
  fixture/skill inputs, port the ten missing candidate checks and necessary typed dependencies, and
  retain the four auxiliary checks for their applicable workflows. It must also compare the upstream
  knowledge-generation mechanism—not only exported knowledge—with this repository's collectors so
  the deployed system owns a complete, independently reproducible generation path.

  Every imported mechanism, check, fact artifact, or pattern receives an explicit
  adopted/adapted/diagnostic/quarantined/not-applicable/deferred disposition and local negative-
  control proof before it can become blocking or factual. Aspose.org itself may contain defects,
  false positives, incomplete assumptions, or workflow-specific policy; newer is not automatically
  better, upstream use is not proof, and dirty sibling working-tree bytes are never imported. A
  module-version/blob-hash currency tripwire detects later drift but cannot silently alter the
  deployed contract. Acceptance remains self-contained and succeeds with the sibling checkout absent.
- **#107 — Control-repo auto-push.** This repository's own landed commits are pushed to its own
  `origin` automatically and immediately, with no separate confirmation, mechanically enforced by a
  `post-commit` hook (`scripts/governance/post_commit_push.py`) that never force-pushes. The
  product-repo write path (`open_presentation_pr`, `AUTH-004`, `GOV-018`, decision #69) is entirely
  unchanged — this decision was scoped, on request, to this control repository's own remote only.
- **#108 — Candidate-first graph-native portfolio proof.** The immediate delivery target is the
  dynamic processable denominator (31/31 at the reviewed registry revision), with typed
  non-processable dispositions outside that numerator. The existing portfolio task remains the
  parent; a bounded child horizon first closes acceptance identity, then one complete sealed 30/30
  candidate and immediate no-op, and only then implements a minimal allow-listed mission runner
  around the proven transaction. Four independently built accelerators enter only at their causal
  boundaries: candidate benchmark acceptance and complete-transaction replay attestation are
  mandatory parts of the first sealed candidate; typed external fact-block resolution is adapted
  before the general runner; and canonical fleet causal reduction is adapted before ecosystem
  fan-out. Standalone branches, tests, reports, or schemas never satisfy their owning task. Each
  module is rebased onto current contracts, its known limitations are repaired, and it is proven on
  current real artifacts without creating another controller, lifecycle, rubric, fact authority,
  or terminal-status path. Canaries, fleet, hosted reconstruction, and adversarial audit are
  promoted just in time. Current `qwen3-next` routing and Aspose.org comparison are versioned
  development inputs, not immutable mission or deployed dependencies. The runner initially
  executes existing handlers only and never authors, commits, pushes, or publishes code/content.
- **#109 — Pinned-content-hash consistency is mechanically enforced, never hand-remembered.** Every
  place this codebase pins a recorded hash/count against recomputed source truth (the composition
  document-template hash, the vendored Aspose.org check-battery manifest, `PUBLIC_QUALITY_CHECKS_
  VERSION`, the composition-characterization test fixtures, `plans/requirements.md`'s own summary
  counts, and `validate_compact_authority.py`'s semantic-hash checks) is registered in one declarative
  checker run as its own fast, independent CI job, separate from the full pytest matrix, that fails
  loudly with the exact command to re-pin. This does not prevent a deliberate contract change from
  needing a human to re-pin it; it converts silent, days-old wrongness into next-commit loud wrongness.
  Proven need: the 2026-08-27 production recovery sprint found six live instances of exactly this drift,
  none a behavioral regression, all traceable to a real code change whose pin was never updated in the
  same commit.
- **#110 — Every LLM-authored judgment surface is ratcheted; none is exempt.** The claim-disposition,
  bounded-review, section-authoring, and trusted-fidelity-review judgment surfaces already persist an
  accepted verdict keyed by content hash plus a deliberately-bumped contract-version literal, so a
  rerun with unchanged inputs reproduces the same verdict instead of re-rolling qwen3-next's proven-
  nondeterministic tool-call arguments (Decision #105). The prose-quality check is the one surviving
  surface with no such cache; it must gain one, keyed identically (content hash plus a new
  `PROSE_QUALITY_CONTRACT_VERSION` literal), before `L8-PF-03-SEALED-CANDIDATE-NO-OP`'s own "unchanged
  rerun performs zero new author/reviewer calls" acceptance check can be true in practice.
- **#111 — Composition-plan reuse invalidation is scoped to actual per-repository dependency, never one
  global content hash.** `document_template_hash()`'s current single glob-wide digest over ~50 files
  plus four broad patterns invalidates every repository's cached plan on any byte changed anywhere in
  that surface, regardless of whether a given repository's own composition depends on the changed path
  — the proven mechanism behind "a fix cannot land mid-fleet-pass without invalidating every cached
  plan." The reuse gate must instead hash the recorded, actually-exercised per-repository dependency set
  (mirroring `ProvenTransactionContextV1.dependency_hashes`'s existing precedent of hashing what is
  actually exercised, not a static glob); the current global hash remains as a non-blocking provenance/
  era label and the trigger for periodic full-fleet re-validation at declared campaign boundaries,
  finishing what Decision #90's "component deltas rather than global invalidation" language already
  commits to. Cutover follows a shadow period — dual-hash logging for at least one full portfolio pass,
  reviewed before the reuse decision itself switches — because under-invalidation is worse than
  over-invalidation.
- **#112 — Convergence-critical ratchet state is durable and portfolio-shared, never disposable
  local-only state.** The claim-disposition ratchet and blocked-decision cache are not derived output;
  they are the accumulated, validated record of which nondeterministic model answers this project has
  already stood behind, and today live only under gitignored `runs/`, restored by nothing (confirmed:
  zero `actions/cache` usage in any workflow). They must route through the same `GitStateBackend` mission
  state already uses, under their own key namespace, batched per repository-pass, with a CAS-write
  failure treated as non-fatal (log, retry next pass) rather than blocking a candidate. This does not by
  itself resolve two machines' literal first concurrent encounter with a brand-new claim (Decision
  #113 protects that frontier); it ensures an accepted verdict becomes visible to every other
  machine/CI run the first time anyone accepts it, instead of only to whichever machine happened to.
  Requires a load-characterization pass at full fleet scale before fleet-wide reliance.
- **#113 — CAS post-push-failure classification is hardened as defense-in-depth, with confidence stated
  honestly.** `_is_non_fast_forward()` classifies a push failure by matching hardcoded stderr
  substrings; on any push failure the backend should instead re-fetch and structurally re-compare
  state_version/SHA before deciding stale vs. hard-error, rather than trusting failure-text matching
  alone — necessary regardless of root cause once Decision #112 adds more traffic through this exact
  path. The CI "both saved" anomaly this decision originally left as an unreproduced, unexplained open
  unknown is now root-caused and fixed (2026-08-29): reproduced reliably (27/30) by matching real CI's
  actual concurrency shape — `pytest -n 4 --dist worksteal` under a 2-vCPU constraint, matching
  GitHub's standard runner, not this project's typically many-core dev machines, which is exactly why
  earlier manual probes and even unconstrained local reruns of the same test could not reproduce it.
  Root cause, confirmed at the git-object level with per-process instrumentation: two racing writers
  computing the *same* target state produce a byte-identical commit (same tree, parent, pinned
  author/committer identity, message, and second-granularity timestamp), and git legitimately treats
  pushing an object that already equals the ref's current value as a no-op ("Everything up-to-date"),
  not a rejection — so both callers observed `outcome="saved"`. `--force-with-lease` does not help; git's
  up-to-date short-circuit fires before any lease/force check runs. Fixed by adding a per-attempt nonce
  to the commit *message* (not the persisted state payload, so no schema change) in `save()` and
  `save_model_route_status()`, the two call sites whose payload can plausibly collide across
  independent writers; `_acquire_lock_generic`'s lock payload already includes a `holder_id` uuid and
  was never exposed to this class. Verified via `--force-with-lease` alone failing to fix a raw git
  reproduction, then the nonce fix reversing 27/30 failures to 0/30 twice under identical conditions.
  The CAS primitive's push-time compare-and-swap itself remains correct as designed for genuinely
  different concurrent writes (confirmed separately by direct raw-git testing) — this was narrower and
  more specific than a general locking-discipline gap.

- **#114 — `POC-FREEZE.md` and both `CLAUDE-CODE-DIRECTIVE*.md` files are retired, not deleted.**
  The freeze was de facto superseded around 2026-08-10, when `runs/share/poc/POST-CLAUDE-HANDOFF.md`
  recorded the explicit decision to converge the accelerated `poc` runner's output onto the canonical,
  mission-graph-governed `supervise` pipeline — the exact machinery the freeze told agents to bypass
  and never edit. Every session since has correctly operated on the canonical path, not the frozen one,
  but the freeze file itself was never marked retired, which let a concurrent agent read it literally
  and bypass the mission graph again on 2026-08-28, reintroducing a known pinned-hash-drift defect
  class (see the `GOV-033`/`GOV-034` entries this same day). All three files now carry an explicit
  RETIRED banner pointing here and are kept as forensic/reusable-input evidence per GOVERNANCE.md rule
  9, not deleted — their historical record of what was tried and why remains genuinely useful.

Aspose.org remains an independently qualified, development-only comparative corpus, never a
presumed-perfect specification, deployed dependency, or factual authority. Repository order may
change only through the durable dependency graph; changing a
preference cannot silently enlarge the current task or invalidate unrelated accepted stages.

## Architecture

```text
authorized discovery -> RegistryRevisionV1 -> immutable snapshot -> processability
  -> verified ProductFactsV2
  -> native fact selection + conflict reconciliation
  -> repository assessment -> semantic graph + component-versioned document plan
  -> candidate + native patch -> deterministic validation
  -> 30-point criterion evidence + independent factual/visitor review
  -> immediate complete-transaction no-op -> portfolio adversarial audit
  -> read-only freshness reconciliation -> PR_ELIGIBLE proposal payload
  -> separately authorized proposal effect
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
repairs are serial. After the first complete 30/30 candidate, no-op, recovery, cache, and aggregation
transaction passes, two disjoint repository workers may run; a third is admitted only while speedup
is at least 1.5x and coordination overhead at most 25 percent. Canaries follow configured platform
priority when otherwise ready, but the transaction may qualify any dependency-ready ecosystem before
production transport. Independent verification never authors accepted work.

### Small-goal execution and anti-drift

The umbrella mission never directly authorizes implementation. The controller selects one stage,
one task, and one `TaskExecutionFocusV1`. Visible work is admitted only when the repository matches
that focus, the named observer owns an unexpired durable claim, the graph hash is current, and the
approach budget remains open. Nonblocking discoveries become backlog; they cannot enlarge the task.
Model findings remain allegations until exact evidence adjudicates them; documentation, evidence promotion,
commit, and push occur once per closed causal repair cluster rather than per phrase-level correction. Parallel
repository workers remain disabled whenever the multi-process same-ref CAS proof is unstable in clean CI,
even if a single local rerun passes.

The current bounded small-goal catalog is:

1. `DELIVERY-PORTFOLIO-AUTHORITY` — reconcile the 31-processable/two-disposition campaign identity.
2. `DELIVERY-KNOWLEDGE-TO-BYTES` — finish the five imported-knowledge consumers and acceptance identity.
3. `DELIVERY-FIRST-COMPLETE-CANDIDATE` — produce one complete current Aspose.3D Python candidate.
4. `DELIVERY-FIRST-SEALED-NO-OP` — independently seal it at 30/30 and prove immediate no-op.
5. `DELIVERY-PROVEN-TRANSACTION-RUNNER` — automate only that accepted transaction.
6. `DELIVERY-SEVEN-ECOSYSTEM-CANARIES` — qualify one complete candidate per supported ecosystem.
7. `DELIVERY-REGISTRY-FACT-WARMUP` — overlap the final canary with source-complete discovery and
   current-contract fact preparation.
8. `DELIVERY-README-PORTFOLIO-PROOF` — reach 31/31 accepted and no-op-proven candidates and pass one
   independently reconstructed portfolio adversarial audit.
9. `DELIVERY-PORTFOLIO-PUBLICATION-READY` — refetch sources, rebuild only drifted repositories, derive
   `PR_ELIGIBLE`, and prepare exact proposal/rollback/authorization payloads with zero product effects.

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
4. Complete non-live suite at shared-contract, first sealed transaction, ecosystem-canary freeze,
   portfolio freeze, and declared later delivery boundaries.
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
contracts. Every refresh is bound to committed upstream blobs and independently reconciled against
repository truth, the presentation contract, local fixtures, negative controls, and independent
review. This includes comparing the upstream mechanism that generates product knowledge with this
repository's native collectors, not merely copying its final reports. Upstream defects are adapted,
quarantined, or rejected rather than inherited. Deployed and acceptance runs never read or depend on
the sibling repository, its reports, skills, scripts, or caches.

## Build Checklist

- [ ] **Pinned-content-hash enforcement (Decision #109):** one declarative registry of recorded-hash
  vs. recomputed-truth checks (document-template hash, check-battery manifest, checks-source-hash,
  composition-characterization fixtures, `plans/requirements.md` summary counts,
  `validate_compact_authority.py`'s semantic-hash checks) run as its own fast, independent CI job with
  a fix-command failure message. Wire `validate_compact_authority.py` into CI once its 6 current
  pre-existing errors (unrelated to this sprint) are resolved; it is not currently invoked by
  `.github/workflows/ci.yml`.
- [ ] **Campaign authority:** freeze the current RegistryRevision, 31-processable/two-disposition
  partition, 30-point rubric, check-registry hash, graph queue, and no-effect boundary.
- [ ] **Qualified development-oracle refresh:** bind committed Aspose.org source blobs; diff the
    knowledge-generation mechanism, knowledge artifacts, checks, runner inputs, schemas, data, fixtures,
    and skill rules; bind producer HEAD/dirty fingerprint and obtain a twice-stable snapshot of the
    latest complete synchronized canonical visitor-quality corpus; reconcile its denominator and fresh
    aggregate audit; derive a
    qualified benchmark profile; import only necessary behavior after independent qualification;
    regenerate the classification; and prove the local result with the sibling checkout absent.
- [ ] **Knowledge-to-bytes:** prove current-source polarity, final post-render accountability, and
  bounded useful-byte consumers for feature, format, install, limitation, and troubleshooting claims.
- [ ] **First complete candidate:** generate Aspose.3D Python through the canonical supervisor with
  complete source, fact, knowledge, claim, component, review, and patch lineage.
- [ ] **First sealed transaction:** independently accept the exact candidate at 30/30 with zero hard
  disqualifiers, integrate and real-candidate-calibrate the qualified benchmark comparator, and prove
  an independently attested immediate fresh-process zero-provider no-op from separate first/replay
  bundle roots. Lifecycle reopening preserves dependency-valid review-packet caches. Requires the
  prose-quality judgment surface to be ratcheted like every other one (Decision #110) and CAS
  post-push-failure classification hardened (Decision #113) before a zero-provider-call rerun claim is
  trustworthy in practice.
- [ ] **External fact-block resolver:** adapt the qualified standalone decision seam to real truth-salvage,
  acquisition, and local-verification diagnostics through its smallest safe public seam; bind current
  evidence/dependency fingerprints; and prove all applicable classes plus the five current receipts before
  the general runner. Defer unrelated refactoring unless focused safety or correctness proof shows the seam
  cannot be integrated safely.
- [ ] **Minimal graph runner:** automate only the proven transaction through typed allow-listed actions,
  durable checkpoints, recovery, and effect-null safety. The claim-disposition ratchet and
  blocked-decision cache route through the shared durable state backend under their own key namespace
  (Decision #112) rather than machine-local `runs/`, batched per repository-pass with non-fatal
  CAS-write failure, after a load-characterization pass at full fleet scale.
- [ ] **Fleet causal reducer:** adapt the qualified standalone reducer to canonical first-boundary receipts,
  harden opaque-data guards through tiers four to six, and prove complete deterministic cluster accounting
  plus shared-once/failed-only repair scheduling before ecosystem fan-out.
- [ ] **Seven ecosystem canaries:** qualify and no-op-prove one current processable representative per
  Python, .NET, Java, C++, TypeScript, Rust, and Go.
- [ ] **Registry and fact warmup:** reconcile authenticated all-visibility discovery, freeze the current
  RegistryRevision, and prepare current-contract facts without advancing candidate states.
- [ ] **Portfolio proof:** execute failed-only repair and reach 31/31 processable accepted/no-op bundles,
  retain two typed PSD dispositions, pass adversarial audit, and independently reconstruct one portfolio
  acceptance package. Composition-plan reuse gates on a per-repository recorded dependency-set hash, not
  one global glob digest (Decision #111), landed only after a one-full-pass shadow period comparing both
  hashes; the global hash remains as a non-blocking provenance label and full-fleet-revalidation trigger
  at declared campaign boundaries.
- [ ] **Autonomous publication readiness:** refetch every target read-only, heal source/registry drift,
  derive `PR_ELIGIBLE` for every processable repository, and validate the complete proposal/rollback/
  authorization package without a product effect.
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
- [ ] Only a current-hash lifecycle advance, valid finding adjudication, strictly narrower evidenced first
  boundary, proven shared-blocker removal, or accepted/no-op repository qualifies as material progress;
  activity artifacts cannot reset the budget.
- [ ] Every model finding is adjudicated against its exact candidate span, facts, deterministic contract,
  and document plan before repair; unsupported findings change no candidate bytes and have an offline
  regression.
- [ ] The current FP03 finding ledger preserves the supported limitations grouping repair, rejects the
  unsupported additional-examples raw-list allegation, and admits no additional repair without exact evidence.
- [ ] Narrative documentation, evidence promotion, commit, and push occur once per closed causal repair
  cluster rather than once per reviewer phrase or micro-fix.
- [ ] Parallel repository lanes remain disabled until clean-Linux multi-process CAS and a bounded two-worker
  proof each produce exactly one saved writer and one stale writer with no lost update.
- [ ] The portfolio registry contract uses canonical JSON identity so CRLF and LF checkouts load the same
  frozen graph, while CI fetches the history required by compact-authority verification.
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
- [ ] Candidate benchmark acceptance is bound to current candidate/profile/review/predecessor hashes,
  contributes evidence to the existing 30 criteria, and fails closed on an applicable unsupported
  dimension; it does not create an alternate score or factual authority.
- [ ] Complete-transaction replay compares separately materialized immutable bundle roots, proves certain
  zero-provider accounting, and never deletes or recomputes a validated review-packet cache whose complete
  dependency key is unchanged.
- [ ] External fact-block resolution consumes real pipeline diagnostics and fingerprints, never fabricates
  facts, omits only nonessential unsupported claims, and records exact external owner/resume predicates.
- [ ] Fleet causal reduction consumes canonical first-boundary receipts, accounts for every failed repository,
  rejects opaque bulk clusters at tiers four through six, and cannot transition lifecycle or terminal state.
- [ ] Acceptance and deployed runs succeed with the Aspose.org checkout unavailable; no sibling
  report, raw knowledge record, skill, script, or cache is a runtime input or factual proof.
- [ ] After the bounded local retry/replan budget is exhausted, development may consult the current
  Aspose.org README-refresh skill, associated scripts, knowledge producer, and matching generated
  candidate; every adopted lesson is independently qualified and ported locally before use.
- [ ] The Aspose.org import manifest binds committed upstream commit/blob hashes and accounts for all
  discovered knowledge generators, artifacts, and checks; every imported behavior has an explicit
  local disposition, applicable hard gates pass negative controls without unresolved false positives,
  evaluator errors fail closed, and a newer upstream snapshot never silently changes acceptance.
- [ ] Mermaid validation proves semantic topology and official-rendered SVG geometry, not syntax alone,
  and independent review rejects a correct-but-unhelpful document.
- [ ] Contract validation rejects collapsed selected capabilities, collapsed material limitations,
  fully collapsed development/testing guidance, untagged or whitespace-corrupt code fences, more
  than two Core columns, unequal endpoint presentation, semantic block/workflow repetition, and any
  merged source unit without one non-empty canonical destination.
- [ ] No general runner precedes one complete 30/30 candidate and immediate complete-transaction no-op;
  no fleet fan-out precedes one accepted current candidate per supported ecosystem.
- [ ] Every product effect is limited to a complete, independently approved, no-op-proven, source-fresh,
  `PR_ELIGIBLE` portfolio under fresh exact authorization; readiness cannot itself execute an effect.
- [ ] A concurrent repository-local-write lane is admitted only after transaction isolation, under
  disjoint paths, with no shared-state, aggregate, transition, commit, or effect authority.
- [ ] No local/`act` run writes a product remote and no effect writes a default branch.
- [ ] Recovery, deduplication, drift, lost-response, authorization, and corruption controls pass.
- [ ] Full-registry evidence is checksum-complete and independently reproducible.
- [ ] Level 7/8 observations run after deployment without blocking deliverables.

## Changelog

History lives in `logs/`; decisions retain stable IDs in `plans/decisions/catalog.jsonl`.
