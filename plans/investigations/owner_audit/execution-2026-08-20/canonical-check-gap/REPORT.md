# OPT-CANONICAL-103-CHECK-GAP -- canonical Aspose.org check module vs. optimizer bridge

Audit date: 2026-08-20
Optimizer pin (expected and confirmed): `aa998102191c530af4dca3a6895d62a4027a613e` (`git rev-parse HEAD`, clean working tree)
Read-only. Same VS Code workspace, no worktree/clone/branch. No tracked file edited, nothing committed, no
Qwen, no Docker, no full suite. Time-boxed to 45 minutes.

## 0. What "canonical" means in this pass, and its one real limitation

The canonical Aspose.org check module referenced by this ticket is not committed to this git repository as
source text. It exists only as prior owner-audit evidence:

- `plans/investigations/owner_audit/acceptance_runner/SOURCE_INVENTORY.json` records an operator upload
  `readme-refresh-complete-bundle-20260819-174412.zip` (sha256
  `2d8eb6ae810d920b98136f3fa587b46d36b2e0c6b5250df109fa98c73e470465`) whose
  `files/scripts/pipeline/commands/foss/readme_refresh_checks.py` has sha256
  `5d6da30c104957f65030ce09656bea866c513df6516da48c21235c71d74214aa`.
- `plans/investigations/owner_audit/acceptance_runner/REPRODUCTION.md` records the exact reproduction command
  (`rg '^def check_' ... | wc -l`) and its result: **103** top-level `check_*` functions, against the
  optimizer's then-current vendored file (**89** functions, at optimizer pin `d71f38b6`).
- `plans/investigations/owner_audit/defect_gate_map/DEFECT_GATE_MATRIX.json`, defect
  `D12-MISSING-14-OF-CANONICAL-103-CHECKS`, records the exact 14 missing names by AST `comm -23` diff.

This audit could not re-fetch or re-count that upload (read-only, no network access performed, and the zip
is not in this repository). What it *could* and did verify independently: the optimizer side of that
comparison is **unchanged**. `git diff --stat d71f38b6a050b5282f0ada314f9ee4de35950426 aa998102191c530af4dca3a6895d62a4027a613e -- src/readme_agent/vendored_asposeorg/scripts/pipeline/commands/foss/readme_refresh_checks.py`
is empty (byte-identical file), and a fresh AST parse at HEAD independently re-derives exactly 89 top-level
`check_*` functions, matching the prior audit's count exactly. **The 103/89/14 figures are therefore still
current and applicable to this exact pin**, but the 103-count and the 14 missing names remain second-hand
evidence carried forward from the prior audit, not independently re-derived from canonical source text in
this pass. See `CHECK_103_MATRIX.json.canonical_source_provenance` for the full chain and
`INGEST_MANIFEST.json` for every source read.

## 1. Headline numbers

| Metric | Value |
|---|---|
| Canonical top-level `check_*` functions (from evidence) | **103** |
| Optimizer-vendored `check_*` functions (AST-confirmed at `aa9981021`) | **89** |
| Missing (canonical minus vendored) | **14** |
| Vendored checks currently classified `blocking: true` | **11** |
| Vendored checks classified `applicable_after_adaptation` (hard or heuristic, not yet blocking) | 61 |
| Vendored checks classified `diagnostic_heuristic` (reviewer-visible only, never blocking) | 17 |
| Hard-gate, `applicable_after_adaptation` checks that **never run** today (no producer wired at all) | 32 |

Full per-check detail (all 103) is in `CHECK_103_MATRIX.json`. This report gives the narrative; the JSON
files are the source of truth for individual checks.

## 2. Enumeration method (requirements 1-4)

- Canonical names: taken verbatim from `DEFECT_GATE_MATRIX.json`'s D12 evidence string (14 names) union the
  89 vendored names below (89 + 14 = 103, matching the independently reproduced counts on both sides).
- Vendored names: `python -c "... load_check_registry() ..."` against
  `src/readme_agent/validation/aspose_checks/__init__.py` -- this repo's own production registry loader,
  not a hand re-parse, so severity/scope/section/parameters below are ground truth as the running code sees
  them, not re-inferred.
