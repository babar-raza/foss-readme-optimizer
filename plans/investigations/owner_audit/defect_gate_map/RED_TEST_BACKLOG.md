# Failing-before / passing-after test backlog

Pin used for initial failure analysis: `d71f38b6a050b5282f0ada314f9ee4de35950426`. Later observed runtime change `05ef1e532ae34bea07fefe951543a43f41ca55c4` closes the SEO truth-citation defect; later `91d9479b1e1fa12a9af41c1692b6f8f421db5f76` adds evidence only.

Every item below is intentionally the smallest fixture that demonstrates the missing contract. “Hard” means the assertion must eventually prevent acceptance; “review” means it calibrates a probabilistic judgment and cannot be the sole source-truth gate.

## P0 — source truth before rendering

### RED-01 — Public method that only raises is not a supported behavior (hard)

- Owner: `src/readme_agent/facts/curated_python_api_eligibility.py`, `src/readme_agent/facts/curated_python_api_projection.py`, `src/readme_agent/presentation/verified_template_api_descriptions.py`
- Test: extend `tests/unit/test_curated_python_api_eligibility.py` and `tests/unit/test_verified_template_api_descriptions.py`.
- Fixture: exported `NurbsSurface.to_mesh()` whose body is only `raise NotImplementedError`.
- Red assertion: rendered member description must not contain positive “Supports converting … to mesh.”
- Green contract: keep public visibility separate from behavioral availability; produce a scoped limitation or withhold behavior prose.

### RED-02 — FBX contradiction resolves negative with a positive control (hard)

- Owner: `src/readme_agent/facts/aspose_knowledge_selection.py`, `src/readme_agent/facts/curated_constraint_evidence.py`.
- Test: extend `tests/unit/test_aspose_knowledge_selection.py`.
- Fixture: one positive FBX-export claim plus `save` and `save_to_stream` limitation claims, all citing an existing `FbxExporter.py` whose methods raise. Add a working OBJ exporter.
- Red assertion: current selection accepts verified positive and negative aggregates without conflict.
- Green contract: the public FBX export proposition is limitation-only/unavailable; working OBJ stays positive.

### RED-03 — Barcode PDF contradiction resolves negative; PNG/SVG stay positive (hard)

- Owner/test seam: same as RED-02.
- Fixture: `PdfRenderer.render` and `Barcode.to_pdf` raise; PNG/SVG methods return output.
- Red assertion: PDF support is selectable as verified alongside its limitation.
- Green contract: PDF support is blocked or false, its limitation is selected, and PNG/SVG are unchanged.

### RED-04 — COLLADA internal implementation is not public-route support (hard)

- Owner: `src/readme_agent/facts/curated_constraint_evidence.py`, selector resolution.
- Test: extend `tests/unit/test_curated_constraint_evidence.py`.
- Fixture: existing synthetic Scene/IOService/Exporter/FbxExporter/ColladaExporter dispatch graph.
- Red assertion: a flat positive COLLADA export claim can authorize public support.
- Green contract: assert two propositions simultaneously: internal exporter implemented; public `Scene.save` unavailable with exact dispatch limitation.

### RED-05 — Distribution name is not Python import root (hard)

- Owner: Python acquisition/example verification and template adapter.
- Test: add two cases to the existing Python acquisition/example test seam, plus an end-to-end composition assertion.
- Fixtures: `aspose-3d-foss` -> `aspose.threed`; `aspose-note` -> `aspose.note`.
- Red assertion: slug-derived `aspose_3d_foss`/`aspose_note` can be rendered without module execution.
- Green contract: only source-resolved roots compile/execute; wrong roots hard-fail.

### RED-06 — `setup.py` dependency state is not silently empty (hard)

- Owner: `src/readme_agent/facts/python_dependency_acquisition.py`.
- Test: `tests/unit/test_python_dependency_acquisition.py` (create if absent).
- Fixtures: setup.py A declares `install_requires=['dep-a']`; setup.py B declares `install_requires=[]`.
- Red assertion: A and B both return indistinguishable `[]`.
- Green contract: A returns `dep-a` or an explicit unsupported/gap result; B alone can prove an empty set. Never execute setup.py.

## P0 — validation and acceptance closure

### RED-07 — Applicable blocking skip/error cannot pass (hard)

- Owner: `src/readme_agent/validation/aspose_checks_bridge.py`, `src/readme_agent/readme/document_validation.py`.
- Tests: extend `tests/unit/test_aspose_checks_registry.py` and `tests/unit/test_aspose_checks_fixture_coverage.py`.
- Fixture: one synthetic `blocking=true` descriptor. Subcases: missing required kwarg, raises, returns non-list.
- Red assertion: result/document remains valid with the name in skipped/errored.
- Green contract: each subcase is a typed proof-obligation failure; only explicitly governed nonapplicability is a nonblocking skip.

