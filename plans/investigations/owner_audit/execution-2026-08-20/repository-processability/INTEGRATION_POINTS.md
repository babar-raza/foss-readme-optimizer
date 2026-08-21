# Integration points for the repository-processability gate

Read-only audit output. No tracked file was edited to produce this document. All claims below
are anchored to file paths and line-level behavior read directly from the current tree at
`aa998102191c530af4dca3a6895d62a4027a613e`.

## 1. Earliest production-runtime point

The per-repository production flow is, in order:

```
data/products.json (registry) --entry-->
  registry/intake.py::classify_readonly_intake()      <-- EARLIEST GATE POINT
    (called from supervisor/intake.py::run_readonly_intake_preflight(),
     itself called "before the normal supervisor" per that module's own
     docstring, i.e. before supervisor/loop.py::supervise_repo())
  --INTAKE_READY/BLOCKED_*-->
  supervisor/loop.py::supervise_repo()
    --SNAPSHOTTED--> repository_snapshot.py::capture_repository_snapshot()
    --PROFILED-->    profile/detector.py (ecosystem/package-root detection)
    --FACTS_COLLECTING/FACTS_READY--> facts/provider.py::get_product_facts() (no LLM yet)
    --PLAN_READY-->
    --CANDIDATE_GENERATED--> supervisor/specialist_tier.py::run_specialist_tier()
                              -> specialists/* -> llm/planner_client.py (Qwen calls happen here)
                              -> readme/candidate_pipeline.py (candidate generation)
    --AGENT_REVIEWING/AGENT_APPROVED--> specialists/independent_readme_review.py
                                        (independent review, "scoring")
    --HUMAN_REVIEW_READY / PR_ELIGIBLE / PR_PROOF_COMPLETE--> presentation/publication
```

`registry/intake.py::classify_readonly_intake()` (called via
`supervisor/intake.py::run_readonly_intake_preflight()`) is the **earliest point in the
production runtime** where a repository is inspected at all, and it runs strictly before
every one of: facts collection (`facts/provider.py`), Qwen/specialist-tier calls
(`supervisor/specialist_tier.py` -> `llm/planner_client.py`), candidate generation
(`readme/candidate_pipeline.py`), independent review
(`specialists/independent_readme_review.py`), and any scoring/validation pass. A
processability check placed inside this function (or immediately alongside it, consuming the
same `RepositorySnapshotV1` it already receives) is the earliest hook that prevents all five
downstream costs named in the audit brief.

Today `classify_readonly_intake()` inspects only the README (`snapshot.readme_path`); it does
not walk the full tree. It is already given a `RepositorySnapshotV1` (see below) whose
`snapshot_root` is a real local clone, so a full-tree walk for the processability check can
reuse the exact same traversal machinery `src/readme_agent/inspection/file_inventory.py`
already provides (`scan()`, `find_all_manifest_roots()`, `NOISE_DIRS`, `README_FILENAMES`,
`LICENSE_FILENAMES`) — the generic name/glob rules this audit's classifier deliberately
mirrors (see `_fetch_and_classify.py` in this directory) rather than inventing a second,
independently-drifting definition.

## 2. Existing typed terminal/outcome model to reuse

**Reuse `IntakePreflightOutcomeV1` / `ReadOnlyIntakePreflightV1` / `IntakePreflightBindingV1`
(`src/readme_agent/state/lifecycle_schema.py` + `src/readme_agent/registry/intake.py`). Do not
propose a new controller.**

This is already exactly "the existing typed terminal/outcome model" the audit brief asks for:

- `IntakePreflightOutcomeV1` (`state/lifecycle_schema.py:117-126`) is a closed `Literal` of
  read-only intake outcomes: `READY_FAST_PATH`, `READY_FULL_PIPELINE`, `BLOCKED_EVIDENCE`,
  `BLOCKED_CLASSIFICATION`, `BLOCKED_ACCESS`, `BLOCKED_UNSUPPORTED`, `NOT_APPLICABLE`,
  `SYSTEM_FAILURE`.
