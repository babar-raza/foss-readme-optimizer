# Post-POC backlog

- 2026-08-09: poc runner failed for aspose-html-foss/Aspose.HTML-FOSS-for-Python: ValueError: verified template lacks required capability, acquisition, or example facts
- 2026-08-09: aspose-html-foss/Aspose.HTML-FOSS-for-Python cannot deliver a verified README:
  its pyproject.toml declares `build-backend = "setuptools.backends.legacy:build"`, a module
  that does not exist in setuptools, so every `pip install .` fails before building and the
  acquisition/example proofs stay blocked. Upstream one-line fix: use
  `build-backend = "setuptools.build_meta"` (as every other portfolio repo does), then re-run
  `readme-agent poc --repo aspose-html-foss/Aspose.HTML-FOSS-for-Python`.
- 2026-08-09: poc runner failed for aspose-pdf-foss/Aspose-PDF-FOSS-for-Python: ValueError: invalid README header visual: capability_columns_short failed
- 2026-08-09: poc runner failed for aspose-slides-foss/Aspose.Slides-FOSS-for-Python: verified diagram has 0 input node(s); requires 1
- 2026-08-09: poc runner failed for aspose-tex-foss/Aspose.TeX-FOSS-for-Python: verified diagram has 0 input node(s); requires 1
- 2026-08-09: poc runner failed for aspose-words-foss/Aspose.Words-FOSS-for-Python: verified diagram has 0 input node(s); requires 1
- 2026-08-09: poc runner failed for aspose-html-foss/Aspose.HTML-FOSS-for-Python: ValueError: compiled verified presentation is invalid: API reference contains an incomplete generic description
- 2026-08-09: poc runner failed for aspose-slides-foss/Aspose.Slides-FOSS-for-Python: verified diagram has 0 input node(s); requires 1
- 2026-08-09: poc runner failed for aspose-tex-foss/Aspose.TeX-FOSS-for-Python: verified diagram has 0 input node(s); requires 1
- 2026-08-09: poc runner failed for aspose-words-foss/Aspose.Words-FOSS-for-Python: verified diagram has 0 input node(s); requires 1
- 2026-08-09: poc runner failed for aspose-slides-foss/Aspose.Slides-FOSS-for-Python: verified diagram has 0 input node(s); requires 1
- 2026-08-09: poc runner failed for aspose-tex-foss/Aspose.TeX-FOSS-for-Python: verified diagram has 0 input node(s); requires 1
- 2026-08-09: poc runner failed for aspose-words-foss/Aspose.Words-FOSS-for-Python: composition opening summary contains invalid sentence punctuation
- 2026-08-09: BarCode header-visual mismatch — the composed candidate's output labels
  canonicalized MIME subtypes ("PNG (image/PNG) files") while the document-plan render
  produces lowercase ("image/png"), so candidate_exact_mermaid fails. Canonical-abbreviation
  application to diagram endpoint labels is unstable across the two render sites; unify the
  canonicalization step (apply once, in the authoritative candidate derivation) and re-run.
- 2026-08-09: Cells retains 9 blocking source claims (feature bullets, contribution steps,
  support links) that are fact-authorized preserves without a merged placement; per-claim
  routing found no structural home. Needs a working-condition placement lane that routes
  fact-authorized leftovers without pre-empting whole-section preservation (a naive
  preserve-path deferral regressed Security-section carry and was reverted).
- 2026-08-09: RESOLVED same day - TeX now DELIVERED clean (12/12). The earlier diagnosis
  ("verified template lacks required capability, acquisition, or example facts") had a wrong
  root cause: api.public_surface WAS verified with usable package metadata; the real gaps were
  (a) empty class member inventories (extraction-depth gap, still open below) starving the
  generated example, (b) mandatory verified_installation claims with no accepted binding
  dropping silently instead of deferring, and (c) description fallbacks emitting text the
  presentation lint bans. Fixed general lanes: import-only statically-validated Quick Start
  fallback, working-condition deferral for unbindable mandatory obligations, concrete-operation
  description fallbacks.
