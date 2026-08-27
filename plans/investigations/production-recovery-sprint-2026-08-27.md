# Production recovery sprint — 2026-08-27

Planning-only sprint. Independently verifies an external review's claims against live code and state,
separates symptoms from root causes from structural weaknesses, and proposes five mechanism-level
decisions (R1-R5). Supersedes nothing; heals `plans/master.md` (Status, Decision Ledger #109-113, Build
Checklist) and `plans/requirements.md`/`catalog.jsonl` in place. No implementation performed here.

## Repository state at investigation start

- Branch `main`, HEAD `6cf92fcb400fe449178307520eb528930189a2d2`, upstream `origin/main`, working
  tree clean. Three unrelated commits landed on `origin/main` from a concurrent session during this
  sprint (`e191d0195`, `670cc1eee`, `f2ae015b5` — RDM-028 risk flag, FACT-018 corroboration, a log
  backfill); re-verified before every edit below that they don't collide with this sprint's changes
  (confirmed: touched `logs/2026-08-27.md`, `logs/README.md`, two `requirements/catalog.jsonl` rows,
  and the graph's `requirement_catalog.sha256` pointer — record count unchanged at 509).
- Reviewed commit `cdb7d0d` is 3 commits behind the HEAD above.
- CI: latest 8/8 runs on `main` are `failure` (`gh run list`). Last success: commit at
  `2026-08-02T11:01:33+05:00`; **694** commits since (`git rev-list --count`), matching the brief's
  "~691."
- Static checks re-run live this sprint: `ruff check .` → all checks passed; `ruff format --check .`
  → 1535 files already formatted; `mypy src` → no issues in 866 files. All three clean, confirming the
  brief.
- Live `supervise --mission-action status` (read-only): `graph_sha256` matches the on-disk Level-8
  graph exactly; `graph_drift: false`; `unresolved_tasks: 49`; `blocked_external_tasks: 1`;
  `portfolio_denominator: 34`; `facts_ready: 23/34`; `candidate_generated: 2/34`;
  `deterministic_validated: 1/34`; `agent_approved: 1/34`; `no_op_proven: 1/34`; `human_accepted: 0/34`;
  `first_failing_boundary: FACTS_READY`; no active/eligible/next task.
- `plans/requirements/catalog.jsonl`: 509 records (IMPLEMENTED 169, PLANNED 123, PARTIAL 104,
  BACKLOG 49, GOVERNANCE 35, DEPRECATED 23, RESEARCH-GATED 6).
  `scripts/governance/validate_plan_structure.py` → "Plan structure clean (141 warning(s))" — matches
  the brief exactly.
- `scripts/governance/validate_compact_authority.py` → **exit 1, 6 pre-existing errors**, unrelated to
  anything in this sprint's scope (requirement-migration-matrix count/ID-set mismatch; semantic-hash
  mismatch on tasks `L8-WAVE1-CANONICAL-SAFETY-SPINE`, `L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME`,
  `L8-WAVE4-PRESENTATION-INTELLIGENCE`, `L8-PF-04-MINIMAL-GRAPH-RUNNER`). **Not wired into CI**
  (`.github/workflows/ci.yml` runs only `run_full_pytest.py` and `validate_plan_structure.py`) — a
  governance validator that already implements exactly the "recorded hash vs. recomputed truth"
  pattern this report recommends generalizing (R1) exists, is currently broken, and nobody is told.
  Logged as a finding, not fixed here (out of scope — a real defect-fix task of its own; see Build
  Checklist).

