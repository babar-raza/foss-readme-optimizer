# Prioritized repair backlog

This is a narrow repair sequence for the existing optimizer machinery. Do not add a second orchestrator, a second fact graph, or a free-form LLM fallback.

## Exit rule before portfolio fan-out

Do not fan out beyond one current 3D/Python canary until all P0 items below are merged and that canary has:

- individually verified selected items;
- a non-empty normalized imported API projection or an explicit, truthful reason it is unused;
- exact post-render knowledge spans bound to the candidate SHA;
- all 11 blocking Aspose checks run successfully (no skip/error);
- deterministic validation, factual review, blind review, final verdict, and zero-provider-call unchanged rerun.

## P0-1 — prevent verification laundering and normalize evidence keys

**Cause**

- `src/readme_agent/facts/aspose_knowledge_selection.py::_file_evidence_corroboration` reads only `evidence[].file`.
- `select_knowledge_claims` computes `verified_any` for an entire field and omits verification/corroboration from item values.

**Smallest repair**

1. Accept both `file` and `source_file` through one validated repository-relative path helper.
2. Store `verification_state`, `corroboration`, and evidence reference on every item.
3. Set an aggregate output-authorizing state only when every item is verified and no item conflicts (`verified_all`), or split verified and supporting items into different fact records.
4. Ensure `accepted_composition_fact_ids` can never admit a mixed aggregate.

**Regressions**

- Synthetic field with one verified and two unverified items: zero unverified items in author payload; claim map cannot cite them.
- Real 3D/Python: five selected `source_file` references resolve; install becomes one verified plus two supporting/unverified, never one wholly verified list.
- Real Barcode/Python: five feature and three troubleshoot claims become corroborated without changing unrelated dispositions.
- Reject absolute paths, traversal, directories, and symlink escape.

**Invalidation**

`FACTS_COLLECTING` onward: ProductFacts, facts hash, assessment if fact-sensitive, plan, candidate, provenance, claim map, validation/reviews, verdict, no-op.

## P0-2 — normalize imported structured API before claiming coverage

**Cause**

`detect_api_public_surface` requires literal `visibility=public` and truthy `reachable`, while the trio schemas use `public`, `exported`, `conventional`, false/missing `reachable`. Downstream compactors expect `classes` as a list, while the legacy detector emits a dictionary. The claim selector still rejects 3,398 trio API claims as covered.

**Smallest repair**

1. Add one canonical API-surface adapter keyed by ecosystem/schema version.
2. Derive reachability only from repository-verifiable export/public-import evidence.
3. Emit the downstream canonical `classes: list[dict]` shape with bounded members.
4. Change API-claim suppression to require a non-empty accepted canonical API fact for the same semantic surface; otherwise retain bounded corroborated API claims.

**Regressions**

- Use the actual imported files: 3D 327 rows, Note 54, Barcode 146.
- Assert non-empty canonical public type projection for each.
- Assert prompt compacting retains class names and bounded members.
- Assert template API reference consumes the same shape.
- Assert API claims are rejected only when equivalent structured coverage is demonstrated.

**Invalidation**

`FACTS_COLLECTING` onward.

## P0-3 — make knowledge-application evidence post-render and byte-true

**Cause**

The only production write is in `supervisor/product_truth.py` before a document plan exists. The evidence builder scans `document_plan.operations` but not `candidate_content_provenance`.

**Smallest repair**

1. Preserve the fact-stage report as `status: provisional` if useful.
2. After candidate and claim-map creation, rewrite/finalize the report with candidate SHA, plan SHA, claim-map SHA, operation citations, and candidate-content provenance.
3. Record separate counts for prompt-visible, plan-cited, attribution-only, and exact visible spans.
4. Block acceptance if a candidate provenance/claim-map imported fact lacks a final disposition or if an alleged visible influence lacks an exact byte binding.

**Regressions**

- Verified-template compile operation with empty `fact_ids` but non-empty `candidate_content_provenance` produces real spans.
- Agentic operation-cited fact produces a span.
- Prompt-visible but uncited fact produces zero spans.
- Attribution-only SEO produces zero visible spans.
- Final report hashes the exact candidate and becomes stale after a one-byte edit.

**Invalidation**

`CANDIDATE_GENERATED` onward for evidence-only implementation; if acceptance now requires final lineage, re-evaluate all existing accepted candidates.

## P0-4 — fail closed on blocking check skip/error

**Cause**

`run_aspose_checks().valid` considers only returned critical findings. `blocking_aspose_check_findings()` cannot emit a missing/errored check. Document validation therefore accepts a candidate when a blocking check cannot run.

**Smallest repair**

For every name in `load_blocking_check_names()` require exactly one interpretable run outcome. Missing parameters, exception, non-list response, or registry absence becomes a critical infrastructure finding. Keep nonblocking adaptation/diagnostic checks visible but nonblocking.

