# Source-versus-knowledge truth audit

Audit date: 2026-08-19  
Optimizer audit pin: `6d112bbf88bc54f7ef3367b16ef8e9b769bdfb51`  
Later observed optimizer tip: `d71f38b6` (`eaf5eef6` fixed five baseline failures; later changes were auto-push governance; no audited knowledge-selection/product-truth change)  
Scope: current public source, pre-refresh README, current published README, imported knowledge, Aspose bundle evidence, and optimizer candidates for the three Python repositories named below.

## Decisive verdict

The import is not primarily losing files. For Note and Barcode, the promoted optimizer knowledge is semantically equal to the Aspose bundle after normalizing line endings and the optimizer's snippet authorization header. The blocking defects are that the imported corpus contains unresolved or weakly evidenced statements, and the optimizer converts those statements into “verified” facts using file existence rather than proposition-level evidence.

The current selector is therefore unsafe even when `repo_sha` is current. On 3D it accepts a working `NurbsSurface.to_mesh` claim although that method raises `NotImplementedError`. On Barcode it accepts positive PDF-export claims and the negative `NotImplementedError` claims for the same methods in the same run. The 3D COLLADA limitation, however, is correctly scoped: an internal exporter is implemented, but the public `Scene.save` route is broken. This distinction reinforces the defect—symbol or file existence cannot establish public capability. The models nevertheless report `has_conflicts=false`, have no `merge_conflicts.json`, and expose no truth gaps.

This is the smallest causal chain:

1. Aspose acquisition/enrichment emits mixed-scope and sometimes contradictory material.
2. Optimizer imports the bundle faithfully but does not close evidence or reconcile polarity.
3. `src/readme_agent/facts/aspose_knowledge_selection.py::_file_evidence_corroboration` (line 236 at the audit pin) treats an existing cited file as corroboration without checking cited line, symbol, excerpt, method body, direction, or claim polarity.
4. `_claim_eligibility` (line 260) permits uncorroborated claims when the knowledge SHA is current.
5. `select_knowledge_claims` (line 350) ranks and caps claims by output field but performs no entity/action/direction conflict pass.
6. The unit test at `tests/unit/test_aspose_knowledge_selection.py:171` explicitly expects a format claim to verify when its evidence file contains only a placeholder comment. It enshrines, rather than catches, the defect.

The conclusion is not that Aspose's machinery should be discarded. Its repository inventory, syntax extraction, limitation scan, snippets bank, provenance, and staged candidate workflow are valuable. They must be reused with stricter proposition-level verification and deterministic reconciliation.

## Lineage and runtime disposition

| Repository | Current public SHA | Imported knowledge SHA | Pre-refresh SHA | Runtime | Selected |
|---|---|---|---|---|---:|
| 3D/Python | `ee05c1ba9153ef5916b7a108406c794f2e464d01` | same | `ab1a2267a0ba6302311d0c7c4ad01494974c7d76` | current | 35 / 3,452 |
| Note/Python | `41de2e8ab478b5aeff3663f7f7cbf83b19fdf676` | `6d97a522a9ed24708687911f1aabb76e2dea2da7` | same as knowledge | stale revision | 6 / 333 |
| Barcode/Python | `06eca5c01e13ed6d59a640f1cf330c1c5a57d151` | `53f2c3350b8171f2c8275e7b1a178f218695ac45` | same as knowledge | stale revision | 13 / 375 |

Only `README.md` changed between the Note and Barcode knowledge revisions and current tips. Their code, manifests, and licenses did not change, so code-derived facts can still be supported while README excerpts are stale. Imported `index.json` nevertheless says `stale=false` for both.

The current public READMEs are already Aspose refresh outputs, not original inputs. For Note and Barcode, optimizer `ORIGINAL-README.md` is byte-equivalent to the pre-refresh source. For 3D, the sealed pre-refresh replay is `ab1a2267…`; its bytes are absent from the optimizer finalized artifacts and must be fetched from that historical commit. The optimizer's 3D `ORIGINAL-README.md` instead matches the post-refresh merge state at `62fb89f3…`. The optimizer's accepted candidates are different documents and were not published:

| Repository | Optimizer accepted candidate | Candidate bytes | Current published bytes | Sequence similarity |
|---|---|---:|---:|---:|
| 3D/Python | `5735c3…` | 76,093 | 17,983 | 0.047 |
| Note/Python | `2333e0…` | 25,689 | 23,016 | 0.147 |
| Barcode/Python | `2cac2f…` | 17,539 | 11,093 | 0.202 |

`AGENT_APPROVED` is consequently not evidence of parity with Aspose's published candidate.

## Product findings

### 3D/Python

- Provenance is current, but semantic truth is not. `formats.md` marks FBX import/export “Yes”; `FbxExporter.save` and `save_to_stream` are stubs. It marks COLLADA export “Yes,” but public `Scene.save` is not functional for COLLADA: the public formats module exposes a legacy `ColladaSaveOptions` not derived from `SaveOptions`, and extension dispatch reaches `FbxExporter.supports_format`—inherited as `NotImplementedError`—before the registered COLLADA exporter. `ColladaExporter.export` itself is implemented and its direct internal tests work. Public capability and internal implementation must therefore remain separate. Working 3MF import/export is omitted. Units such as degree, radian, points, and absolute are misclassified as formats.
- `limitations.md` is strong deterministic evidence: 401 rows match 401 concrete `NotImplementedError` methods. Yet the positive format/features layer is not reconciled against it.
- All 327 imported API tuples resolve exactly, but the source contains 344 top-level class/function definitions; public reachability is not established. All 154 imported graph edges match, with two `Generic[T]` edges omitted.
- Of 3,452 claims, 635 have no evidence. Another 538 evidence records name absent files, affecting 491 claims. Only 9 of 71 README excerpts occur exactly in the current README.
- `install.md` is contradicted: it verifies `import aspose_3d_foss`, while the actual import root is `aspose.threed`; the dated package registry says the PyPI candidate was unpublished, and the current README uses source checkout plus `pip install -e .`.
- Current `LICENSE` is MIT, but the model license is empty and no license claim exists.

### Note/Python

- The promoted knowledge SHA is the pre-refresh SHA, although current source differs only in README. This is a revision/evidence-lineage defect, not code drift.
- All 54 API entries resolve, but three are nested implementation helpers. The API, coverage, and index layers report 54, 50, and 39 classes respectively without a reconciled visibility definition. Two of 26 class-graph edges are nested local Flowable helpers.
- PDF export is supported. OneNote variants are recorded only as “detect,” so `formats.md` renders the package's primary `.one` read capability as neither import nor export.
- `pip install aspose-note>=26.3.2` is supported by manifest and dated registry evidence, but the verification import is wrong: `aspose_note` instead of `aspose.note`.
- The root license is MIT, while `pyproject.toml` and the model use `LicenseRef-Aspose-Split`, and `THIRD_PARTY_NOTICES.md` exists. A single undifferentiated label is incomplete.
- Ninety-seven snippets compile as fragments; 13 came from the pre-refresh README and none occur exactly in the current README. They still require imports, fixtures, `self`, or surrounding setup.

### Barcode/Python

- The promoted knowledge SHA is pre-refresh although only README changed. The complete-bundle clone cache already has the current README, proving acquisition advanced further than promotion.
- All 146 API tuples resolve, and all 55 graph edges match. API visibility is unresolved: the coverage ledger tracks 79 classes and the index exposes 26.
- PNG and SVG export are supported. PDF export is contradicted: `PdfRenderer.render` and `Barcode.to_pdf` raise `NotImplementedError`. Caveats exist in `formats.json` but are lost in `formats.md` and runtime selection.
- Six concrete limitation rows are exact. The selector still simultaneously verifies six positive export claims and six limitation claims for the same PDF paths.
- Four claims have no evidence. Fifty-six evidence records cite absent pseudo-files, affecting 49 claims. Only two of 11 README evidence excerpts occur exactly in the current README.
- The direct PyPI install is not repository-proven and conflicts with the dated registry's unpublished status; the current README uses source installation. The import root itself is correct.

## Cross-cutting acquisition and ledger defects

`scripts/data-refresh/detect_aspose_upstream_drift.py::_compare_bundle` (line 77) is invoked only for `knowledge/*/*/merged/bundle_manifest.json` paths (line 152). Note/Python and Barcode/Python have no `bundle_manifest.json`, so the detector cannot see them. It also compares the imported bundle to the upstream Aspose corpus; it does not compare each live target repository default-branch SHA or promote refreshed knowledge.

