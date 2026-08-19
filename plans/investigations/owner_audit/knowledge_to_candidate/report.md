# Knowledge-to-candidate owner audit

Date: 2026-08-19  
Mode: read-only forensic audit; no repository, target-repository, or GitHub mutation  
Optimizer audit pin: `6d112bbf88bc54f7ef3367b16ef8e9b769bdfb51`  
Later observed `main`: `d71f38b6` (intervening `eaf5eef6` repaired five baseline-test failures; later changes are auto-push/auth robustness; no knowledge-path invalidation of this audit)  
Imported-corpus manifest aggregate SHA-256: `a61de2b9cdd30956c585b02d16e5f1b6bc0beccf4ee9b1fbb66312492b2cd821`

## Executive verdict

The optimizer has imported a substantial portion of the aspose.org knowledge base, but it has **not yet established an end-to-end, fail-closed knowledge-to-visible-output contract**. It can load and select claims, and verified selected facts are offered to Qwen3 Next, but most imported artifact families are not production inputs, the accepted truth gate does not require any imported-knowledge field, the deterministic renderer does not consume the six new claim fields, and the only production `knowledge-application.json` write happens before a document plan exists. Consequently, “loaded,” “selected,” “prompt-visible,” “cited,” “attributed,” and “changed candidate bytes” are presently conflated.

The three live calibration repositories demonstrate the gap:

| Repository | Current target SHA | Imported bundle SHA | Freshness | Raw claims | Selected items | Verified selected items | Imported claim fields offered to Qwen | Proven visible imported-claim spans |
|---|---|---|---|---:|---:|---:|---:|---:|
| 3D/Python | `ee05c1ba9153ef5916b7a108406c794f2e464d01` | same | current | 3,452 | 35 | 16 | 2 | 0 |
| Note/Python | `41de2e8ab478b5aeff3663f7f7cbf83b19fdf676` | `6d97a522a9ed…` | stale | 333 | 6 | 6 | 1 | 0 |
| Barcode/Python | `06eca5c01e13ed6d59a640f1cf330c1c5a57d151` | `53f2c3350b81…` | stale | 375 | 13 | 13 | 3 | 0 |

“Proven visible” is zero, not a claim that no model could ever use the facts. It means the available artifacts contain no current post-feature run whose exact candidate byte spans are bound to these selected imported facts. The historical optimizer candidates predate the new knowledge layer and contain no `knowledge-application.json`; exact normalized selected-claim text matches are zero in all three historical candidates.

The immediate course is not to expand machinery. Repair the narrow lineage and verification seams, run the seven-case calibration set below, and refuse portfolio fan-out until one current 3D/Python run proves every stage.

## Source identity and contamination boundary

Four artifacts must not be treated as interchangeable:

1. The imported bundle’s `model.yaml.repo_sha` is the source revision at knowledge extraction.
2. The historical optimizer candidate is bound to its own older `source_revision`.
3. The current target repository tip already contains a refreshed README.
4. The aspose.org `repo-presenter-regen-full` candidate is an independent candidate artifact.

The current target pins are documented in `work/owner_audit/repository_pins.md`. The historical optimizer evidence roots are:

- `plans/investigations/evidence/finalized-repository-readmes-v1/repositories/python/3d--62fb89f3ca76--5735c3f66e57/`
- `plans/investigations/evidence/finalized-repository-readmes-v1/repositories/python/note--6d97a522a9ed--2333e0c29565/`
- `plans/investigations/evidence/finalized-repository-readmes-v1/repositories/python/barcode--53f2c3350b81--2cac2f2bfa46/`

Those candidates are not evidence of current knowledge use. Each was generated from an older target revision, reports deterministic salvage rather than an authoring response, and has a null/empty author prompt record.

Candidate identity comparison (word counts are descriptive, not quality scores):

