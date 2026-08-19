# Candidate-defect gate audit

Audit date: 2026-08-19  
Optimizer `main` pinned at start: `d71f38b6a050b5282f0ada314f9ee4de35950426`  
Latest `main` observed during audit: `91d9479b1e1fa12a9af41c1692b6f8f421db5f76`  
Canonical comparison source: attached `readme-refresh-complete-bundle-20260819-174412`

## Conclusion

The optimizer is strong at artifact integrity and replay consistency, but still weak at semantic proof. It can prove that a candidate, plan, facts, validation output, review receipt, and no-op replay agree byte-for-byte while all of them share an overbroad or wrongly scoped premise. That is exactly how a false `NurbsSurface.to_mesh` behavioral claim reached an `AGENT_APPROVED` 3D candidate and later `NO_OP_PROVEN` evidence.

The main gap is not “Qwen quality.” It is that deterministic evidence is sometimes reduced to file/symbol existence, opposite-polarity propositions are not reconciled, public routes are conflated with internal implementation, some strict calculations are only diagnostic, and reviewer coverage is not exhaustive. A stronger model may notice some errors, but it cannot make this repeatable on a constrained runner.

The fastest safe repair sequence is:

1. Make repository truth proposition-scoped and polarity-aware before rendering.
2. Make every applicable hard check a proof obligation: pass or block; skip/error cannot pass.
3. Make source reconciliation success and typed omissions part of acceptance.
4. Require exhaustive candidate-claim review coverage, then add bounded separated-review fallback for Qwen truncation.
5. Restore canonical check-inventory parity and bind every semantic change into cache keys.

## What the current gate chain actually does

| Layer | Current strength | Material hole |
|---|---|---|
| Imported knowledge | Deterministic manifest, freshness and bounded selection | For non-license claims, an existing cited file is enough to call a claim corroborated; cited line/symbol/content/scope/polarity are ignored. |
| Selected facts | Stable IDs and accepted verification states | `verified_any` marks an aggregate field verified when only one selected member is verified; per-item state is not retained in the value. `aspose.*` fields are not required `README_TRUTH_FIELDS`. |
| Plan/render | Hash-bound operations, protected-content and claim-accountability structures | Broad facts can authorize narrower behavioral prose. Public API presence becomes “Supports …” even when the body raises. |
| Deterministic validation | Good reconstruction, hashes, protected fragments, selected-fact citations | Only 11 of 89 vendored Aspose checks are blocking; applicable hard skip/error passes. Reconciliation errors and omission counts are evidence-only. |
| Independent review | Separate blind/factual roles and grounded packets | No proof that every material candidate claim received a factual disposition. Merged Qwen output can truncate at 4000 tokens before fallback is reachable. |
| Acceptance/no-op | Strong hash and dependency consistency | Stability is mistaken for semantic quality; reconciliation/check-coverage success and exhaustive reviewer coverage are not acceptance predicates. |
| Cache invalidation | Facts, templates, vendored checks, prompts and schemas are substantially hashed | Reviewer execution policy/client/token limits are not in reviewer-standard hash. Reconciliation and check-coverage helper semantics are not direct stage dependencies. |

## Exact high-risk chains

### 1. 3D `NurbsSurface.to_mesh`

The imported `api_method` claim `3d/python/CLM-3d-b3b916` is not directly selected because API kinds are delegated to `api.public_surface`. That does not make the outcome safe. The curated API fact `api.public_surface:python-exports` records the method as public because it exists and is exported. `verified_template_api_descriptions.py` then turns method presence into positive “Supports …” behavior. Neither the named-member heuristic nor the reviewer proves that the method body does anything other than raise `NotImplementedError`.

This is the clearest calibration red test: public visibility may remain true, but behavioral support must be false.

### 2. 3D FBX and Barcode PDF contradictions

Both are the same selector defect:

- positive claims cite files/classes/methods that exist;
- negative claims cite `NotImplementedError` bodies;
- the generic selector treats file existence as corroboration for both;
- the facts land in different aggregate fields, so conflict resolution never joins them;
- a heuristic text contradiction check is nonblocking.

The repair must create a proposition key such as `(family, platform, format, direction, public_route)` and apply current repository negative evidence supremacy before the plan is built. PNG/SVG and working 3D formats must remain positive controls, preventing blanket suppression.

### 3. 3D COLLADA scope

COLLADA is not a simple contradiction. `ColladaExporter.export` is implemented and its direct tests pass, while the public `Scene.save` route fails because of save-option and dispatcher-chain defects. The optimizer already has a strong detector, `_collada_dispatch_limitation`, which proves that chain. The correct output is two scoped truths, not rejection of all positive internal evidence and not promotion to public support.

### 4. Wrong Python import roots

The supplied knowledge says `import aspose_3d_foss` and `import aspose_note`; actual roots are `aspose.threed` and `aspose.note`. Those standalone install documents are currently supporting-only and their bad strings happen not to be selected. There is no general Python import-root check: package registry matching validates a distribution, and the canonical source-import check is Java-oriented. A two-repository executable regression is required so future ingestion cannot reactivate the bad strings.

### 5. July Note Maven/JDK fabrication

The July Note/Python proposal inserted `mvn clean install` and a JDK requirement. Its own review reported the result unverified, so this artifact is evidence of unsafe generation, not false final approval. Current Python acquisition logic probably prevents recurrence, but no pinned end-to-end Note regression proves it. Missing acquisition evidence must lead to withholding/blocking, never cross-ecosystem substitution.

### 6. Reconciliation is strict internally and fail-open externally

