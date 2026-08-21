# RED Test Plan

All new tests target `tests/unit/test_separated_readme_review.py` (extending its existing
`SequenceClient`/`CapturingClient`/`_blind_accept`/`_factual_accept` fixture helpers, lines 1-82) plus
two smaller files for the client/schema layer. Every test below is RED against the current tree at
pin `aa998102191c530af4dca3a6895d62a4027a613e` and is written to go GREEN against
`IMPLEMENTATION_PATCH_MAP.md` without further design changes. None of these tests are written or run
by this design task — this is the plan, not the patch.

Fixture data reuses the module-level `ORG_REPO`, `ORIGINAL`, `CANDIDATE`, `FACTS`, `PLAN` constants
already defined at the top of `test_separated_readme_review.py` (lines 30-58).

## Fixture: `FailingThenClient`

New small fixture, alongside `SequenceClient` (line 71):

```python
class RaisingClient:
    """Raises a fixed exception on every call; used to simulate the normal merged
    call failing before recovery clients ever see a message."""

    def __init__(self, exc: Exception):
        self._exc = exc
        self.messages_seen = []

    def analyze(self, messages):
        self.messages_seen.append(messages)
        raise self._exc
```

## 1. `malformed` fixture

**Test:** `test_merged_malformed_arguments_recovers_both_facets_via_separated_clients`

- `merged = RaisingClient(LLMError("forced tool call arguments were not valid JSON: ..."))`
- `blind_fallback = SequenceClient([_blind_accept("visitor-ready via recovery")])`
- `factual_fallback = SequenceClient([_factual_accept("grounded via recovery")])`
- Call `run_separated_readme_review(..., merged_client=merged, blind_fallback_client=blind_fallback,
  factual_fallback_client=factual_fallback)`.
- Assert: `result.verdict == "ACCEPT"`; `len(merged.messages_seen) == 1`;
  `len(blind_fallback.messages_seen) == 1`; `len(factual_fallback.messages_seen) == 1`; total physical
  calls = 3; `result.review_recovery_receipt.merged_call_outcome == "malformed_arguments"`;
  `result.review_recovery_receipt.blind_facet_recovery.triggered is True`;
  `result.review_recovery_receipt.factual_facet_recovery.triggered is True`.

## 2. `truncation` fixture

**Test:** `test_merged_truncated_response_recovers_both_facets_and_records_finish_reason`

- `merged = RaisingClient(LLMTruncatedResponseError("...", finish_reason="length",
  completion_tokens=4000))`
- Same fallback wiring as above.
- Assert: `result.review_recovery_receipt.merged_call_outcome == "truncated_response"`; both facets
  recovered; total physical calls = 3.
