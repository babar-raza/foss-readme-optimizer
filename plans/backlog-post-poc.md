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