| Product | Current published README | Aspose candidate | Historical optimizer candidate |
|---|---|---|---|
| 3D/Python | SHA `66ceadf1…`, 1,894 words | `files/reports/repo-presenter-regen-full/3d/python/readme.md`, SHA `2fa5c43f…`, 5,501 words | SHA `5735c3f6…`, 8,631 words |
| Note/Python | SHA `fd47d03c…`, 2,656 words | `…/note/python/readme.md`, SHA `3ce54cb4…`, 2,576 words | SHA `2333e0c2…`, 2,868 words |
| Barcode/Python | SHA `4e311891…`, 1,300 words | `…/barcode/python/readme.md`, SHA `6b87c37d…`, 1,349 words | SHA `2cac2f2b…`, 1,804 words |

## What was imported

Evidence at the audit pin:

- `data/imported/` contains 3,276 files and 110,461,796 bytes.
- The imported product snapshot and bundle tree contain 31 family/platform bundles: Python 12, .NET 6, Java 4, C++ 4, TypeScript 2, Go 2, Rust 1.
- The optimizer registry has 33 entries. PSD/Python and PSD/.NET are not in the imported corpus.
- Raw aggregate inventory: 97,303 claims; 10,196 API-surface entries; 695 format rows; 4,635 class-graph rows; 7,708 coverage-matrix rows; 2,445 snippet-index rows.
- Claim-kind distribution: `api_method` 60,345; `api` 21,526; `api_class` 7,855; `feature` 2,212; `troubleshoot` 1,548; `api_field` 1,220; `format_support` 1,126; `limitation` 884; `format` 440; `install` 114; `dependency` 21; `license` 12.

Each of the 31 bundles has `claims.json`, `model.yaml`, API surface, formats, class graph, coverage matrix, index, install/limitations Markdown, and baseline ledger/head. Only 18 have a bundle manifest; other delta/receipt artifacts vary by bundle.

### Actual production consumption

`src/readme_agent/facts/provider.py:361-382` is the production join point. It invokes:

1. `build_aspose_detection_bundle()` / `aspose_fact_records()` — legacy detectors using imported keywords, diagram archetypes, package registry, aspose.com targets/backlinks, diagram dependencies, model/claims, and structured API surface, plus current clone license/dev-test evidence.
2. `knowledge_claim_fact_records()` — the new full-claim loader/selector, directly reading only `merged/claims.json` and `merged/model.yaml`.
3. `relevant_seo_keyword_fact_record()` — a filtered SEO fact.

`data/imported/data/products.json` is used to decide expected corpus scope. `knowledge_manifest.json` is hashed into the fact-acceptance contract. The following imported families are **not direct current fact-provider inputs**: standalone `formats.*`, `install.md`, `limitations.md`, snippet bodies/index, class graph, coverage matrix, ledgers, deltas, bundle manifests, pipeline-run metadata, index, and merge reports. Some appear in vendored aspose.org code, but the optimizer does not run that orchestration; it only bridges selected check functions against its own candidate/facts. They are presently dead or supporting-only from the optimizer production perspective.

## Trio lineage, stage by stage

### Raw availability

| Product | Claims | API rows | Formats | Class graph | Coverage | Snippet index |
|---|---:|---:|---:|---:|---:|---:|
| 3D/Python | 3,452 | 327 | 97 | 154 | 327 | 100 |
| Note/Python | 333 | 54 | 5 | 26 | 50 | 97 |
| Barcode/Python | 375 | 146 | 6 | 55 | 79 | 100 |

All claims loaded and received a disposition in the forensic reproduction. This does not mean all were eligible or useful.

### Claim selector

3D/Python considered 3,452 claims, selected 35, rejected 3,417, and produced five field-level `FactRecordV2` records:

- feature: 8 unverified, uncorroborated;
- format support: 8 verified, corroborated;
- install: 3 unverified, uncorroborated;
- limitation: 8 verified, corroborated;
- troubleshoot: 8 unverified, uncorroborated.

Rejections: 2,730 “covered by API surface,” 683 over per-field cap, 4 below confidence. Only the two verified fields (16 items) are output-authorizing and offered to Qwen under current acceptance filtering.

Note/Python considered 333, selected six, rejected 327, and produced one verified format-support field. Rejections: 324 “covered by API surface,” three stale and uncorroborated. Six items are offered to Qwen.

Barcode/Python considered 375, selected 13, rejected 362, and produced three verified fields: six format-support, six limitations, one license. Rejections: 344 “covered by API surface,” 17 stale and uncorroborated, one dependency-covered. Thirteen items are offered to Qwen.