- 2026-08-09: TeX class member inventories are empty (15 catalog classes, 0 members) - same
  private-module re-export extraction-depth gap as BarCode/HTML; richer Quick Start and
  per-member API tables need the member inventory to see through re-export chains.
- 2026-08-09: 38 non-live tests pin pre-#99 fail-closed expectations (deferred-at-approval, source-assurance reinsert, final-claim corpus); update the expectations to the working-condition contract.
- 2026-08-09 (platforms): RESOLVED same day - non-Python delivery crashes closed as general
  working-condition lanes: mermaid casing unified into the authoritative header render
  (BarCode-class two-site instability), formats-optional scope citation, required-slot
  omission with working-condition accounting (quick start / key capabilities / at a glance /
  scope), diagramless badges-only header for zero-capability-evidence repos, accepted-only
  purpose/audience summary gates with identity-grounded fallback, deterministic
  opening-summary punctuation repair, identity-only clone acquisition fallback, and a
  one-retry lane for LLM plan composition in the poc runner.
- 2026-08-09 (platforms): Go/TypeScript/C++/Rust ecosystems lack capability/format/example
  verification lanes - extraction produces assertions but nothing verifies them (Go: blocked
  with "no input/output format survived isolated-consumer and native-extractor verification";
  TS/C++: mostly missing). Working-condition delivery ships minimal verified READMEs
  (identity + acquisition + license); richer content needs per-ecosystem verifiers.