**Post-edit validator re-check**: `validate_plan_structure.py` (CI-wired) is clean after every edit in
this sprint — 0 errors, 145 warnings (up from 141; the 5 new requirement rows exceed the 1500-char
retrofit-on-touch soft guidance, same as several of the team's own concurrent same-day additions).
`validate_compact_authority.py` (not CI-wired, already broken before this sprint) now reports 9 errors,
up from 6: editing four taskcards' `acceptance_checks` and appending ~90 lines to `plans/master.md`
triggered its per-task semantic-hash pins and a 600-line master.md budget this validator enforces
internally (no matching rule found in `GOVERNANCE.md` itself — specific to this one dormant script).
Not fixed here — regenerating its semantic-hash pins is real implementation work, and the script isn't
part of the enforcement boundary today regardless. Recorded transparently rather than hidden; wiring
and repairing this validator is exactly what the `L8-PF-00` acceptance-check addition above already
calls for.

## Method

Direct read-only commands (git, gh, pytest, mypy/ruff, governance validators, a scratch CAS-classifier
probe against a throwaway local bare remote) plus eight parallel read-only investigation agents across
two passes: state/CAS backends, controller call graphs, README-quality causal chain, governance/graph/
evidence-identity rules, CAS live reproduction, composition-characterization hash-failure root cause,
scope of LLM-judgment caching, and ratchet-state portability. No product/target repository was read
beyond what's already vendored/cloned locally by existing code paths; no paid LLM call was made; no
state was mutated.

## Two problems that look similar but are not the same problem

**Problem 1 — CI redness is a recurring process gap, not a reproducibility defect.** Every currently red
test traced to ground truth is a pinned/recorded content-hash a deliberate, verified code change left
behind without updating, or a fixture predating the code it now fails against — never a behavioral
regression, and never LLM-related.

**Problem 2 — real, structural rerun-inconsistency exists, but it lives in the live portfolio pipeline,
not the CI suite**, and has two distinct mechanical causes plus one amplifier (below).

## Claim verification ledger

Legend: **PROVEN** (direct evidence, reproduced or precisely cited) / **PROVEN-REFINED** (true but the
brief's framing was imprecise) / **DISPROVED** / **CHANGED-SINCE-REVIEWED-COMMIT** / **UNKNOWN**.

### 2.1 CI trustworthiness

| Claim | Status | Evidence |
|---|---|---|
| CI currently failing, ~22-23 tests, same failure shapes | PROVEN | `gh run list` 8/8 failure; latest 3.12 run: 22 failed, 5408 passed, 6 skipped, same test names |
| Last success Aug 2, ~691 commits behind | PROVEN | Exact commit found; 694 commits counted |
| Static checks (Ruff/format/mypy) pass | PROVEN | Re-run live this sprint, all clean |
| Failures span CAS, supervisor loop, external fact-block adapters, characterization hashes, source assurance, check-battery, dependency rendering, cross-platform paths | PROVEN, but root causes are narrower than the category list implies | See CI failure classification table below — every traced instance reduces to one of two mechanisms, not ten independent defect classes |

### CI failure classification (every failing test file traced to a concrete cause)

| Test file | Classification | Root cause |
|---|---|---|
| `test_readme_composition_characterization.py` (3 cases) | STALE_FIXTURE, tracked (VER-013) | Last deliberate hash update `a020a753b` (2026-08-23); 26 shared `readme/*.py` helper files changed since without a re-pin. Exact causal commit not pinned (would require bisecting old revisions, out of scope for a read-only sprint). |
| `test_aspose_org_check_battery_source.py::test_vendored_check_battery_matches_its_content_addressed_manifest` | CONTRACT_DRIFT_UNACKNOWLEDGED, root-caused exactly | Commit `04246331c` (2026-08-26) edited the vendored check file in place for a real false-positive fix, never re-ran the manifest hash. Distinct from the already-known Decision #106 vendored-check-completeness gap. |
| `test_public_candidate_quality_registry.py::test_checks_source_hash_matches_recorded_version` | STALE_FIXTURE, tracked (VER-013) | Long-standing unbumped `PUBLIC_QUALITY_CHECKS_VERSION` pin, predates this session. |
| `test_supervisor_loop.py` (4 cases), `test_external_fact_block_adapters.py`-adjacent fixture failures | TEST_ASSUMPTION_WRONG (fixture contract drift), tracked (VER-012) | Live-reran: failures raise inside **fake/fixture** LLM clients (`GroundedAcceptingRoleReviewClient`), never a real model call. `run_grounded_role()` sends a `context_mode="compact_grounding_retry"` message on retry; the test double predates that shape. |
| `test_evidence_writer.py::test_atomic_write_survives_a_destination_beyond_windows_max_path` | TEST_ASSUMPTION_WRONG | "fixture must exceed MAX_PATH to be meaningful" — a Windows path-length fixture-construction bug, not a product defect. |
| `test_verified_source_assurance.py`, `test_verified_source_opening.py`, `test_verified_template_sections.py`, `test_verified_template_structural_lineage.py`, `test_repository_presentation_template.py`, `test_verified_template_api_descriptions.py` | Independently tracked backlog items (VAL-019 and siblings), pre-existing per their own catalog entries, confirmed unrelated to this sprint's scope by the team's own git-stash isolation method on 2026-08-25 | Not re-investigated in depth this sprint — already diagnosed and logged by the team's own concurrent work; duplicating that effort would not add information. |

**Net finding: zero of the 22 currently-failing tests are LLM-nondeterminism-related, and zero are
newly-discovered regressions.** All are either a pinned-hash/fixture synchronization gap (10 of 22,
Problem 1) or already independently tracked, pre-existing, unrelated backlog items (the remainder).
This sharply narrows what "fix CI" actually requires: no core-invariant is silently broken; the work is
(a) re-pinning known-stale hashes/fixtures, most already logged, and (b) building the enforcement layer
(R1) that stops this from recurring at the pace this project ships.

### 2.2 Durable mission state vs. loaded graph

| Claim | Status | Evidence |
|---|---|---|
| `graph_drift=true`, no active/eligible/next task, 49 unresolved, 1 externally blocked, first failing boundary FACTS_READY | PARTIALLY DISPROVED / CHANGED | Live status: `graph_drift: false` (already healed since the reviewed commit); the graph hash matches the on-disk file exactly. The task-availability symptoms (no active/eligible/next, 49 unresolved, 1 blocked, FACTS_READY boundary) **do** still hold. |
| 0/34 at every lifecycle boundary | DISPROVED | Live: `facts_ready 23/34, candidate_generated 2/34, deterministic_validated 1/34, agent_approved 1/34, no_op_proven 1/34, human_accepted 0/34`. |
| (found independently) `plans/master.md`'s own Status prose is current | DISPROVED | It states "0/31... zero current candidates... no-op proofs" against a 31-denominator; live status shows denominator 34 and `no_op_proven 1/34`. The authoritative plan's own status text had drifted from live truth — fixed in this sprint's edits below. |
| A fresh clone can recover current mission accurately | PARTIALLY DISPROVED, see 2.3/2.6 below | Mission task-graph state is durable and portable (routes to `origin`). Repository-lifecycle/acceptance state and, critically, the ratchet/corroboration state that makes results *reproducible* are not (see Problem 2). |

### 2.3 State authority split

| Claim | Status | Evidence |
|---|---|---|
| Mission state → remote Git, repo lifecycle → local bare Git | PROVEN-REFINED | Real, but **profile-conditional**, not blanket: `commands_supervision.py:1215-1231` routes local-only only under the `local_poc` profile; `commands_lifecycle.py`/`commands_governance.py`/`commands_compatibility.py` always use the remote backend. `mission_command.py:44-53` is the one place it's **unconditionally** local regardless of profile — every `--mission-action` invocation (including `status`) reads/writes repository-lifecycle state from the local bare repo. |
| A second, non-Git local substrate | PROVEN, not in the original brief | Blocked-decision cache and completed-bundle cache are plain JSON files under `runs/`, never CAS-governed at all — a third state class beyond "remote Git" / "local bare Git." |

**State-ownership table** (domain / backend / durability / portability / consumer):

| Domain | Backend | Durable? | Portable to fresh clone? | Read by `status`? |
|---|---|---|---|---|
| Mission task graph/status | `GitStateBackend` → `origin` | Yes | Yes | Yes |
| Repository lifecycle facts (`DomainStateV1`) | Profile-conditional; unconditionally local under `mission_command.py` | Local_poc: no | Local_poc: no | Indirectly |
| README-POC pipeline status/acceptance axes | Same as above | Local_poc: no | Local_poc: no | Yes, via lifecycle scoreboard |
| Global model-route enable/disable | `GitStateBackend` → `origin` (direct, not routed) | Yes | Yes | No |
| Blocked-decision cache | Plain local JSON, `runs/` | No | No | No |
| Completed-bundle reuse cache | Plain local JSON, `runs/` | No | No | No |
| Candidate evidence bundles/manifests | Plain local filesystem, `runs/` | No | No | No |
| **Claim-disposition ratchet (per-repo + portfolio-shared)** | Plain local JSON, `runs/` | **No** | **No** | No |

### 2.4 Multiple effective controllers

All PROVEN, exactly as alleged, with precise citations (unchanged from the first verification pass):

- `portfolio-proof` discards the supervisor's return code: `full_pipeline_modes.py:89` calls
  `supervise_call(namespace)` and never checks it; classification is entirely independent, post-hoc,
  from `stage_classifier.py`.
- `poc` bypasses the mission graph (its own docstring says so) and writes `README.md` unconditionally
  (`commands_poc.py:617`) after the validation/review block, with no gating `return`/`raise`. Review
  exceptions set `review_open=True` (`:579-582`) but that flag is computed *after* the write and never
  feeds back to block it. **This is a direct, provable violation of the repo's own existing Decision
  #100** ("`poc`... cannot independently issue delivery, approval, or transaction-no-op states") — an
  ordinary defect-fix task against a decision that already says what should happen, not a new decision.
- "Replay"/"no-op proof" is weaker than the brief describes: `local_poc_replay_snapshots.py` just
  `shutil.copytree`s the existing bundle — nothing is re-executed at all, not even same-process.
  `sealed_transaction_replay_attestor.py` only diff/hash-compares two already-materialized copies plus
  checks the LLM ledger for zero new calls. No fresh-process re-run exists anywhere in this path.
- Scheduled/production workflow (`readme-agent-production.yml`) defaults to `--execution-profile
  github_observe` (read-only permission classes); the only write/PR-capable profile
  (`github_proposal`) lives in `readme-agent-supervise.yml`, `workflow_dispatch`-only, never scheduled.
  No workflow reaches `github_apply`.
- Repository-level concurrency is fake in `portfolio-proof`: explicit comment at
  `commands_portfolio_proof.py:141-151` says dispatch is serial, `--max-provider-concurrency` accepted
  but unenforced. A real `RepositoryWorkerPool` exists (`repository_worker_scheduler.py`) but is wired
  only into `commands_supervision.py:1122`, a different command.
- `generate`/`run`/`run-registry` are thin, permission-restricted wrappers around the same
  `supervisor.loop.supervise_repo()` — no independent logic.

### 2.5 Acceptance evidence vs. current truth

| Claim | Status | Evidence |
|---|---|---|
| Sealed evidence can contradict current truth | PROVEN, concretely | Committed `L8-PF-03-SEALED-CANDIDATE-NO-OP` evidence bundle (dated 2026-08-24, Aspose.3D-Python, `NO_OP_PROVEN`) sits alongside `plans/master.md`'s own prior Status prose already saying "changed contracts prevent those historical records from satisfying current acceptance" — the plan already *knew* this, but nothing mechanically relabels the sealed bundle, and the Level-8 taskcard `L8-PF-03-SEALED-CANDIDATE-NO-OP` is still `status: TODO` despite it. |
| Evidence/candidate identity binding is undesigned | DISPROVED — it's real, layered, not unified | `contract_freeze.py` (plan/graph identity), `proven_transaction_runner/contracts.py::ProvenTransactionContextV1` (transaction identity, code-content-hash-bound `dependency_hashes`, scoped to what's actually exercised — real precedent for R3 below), and per-repo `manifest.json` (fact/contract hashes, re-verified live at acceptance time by `facts/repository_knowledge_qualification.py`) already do most of what's asked — just undocumented as one model, and not covering every evidence kind (deterministic-validation/review/rubric/replay verdicts aren't re-checked against contract drift the way facts are). |
| Malformed candidates on disk | PROVEN, verbatim, quoted | `plans/investigations/evidence/finalized-repository-readmes-v1/repositories/python/{3d,font,words,slides}/README.md` — "Supports supportsing format.", "To_bytes not implemented for.", raw `:class:` Sphinx markup, 76,093/76,619-byte files, fully-qualified-constructor "Type" cells. |
| Which gates let this through | PROVEN, with an exact timing root cause | The malformed-prose detector that would catch "supportsing" (`public_quality_lint_checks.py`) first appears at commit `8b05b0537` (2026-08-22); the malformed candidates were sealed 2026-08-11/12 — 10 days earlier — and were never re-validated against the newer contract. The oversized-table generator (`verified_template_api_reference.py::api_reference_markdown()`) has no row cap or FQN-simplification, still true today, independent of the timing gap. No Sphinx-markup detector exists anywhere. The 30-point rubric exists but isn't wired into the blocking pipeline (only into a separate portfolio-proof/owner-audit scoring path). |