Legacy detector fields add verified author-visible records: 3D has four verified of six detector records; Note five of six; Barcode seven of eight. Adding the new claim fields gives 6, 6, and 10 Qwen-eligible imported field records respectively. These are field-record counts, not claim-item counts.

### Resolver and acceptance

The selector returns `FactRecordV2` records to the normal resolver (`provider.py:383-394`). However, `README_TRUTH_FIELDS` in `facts/acceptance_contract.py:20-31` contains only canonical product/acquisition/example/license/relationship fields. None of the new `aspose.*_claims` fields is required for `FACTS_READY`. Therefore a run can be accepted with the imported knowledge absent, dead, or visibly unused.

The accepted composition set then filters selected facts to `verified` or `policy_approved`. `composition_fact_payloads()` includes full compacted values and source identity for every accepted ID (`agentic_composition_inputs.py:113-139`). This is real prompt visibility, but not output use.

### Exact Qwen author context

`plan_readme_composition()` computes accepted IDs, the compact facts packet, overview phrase options, and deterministic assessment; it then supplies the source README, all accepted facts JSON, assessment JSON, phrase options, and repair/diagram hints to a forced-tool call (`agentic_composition.py:132-189`). The route is `qwen3-next` (`env.py:103`). Output is schema-validated and bounded by the tool schema.

The six new claim fields can be cited in a section decision or opening summary. But the main phrase/renderer system is canonical-field oriented:

- overview options use a fixed canonical preference set;
- diagram vocabulary uses canonical visitor render views;
- `visitor_fact_render_view()` has no renderer for the six new imported-claim fields (`facts/render_views.py:205-227`);
- the verified template renderer uses canonical capabilities/formats/license/etc., not the six new fields.

Thus the new claims are prompt-visible but normally have only one direct prose opportunity: the model-authored opening summary. A section decision’s fact IDs are planning rationale, not automatically rendered prose.

### Plan, renderer, candidate, provenance

There is no current post-feature trio bundle proving a selected imported claim altered candidate bytes. The historical trio candidates predate the feature and have zero exact selected-claim-text matches. That exact-match test is conservative—paraphrase could evade it—but there is also no post-render knowledge evidence to establish paraphrased influence.

Verified-template provenance can bind canonical facts to exact byte ranges, and the claim-map builder rejects selected facts that are unverified or conflicted (`readme/claim_map.py:156-174`). That mechanism is sound when the correct per-item fact IDs are supplied. It does not rescue a field-level fact that has already laundered unverified items.

### Review context

The factual packet initially contains all selected facts (`specialists/factual_review_packet.py:178-205`), but its prompt projection keeps only IDs referenced by operations, source sections, claim map, or surface plan (`:93-132`). If there are no referenced IDs at all, it falls back to all facts. If ordinary canonical facts are referenced but imported facts are not, the imported facts disappear from the factual reviewer’s exact prompt and remain only in the inventory hash/count. The blind reviewer receives no fact graph by design. Therefore unreferenced knowledge is not independently checked for omission.

## Confirmed defects

### P0 — field-level verification laundering

`aspose_knowledge_selection.py:552-576` sets the entire field record to verified if **any** selected item in the field is verified (`verified_any`). The item values at `:561-568` omit item verification and corroboration. Downstream sees one verified fact ID and cannot distinguish the unverified members. One verified item can therefore authorize unrelated unverified text.

Actual current trio occurrence under the existing `file`-only corroborator is zero: each selected field is currently homogeneous. This is a **latent but directly reachable production defect**, not a trio incident.

The adjacent corroborator defect makes it easier to trigger. `_file_evidence_corroboration()` reads only `evidence[].file` (`:236-251`), while enriched claims also use `source_file`. Evidence-shape counts:

- 3D: 2,873 evidence records; 2,241 `file`/line and 632 `source_file`/snippet;
- Note: 330, all `file`/line;
- Barcode: 380; 309 `file`/line and 71 `source_file`/snippet.