**Regressions**

- Each of the 11 blocking checks: pass, fail, skipped, exception, malformed return.
- Classification references a nonexistent check: block.
- Report reconciles `run + skipped + errored == registry count` without duplication.

**Invalidation**

`CANDIDATE_GENERATED` validation onward; revalidate all accepted candidates under the repaired check contract.

## P1-1 — separate SEO attribution from authoritative provenance

**Cause**

An unverified `aspose.relevant_seo_keywords` fact can be appended to a capability row’s authoritative `fact_ids` although the row already existed and bytes do not change.

**Smallest repair**

Add a non-authorizing `supporting_fact_ids`/`attribution_fact_ids` channel excluded from claim authorization and visible-influence counts, or verify the keyword fact before allowing it in authoritative lineage.

**Regression**

A matching unverified keyword leaves row bytes and authoritative IDs unchanged, records optional supporting attribution, and compiles a valid claim map.

**Invalidation**

`PLAN_READY` onward.

## P1-2 — make imported-corpus integrity real

**Cause**

The fact contract hashes `knowledge_manifest.json`, not each imported member. Unmanifested byte drift can evade invalidation.

**Smallest repair**

Verify manifest member hashes against disk before fact-cache reuse. Prefer hashing only the selected product bundle plus shared detector data into the scoped fact dependency instead of invalidating all products for unrelated bundle changes.

**Regressions**

- Mutate one selected bundle member without regenerating manifest: fail integrity/reuse.
- Mutate unrelated family bundle: selected product facts remain reusable if scoped dependency design is adopted.
- Regenerated correct manifest restores deterministic key.

**Invalidation**

`FACTS_COLLECTING` for affected product; whole corpus only if aggregate semantics remain.

## P1-3 — add an honest README-only PSD profile

**Cause**

PSD/Python and PSD/.NET are current registry members but absent from imported scope and lack implementation evidence. The loader labels absence non-agent-fixable; product truth blocks.

**Smallest repair**

Create one explicit `repository_profile=readme_only_placeholder` path within the existing fact/acceptance system. Approved facts may cover identity, purpose/status, organization links, contribution/support routes, and repository emptiness. Prohibit installation, API, supported formats, license, performance, and maturity claims without separate evidence.

**Regressions**

- README-only PSD/Python and PSD/.NET generate useful honest candidates.
- Adding code/package metadata automatically exits the placeholder profile and invalidates facts.
- Placeholder candidate cannot contain install commands, API names, format-direction claims, or an unevidenced license.

**Invalidation**

`FACTS_COLLECTING` onward for PSD.

## P1-4 — make imported knowledge a meaningful acceptance dimension

**Cause**

`README_TRUTH_FIELDS` contains no imported-knowledge accountability requirement, so `FACTS_READY` can pass with zero usable imported knowledge.

**Smallest repair**

Do not require arbitrary prose from the corpus. Require instead a typed `knowledge.application_status` summary for every registry product: `applied_visible`, `applied_supporting_only`, `not_applicable`, `missing_required_bundle`, or `blocked_conflict`, with disposition counts and justification. Gate acceptance on an explicit status, not on presence of a marketing sentence.

**Regression**

Trio and PSD cases each resolve to one explicit status; no product silently omits the stage.

**Invalidation**

`FACTS_COLLECTING` onward.

## P2 — Qwen3 Next and GitHub runner execution policy

After P0/P1 closure:

1. Keep deterministic extraction/selection/reconciliation before any provider call.
2. Give Qwen only accepted compact facts, source README, typed preservation dispositions, and exact tool schema.
3. Maximum two author/repair attempts; deterministic validation between attempts.
4. Run one factual and one blind reviewer; factual reviewer must receive every authoritative and supporting fact used by the candidate.
5. Cache by target SHA + selected bundle/member hashes + policy + prompt + template + validator/reviewer contract.
6. Unchanged accepted rerun must make zero provider calls.
7. Use one canary lane, then 2–4 isolated workers; serialize aggregate/cohort writes.
8. Do not run the entire 89-check adaptation backlog on every candidate. Run all applicable checks, but blocking status must never skip/error; preserve full coverage accounting.

## Governed calibration acceptance

The release calibration set is:

- current 3D/Python;
- current Note/Python with stale imported corpus;
- current Barcode/Python with stale corpus/license;
- PSD/Python and PSD/.NET README-only;
- synthetic mixed aggregate;
- synthetic unverified SEO match;
- the three real structured-API schema variants.

Every case must produce a checksum-bound fact graph, exact author packet hash, validated plan, candidate, claim map, final knowledge application, check coverage, factual/blind verdicts, repair history, and unchanged no-op proof. Portfolio scoring must declare its denominator; the supplied evidence does not prove 30/30 clean.
