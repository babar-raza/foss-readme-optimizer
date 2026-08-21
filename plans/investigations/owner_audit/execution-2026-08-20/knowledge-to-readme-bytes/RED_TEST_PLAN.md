# Red test plan: K3 + C1

All tests are new unless noted. Location convention follows `AGENTS.md` ("Testing conventions"):
`tests/unit/` offline by default, no `live` marker (everything here is fixture-driven, no network/LLM).

## K3 -- post-render knowledge accountability

**`tests/unit/test_knowledge_application_evidence.py`** (existing file, extend)

1. `test_report_scans_candidate_content_provenance_not_only_operations` -- build a synthetic
   `ReadmeDocumentPlanV1` with one `candidate_content_provenance` entry citing a selected fact_id and
   **zero** `operations[*].fact_ids` referencing it (the verified-template "one compile op, no fact
   ids" shape repair-backlog.md P0-3 names). Assert `rendered_output_spans` contains a span for that
   fact_id. RED today: current code only iterates `document_plan.operations`, this fact_id produces
   no span.
2. `test_final_dispositions_require_omission_reason_for_every_non_rendered_selected_item` -- select 3
   verified items, render 1. Assert the other 2 each have `final_dispositions[i].omission_reason is
   not None`, and that constructing `KnowledgeApplicationV1` with a non-rendered entry and
   `omission_reason=None` raises (pydantic validator, K3-1). RED today: no `final_dispositions` field
   exists.
3. `test_candidate_sha256_binds_report_to_exact_candidate_bytes` -- build a report against candidate
   text A, then rebuild against a one-byte-edited candidate text B with the identical document_plan
   object; assert `candidate_sha256` differs and a stale-report reuse is detectable. RED today: no
   `candidate_sha256` field exists to go stale.
4. `test_incorrectly_reported_influential_detected_on_rebuild` -- construct a stored report claiming
   a span at byte range [x,y) that does not match a fresh rebuild against the actual current
   candidate; assert the rebuild classifies that item `incorrectly_reported_influential` rather than
   silently trusting the stale claim. RED today: no self-consistency rebuild path exists.

**New file `tests/unit/test_idea_candidate_knowledge_application.py`**

5. `test_prepare_idea_fidelity_candidate_calls_report_with_real_document_plan` -- monkeypatch/spy
   `build_knowledge_application_report`; call `prepare_idea_fidelity_candidate` against a fixture
   repo with >=1 selected imported fact; assert the spy was called with `document_plan is not None`
   and the exact `document_plan` object returned by `build_readme_document_candidate` in the same
   call. RED today: `idea_candidate.py` never imports or calls this function at all (confirmed by
   full-src grep, causal-module-tracer subagent).
6. `test_prepare_idea_fidelity_candidate_return_dict_includes_knowledge_application` -- assert
   `result["knowledge_application"]["status"] == "final"` in the returned dict. RED today: key absent.

**`tests/unit/test_local_poc_evidence.py`** (existing file if present, else new)

7. `test_write_local_poc_readme_candidate_writes_final_knowledge_application_second` -- call
   `write_local_poc_readme_candidate` with a `render_result` containing a `knowledge_application`
   entry with `status="final"`; assert `knowledge-application.json` on disk after the call has
   `"status": "final"`, superseding a pre-existing `status="provisional"` file at the same path
   written earlier in the same bundle dir (simulate `product_truth.py`'s existing write first). RED
   today: `write_local_poc_readme_candidate` never calls the knowledge-application writer at all.

**`tests/unit/test_local_poc_acceptance_binding.py`** (existing file, extend)

8. `test_validate_acceptance_artifact_chain_blocks_on_missing_knowledge_application` -- call with
   `knowledge_application=None` (or an `{"error": ...}` dict) against an otherwise fully-passing
   fixture chain; assert the returned error list contains `knowledge_application_error`. RED today:
   parameter does not exist, so a real run with a missing/broken report currently passes this gate.
9. `test_validate_acceptance_artifact_chain_blocks_on_stale_candidate_sha256` -- supply a
   `knowledge_application` whose `candidate_sha256` does not match the fixture's candidate hash;
   assert `knowledge_application_stale` blocks. RED today: no such check exists.
10. `test_validate_acceptance_artifact_chain_blocks_on_missing_omission_reason` -- supply a
    `final_dispositions` entry with `final_state="unverified_supporting_only"` and
    `omission_reason=None`; assert `knowledge_application_missing_omission_reason:*` blocks (the
    defense-in-depth gate-level check, independent of the schema-level validator in test 2). RED
    today: no such check exists.

**`tests/unit/test_local_poc_cache.py`** (existing file, extend, mirrors the Stage 3B tests already
there for `readme_reconciliation`/`check_coverage` at ~L270-305)

11. `test_local_poc_cache_evaluation_threads_knowledge_application_into_acceptance_chain` -- assert
    `_evaluate_local_poc_cache` loads `knowledge-application.json` from the bundle dir and passes it
    to `validate_acceptance_artifact_chain`, following the exact pattern of the existing
    `readme_reconciliation`/`check_coverage` tests at that location.

## C1 -- required proof pair (explicitly requested by the task)

**New file `tests/unit/test_verified_template_capabilities_knowledge_consumer.py`**

12. **`test_accepted_verified_limitation_claim_changes_candidate_bytes`** (the required "accepted
    knowledge changes useful bytes" proof) -- build a minimal `ProductFactsV2` fixture with one
    `aspose.limitation_claims` item: `verification_state="verified"`, `corroboration="corroborated"`,
    text that does **not** duplicate any canonical `product.limitations` entry in the same fixture.
    Render twice: once with the field present, once with it removed from the fixture (all else
    identical). Assert:
    - candidate bytes differ between the two renders;
    - the added text appears verbatim (or via its exact `candidate_content_provenance`/operation
      span) in the "field present" candidate;
    - the owning operation/provenance entry's `fact_ids` contains the item's real `fact_id`;
    - `build_readme_claim_map` accepts the candidate (fact is verified, no conflict);
    - the post-render `knowledge_application.final_dispositions` entry for this fact_id is
      `rendered_with_exact_span` with a non-null `output_span`.
    RED today: candidate bytes are identical in both renders (C1's whole premise -- zero consumers
    for this field, confirmed by `MISSING_CONSUMER_MATRIX.json`).

13. **`test_unsupported_unverified_knowledge_cannot_change_candidate_bytes`** (the required
    "unsupported knowledge cannot change bytes" proof) -- same fixture shape as test 12, but the
    single `aspose.limitation_claims`/`format_support_claims` item has
    `verification_state="unverified"` (or `has_unresolved_conflict=True`). Render twice (field
    present vs. absent). Assert:
    - candidate bytes are **byte-identical** between the two renders;
    - the item never appears in `accepted_composition_fact_ids()`, never in any operation's
      `fact_ids`, never in `candidate_content_provenance`;
    - `knowledge_application.final_dispositions` for this fact_id is
      `unverified_supporting_only` with a non-null `omission_reason`;
    - (regression guard for the K1 sequencing hazard) additionally parametrize this test with a
      **verified-but-stub-body** fixture item (mirroring `CLM-3d-2d3c40`'s real shape: file exists,
      body is `raise NotImplementedError`) and assert C1-2's inline polarity check still produces
      byte-identical output -- this is the test that must exist and pass *before* C1-2 (format
      support/feature) is allowed to ship, per IMPLEMENTATION_SEQUENCE.md's sequencing note.

**New file `tests/unit/test_verified_template_capability_polarity_check.py`** (C1-2 only)

14. `test_format_support_claim_citing_notimplementederror_stub_is_rejected_at_render_time` -- direct
    unit test of C1-2's new polarity-check helper in isolation (not the full render), using a
    synthetic source file whose cited line is `raise NotImplementedError(...)`; assert the helper
    returns rejected/not-corroborated-for-rendering. This is the narrowly-scoped regression KGAP-002
    itself proposes, reused here as C1-2's own gate rather than waiting on the full K1 fix.

## Fixtures required (new, small, synthetic -- no real repository clone needed for 12-14)

- `tests/fixtures/knowledge_claims/single_verified_limitation.json` -- one `ProductFactsV2` fragment.
- `tests/fixtures/knowledge_claims/single_unverified_format_support.json`
- `tests/fixtures/knowledge_claims/single_verified_stub_body_format_support.json` -- paired with a
  tiny synthetic source file containing `def x(): raise NotImplementedError()` at a known line, cited
  by the fixture's `evidence[].file`/`line`.

## Explicitly out of scope for this red-test set (belongs to K1/K2, not K3/C1)

- Full per-item `verified_all` aggregation (K1) -- test 13's stub-body parametrization above covers
  only the narrow C1-2 gate needed to ship safely, not K1's general fix.
- API-surface schema normalization (K2) -- unrelated to knowledge-application accountability or the
  five unconsumed fields.