### RED-08 — Canonical 103-name parity (hard)

- Owner: vendored check module, registry, classification.
- Test: extend `tests/unit/test_aspose_checks_fixture_coverage.py`.
- Fixture: committed canonical inventory containing the 103 exact top-level names and canonical source hash.
- Red assertion at start pin: exact set difference is the known 14 missing functions.
- Green contract: set equality, one classification row per name, and one explicit bridge disposition per name. Issue-draft-only checks may be governed nonapplicable but may not be absent.

### RED-09 — Reconciliation failure blocks persistence/promotion (hard)

- Owner: `src/readme_agent/readme/readme_reconciliation.py`, `src/readme_agent/supervisor/local_poc_evidence.py`, `src/readme_agent/readme/document_validation.py`.
- Tests: extend `tests/unit/test_readme_reconciliation.py` and `tests/unit/test_local_poc_evidence.py`.
- Fixtures/assertions:
  1. overlapping source ranges -> invalid candidate, not `{error: ...}` evidence plus success;
  2. duplicate identical paragraphs, only one moved -> the other cannot be called relocated by substring match;
  3. omission without typed verified reason -> invalid; policy-superseded removal -> valid;
  4. convert the current real .NET move `xfail` to pass.

### RED-10 — Every material candidate claim receives one factual disposition (hard coverage, review judgment)

- Owner: `src/readme_agent/specialists/factual_review_packet.py`, review result/acceptance modules.
- Tests: `tests/unit/test_factual_review_packet.py`, `tests/unit/test_separated_readme_review.py`.
- Fixture: three material candidate claims; mock reviewer returns judgments for only two.
- Red assertion: approval can proceed because positive findings are treated as adequate.
- Green contract: a deterministic coverage receipt marks the third missing and blocks; exactly one disposition for each of all three passes.

### RED-11 — Qwen merged length failure takes one separated fallback (review transport)

- Owner: `src/readme_agent/specialists/merged_readme_review.py`, `src/readme_agent/llm/reviewer_client.py`.
- Tests: `tests/unit/test_reviewer_client.py`, `tests/unit/test_separated_readme_review.py`.
- Fixture: merged client raises `LLMError` with `finish_reason=length`; separated blind/factual clients return minimal valid tool results.
- Red assertion: top-level error escapes before fallback.
- Green contract: no identical merged retry; exactly one bounded call per separated facet; receipt records trigger, clients and output hashes. Malformed non-length output is separately classified.

### RED-12 — Reviewer execution changes invalidate approval cache (hard)

- Owner: `src/readme_agent/llm/verification_prompts.py`, local cache/acceptance key.
- Test: `tests/unit/test_fact_acceptance_contract.py` or a focused reviewer-standard-hash test.
- Fixture: hold prompts/schemas constant; change merged token budget or fallback-policy version.
- Red assertion: `separated_reviewer_standard_hash()` remains unchanged.
- Green contract: execution-policy hash changes and old review is ineligible.

## P1 — presentation safety and evidence completeness

### RED-13 — Note/Python can never fall back to Maven/JDK (hard)

- Owner: Python acquisition and `presentation/template_adapters.py`.
- Tests: pinned end-to-end case in `tests/unit/test_readme_composition_characterization.py` or `test_agentic_readme_composition.py`.
- Fixture: sealed Note/Python snapshot with unavailable trusted registry evidence.
- Red calibration: historical July artifact emits `mvn clean install`, Maven and JDK.
- Green contract on current pipeline: none of those tokens appear; ecosystem is Python; missing acquisition is withheld or blocks.

### RED-14 — SEO safety closed; persist editorial consumption span (diagnostic-to-hard evidence)

- Safety test already green at `05ef1e53`: grounded keyword changes fallback title bytes and is absent from authoritative `fact_ids`.
- Residual owner: `verified_template_capabilities.py`, capability plan/evidence schema.
- Fixture: the existing “Third-party plugin integration support” / “plugin integration guide” case, persisted through plan/evidence serialization.
- Residual red assertion: no artifact names the exact consumed keyword or title byte span after `keyword_used_here` leaves local scope.
- Green contract: supporting/editorial lineage records keyword source fact, exact consumed value and output span without adding it to factual authorization.

## Required portfolio calibration after unit greens

Run the fixed pipeline against the pinned 3D, Barcode and Note snapshots. Acceptance must demonstrate, in artifacts rather than prose:

- no positive Nurbs/FBX/PDF support;
- scoped internal/public COLLADA distinction;
- correct Python imports;
- no Note Maven/JDK text;
- reconciliation built without error or unexplained omission;
- every applicable hard check ran/passed;
- every material claim has exactly one factual disposition;
- Qwen review either completes merged within budget or records the single separated fallback;
- a second unchanged run is `NO_OP_PROVEN` only after all semantic gates pass.