### 2.6-2.8: see the Root-cause mechanics, Structural weaknesses, and Requirements-scale sections below,
which supersede a first-pass, symptom-level treatment of these with a deeper mechanism-level one.

## Root-cause mechanics for Problem 2 (rerun-inconsistency)

The project already proved **qwen3-next's tool-call arguments are nondeterministic even at temperature
0** (5 identical requests → 5 distinct payloads; Decision #105) and built a "ratchet": persist an
accepted verdict keyed by content hash, replay it instead of re-rolling. **This pattern is correctly
applied in 4 of 6 judgment surfaces:**

| Judgment surface | Ratcheted? | Invalidation granularity |
|---|---|---|
| Claim disposition | Yes | `sha256(claim_text)`; replays only while live re-corroboration against current text still holds (`claim_accountability_llm_disposition.py:188-246`) |
| Bounded independent review (visitor + factual) | Yes | packet+model+schema+sampling+named version-literal constant, bumped deliberately (`bounded_review_repairs.py:181-195`) |
| Section/composition authoring | Yes | packet+prompt+schema+model+sampling+`SECTION_AUTHORING_CONTRACT_VERSION` literal (`section_authoring_cache.py:52-84`) |
| Trusted-readme fidelity review | Yes | `FIDELITY_BATCH_CONTRACT_VERSION` literal (`trusted_fidelity_cache.py:19-61`) |
| 30-point rubric | n/a — deterministic, consumes a pre-built evidence bundle, never calls a model | — |
| **Prose-quality check** (`verify_prose_quality`) | **No — zero caching anywhere in the dispatch path** (`specialists/readme_presentation.py:676-690`) | **None — live model call on every single dispatch regardless of whether this exact text was already scored** |

The ratchet-pattern gap (prose-quality) is narrow and mechanical — one surface never got the cache the
other four already have (**R2**).

**The real structural problem is one layer up**, in what gates whether a repository's whole composed
plan gets reused at all: **`document_template_hash()`** (`readme/document_templates.py:92-130`) — one
SHA-256 digest computed globally over ~50 named files plus 4 broad glob patterns
(`presentation/verified_*.py`, `links/*.py`, `readme/claim_*.py`, `readme/source_claim_*.py`), with
**no per-repository scoping**. Embedded as `template_sha256` in every repo's persisted plan
(`document_plan_finalizer.py:54`), checked verbatim on replay (`document_validation.py:271`). This is
the exact mechanism behind the literal RDM-029 log finding ("cannot be fixed mid-fleet-pass without
invalidating every repository's cached composition plan"): one byte changed anywhere in that
large, actively-edited surface invalidates **all 34 repositories' cached plans simultaneously**,
regardless of whether a given repository's own composition path touched the changed code. Every one of
those 34 then goes back through live, nondeterministic model calls on its next pass. **This is the
dominant mechanical cause of results not holding still between sessions (R3).**

**The amplifier:** the ratchet/blocked-decision state that makes an *accepted* verdict reproduce
deterministically is disposable, local-only, gitignored (`.gitignore:2` = `/runs/`; confirmed via
`git check-ignore -v` and `git ls-files | grep '^runs/'` → 0 hits), and **never restored by CI**
(confirmed: zero `actions/cache` usage in any workflow). Every fresh clone/CI run/new machine starts at
zero accumulated convergence state. Worse, persistence is asymmetric by design — only an *accepted*
verdict is ratcheted; a rejected/uncorroborated one deliberately is not, to allow retry
(`claim_accountability_llm_disposition.py:49-51`). Concretely: two machines racing the identical
first-ever live call for the same claim-content-hash can get two different nondeterministic model
quotes — one corroborates, one doesn't — and the ratchet then **entrenches** whichever answer each
machine happened to get, forever, with no reconciliation channel (**R4**, protected at the frontier by
**R5**).

**A seventh instance found while making this sprint's own graph edits**: the Level-8 graph's own
`requirement_coverage` pointer block (`level8-autonomous-mission-task-graph.yaml:1588-1593`) pins
`record_count: 497` against `plans/investigations/evidence/level8-requirement-taskcard-coverage/
requirement-taskcard-coverage.json` — already stale against the 509-record catalog *before* this
sprint's 5 additions (now 514), via `scripts/governance/build_level8_requirement_taskcard_coverage.py`.
Left un-regenerated deliberately: regenerating it is real implementation/verification work (it
cross-references an `implementation-truth-matrix-2026/matrix.json` and would need the 5 new
requirement IDs properly mapped to owning taskcards first) out of scope for a planning-only sprint —
recorded here as evidence for R1/Decision #109 rather than silently fixed.

## Structural weaknesses (design gaps, not isolated bugs)

1. **No enforcement layer for pinned-content-hash consistency.** Five independent instances
   (`document_template_hash`, the check-battery manifest, `PUBLIC_QUALITY_CHECKS_VERSION`, the
   composition-characterization fixtures, `plans/requirements.md`'s hand-maintained summary counts) —
   plus a **sixth found this sprint**: `validate_compact_authority.py`'s own semantic-hash checks,
   currently red with 6 errors and not wired into CI — each reinvented the same tripwire ad hoc, none
   mechanically enforced. One missing piece of generic infrastructure, not six bugs (**R1**).
2. **Invalidation granularity is bimodal with nothing in between.** Fine, deliberate-bump invalidation
   is proven in 4/6 judgment surfaces; the crudest possible tool (one global glob hash) is used at
   exactly the point that matters most for fleet-wide cost.
3. **No durability tier between "authoritative mission state" and "disposable derived artifact."** The
   ratchet is not derived output; it's the accumulated, validated record of which nondeterministic
   answers the team has already stood behind. Filing it alongside candidate bundles/logs erases the one
   thing whose purpose is preventing repeat nondeterminism exposure.
4. **Accept-only persistence has no reconciliation** — a reasonable per-machine retry policy becomes a
   silent permanent-divergence machine with no shared channel for an accepted verdict to become
   canonical everywhere.
5. **Two different signals — deterministic-invariant breakage (Problem 1) vs. fleet reproducibility
   (Problem 2) — both surface as generic "red,"** pulling attention to hash-chasing instead of the
   structural layer underneath.

## What must be preserved

- The ratchet-and-reuse **pattern** — proven correct in 4/6 surfaces; complete its coverage and give it
  durable storage, don't replace it.
- The CAS structural pre-push staleness check and plain (non-force) push design (`git_backend.py:
  536-581`) — correct as designed.
- Observation-only-by-default workflow posture; append-only Decision Ledger governance; the
  deterministic 30-point rubric consuming a pre-built evidence bundle rather than calling a model;
  never-force-push / never-write-product-repos invariants.
- The overall transaction shape and the layered evidence-identity machinery already built
  (`contract_freeze.py`, `ProvenTransactionContextV1`, per-repo manifests) — R1-R5 operate *inside*
  this shape, at invalidation granularity and durability tiering, not against it.
- The independently-valid, lower-stakes items: the `poc`/`portfolio-proof` defect fixes, the serial
  concurrency gap, and the README-quality causal chain — proceed in parallel, don't gate on R1-R5.

## The redesign (R1-R5) — see `plans/master.md` Decision Ledger #109-113 for the ratified text

Ranked: **R1/R2/R5 small and low-risk (do first). R4 medium (needs load characterization). R3 is the
one flagged for an isolated shadow-mode pilot before any fleet-wide reliance** — the genuine engineering
risk in this plan; see the honest risk statement below.

- **R1 — Generic pinned-content-hash enforcement.** One declarative registry of (label, recompute-fn,
  recorded-value) pairs covering all six known instances; one new fast, independent CI job with a
  "here's the exact command to re-pin this" failure message. Tradeoff: doesn't prevent drift, converts
  silent days-old wrongness into next-commit loud wrongness with a fix command — the realistic ceiling.
- **R2 — Cache `verify_prose_quality`** the same way the other four surfaces already are: keyed on
  `sha256(final_text) + PROSE_QUALITY_CONTRACT_VERSION` (new literal, same precedent as
  `SECTION_AUTHORING_CONTRACT_VERSION`). **Note found this sprint: this is not merely a nice-to-have —
  it's a hidden blocker of `L8-PF-03-SEALED-CANDIDATE-NO-OP`'s own stated acceptance check** ("the
  unchanged rerun performs zero new author/reviewer calls"), which prose-quality's current uncached
  live call violates by construction on every replay.
- **R3 — Scope composition-plan reuse invalidation to actual per-repository dependency**, not one
  global glob. Direction: record, per repository, the actual set of modules exercised while building
  that repository's plan (mirroring `ProvenTransactionContextV1.dependency_hashes`'s precedent — hash
  what's actually exercised, not a static glob); replay hashes only that recorded set. Keep the
  existing global hash as a non-blocking provenance/era label and the trigger for a periodic *full*
  fleet re-validation at declared campaign boundaries — finishing an implementation Decision #90's
  "component deltas rather than global invalidation" language already commits to on paper. Needs a
  shadow period (dual-hash logging for one full portfolio pass) before cutover, because
  under-invalidation (a real dependency silently missed) is worse than over-invalidation.
- **R4 — Promote the ratchet/blocked-decision state to a durable, portfolio-shared tier** via the
  existing `GitStateBackend` mission state already uses, under its own key namespace, so an accepted
  verdict becomes visible to every machine/CI run the first time anyone accepts it. Batches writes per
  repository-pass; a CAS-write failure is non-fatal (log, retry next pass). Needs load characterization
  at full 34-repo scale before rollout.
- **R5 — CAS post-push-failure classification should be structural, not error-text matching**, as
  defense-in-depth. **Revised confidence from the first pass**: a direct probe this sprint (see below)
  found the specific hypothesized failure mode does *not* reproduce against a local bare remote — the
  substring matcher correctly classified a genuine non-fast-forward rejection on a custom
  `refs/readme-agent-state/*` ref 1/1 times, and the existing same-ref concurrency test passed 6/6 local
  runs. The original review's "raw git push rejection" is now better explained by
  `test_state_git_backend_live.py` requiring real GitHub credentials it likely didn't have locally
  (marked `@pytest.mark.live`, needs a specific `x-access-token:$GH_TOKEN` setup this repo's own
  `github-token-recipe` memory already flags as unstable) — an environment/credentials issue, not a
  proven CAS defect. The CI "both saved" anomaly remains **unexplained and unreproduced**; recommend a
  targeted Linux-environment repro before spending implementation effort. R5 is retained as a
  legitimate, low-cost hardening (hardcoded stderr substring matching is inherently git-version/locale
  fragile) but downgraded from "proven root cause" to "prudent defense-in-depth," and made a
  prerequisite for R4 since that redesign adds more traffic through the same code path.

## Validation and regression controls

- **R1**: regression test that intentionally staleness-mismatches one tracked hash, asserts the new
  validator fails with the correct fix-command message; prove it catches the 2 currently-red hash
  instances plus `validate_compact_authority.py`'s 6.
- **R2**: unit test asserting two consecutive calls with identical `final_text` produce exactly one live
  model invocation; a second test proving a bumped contract-version literal forces exactly one fresh
  call.
- **R3**: shadow-mode dual-hash logging for one full portfolio pass before cutover; post-cutover
  regression pair — change a file *not* in a repository's recorded dependency set (assert plan reused),
  change a file that *is* (assert invalidation still fires). Staged as its own isolated pilot.
- **R4**: a fresh-clone reproducibility test that doesn't exist today — seed an accepted ratchet entry
  via the shared CAS backend, wipe `runs/` locally, rerun the identical claim, assert zero new provider
  calls and the identical accept outcome.
- **R5**: extend the local-parallel same-ref race test with a custom-ref rejection whose stderr text is
  deliberately varied (not just the standard local-remote wording confirmed this sprint), asserting
  `"stale"` is still returned; separately, verify (don't assume) whether CI credentials are correctly
  configured for `test_state_git_backend_live.py` before concluding anything about its failure mode.

## Honest risk/uncertainty statement

- **R5's original hypothesis did not survive direct testing this sprint** — reported above as revised,
  not silently dropped. This is exactly the kind of correction the sprint's investigation method is
  supposed to produce; treat it as a demonstration that the other, still-standing findings (R1-R4) were
  independently probed rather than assumed.
- **R3 is the genuine engineering risk in this plan.** The proposed direction (recorded per-operation
  import sets, replacing a static glob) is the most defensible approach the current code supports, but
  is unprototyped, and its correctness under this codebase's actual execution model (sync/async/
  multiprocess worker interaction) is unverified. Staged behind an observational shadow period for
  exactly this reason.
- **R4** changes a hot-path write pattern (local file → networked CAS write); latency/throughput impact
  at full fleet scale is unmeasured, needs a load-characterization step before rollout.
- The CI "both saved" CAS anomaly from the original review remains genuinely unexplained — flagged as
  UNKNOWN, not force-fit into R5's narrative.
- Everything under "what must be preserved" plus the independent quality-track items (API-reference
  curation, Sphinx-markup detection, `poc`/`portfolio-proof` defect fixes) remains valid and can proceed
  in parallel with R1-R5.

## Critical path and parallel lanes

**Critical path**: R1 (independent) → R2 (independent, but unblocks `L8-PF-03`'s own stated acceptance
check) → R5 (hardening, prerequisite for R4's added CAS traffic) → R4 (needs R5 first, needs load
characterization) → R3 (independent of R4, but its shadow-mode pilot benefits from R4's durable ratchet
already being in place so the pilot's own accept/reject decisions are themselves reproducible).

**Safe parallel lanes**: R1 and R2 have no shared files and can run concurrently. The `poc`-write-gating
fix, the `portfolio-proof` return-code fix, and the README-quality items (API-reference curation cap,
Sphinx-markup detector) are all independent of R1-R5 and of each other, and can run in any order/in
parallel — none touch the state or caching layers.

**Stop conditions**: do not cut R3 over from shadow to blocking without at least one full portfolio
pass's dual-hash log reviewed by a human. Do not enable R4 fleet-wide until its load-characterization
pass completes. Do not treat R5 as confirmed-necessary without a matched-environment (Linux CI) repro of
the original "both saved" anomaly.

## Build Checklist additions (wired into `plans/master.md`, not a new top-level list)

Filed under the existing proven-transaction-runner (`DELIVERY-PROVEN-TRANSACTION-RUNNER`) and
portfolio-proof (`DELIVERY-README-PORTFOLIO-PROOF`) catalog items, and reflected as new
`acceptance_checks` lines on Level-8 taskcards `L8-PF-03-SEALED-CANDIDATE-NO-OP`,
`L8-PF-04-MINIMAL-GRAPH-RUNNER`, and `L8-PF-06-REGISTRY-FREEZE-AND-FACT-WARMUP` (see graph diff). Full
~20-field taskcard authoring (per this repo's schema: `allowed_paths`, `forbidden_paths`, `verification`,
`negative_controls`, `rollback_or_recovery`, etc.) is deliberately deferred to execution time, once these
decisions are ratified — this sprint wires them into existing tasks' acceptance criteria rather than
fabricating new standalone taskcards mid-planning-sprint, consistent with Decision #93's compact-
authority cap (10/15 active taskcards currently used).