Five currently selected 3D claims point via `source_file` to files that exist in the current clone. A forensic key-normalization experiment makes the 3D install field mixed: one corroborated/verified item plus two unverified items. With `verified_any`, all three are then exposed under one verified fact ID. Barcode additionally admits eight correctly corroborated claims (five feature, three troubleshoot).

Smallest safe repair: recognize both evidence keys, persist per-item verification/corroboration, and require `verified_all` for an output-authorizing aggregate. Never let a mixed aggregate enter accepted composition; alternatively split it into separate verified and supporting facts.

### P0 — imported API knowledge is classified as “covered” but produces no usable fact

The claim selector rejects API kinds as covered by structured API surface: 2,730 / 324 / 344 trio claims. Yet `detect_api_public_surface()` requires `visibility == "public"` **and** truthy `reachable` (`aspose_detectors.py:649-655`):

- 3D: 327 rows; 184 public, 143 conventional, but every row has `reachable: false`;
- Note: 54 rows; 24 exported, 26 conventional, four missing visibility, and no reachable value;
- Barcode: 146 rows; 79 public, 67 missing visibility, and no reachable value.

Result: no imported `api.public_surface` fact for any trio member. Historical optimizer API facts came from repository AST extraction, not imported knowledge. This is silent imported-knowledge loss masked by the rejection reason.

There is a second schema mismatch: the legacy imported API fact stores `classes` as a dictionary, while both compact prompt projection and template consumers expect a list of class dictionaries. Even bundles that pass the detector can lose class/member detail before Qwen or rendering.

Smallest safe repair: normalize the real schema variants into one canonical list, assign ecosystem-aware reachability (`exported_via_package_init`/public import for 3D, `exported` for Note, `public` for Barcode) with repository corroboration, and only suppress API claims after proving a non-empty canonical structured fact.

### P0 — knowledge-application evidence never reaches post-render truth

The report type correctly distinguishes considered, selected, influenced, and exact rendered spans (`knowledge_application_evidence.py:11-40`). But production calls it only once during fact collection without `document_plan` (`supervisor/product_truth.py:469-481`). No post-render call exists, although the module docstring says one will supersede the first. Therefore `sections_influenced` and `rendered_output_spans` are always empty in production.

Even adding a naive post-render call is insufficient. The builder scans only `document_plan.operations[*].fact_ids` (`knowledge_application_evidence.py:133-162`). Verified-template compilation commonly uses one compile operation with no fact IDs and stores the real lineage in `candidate_content_provenance`. The report must join both operation provenance and candidate-content provenance.

Smallest safe repair: write the report at fact stage as provisional, rewrite it after candidate/claim-map creation, consume both operation and candidate-content provenance, bind candidate SHA, and fail candidate acceptance if a selected/cited imported fact has no accountable final disposition.

### P0 — blocking Aspose checks fail open when skipped or errored

`run_aspose_checks()` records missing-input checks as skipped and exceptions/non-list returns as errored, but computes `valid` only from critical findings that actually returned (`validation/aspose_checks_bridge.py:127-179`). `blocking_aspose_check_findings()` filters only returned findings (`:218-230`). Document validation promotes those findings to errors but never promotes a blocking check’s skipped/errored state (`readme/document_validation.py:556-579`). A classified blocking check can therefore skip or crash and acceptance still passes.

At this pin the vendored registry contains 89 checks: 11 classified blocking, 61 adaptation-required nonblocking, 17 diagnostic heuristic nonblocking. The current bridge may run only a subset. For the 11 blocking checks, skipped or errored must be a blocking infrastructure outcome, not absence of a finding.

### P1 — SEO “influence” is attribution-only and can cite an ineligible fact

`aspose.relevant_seo_keywords` is deliberately unverified (`aspose_seo_keyword_facts.py:96-108`) and therefore excluded from accepted author facts. Yet the template capability builder adds its fact ID to a capability row when text already happens to match (`verified_template_capabilities.py:698-769`). This does not change the row bytes—it is attribution-only—but it enters authoritative provenance. The claim-map builder then correctly rejects unverified provenance facts. The trio has no relevant SEO fact, so this is latent, not an observed trio failure.

Smallest repair: do not put an unverified SEO ID in authoritative `fact_ids`. Record it in a distinct supporting/attribution channel that cannot authorize text and cannot be counted as visible influence, or establish verification before use.

