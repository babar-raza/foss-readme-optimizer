# Required red tests

Add these tests before implementation. Each must fail on `d71f38b6` for the stated reason and pass only after the bounded repair.

## Transport and fallback

1. `test_truncated_merged_tool_json_falls_back_to_both_isolated_facets_once`
   - Merged client raises the exact response-invalid `LLMError` containing `finish_reason='length'` and `completion_tokens=4000`.
   - One blind and one factual fallback return grounded results.
   - Assert calls are merged=1, blind=1, factual=1; verdict is reduced normally; merged receipt is null; history records `merged_response_invalid` and the failure class.
   - Current failure: the exception escapes before fallback.

2. `test_non_length_malformed_merged_tool_json_uses_same_bounded_fallback`
   - Invalid arguments JSON without `finish_reason=length` must recover identically.
   - Prevent a brittle string match that handles only the observed incident.

3. `test_merged_factual_grounding_failure_falls_back_only_factual`
   - Supply a parsed, grounded quality facet and an ungrounded factual facet.
   - Assert the merged call occurs once, isolated factual occurs once, isolated blind is not called, quality result is retained, and no merged receipt is persisted.
   - Current failure: factual grounding runs first and raises with no factual fallback.

4. `test_merged_quality_grounding_failure_preserves_grounded_factual_facet`
   - Strengthen the existing cross-role quality leakage test: factual result hash before/after fallback must match; only blind fallback may run.

5. `test_infrastructure_timeout_does_not_trigger_semantic_fallback`
   - `LLMInfrastructureError` from the merged transport propagates to SYSTEM_FAILURE and neither role fallback runs.

6. `test_fallback_clients_have_one_transport_and_response_attempt`
   - Capture client construction. Assert `transport_max_attempts=1` and `response_max_attempts=1`; grounding may add only one compact correction call.

7. `test_reviewer_absolute_call_budget_is_five`
   - Force merged response-invalid, then one failed and one successful grounding attempt for each role.
   - Assert exactly five provider attempts and that a sixth attempt fails before transport.

## Output bound

8. `test_merged_tool_schema_has_finite_worst_case_below_4000_tokens`
   - Walk every string and array in both facet schemas.
   - Assert every string has `maxLength`, every array has `maxItems`, findings <=4, reasoning <=600, claim <=300, repair <=400.
   - Construct a maximum-length schema-valid object and assert canonical JSON is below the committed character budget chosen to fit 4,000 Qwen tokens with margin.
   - Current failure: several strings/arrays are unbounded.

9. `test_model_need_not_copy_candidate_span_or_supported_fact_evidence`
   - Model payload supplies `candidate_anchor_id` and selected `fact_id`, omitting/nulling copied span/evidence fields.
   - Existing deterministic bind/reconcile code must materialize exact candidate bytes, evidence location/excerpt, and polarity before persisted Pydantic validation.
   - Assert persisted contract remains unchanged.

10. `test_aggregate_role_fields_are_derived_not_model_authored`
    - Omit `failed_criteria`, `sections_affected`, and top-level `required_repair` from transport output.
    - Assert normalization derives them exactly from findings and verdict.

## Input coverage and budget

11. `test_compact_plan_contains_every_candidate_claim_disposition`
    - For the committed 3D fixture, assert compact claim ledger count equals 112 and every full packet claim ID appears exactly once with fact ID, field, operation, disposition/polarity, and candidate anchor identity.
    - Assert exceptions remain detailed and selected facts referenced by claims are present.
    - Current failure: accountable claims are collapsed to counts by fact.

12. `test_trio_request_budget_and_no_coverage_loss`
    - Build merged messages for sealed 3D, Note, and Barcode fixtures.
    - Assert request bytes <=200,000, all candidate anchors are present once, referenced selected fact IDs are present, all compact claim IDs are present, and no full ProductFacts/document-plan dump is embedded.

13. `test_over_budget_request_fails_before_provider_without_truncation`
    - Candidate/facts above the input ceiling must create zero provider calls and a visible typed SYSTEM_FAILURE containing component byte/token estimates.
    - Never slice anchors, facts, or claims to fit.

## Ledger, cache, and runner behavior

14. `test_fallback_receipt_binds_each_physical_call_and_rejects_fake_merged_receipt`
    - Ledger has one failed merged call plus role calls; role records use their actual prompt identities; combined record has no merged receipt.

15. `test_reviewer_contract_change_invalidates_once_then_zero_call_reuses`
    - Old approval is rejected when prompt/schema/projection hash changes.
    - First repaired run reviews; identical next run reaches the existing no-op shortcut with zero provider calls and no duplicate lifecycle event.

16. `test_real_failure_fixture_recovers_without_relaxing_factual_verdict`
    - Replay the committed 3D truncation fixture with deterministic fake responses.
    - Recovery must not convert malformed output to ACCEPT; both isolated grounded facets must independently pass.

## Acceptance command

Run focused tests first, then the repository's official full-suite wrapper, Ruff, format check, and MyPy. The live qualification is not complete until the sealed trio, PSD/README-only fixture, and largest portfolio README all finish within the budgets, followed by an unchanged zero-call replay.