- `ReadOnlyIntakePreflightV1` (`registry/intake.py:44-69`) is the "evidence-safe result; a
  fast-path decision never grants approval" record: `org_repo`, `provider_repository_id`,
  `source_revision`, `contract_hash`, `outcome`, `reason`, plus a `canonical_hash()` — i.e. it
  is already a source-bound, hashable, typed skip/proceed receipt.
  `target_remote_effects_allowed`/`target_local_effects_allowed` are hard-pinned `Literal[False]`
  — this model is explicitly incapable of authorizing a write, which matches "read-only audit"
  intent exactly.
- `IntakePreflightBindingV1` (`state/lifecycle_schema.py:323-337`) is described in its own
  docstring as "**Source-bound terminal outcome of one read-only intake inspection**" — the
  literal terminal/outcome model the audit brief is asking for — and is what gets persisted per
  repo (`state/readme_poc_intake.py::complete_readonly_intake_preflight()`).
- The pipeline already refuses to advance past a `BLOCKED_*`/`NOT_APPLICABLE` outcome from this
  stage before `SNAPSHOTTED`/`PROFILED`/`FACTS_COLLECTING` — see the `ReadmePocStatusV2` ordering
  in `state/lifecycle_schema.py:89-114` (`INTAKE_PREFLIGHTING`, `INTAKE_READY` precede
  `SNAPSHOTTED`), and `supervisor/specialist_tier.py:42-57`'s
  `_PRE_CANDIDATE_LIFECYCLE_STATUSES`, which lists every lifecycle stage that must complete
  before `README_PRESENTATION`'s candidate-generation domain is allowed to run.