`build_readme_reconciliation_report` raises for overlapping ranges and unaccounted loss. `_readme_reconciliation_report_or_error` catches that error and persists an error object so candidate persistence cannot fail. Relocation uses substring containment rather than a one-to-one source/destination identity, and any operation overlapping a gap can cause an `omitted` classification without a typed verified reason. The existing real .NET move test remains `xfail`.

This must become a hard acceptance gate. An evidence file saying reconciliation failed is not reconciliation.

### 7. SEO safety was repaired after the audit pin; output-span evidence remains

At the start pin, `aspose.relevant_seo_keywords:aspose-knowledge` was correctly unverified but the capability renderer appended it to authoritative `fact_ids` when a keyword matched. Commit `05ef1e532ae34bea07fefe951543a43f41ca55c4`, observed while this audit was running, closes that safety defect: a grounded keyword can measurably change only a generic fallback title and is never cited as factual evidence. Tests cover changed bytes, no-op/unrelated input and one-use behavior.

The remaining gap is auditability, not factual authorization. `keyword_used_here` is local control state and the emitted capability row persists only markdown, authoritative fact IDs and coordinates. No candidate evidence artifact binds the exact consumed keyword to the title output span. The fix is therefore satisfactory for safety but incomplete for the requested “actual consumption/output-span evidence.”

### 8. Qwen merged-review truncation

The merged reviewer is capped at 4000 output tokens with one transport attempt and one response attempt. The observed Qwen response ended with `finish_reason='length'` and truncated JSON. `execute_merged_readme_review` calls `client.analyze()` before the only fallback `try`, so the current isolated blind fallback is unreachable for this failure. The correct recovery is one bounded switch to separated factual and blind reviews, not another identical merged call.

The reviewer-standard cache key hashes prompts and schemas, but not the reviewer client, token budget, model route, attempt policy, or merged-fallback execution code. These must be versioned into acceptance so a changed review policy cannot reuse old approval.

### 9. Aspose check coverage

AST comparison, not prose counts, gives:

- canonical attached source: 103 top-level `check_*` functions;
- optimizer vendored source at `d71f38b6`: 89;
- missing: 14;
- local classification: 11 `applicable_reusable` blocking, 61 `applicable_after_adaptation` nonblocking, 17 `diagnostic_heuristic` nonblocking.

The 14 missing names are recorded exactly in `DEFECT_GATE_MATRIX.json`. Two are issue-draft-only. The remaining twelve include scope, frozen-block, SEO-plan, dependency, diagram, image/content-unit and quick-start checks with direct README-quality value. Existing tests prove local registry/classification consistency, not equality to a pinned canonical 103-name manifest.

Separately, `run_aspose_checks` records missing arguments as `checks_skipped`, exceptions/non-list returns as `checks_errored`, and still computes `valid` only from critical findings. `document_validation` only adds normalized findings from the 11 blocking rows. Therefore an applicable blocking check can skip or error and the candidate can remain valid.

## Hard gates versus heuristics

These should be hard deterministic gates:

- public-route capability versus `NotImplementedError`/dispatch reality;
- proposition-level positive/negative conflict resolution;
- Python import-root execution;
- selected/cited fact verification and scope compatibility;
- applicable blocking check completion;
- exact source reconciliation with typed, verified omissions;
- canonical check-inventory and classification completeness;
- exhaustive reviewer coverage receipt (coverage is deterministic even though judgments are not);
- candidate/review cache-key completeness.

These should remain secondary heuristics/reviewer concerns:

- prose quality, tone and information architecture;
- semantic redundancy and readability;
- fuzzy claim-scope suspicion;
- SEO wording preference;
- qualitative diagram usefulness.

A heuristic finding may block after calibration, but it must not be the only defence against a source-level contradiction that can be determined mechanically.

## Acceptance and cache changes required

Acceptance should require all of the following, not merely persist the artifacts:

- no unresolved proposition-level contradiction;
- every selected aggregate member has its own retained verification state and evidence;
- all applicable blocking checks ran and passed;
- reconciliation report built successfully, partitions the source once, and has no unexplained omission;
- every material candidate claim has a factual-review disposition;
- the review execution-policy hash matches the current client/model/token/fallback implementation;
- the canonical 103-name inventory is matched or every absent issue-only check has a governed nonapplicability record.

Add direct stage dependency inputs for `readme_reconciliation.py` and `aspose_check_coverage.py`. Add reviewer client/execution policy to `separated_reviewer_standard_hash()` or a new acceptance-bound execution hash. The existing hashing of `aspose_knowledge_selection.py`, the vendored check source, bridge and classification is appropriate and should be preserved.

### 10. Later Boundary A evidence: `setup.py` dependencies can become silent empty lists

Commit `91d9479b1e1fa12a9af41c1692b6f8f421db5f76` is evidence-only and does not change runtime behavior. Its `KGAP-001` finding is valid: `python_dependency_acquisition.py` returns bare `[]` for any non-`pyproject.toml` manifest, while `dependency_snapshot.py` honestly reports not-applicable. The audited 3D `setup.py` declares an empty list, so the current product result is benign by coincidence; a different `setup.py` with real `install_requires` would be silently misrepresented. D13 gives the minimal two-fixture regression.

## Evidence limitations

This is a strictly read-only source/artifact audit. It did not run target product suites or mutate optimizer/GitHub. Historical defects are used as failing calibrations; they do not by themselves prove that every current candidate still reproduces the identical prose. Where current code appears to have reduced a historical risk (notably the Note Maven fallback), the matrix says “likely fixed but unproven” and requests an end-to-end regression rather than claiming closure.