- Companion **client-layer** test in `tests/unit/test_verifier_client.py`:
  `test_forced_tool_call_raises_typed_truncation_error_on_finish_reason_length` — build a fake
  `requests.Response` (existing test file's own response-fixture convention) with
  `finish_reason="length"` and unparseable `arguments`; assert `LLMTruncatedResponseError` raised with
  `.finish_reason == "length"` and `.completion_tokens` populated from `usage.completion_tokens`.

## 3. `factual-failure` fixture (the primary defect this design fixes)

**Test:** `test_merged_factual_grounding_failure_recovers_only_factual_facet`

- `merged = SequenceClient([{"quality": _blind_accept("visitor-ready"), "factual":
  <payload identical to the existing test_merged_false_missing_premise_fails_closed_without_repeating_call
  fixture at line 1443-1461>}])`
- `factual_fallback = SequenceClient([_factual_accept("grounded via recovery")])`
- Call with `merged_client=merged, factual_fallback_client=factual_fallback` (no
  `blind_fallback_client` — blind never fails here, must never be called).
- Assert: `result.verdict == "ACCEPT"`; `len(merged.messages_seen) == 1`;
  `len(factual_fallback.messages_seen) == 1`; total physical calls = 2;
  `result.review_recovery_receipt.blind_facet_recovery is None` (blind was never unresolved, must not
  appear as a triggered-false recovery record either — it's simply absent);
  `result.review_recovery_receipt.factual_facet_recovery.triggered is True`;
  `result.blind_quality_review.identity.prompt_id == "merged_readme_review"` (blind identity
  untouched — still from the merged call);
  `result.factual_plan_review.identity.prompt_id == "factual_readme_plan_review"` (recovered facet
  now carries the separated identity, symmetric to the existing blind-fallback assertion pattern at
  line 1428).
- **Regression guard**: `test_merged_false_missing_premise_fails_closed_without_repeating_call`
  (existing, line 1443) must still pass **unmodified** — it calls
  `run_separated_readme_review(..., merged_client=merged)` with **no** `factual_fallback_client`,
  and must still raise `LLMError` with `len(merged.messages_seen) == 1`. This is the explicit
  backward-compatibility check: recovery is opt-in via the fallback-client parameters, exactly like
  the existing blind-only fallback today.

## 4. `one-facet-only` fixture (symmetric case, blind side)

**Test:** `test_merged_blind_cross_role_leakage_recovery_receipt_records_single_facet`

- Reuses the existing `test_merged_cross_role_quality_leakage_uses_one_isolated_blind_fallback`
  fixture (line 1402) unmodified for the client wiring, adding assertions:
  `result.review_recovery_receipt.blind_facet_recovery.triggered is True`;
  `result.review_recovery_receipt.factual_facet_recovery is None`; `total_physical_calls == 2`.
- This confirms the new receipt doesn't change any existing passing assertion in that test, only adds
  observability to a path that already works today.

## 5. `success` fixture (normal path, receipt absence)

**Test:** extend `test_default_merged_client_makes_one_call_and_binds_two_grounded_facets`
(line 1372, existing) with: `assert result.review_recovery_receipt is None`. No new test needed — one
new assertion on an existing green test, confirming requirement 5/10 (1 call, no receipt) is not
regressed by the new field's default.

## 6. `zero-call-cache` fixture (requirement 10)

**Test:** `test_accepted_unchanged_candidate_makes_zero_provider_calls_and_no_recovery_receipt`

- Location: nearest existing coverage is `supervisor/loop.py`'s own no-op tests (not in this file);
  add this test alongside them, e.g. `tests/unit/test_loop_noop_reuse.py` (verify exact existing
  filename before authoring — the earlier investigation found the check at `loop.py:317-363`,
  `supervise_repo`).
- Fixture: persist a prior `RunStateV2` with `readme_poc_lifecycle.status == "AGENT_APPROVED"` and an
  unchanged candidate hash (existing fixture pattern used by that file's current no-op tests).
- Wrap both `execute_merged_readme_review` and `LiveForcedToolClient.call` with a call-counting spy
  (`unittest.mock.patch`, asserting `call_count == 0`) for the duration of `supervise_repo(...)`.
- Assert: lifecycle transitions straight to `NO_OP_PROVEN`; zero calls to either wrapped function;
  no `QwenReviewRecoveryReceiptV1` is constructed (assert the spy on
  `QwenReviewRecoveryReceiptV1.__init__` — or simpler, assert the persisted state's
  `review_recovery_receipt` field, if present at all in that older state shape, remains whatever it
  already was — this path predates and is untouched by the new field).

## 7. Additional invariant tests (requirement 8, 13, non-interference)

- `test_recovery_calls_receive_identical_candidate_and_facts_as_the_failed_merged_call` — assert
  (via the fixture clients' captured `messages_seen`) that the candidate-anchor catalog and fact IDs
  serialized into the blind/factual recovery messages are byte-for-byte the same as what the merged
  message would have contained (compare against `build_blind_quality_review_messages`/
  `build_factual_plan_review_messages` called directly with the same `blind_input`/`factual_input`
  fixtures).
- `test_oversized_merged_request_skips_normal_call_and_recovers_both_facets` — build a `candidate_text`
  larger than 200 KB (repeat a paragraph), assert `merged.messages_seen == []` (never called) while
  both recovery clients are invoked exactly once each; `merged_call_outcome ==
  "request_ceiling_exceeded"`.
- `test_recovery_exhaustion_surfaces_system_failure_not_reject_repairable` — both fallback clients
  return payloads that fail grounding twice in a row (`max_attempts_override=2` exhausted); assert the
  resulting verdict is `SYSTEM_FAILURE` (not `REJECT_REPAIRABLE`), addressing requirement 11's
  non-interference invariant directly.
- `test_worst_case_five_calls_when_both_facets_need_a_compact_retry` — both fallback clients need one
  ungrounded-then-corrected turn each (existing `SequenceClient` two-item pattern, mirroring
  `test_wrong_quick_start_metric_retries_once_and_preserves_attempt_history` at line 1570); assert
  `total_physical_calls == 5` and both fallback clients see exactly 2 messages each.

## Traceability

| Required fixture | Test(s) |
|---|---|
| malformed | §1 |
| truncation | §2 |
| factual-failure | §3 |
| one-facet-only | §4 |
| success | §5 |
| zero-call-cache | §6 |