- Missing set: the 14 names above, cross-checked as disjoint from the vendored 89 (`set(registry) &
  set(MISSING_14) == set()`), confirmed programmatically while building `CHECK_103_MATRIX.json`.

## 3. Every canonical check, five-bucket disposition (requirement 5)

`CHECK_103_MATRIX.json` gives, per canonical name: `hard_advisory_status` (mechanically derived from the
vendored function's own docstring for the 89; `unknown_not_vendored` for the 14), `currently_classified_status`
(from `data/aspose_check_classification.json`), `blocking`, a **runnable/skipped/errored/absent** disposition
(`dominant_input_gap_type` plus `candidate_acceptance_effect`), `required_inputs` (exact parameter tuple from
the live registry), `current_input_producer_by_param`, and `smallest_adaptation`-equivalent reasoning baked
into `candidate_acceptance_effect` and (for the 14) `MISSING_CHECK_ADAPTATION_PLAN.json`.

Disposition summary across the 89 vendored checks, by input-gap type:

| Dominant input gap | Count | Meaning |
|---|---:|---|
| `always_available` | (readme_text/markdown_text only) | Runs on every candidate; no producer gap |
| `conditional_fact_dependent` | archetype/install_info/license_file/enterprise_link/dependency_snapshot | Runs only when the matching `aspose.*` fact survived selection |
| `conditional_fact_dependent_family_platform` | family/platform/own_family | Runs only when *any* `aspose.*` fact with `source.location` starting `data/imported:` survived selection -- see check_banner_present below |
| `not_applicable_by_design_diff_pair` | old/new readme/markdown text | Deliberately never supplied -- see §5 |
| `missing_producer` | everything else (dispositions, content_units, structural_units, code_units, badges, clone_cache_root, reference_index/class_names/dir, exclusions, detected_artifacts, diagram geometry inputs, canonical_casing, upstream_issues_text, allowed_headings, known_family_display_names, homepage, package_registry, docs_texts, corroboration) | No code path supplies this value at all today |

(Exact per-check membership is in `CHECK_103_MATRIX.json`; counts are visible by filtering
`dominant_input_gap_type`.)

## 4. Applicable hard checks that can currently skip or error without blocking (requirement 6)

Full detail in `HARD_CHECK_INPUT_MATRIX.json`. Two distinct, real gaps exist, not one:

**A. The 11 classified-blocking checks can still fail to actually block.** Ten of them
(`check_api_reference_detail_collapsed`, `check_dependency_native_system_scope_limitations_placement`,
`check_enterprise_edition_naming`, `check_examples_table_collapsed`, `check_no_duplicate_badges_in_candidate`,
`check_no_excluded_domain_links`, `check_no_implementation_bridge_disclosure`,
`check_project_structure_canonical_tree_format`, `check_section_intro_no_meta_narration`,
`check_unqualified_dependency_claims`) require only `readme_text`/`markdown_text`, which are always supplied,
so they have **no skip risk**. But if any of them **errors** (raises, or returns a shape the bridge can't
interpret), `AsposeCheckResultV1.findings` never sees it -- zero critical findings are produced, so
`aspose_checks.valid` stays `True`. This is caught (fails closed) **only** in
`local_poc_acceptance_binding.py::validate_acceptance_artifact_chain` (commit `907ac0847`, 2026-08-20,
error-only). It is **not** caught in `document_validation.py::validate_readme_document_candidate` -- the
broader gate reached from `commands_poc.py`, `presentation/document_planner.py`,
`specialists/readme_factuality.py`, `verification/checks.py`, and `verification/readme_proposal_bundle.py`.
An error in any of these 10 during a run through those five call sites still fails open.

**B. `check_banner_present` (requirement 7) is the one blocking check with a real skip pathway, and it is
wide open.** Its own docstring: "Hard gate (2026-08-09, MT026). Every candidate README must carry the real,
live per-product banner asset ... confirmed live for all 30 current products before this rule was written."
Its parameters are `(readme_text, family, platform)`. `family`/`platform` are supplied by
`aspose_checks_bridge.py::_real_kwargs` **only** by scanning selected `aspose.*` facts for one whose
`source.location` starts with `"data/imported:"` and splitting it -- i.e. only when real imported Aspose
knowledge survived selection for this exact candidate. Per the repo's own 2026-08-19/20 GOV-014 backlog
entry (`plans/backlog-post-poc.md:362-379`), this **skips in nearly every non-full-portfolio run**, and the
narrow error-only fail-closed fix in §A above was deliberately *not* extended to `skip` because doing so
broke 36+ unrelated tests and a real end-to-end supervisor-loop test. So today, a check whose own docstring
calls it a hard gate that "makes it structurally impossible to ship undetected" almost never actually runs,
and its `blocking: true` classification carries near-zero real enforcement.

The generic existing source requirement #7 asks for: **`data/products.json`**, the 33-repository registry,
already carries `family` and `platform` for every registered repository deterministically at load time
(e.g. `{"family": "3d", "platform": "java", "repo_url": "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Java", ...}`),
independent of whether any Aspose knowledge fact was ever imported, selected, or survived verification. This
is not currently threaded into `run_aspose_checks()`/`_real_kwargs()`. Notably, the GOV-014 backlog entry
already reaches the same conclusion independently ("derive family/platform from a broader real source e.g.
the run's own `org_repo`/registry entry"). `RepositorySnapshotV1.org_repo` (format `org/repo`) is already
threaded through the pipeline and matches `data/products.json[*].repo_url`'s path suffix -- the join key
already exists; it is simply not wired into the bridge. This is the smallest closing action for the
`check_banner_present` gap, and it does not require any new data acquisition.

**C. A distinct, larger population never runs at all.** 32 hard-gate, `applicable_after_adaptation` checks
(names in `HARD_CHECK_INPUT_MATRIX.json.never_attempted_applicable_hard_gates`) are not classified blocking
*and* have `runnable_now: false` -- their real-data inputs (mostly `dispositions`, `content_units`,
`structural_units`, diagram-geometry inputs) are not wired into the bridge at all, so they skip on literally
every run today. This is a different, larger gap than A/B: not "skip instead of blocking" but "never even
attempted," pending producer wiring rather than an acceptance-gate fix.

## 5. Genuine evidence-backed N/A vs. missing input (requirement 8)

Two clear examples of real, documented non-applicability -- not silently dropped coverage:

1. **Diff-pair checks** (`check_dropped_content`, `check_only_mermaid_block_changed`,
   `check_only_sections_changed`) declare `old_readme_text`/`new_readme_text` or
   `old_markdown_text`/`new_markdown_text`. `aspose_checks_bridge.py::_real_kwargs`'s own docstring explains
   why these are *deliberately* never supplied: feeding `old==new` (the only value this bridge could
   construct, since it validates one candidate snapshot, not a before/after diff) would make the check
   vacuously pass every time -- "worse than skipping it outright, since a vacuous pass looks like a verified
   clean result." This is a genuine, reasoned N/A for this bridge's current single-snapshot scope, not a
   missing producer.
2. **The two issue-draft-only missing checks** (`check_issue_draft_rejection_list`,
   `check_no_internal_details_leaked_into_issue_draft`) -- D12's own evidence text already flags these as
   "not candidate gates for README-only execution." This repository's pipeline produces README candidates,
   not upstream issue drafts; porting these would require inventing an issue-draft producer this pipeline
   does not have and was never meant to have. `MISSING_CHECK_ADAPTATION_PLAN.json` recommends recording
   these as an explicit, governed `not_applicable_for_readme_only_scope` classification bucket instead of
   either silently omitting them or fabricating a producer -- so the canonical-103 accounting still
   reconciles exactly (see requirement 10 / RED_TEST_PLAN.md).

Everything else missing a real input (`dispositions`, `content_units`, `structural_units`, `code_units`,
badges, `clone_cache_root`, `reference_index`/`reference_class_names`/`reference_dir`, `exclusions`,
`detected_artifacts`, diagram-geometry parameters, `canonical_casing`, `upstream_issues_text`,
`allowed_headings`, `known_family_display_names`, `homepage`, `package_registry`, `docs_texts`,
`corroboration`) is a real, honest producer gap -- machinery not yet built or wired for this pipeline -- not
evidence-backed non-applicability. `check_banner_present`'s family/platform gap belongs in this bucket too,
except that (unlike the others) a generic, already-available source (`data/products.json`) exists and is
simply not wired -- see §4B.

## 6. Porting policy for the missing 14 (requirement 9)

None of the 14 missing checks' actual canonical bodies are available in this repository (only names, per
§0). `MISSING_CHECK_ADAPTATION_PLAN.json` infers each one's likely shape from its already-vendored sibling
family in the *same* section (e.g. `check_additional_example_headings` next to the vendored, blocking
`check_examples_table_collapsed`; `check_scope_compliance` next to `check_scope_limitations_format`, whose
own classification reason already warns "requires an exact Enterprise Edition closing-paragraph convention
this repo's own template does not currently produce" -- i.e., a concrete, already-observed instance of the
exact blind-copy risk requirement 9 warns against). Every entry is explicitly labeled inferred, not
confirmed, and every `policy_configurability_note` calls out what must stay family/template-configurable
(heading text, wording conventions, thresholds) rather than being ported as Aspose's literal string or
constant.

One check, `check_frozen_blocks_unchanged`, has a materially better answer than "no producer exists": this
repository already has a **native** frozen/protected-content concept --
`document_validation.py`'s `authorized_protected_corrections`, `working_condition_hidden_fragment_ids`, and
`find_presentation_span` already identify and track protected spans for an unrelated purpose. The smallest
adaptation binds this check's intent (protected content must not change) to that existing tracker rather
than inventing a new frozen-block representation. Similarly, `check_seo_keyword_plan_usage` can likely reuse
the `aspose.relevant_seo_keywords` fact and keyword-consumption renderer already fixed in commit `05ef1e532e`
(per `defect_gate_map/REPORT.md` finding #7) rather than building a new SEO producer.

## 7. What is already fixed vs. still open, at this exact pin

Confirmed by reading the actual current source (not assumed from the prior audit):

- **D11 (blocking skip/error fails open) -- partially fixed.** Commit `907ac0847` (2026-08-20) added
  `blocking_aspose_check_gaps()` and wired it into `local_poc_acceptance_binding.py`'s
  `validate_acceptance_artifact_chain`, but deliberately only for `outcome == "error"`, and only reachable
  through the local-POC candidate/`check-coverage.json` acceptance path (`local_poc_cache.py`). The broader
  `document_validation.py::validate_readme_document_candidate` gate -- used by five other call sites --
  still does not inspect skip/error state at all. See §4A.
- **D12 (14 missing canonical checks) -- not fixed.** No `canonical_check_inventory.json` is committed;
  `tests/unit/test_aspose_checks_registry.py::test_registry_loads_the_complete_derived_inventory` only
  asserts `len(registry) >= 80` (a loose lower bound), not exact parity with a pinned 103-name manifest. The
  vendored file is unchanged since the prior audit (§0), so the gap is exactly the same 14 names.
- **`check_banner_present` (GOV-014, requirement 7) -- open, already correctly scoped by the repo's own
  backlog.** `plans/backlog-post-poc.md:362-379` already names the right fix direction (broaden
  family/platform derivation beyond the imported-knowledge fact). This audit's contribution is confirming
  the concrete generic source (`data/products.json` + `RepositorySnapshotV1.org_repo`) and that it is not yet
  wired.

## 8. Deliverables in this directory

- `CHECK_103_MATRIX.json` -- all 103 canonical checks, one row each (requirements 1-5, 8).
- `HARD_CHECK_INPUT_MATRIX.json` -- the 11 blocking checks' skip/error/gating detail, plus the 32
  never-attempted hard gates (requirements 6, 7).
- `MISSING_CHECK_ADAPTATION_PLAN.json` -- per-missing-check adaptation plan, sibling-derived, explicitly
  inferred (requirements 9, 10).
- `RED_TEST_PLAN.md` -- exact red-test names and target files (requirement 10).
- `INGEST_MANIFEST.json` -- every source read, every command run, and the explicit boundary constraints
  honored (no Docker/Qwen/full suite/network fetch/tracked-file edit).
- `PROPOSED_COMMIT_MESSAGE.txt` -- drafted for a *future* implementation commit; nothing was implemented in
  this pass.
- `SHA256SUMS` -- checksums of every file in this directory (including itself, excluded from its own hash
  listing per usual convention).
