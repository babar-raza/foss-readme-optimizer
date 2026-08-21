# OPT-KNOWLEDGE-TO-README-BYTES -- audit and K3/C1 repair design

Pin: `aa998102191c530af4dca3a6895d62a4027a613e` (confirmed = HEAD, working tree clean at start).
Mode: read-only audit + design. No tracked file edited, no commit, no Qwen call, no Docker, no test
run. Outputs written only to `runs/owner_audit_staging/knowledge-to-readme-bytes-aa9981021/`.

## Executive verdict

The knowledge-to-README-bytes path has not changed in its causal mechanics since a prior owner audit
on 2026-08-19 (pin `6d112bbf88bc54f7ef3367b16ef8e9b769bdfb51`) -- `git log 6d112bbf..HEAD` is empty
for every file that produces, selects, or renders imported knowledge. What *has* changed in the 12
intervening commits is adjacent machinery: blocking-check skip/error gating now fails closed
(`907ac0847`), source-reconciliation gained a real five-bucket accountability report and closed a
real content-loss bug in the `net` fixture (`c9c0e80f1`, Stage 3A), and one of six imported-claim
fields (`relevant_seo_keywords`) gained a real, shipped, byte-changing renderer consumer
(`05ef1e532`, KNOW-013). None of that touches K3 or C1.

**K3 (post-render knowledge accountability) is confirmed still open, with live evidence from today.**
Fresh `knowledge-application.json` files exist for all three calibration products, written today
(2026-08-20, this exact pin) at `runs/readme-poc/<org>__<repo>/<source_revision>/`. All three report
`sections_influenced: []` and `rendered_output_spans: []` -- not because nothing was selected (35 / 6
/ 13 items were), but because the report's only production call site
(`supervisor/product_truth.py:473-481`) never passes a real `document_plan`, and no second,
post-render call exists anywhere in `src/` (confirmed by full-source grep). The module's own
docstring already promises this second call in `readme/idea_candidate.py`; that file has no such
call today. This is a wiring gap in an otherwise-designed mechanism, not a redesign.

**C1 (accepted knowledge changes useful bytes) is confirmed still open for 5 of 6 fields**
(`feature_claims`/`format_support_claims`/`install_claims`/`limitation_claims`/`troubleshoot_claims`),
matching `KNOW-013`'s own `PARTIAL` status verbatim. Zero consumers exist in `render_views.py`,
`verified_template_capabilities.py`, or any `document_*.py` editorial module for these five fields.