- 2026-08-09 (platforms): .NET capability phrases are raw XML-doc sentences ("Render state
  for building the...") - diagram labels truncate mid-phrase and capability descriptions trip
  repeats-title lint. Needs a .NET capability-phrase distillation lane.
- 2026-08-09 (platforms): .NET 3D retains major_capabilities/api_public_surface prose claims
  without a merged placement - same placement-lane gap as Cells/Email Python.
- 2026-08-09 (platforms): Go "Requires" badge duplicates the platform token
  ("Requires: Go Go 1.24.5+") - badge label composition should not repeat the platform name.
- 2026-08-09 (platforms): LLM opening summaries can carry capability prose beyond accepted
  facts (Go summary described spreadsheet capabilities while product.capabilities is
  blocked); deterministic claim grounding rejects it downstream, but the summary lane should
  be constrained to accepted evidence at authoring time.
- 2026-08-09 (platforms): aspose-words-foss/Aspose.Words-FOSS-for-.NET cannot clone - the
  upstream repository has a missing Git LFS object (TestData/Model/Charts/
  TestSurfaceChartSegments.docx, remote missing object 3c72e272...). Upstream defect for the
  product agent; local workaround is LFS-smudge-skipped baseline clones (the README pipeline
  never needs LFS binaries).
- 2026-08-09 (platforms): RESOLVED same day - Words-.NET clone (work clones now skip LFS
  smudge like baselines) and oversized diagrams (input/output nodes trim to presentation
  targets; selected capabilities stay complete). All 19 non-Python repos deliver.
- 2026-08-09 (platforms): a broad working-condition deferral for unverified example fences
  (primary_example/additional_examples obligations) was tried and reverted - it violated the
  six pinned example-deferral guarantees in test_verified_source_claim_omissions.py
  (execution-verified examples must never defer; surviving candidate bytes must never defer;
  deferral requires an executed minimal example and fixture-absence proof; prose never
  defers). An ecosystem-general example-deferral lane must generalize those preconditions
  (executed minimal example + fixture proof for .NET/Java/C++/TS/Go/Rust) instead of
  bypassing them; until then non-Python example claims stay visible as blocking accountability
  rows in validation.json.
- 2026-08-09 (PSD Python): RESOLVED local candidate delivery. The private repository now uses
  authenticated read-only cloning, the established local Git-ref state backend, and an explicit
  Python policy profile while remaining `mode: disabled`. Required presentation slots may omit an
  unsupported license rather than inventing one. The upstream repository contains only a two-line
  README and no license or implementation evidence, so its visible candidate remains
  `VALIDATION_FAILED` on one preserved source claim until authoritative product content arrives.
- 2026-08-09: poc runner failed for aspose-psd-foss/Aspose.PSD-FOSS-for-Python: baseline clone of aspose-psd-foss/Aspose.PSD-FOSS-for-Python failed: Cloning into 'D:\Users\prora\OneDrive\Documents\GitHub\foss-readme-optimizer\runs\baseline\aspose-psd-foss__Aspose.PSD-FOSS-for-Python'...
fatal: Cannot prompt because user interactivity has been disabled.
fatal: could not read Username for 'https://github.com': terminal prompts disabled

- 2026-08-09: poc runner failed for aspose-words-foss/Aspose.Words-FOSS-for-Python: RuntimeError: durable product-facts evidence hash does not match lifecycle state for aspose-words-foss/Aspose.Words-FOSS-for-Python@4473f8cbeef1a65961adc7de304d982ada53a1dd
- 2026-08-09: poc runner failed for aspose-words-foss/Aspose.Words-FOSS-for-Python: container registry acquisition remained unavailable after bounded retry
- 2026-08-09: poc runner failed for aspose-words-foss/Aspose.Words-FOSS-for-Python: container registry acquisition remained unavailable after bounded retry
- 2026-08-09: poc runner failed for aspose-words-foss/Aspose.Words-FOSS-for-Python: ValueError: valuable source detail has no canonical presentation destination: claim:3345:3058101d753ee667:unclassified
- 2026-08-09: poc runner failed for aspose-words-foss/Aspose.Words-FOSS-for-Python: ValueError: preserve disposition lost a source claim without exact fact-bound replacement candidate content: claim:3345:3058101d753ee667
- 2026-08-09: poc runner failed for aspose-html-foss/Aspose.HTML-FOSS-for-Python: ValueError: invalid contextual README links: candidate repeats an Aspose target
- 2026-08-18 (GOV-014): full unit suite has 12 pre-existing failures unrelated to the
  claim-accountability LLM-disposition Phase 3 wiring or the source-placement duplicate-ID
  fix landed the same day (both confirmed via `git stash` A/B against session baseline;
  neither change touches these paths). Triaged, not fixed here — out of this session's scope:
  - Stale evidence-fixture path (8 tests): `test_verified_source_opening.py` (3),
    `test_readme_composition_characterization.py::test_public_composition_call_signatures_are_characterized`
    was NOT this one (see below) but `test_agentic_readme_composition.py::
    test_agentic_plan_is_source_and_fact_bound_and_changes_the_candidate`,
    `test_golden_workflow_coordinates.py::test_note_source_workflow_is_covered_by_the_canonical_renderer`,
    `test_source_claim_structured_matching_exact.py::
    test_current_note_feature_and_api_deferrals_have_accepted_fact_ids`,
    `test_trusted_transform_review.py::
    test_canonical_trusted_pipeline_persists_approval_then_exact_no_op` all read
    `plans/investigations/evidence/finalized-repository-readmes-v1/repositories/python/
    pdf--537b8273b185--bd8699b68869/...`, but the on-disk directory is now
    `pdf--537b8273b185--189b3321da5e` (evidence regenerated by a later "clean promotion
    rebuild" commit, d50f4fbf9, without updating these hardcoded fixture paths).
  - Stale golden hash (3 tests): `test_readme_composition_characterization.py::
    test_document_composition_bytes_and_plan_are_characterized` for the 3 Java cases
    (cells/3d/pdf) — candidate bytes still match the pinned `candidate_hash`, but the pinned
    `plan_hash` no longer matches `plan.model_dump(mode="json")`; some prior change to the
    plan schema/content was never re-pinned for these 3 parametrized cases.
  - `test_portfolio.py::test_completed_local_poc_status_advances_only_with_valid_bundle`
    reappeared failing despite the 2026-08-15 freshness-service TB-03 GOV-014 row (see
    `plans/investigations/evidence/freshness-service-tb-03/gov-014-backlog-row.patch`)
    recording it as fixed/closed-loop — needs re-diagnosis, not assumed still-fixed.
  - `test_local_poc_review_evidence.py::test_no_op_proof_reuses_the_exact_accepted_review_binding`
    passes in isolation and in every small batch tried, but failed inside the full
    ~3900-test run — order/state-dependent flakiness (likely shared cache or global
    registry state leaking across test modules), not reproduced standalone.