### P1 — corpus checksum can miss unmanifested byte drift

The `imported_knowledge` contract hashes selector/loader code plus `knowledge_manifest.json`, not every imported file (`facts/acceptance_contract.py:58-62,286-315`). This is efficient only if manifest integrity is independently checked. A corpus file mutated without regenerating the manifest will not change the component hash. Add manifest-to-tree verification before reuse, or hash the selected bundle members directly.

## PSD README-only repositories

Optimizer evidence is unambiguous:

- PSD/Python and PSD/.NET are two of 33 registry products but absent from the 31-bundle imported corpus.
- `load_knowledge_claims_with_findings()` returns `product_platform_not_in_imported_corpus`; its documentation treats that as non-agent-fixable (`aspose_knowledge_claims.py:152-160,253-260`).
- The existing unit test explicitly expects that result.
- The optimizer’s PSD upstream-issues evidence records README-only repositories with no code/license and blocks them as `BLOCKED_MISSING_EVIDENCE`.

The supplied aspose.org bundle contains no PSD candidate, so the statement that aspose.org handles PSD cannot be independently verified from this bundle. The optimizer demonstrably does **not** handle them.

Do not invent implementation truth. Add an explicit README-only/placeholder product profile with approved family identity, repository status, contribution/support links, and honest “no implementation is present here” wording; forbid package install, API, format-direction, license, and maturity claims unless separately evidenced. Treat registry-without-corpus as a coverage defect or explicit profile, never a benign invisible absence.

## What “near perfection” and “30/30” mean in the supplied evidence

The aspose.org bundle proves sophisticated process assets and strong test depth, not a clean 30/30 portfolio:

- `verification/results.txt` records 1,078 scoped tests passed, 0 failed/skipped/errors in 183.50 seconds and a complete 2,133-entry bundle hash reconciliation.
- `repo-presenter-regen-full` contains 31 canonical README files.
- `files/reports/_scratch/mt056_audit_portfolio_FINAL.json` evaluates 30 of them (Cells/TypeScript is omitted), reports `clean_count: 8`, `dirty_count: 22`, `total: 30`, and `skipped: []`.
- Only 13 of those 30 are marked published; five are both clean and published in that audit.

Therefore the bundle contains **no evidence of 30/30 clean candidates**. Its value is the mechanism: exhaustive content-disposition ledgers, repeated portfolio sweeps, precise hard-gate findings, repair-specific scratch evidence, and a large check suite. “Near perfection” is a user assessment of candidate quality, not a mechanically demonstrated 30/30 fact in this package. Optimizer should copy the discipline—complete disposition, exact preservation checks, typed failures, repair loops—not the unsupported score.

The optimizer’s own committed cohort is also not 30/30: `finalized-repository-readmes-v1/cohort-manifest.json` is explicitly `PARTIAL-VERIFIED-PORTFOLIO`, with 10 promoted README artifacts out of its historical registry denominator 32 (10/13 Python), zero product effects, and zero remote writes. Current registry denominator is 33.

## Required quality rubric and acceptance gates

### P0 factual and lineage safety

1. **Identity:** target source SHA, imported `repo_sha`, source README hash, candidate hash, and current target status are stored separately.
2. **Corpus accountability:** every registry entry is either covered by an imported bundle or an explicit approved profile; no silent out-of-corpus product.
3. **Per-item verification:** every output-authorizing item is individually verified/corroborated; mixed aggregates never inherit `verified` from one member.
4. **Conflict supremacy:** current repository evidence wins. Contradictions are rejected or explicitly resolved; 3D FBX is the mandatory calibration contradiction.
5. **Byte-level lineage:** every visible factual claim has exact candidate-byte provenance and a verified selected fact; supporting-only attribution cannot authorize prose.
6. **Fail-closed checks:** every classified blocking check must return pass/fail; skipped/error blocks acceptance.

### P1 knowledge and content quality