**What would be new:** one additional `IntakePreflightOutcomeV1` literal value (e.g.
`BLOCKED_NO_SUBSTANTIVE_CONTENT` — naming is a product-owner decision, not this audit's to make)
and one additional branch inside `classify_readonly_intake()` that runs the generic
README/LICENSE/administrative/substantive classification over the full snapshot tree before the
existing README-only checks. No new state slot, no new binding model, no new controller.

Compare-and-reject candidates considered and rejected:

- `ConvergenceOutcome`/`SuperviseStatus` (`supervisor/convergence.py:38-67`) — this is the
  *supervise-loop* level stop-condition classifier (`CONVERGED_*`, `BLOCKED`,
  `PARTIAL_WITH_*`), evaluated only once the loop has already run; too late and too coarse
  (single `BLOCKED` status with a free-text `blocked_reason`, not a typed evidence receipt).
- `BlockedDecisionRecordV1`/`blocked_decision_cache.py` — a *reuse-across-runs* cache for an
  already-classified `BLOCKED` supervisor outcome (skip re-executing a repo that failed
  yesterday for the same reason). Complementary, not a substitute: once
  `classify_readonly_intake()` (or `run_specialist_tier`) records the new
  processability-blocked outcome, this existing mechanism is the natural place a *second* skip
  layer would live if repeated re-derivation ever became expensive — but the intake preflight's
  own `IntakePreflightBindingV1` + dedup-key caching already covers that need at the earliest
  point (see §3), so no second cache is required.

## 3. Skip-receipt fields and cache invalidation (deterministic, already-present mechanism)

`ReadOnlyIntakePreflightV1` + `IntakePreflightBindingV1` already carry every field a
deterministic, cache-invalidating skip receipt needs:

| Field | Source | Role for a processability skip |
|---|---|---|
| `org_repo` | `registry/intake.py:50` | registry identity |
| `provider_repository_id` | `registry/intake.py:51` | stable GitHub node identity, immune to repo renames |
| `source_revision` | `registry/intake.py:52` | the pinned commit SHA the skip decision is bound to |
| `contract_hash` | `intake_contract_hash()` (`registry/intake.py:72-86`) | hash of `active`/`ecosystem`/`platform`/`policy_profile` + `INTAKE_PREFLIGHT_CONTRACT_HASH` (a version constant for the classifier's own rules) |
| `outcome` | `IntakePreflightOutcomeV1` | the new literal value, e.g. `BLOCKED_NO_SUBSTANTIVE_CONTENT` |
| `reason` | free text, `min_length=1` | e.g. `"pinned tree contains only README and/or LICENSE files"` |
| `canonical_hash()` | `registry/intake.py:63-69` | content-addressed hash of the whole receipt |
| `result_hash` (on `IntakePreflightBindingV1`) | `state/lifecycle_schema.py:331` | binds the persisted record to that exact `canonical_hash()` |
| `evidence_refs` | `state/lifecycle_schema.py:333` | pointer(s) to the written receipt file (`_write_intake_evidence()`, `registry/intake.py`-caller `supervisor/intake.py:174-198`, writes `intake/preflight.json` + a per-attempt receipt under the repo's evidence bundle dir, then `refresh_sha256sums()`) |

**Cache invalidation is already correct and requires no new logic**: reuse is gated by
`intake_preflight_dedup_key(org_repo, provider_repository_id, source_revision, contract_hash)`
(`state/readme_poc_intake.py`). The moment upstream content changes, GitHub's default-branch
HEAD moves, `source_revision` changes, the dedup key changes, and
`begin_readonly_intake_preflight()` (`state/readme_poc_intake.py`) forces re-execution — i.e.
the instant "substantive content later appears," the very next intake preflight for that repo
observes the new `source_revision`, re-runs `classify_readonly_intake()` against the new tree,
and produces a fresh outcome. If the classifier's *own rules* change (e.g. a new manifest glob
is registered), `INTAKE_PREFLIGHT_CONTRACT_HASH`/`intake_contract_hash()` changes too, which
also busts the dedup key — so a rule change re-validates every repo, not just ones with new
commits. **A skip is exactly as durable as the pinned commit it is bound to, and never more.**

## 4. Portfolio-wide MIT license policy authority

**Do not treat `license/auditor.py::detect_license()` as the org-wide MIT fact.** That module
(`src/readme_agent/license/auditor.py`) is repository-file/GitHub-API detection evidence
(`LicenseState(detected, source="github_api"|"file_content"|"undetected")`) — it answers "what
does this specific repo's files say," and multiple real registry repos already show it
returning `None`/`undetected` from the GitHub API side even though the repo *is* MIT (see
`REGISTRY_PROCESSABILITY_MATRIX.json`: `cells/cpp`, `cells/java`, `cells/net`, `cells/python`,
`cells/typescript` all show `github_declared_license_spdx: null` despite each having a real
LICENSE file present in-tree).

**The correct existing authority is `config/policies/<policy_profile>.yml`'s
`required_elements.license_mentioned.detected_license`**, consumed at
`src/readme_agent/facts/provider.py:257` into the `declared_license` fact field. This is a
human-confirmed, per-repo config value (see the comment at
`config/policies/aspose-cells-foss.yml:6-9`: *"GitHub's license classifier reports null for
this repo ... but the repo's own README states MIT — use that ground truth, never invent a
license"*), not something re-derived from a live repository scan on every run. A repo whose
license has not yet been confirmed carries an explicit placeholder instead of a guess (see
`config/policies/aspose-psd-foss-net.yml:5-6`:
`detected_license: 'TODO(human): could not verify automatically -- confirm manually before
enabling'`).

**Consequence for the processability classifier**: a repository's LICENSE-file class in the
matrix (§ counts in `REGISTRY_PROCESSABILITY_MATRIX.json`) must stay strictly a file-presence
observation. It must never be written back into, or read as confirmation of, the
`declared_license`/policy-authority fact — those are two different sources of truth for two
different questions (file presence vs. organization-confirmed license text), and the binding
policy text is explicit that "repository-file absence must not be represented as
repository-detected MIT evidence." Concretely: the classifier's LICENSE-variant count/paths are
evidence for *processability* only; `declared_license` continues to come exclusively from
`config/policies/*.yml`, unchanged by this gate.