The coverage/conflict layers are descriptive but not governing. Examples include 3D's `forbidden_count=50` versus 401 limitations, the three incompatible Note API counts, and Barcode's positive/negative PDF collision. No product has a conflict ledger that makes these discrepancies fail closed.

The SEO source is cross-ecosystem polluted: 327/375 3D strings, 207/305 Note strings, and 185/203 Barcode strings mention .NET/C# or related ecosystems. Runtime filtering retains zero for all three. That is safe today but means the registry contributes no keywords; zero retention should be an acquisition warning, not silent success.

Aspose.org FOSS links are useful discovery material. Aspose.com links are enterprise surfaces, and Barcode's largely target Python-via-Java/.NET rather than this pure-Python package. They are `external-only` evidence and must never corroborate a FOSS API claim without an explicit product/scope bridge.

## Prioritized reuse-and-repair map

### P0 — make selection proposition-safe

1. Enhance `_file_evidence_corroboration`; retain its path safety checks, but require the cited line/range or symbol to contain evidence relevant to the normalized proposition. Return separate statuses such as located, supports, contradicts, and unresolved. A file's existence must never mean “verified.”
2. Add a deterministic conflict key before ranking: `(subject/symbol, operation, direction, format, scope)`. Reconcile positive and negative claims; concrete implementation/exception evidence outranks prose or declarations. Unresolved conflicts must be excluded from generation and written to a conflict ledger.
3. Remove current-SHA as a substitute for corroboration in `_claim_eligibility`. Freshness may lift a stale gate; it must not make an unsupported claim eligible.
4. Replace the placeholder-file unit expectation with three regression fixtures: 3D FBX/NURBS/COLLADA, Barcode PDF, and a true supported export. For COLLADA, assert both internal exporter implementation and failed public `Scene.save` reachability instead of collapsing them. Assert exact scope/polarity and that no field contains incompatible dispositions.

### P1 — close provenance, installation, and formats

5. Enhance drift detection to enumerate every `model.yaml`, including manifest-less pairs, compare live target default-branch SHA, distinguish README-only from code/manifests/license drift, and fail when index freshness contradicts revision state. Regression-test Note and Barcode.
6. Derive installation as a small decision table: manifest distribution name, actual import root, dated external publication state, and repository source-install path. Never synthesize the import module from the distribution name. Test all three repositories.
7. Build format direction from dispatcher/reader/writer implementation plus executable tests and negative evidence. Preserve caveats into the rendered fact. Test 3D FBX and 3MF, Note `.one`, and Barcode PDF/PNG/SVG.

### P2 — tighten useful existing machinery

8. Reconcile API visibility and all counts from one canonical filtered surface; exclude nested/local helpers and explicitly label internals.
9. Enforce evidence closure: reject missing files, pseudo-files, absent excerpts, and README evidence whose content hash belongs to a superseded revision.
10. Keep the snippet bank, but adapt selected fragments into standalone examples and execute them in a bounded product environment before publication.
11. Keep strict SEO ecosystem filtering and add a diagnostic/failure threshold when a product retains zero usable terms.

These changes enhance existing selectors, drift checks, ledgers, and extractors. They do not require a parallel architecture or a new autonomous subsystem.

## Scope and limitations

This is principally a static, reproducible audit of the pinned repository states and supplied/imported artifacts. External URLs and present-day package-index publication were not live-validated; such fields are classified `external-only` or qualified by the registry's 2026-08-01 observation. Full product test suites were not executed. A targeted 3D COLLADA probe and `python -m unittest tests.test_collada_exporter` were executed: the five direct internal-exporter tests passed while both tested public `Scene.save` routes failed as described. “Compiles” for snippets means Python compilation as extracted, not standalone runtime success.

Optimizer main advanced after the audit pin. At `eaf5eef6`, the five previously observed baseline failures were repaired by excluding `template_sha256` from semantic plan hashes after verifying outputs were unchanged and by skipping a mutable Note artifact on hash mismatch; the reported result was 4,207 passed, one skipped, one xfailed, zero failed. Later observed tips through `d71f38b6` were auto-push governance. This restores baseline health but does not modify the selector, drift ownership, or product-truth findings audited here.

Machine-readable classifications and evidence are in `truth_matrix.json`; exact reproduction commands are in `reproduction.md`; input/output checksums are in `sha256-inventory.json`.