7. **Stage ledger:** for every artifact family and claim: available → parsed → accepted/supporting/rejected → offered to author → cited in plan → rendered span → reviewed.
8. **Structured API usability:** schema-normalized public/reachable names survive into Qwen context and template output; API claims are suppressed only after equivalent coverage is proven.
9. **Preservation:** every source content unit has a disposition; retained/merged units are anchored to exact candidate spans; omission requires typed rationale.
10. **Visible-use truth:** prompt visibility and matching attribution are not counted as output influence. Influence requires changed bytes or exact surviving provenance.
11. **README-only honesty:** PSD produces a useful, polished repository-status README without unsupported code/install/API/license claims.

### P2 repeatability and runner suitability

12. **Determinism:** identical source SHA, corpus SHA, policy, prompts, template, and model route reproduce facts/plan/candidate or a typed no-op.
13. **Bounded Qwen:** forced-tool schemas, compact evidence packets, deterministic validation, at most two author/repair attempts, and no free-form fallback.
14. **Independent review:** factual review receives every fact that authorizes or supports candidate prose; blind review remains fact-independent.
15. **Post-render evidence:** final knowledge application, claim map, check coverage, review, and no-op artifacts are checksum-bound to the candidate.
16. **Resource budget:** per-field caps remain; shared corpus parsing is cached/content-addressed; one verified canary precedes 2–4 isolated lanes; aggregate mutation remains serialized.

“30/30” is attained only when all 33 current registry entries have an explicit status and all 30 intended delivery targets (if 30 remains the governed denominator) pass these gates at current revisions. The denominator and exclusions must be declared, not inferred.

## Calibration set for Qwen3 Next

1. **3D/Python current SHA:** current corpus, `source_file` corroboration, mixed-field regression, and FBX contradiction. Expected: no unsupported export claim; explicit limitation preserved; all selected items retain individual states.
2. **Note/Python current SHA:** stale imported bundle. Expected: only independently corroborated items authorize output.
3. **Barcode/Python current SHA:** stale bundle with format, limitation, and license claims. Expected: 13 selected verified items remain independently traceable.
4. **PSD/Python and PSD/.NET:** README-only/no imported bundle. Expected: honest repository-status candidate, not `BLOCKED_MISSING_EVIDENCE`, and zero implementation claims.
5. **Synthetic mixed field:** one verified plus two unverified items. Expected: aggregate rejected from accepted composition or split; never all-authorized.
6. **Synthetic matching unverified SEO keyword:** expected byte-identical capability row with supporting-only attribution; claim map remains valid.
7. **Structured API schema variants:** the actual 3D, Note, and Barcode imported API files. Expected: non-empty normalized public-surface projection and stable class/member counts.

For each case capture author input hash, tool output, validated plan, candidate bytes, claim map, final knowledge application, deterministic checks, factual/blind verdicts, repair history, and unchanged rerun with zero provider calls.

## Minimal implementation sequence

1. Fix per-item verification and `source_file` corroboration together; add the real 3D plus synthetic mixed-field regression.
2. Normalize structured API surface and stop claiming API coverage until a usable structured fact exists.
3. Make knowledge-application evidence post-render and provenance-aware; turn missing lineage into a candidate acceptance failure.
4. Fail closed on blocking Aspose check skips/errors.
5. Remove unverified SEO IDs from authoritative provenance.
6. Add PSD explicit profile and calibration.
7. Run one current 3D end-to-end canary. Only after its exact byte lineage, two independent reviews, and zero-call no-op pass should Note and Barcode run, followed by bounded portfolio fan-out.

Any change in steps 1–3 invalidates `imported_knowledge`/`ProductFactsV2`, `facts_hash`, assessment if fact-sensitive, composition plan, candidate, provenance/claim map, validation/review, final verdict, and no-op proof. The cache maps fact-contract changes to `FACTS_COLLECTING`; downstream artifacts must be recomputed. A pure presentation-only change may begin at `PLAN_READY`, but none of the P0 repairs above is presentation-only.

## Evidence versus inference

Evidence in this report is derived from committed code, committed evidence artifacts, the supplied complete bundle, and read-only calculations over imported JSON plus the pinned clones. Inferences are limited to predicted behavior after a proposed repair (for example, Qwen use after structured API normalization) and are labeled as expected outcomes. No live production run was executed, no Qwen endpoint was called, and no target or control repository was changed.