**New finding from today's live data, not in the 2026-08-19 report:** two of 3D's known false-positive
format-support claims (`CLM-3d-2d3c40` "export support for Fbx via FbxExporter",
`CLM-3d-4ae50d` "import support for degree format") were *not* selected today -- but only because they
lost a selection-cap tiebreak (`rejection_reason: exceeds_selection_cap`) while carrying
`verification_state: verified, corroboration: corroborated`, identical to the 8 items that *were*
selected. The corroboration check that marks them "verified" only checks that the cited file exists,
never that its content still supports the claim (K1; independently reconfirmed 2026-08-20 by the
`readme-knowledge-lineage-audit` lane's `KGAP-002`, unconnected to this task). This is why
`IMPLEMENTATION_SEQUENCE.md` gates C1's format-support/feature consumer behind a narrow inline
polarity check rather than shipping on `verification_state` alone.

## Method

1. Confirmed pin = HEAD, clean tree.
2. Located and read the existing `plans/investigations/owner_audit/knowledge_to_candidate/` bundle
   (2026-08-19, pin `6d112bbf`) and the newer, independent `readme-knowledge-lineage-audit` lane
   (2026-08-19/20) -- both already contained deep, evidence-grounded characterization of this exact
   path, using the same K1/K2/K3/V1/C1 gate names this task references.
3. Verified via `git log 6d112bbf..HEAD -- <file>` that every causal file that audit characterized is
   byte-unchanged at the current pin -- so its line numbers, item counts, and field dispositions were
   reused rather than re-derived, freeing this task's budget for (a) reconciling what *did* change,
   and (b) the repair design itself.
4. Two parallel research agents: one located the actual latest 3D/Note/Barcode artifacts (found
   today's fresh `knowledge-application.json` for all three, plus confirmed no fresh candidate exists
   for any of the three -- Docker-blocked container-registry acquisition, per
   `plans/backlog-post-poc.md`'s last three lines); one traced exact current file:line state of every
   K3/C1 causal module.
5. Directly parsed (not fully loaded) all three fresh `knowledge-application.json` files with a
   read-only `python -c` JSON inspection to extract summary fields and full accepted-disposition
   lists -- confirmed the reused 2026-08-19 numbers exactly, and surfaced the `exceeds_selection_cap`
   finding above.
6. Traced the exact current call chain from `idea_candidate.py` through `local_poc_evidence.py`'s
   existing "best-effort report, blocking gate applied later" idiom (already used by
   `readme_reconciliation`/`check_coverage`) to `local_poc_cache.py` -> `local_poc_acceptance_binding.py`,
   to find the minimal, idiomatic hook points K3-3/K3-4 target.
7. Designed K3 and C1 against those exact points; wrote the required deliverables.

## What "actual latest 3D, Barcode, and Note artifacts" means here

No complete, fresh, post-knowledge-layer **candidate** exists for any of the three products at this
pin -- today's runs reached `FACTS_READY` and produced fresh facts + `knowledge-application.json`,
then stalled before `CANDIDATE_GENERATED` (Docker/container-registry unavailable, confirmed by
`runs/share/poc/RESULTS.md` and `plans/backlog-post-poc.md`'s 2026-08-20 entries). The last real
candidate for each product predates today (`superseded/` subfolders dated 2026-08-19 or earlier).
"Actual latest artifacts" therefore means: today's live facts/selection/knowledge-application layer
(genuinely current, genuinely this pin), joined against the most recent available candidate-side
evidence (the pre-knowledge-layer historical trio in `finalized-repository-readmes-v1/`, explicitly
labeled stale/pre-feature, exactly as the 2026-08-19 audit already established it must be). This
task's job -- confirmed by the constraint list (no Qwen, no Docker) -- is to design the repair, not to
force a fresh candidate through a broken container dependency.

## Trace through the nine stages (summary; full detail in FACT_TO_OUTPUT_MATRIX.json)

For all three products, every selected item's journey is identical through stage 6 and then forks:

1. **Imported claim + evidence** -- `data/imported/knowledge/<product>/python/merged/claims.json`.
2. **Selection disposition** -- `aspose_knowledge_selection.py`; per-item `verification_state`/
   `corroboration`/`rejection_reason`, live-confirmed today in each product's `dispositions[]`.
3. **FactRecordV2** -- one record per field, `verified` only if the field-aggregate rule
   (`verified_any`, K1's known defect, not this task's primary scope) says so.
4. **Qwen author packet** -- `agentic_composition_inputs.py::composition_fact_payloads` includes
   every `accepted_composition_fact_ids()` member unconditionally, field-agnostic (code-confirmed).
   Reached by: 3D format_support+limitation (16 items), Note format_support (6), Barcode
   format_support+limitation+license (13) = 35 items total across the trio. Not reached by: 3D
   feature/install/troubleshoot (19 items) -- field-locked unverified.
5. **Document plan** -- `document_renderer.py::build_readme_document_candidate` ->
   `ReadmeDocumentPlanV1`; operations carry `fact_ids`, `candidate_content_provenance` carries the
   verified-template route's lineage.
6. **Render operation / verified-template provenance** -- confirmed zero consumers for 5 of 6 fields
   (`MISSING_CONSUMER_MATRIX.json`); `relevant_seo_keywords` is the sole exception, attribution-only.
7. **Claim map** -- `claim_map.py` would reject any operation/provenance citing these fields if they
   were ever wrongly cited unverified; sound, unused here since nothing cites them.
8. **Final candidate span** -- none exist for any of the 54 selected trio items, live-confirmed.
9. **Review + acceptance** -- `factual_review_packet.py` only projects fact IDs actually referenced
   by operations/claim map/surface plan; since nothing cites these fields, they are invisible to
   independent review too, not merely to rendering.

## Confirm: is `knowledge-application.json` still written only before rendering, and is
verified-template provenance still invisible to it?

**Yes to both, confirmed live today, at this pin.** `product_truth.py:473-481` is the only call site
in `src/`; it never threads `document_plan`. `build_knowledge_application_report` scans only
`document_plan.operations[*].fact_ids`; `candidate_content_provenance` (the verified-template
route's actual lineage channel) is never referenced by this module at all.

## Classification summary (8-category vocabulary; full item-level table in FACT_TO_OUTPUT_MATRIX.json)

| Category | Count (of 54 selected trio items) | Products |
|---|---:|---|
| `rendered_with_exact_span` | 0 | -- |
| `preserved_equivalent` | 0 | -- |
| `supplied_to_qwen_not_used` | 35 | 3D (16), Note (6), Barcode (13) |
| `selected_never_supplied` | 0 | -- (no consumer has ever been reached to decline anything) |
| `rejected_with_reason` | 3417+327+362 (raw-claim level, not selected) | all three |
| `silently_lost` | 0 observed | -- |
| `unverified_supporting_only` | 19 | 3D only (feature/install/troubleshoot) |
| `incorrectly_reported_influential` | 0 | none -- the artifact is honest about its own incompleteness (Gate R5, 2026-08-19, already fixed the old "intent implies influence" bug); the defect is *absence* of post-render proof, not a false claim of influence |

## Repair design

See `IMPLEMENTATION_SEQUENCE.md` for the full, file/function/line-exact design (K3-1..K3-5,
C1-1..C1-5) and `RED_TEST_PLAN.md` for the 14 required tests, including the two explicitly requested:
one proving accepted knowledge changes useful bytes (test 12), one proving unsupported knowledge
cannot (test 13, with a stub-body/polarity parametrization tied directly to today's live
`CLM-3d-2d3c40` finding).

Both repairs reuse only existing plan/render/provenance/acceptance-binding machinery: no new
pipeline, no product/platform branches (every change is field-keyed and ecosystem-generic), exact
`global_claim_id` -> output-span binding via the existing `candidate_content_provenance`/operation
`fact_ids` channels, a real post-render accountability artifact (`knowledge-application.json` v3,
`status="final"`), a required non-null `omission_reason` for every selected-but-unrendered item
(enforced twice: schema validator + acceptance-gate check), an acceptance-blocking gate for a
missing/invalid/stale final report, bounded per-run caps reusing the selector's existing per-field
cap value (no new stuffing surface), and invalidation via the existing `candidate_sha256` staleness
check (no new cache-key machinery needed).

## Live caveat noticed at validation time (not investigated further, per this repo's protocol)

At the very end of this pass, `git status` showed **uncommitted, in-progress working-tree changes to
tracked files this audit never touched**: `src/readme_agent/facts/acceptance_contract.py` (+2),
`src/readme_agent/facts/aspose_knowledge_selection.py` (180 lines changed), a new untracked
`src/readme_agent/facts/knowledge_evidence_verification.py` (7,955 bytes), and
`tests/unit/test_fact_acceptance_contract.py` (+6). These are consistent with an in-progress K1
(per-item verification laundering) fix, apparently landing concurrently in this same working tree
while this audit ran -- the repo's git history confirms the tree was clean at this conversation's
start. This task made zero edits to any tracked file (verified: every `Write`/`Edit` call in this
session targeted only `runs/owner_audit_staging/knowledge-to-readme-bytes-aa9981021/`); this note is
observational only, per this repo's standing guidance to flag rather than touch concurrent
in-progress work. If K1 lands for real, re-validate this report's `unverified_supporting_only`
classifications and the `exceeds_selection_cap` sequencing hazard against the post-K1 selector
before relying on them.

## Limitations of this pass (time-boxed to 60 minutes)

- Full raw-claim-to-rejection-reason enumeration (3,417 / 327 / 362 rejected items) was not
  individually itemized in FACT_TO_OUTPUT_MATRIX.json -- only the selected 54 items are itemized by
  `global_claim_id`, which is what "trace every *selected* imported fact" requires; rejected-item
  detail is available verbatim in each product's live `dispositions[]` array (paths in
  `INGEST_MANIFEST.json`) if a future pass needs it.
- No fresh candidate could be produced or observed for any of the three products (Docker-blocked, out
  of this task's allowed tool scope regardless) -- stages 5-9 for a *current* candidate are therefore
  traced via code-path proof (what the current code would/would not do) rather than a fresh
  transcript, clearly labeled as such throughout this report and the matrix.
- API-surface (K2) and full per-item verification aggregation (K1) are characterized here only where
  they intersect K3/C1's safe sequencing (the `exceeds_selection_cap` finding); their own full repair
  designs remain out of this task's scope, as directed.
