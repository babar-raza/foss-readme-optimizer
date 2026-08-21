# Implementation Patch Map

Pin `aa998102191c530af4dca3a6895d62a4027a613e`. Every entry names an exact existing module/function
and, where new, the exact new symbol and its insertion point. No file is modified by this design
task itself — this is the map for whoever implements it next.

## 1. `src/readme_agent/errors.py`

Add two typed exceptions, following the existing sparse-subclass convention
(`LLMInfrastructureError(LLMError)` is the precedent, `errors.py:48-49`):

```python
class MergedReviewSchemaError(LLMError):
    """The merged review response was missing/extra top-level facet keys."""

class LLMTruncatedResponseError(LLMError):
    """A forced tool call response was cut off at finish_reason == 'length'."""
    def __init__(self, message: str, *, finish_reason: str, completion_tokens: int | None) -> None:
        super().__init__(message)
        self.finish_reason = finish_reason
        self.completion_tokens = completion_tokens
```

No other new exception types — malformed-non-truncated JSON and transport failures keep using the
existing `LLMError` / `LLMInfrastructureError`, classified by type at the catch site in
`execute_merged_readme_review`.

**Tests:** none directly; exercised transitively by `RED_TEST_PLAN.md` fixtures.

## 2. `src/readme_agent/llm/schema.py`

Add two fields, both optional so every existing constructor call (`LLMResponseMeta()`,
`LLMResponseMeta(request_id=..., ...)`) keeps working unchanged:

```python
class LLMResponseMeta(BaseModel):
    request_id: str | None = None
    created: int | None = None
    model: str | None = None
    usage: Usage | None = None
    finish_reason: str | None = None   # new
    latency_ms: float | None = None    # new
```

**Why here and not a new model:** `AnalysisResult.meta` (`llm/analysis_client.py`) already carries
`LLMResponseMeta` end-to-end into `MergedReviewCallReceiptV1`'s constructor context
(`merged_readme_review.py:181-184`); adding fields here is the only change needed to make
latency/finish_reason available to the new receipt without threading a second object through every
call site.

**Tests:** `tests/unit/test_reviewer_client.py` — add assertions that a successful call populates
both fields.

## 3. `src/readme_agent/llm/verifier_client.py`

In `LiveForcedToolClient.call()` (line 116), wrap `self._request(...)` with
`start = time.monotonic()` / `latency_ms = (time.monotonic() - start) * 1000` and pass it into
`_parse_response`.

In `_parse_response` (line 172-225), read `finish_reason = choices[0].get("finish_reason")` **before**
the `json.loads` call (currently read only inside the `except` branch at line 202). If
`finish_reason == "length"`, raise `LLMTruncatedResponseError` instead of the current bare `LLMError`
(still inside the `except json.JSONDecodeError` branch — truncation that produces invalid JSON is the
common case). Populate `meta.finish_reason` and `meta.latency_ms` on the success path too (so a
syntactically-valid-but-truncated response is still flagged, per `REPORT.md` §6 risk).

```python
finish_reason = choices[0].get("finish_reason")
try:
    arguments = json.loads(function.get("arguments") or "{}")
except json.JSONDecodeError as exc:
    completion_tokens = (body.get("usage") or {}).get("completion_tokens")
    if finish_reason == "length":
        raise LLMTruncatedResponseError(
            f"forced tool call response was truncated: {exc}",
            finish_reason=finish_reason,
            completion_tokens=completion_tokens,
        ) from exc
    raise LLMError(
        "forced tool call arguments were not valid JSON: "
        f"{exc}; finish_reason={finish_reason!r}; completion_tokens={completion_tokens!r}"
    ) from exc
...
meta = LLMResponseMeta(..., finish_reason=finish_reason, latency_ms=latency_ms)
```

**Tests:** `tests/unit/test_verifier_client.py` — new cases for `finish_reason="length"` +
JSON-decode failure raising `LLMTruncatedResponseError` with both attributes populated, and for
`latency_ms`/`finish_reason` present on a normal success response.

## 4. `src/readme_agent/llm/merged_readme_review.py`

Add the pre-flight ceiling guard, co-located with `build_merged_readme_review_messages`:

```python
_MAX_REQUEST_BYTES = 204_800  # 200 KB, REQUEST_OUTPUT_BUDGET.json::request_ceiling

def enforce_merged_review_request_ceiling(messages: list[dict]) -> None:
    size = sum(len(str(m.get("content", "")).encode("utf-8")) for m in messages)
    if size > _MAX_REQUEST_BYTES:
        raise MergedReviewRequestTooLargeError(
            f"merged review request is {size} bytes, exceeds {_MAX_REQUEST_BYTES}-byte ceiling"
        )
```

(`MergedReviewRequestTooLargeError` is a third small addition to `errors.py`, same shape as the two
above — omitted from section 1 for grouping clarity, listed here since it is called only from this
module.)

**Tests:** new `tests/unit/test_merged_readme_review_messages.py` (does not exist today) or added to
the existing prompt-building tests — one case building an oversized synthetic candidate and asserting
`MergedReviewRequestTooLargeError`.

## 5. `src/readme_agent/specialists/merged_readme_review.py` (the core patch)

This is the one behavior-changing module. Current shape: `execute_merged_readme_review`
(lines 52-197). Changes:

1. **New parameter** `factual_fallback_client: AnalysisClientLike | None = None`, symmetric to the
   existing `blind_fallback_client` parameter (line 63).
2. **New leading step** (line 66, before `messages = build_merged_readme_review_messages(...)`):
   call `enforce_merged_review_request_ceiling(messages)` right after building them, before line 74's
   `client.analyze(messages)`.
3. **Wrap the normal call** (currently unguarded line 74):
   ```python
   try:
       analysis = client.analyze(messages)
       if not isinstance(analysis.parsed, dict) or set(analysis.parsed) != {"quality", "factual"}:
           raise MergedReviewSchemaError(
               "merged README review must return exactly quality and factual facets"
           )
   except (LLMTruncatedResponseError, LLMError, LLMInfrastructureError, MergedReviewSchemaError) as exc:
       return _recover_both_facets(exc, ...)  # new helper, see below
   ```
   Note `MergedReviewRequestTooLargeError`/`LLMInfrastructureError`/`LLMTruncatedResponseError` are
   all `LLMError` subclasses so a single `except LLMError` clause catches all four; the classification
   for the receipt's `failure_kind` field is done by `isinstance` inside the handler, not by separate
   `except` clauses (keeps the control flow linear).
4. **Catch the factual grounding failure** (currently uncaught, lines 81-89) with the same
   `try/except GroundedRoleFailure` shape the blind facet already uses at lines 93-104, calling a new
   `_recover_factual_facet` helper (mirrors the existing inline blind-recovery block at lines 104-129,
   extracted so both directions share one shape — see below).
5. **Extract the existing blind-recovery block** (lines 104-129) into a `_recover_blind_facet` helper
   with the same signature shape, so both facets share one `max_attempts_override=2` recovery call
   convention instead of the blind path alone hardcoding its own.
6. **New receipt construction**: after all facets are resolved (normal or recovered), build
   `QwenReviewRecoveryReceiptV1` (new model, see §6) whenever *any* recovery occurred; `None`
   otherwise. Thread it through `MergedReviewExecutionV1` as a new field
   `recovery_receipt: QwenReviewRecoveryReceiptV1 | None`.
7. **Identity note**: recovered facets keep using the existing isolated-fallback identity constants
   (`_BLIND_ACTOR_ID`/`_BLIND_PROMPT_ID` already present at lines 36-37; add symmetric
   `_FACTUAL_ACTOR_ID = "llm-route:factual-readme-plan"` / `_FACTUAL_PROMPT_ID =
   "factual_readme_plan_review"` — the latter already exists as a literal in
   `separated_readme_review.py:51`, reuse that constant rather than re-declaring it). This keeps
   `combine_review_verdicts`'s `separated_identity_valid`/`merged_identity_valid` split
   (`readme_review_reducer.py:81-105`) working unmodified: `merged_call_receipt` becomes `None`
   whenever either facet recovers, exactly as it already does today for blind-only recovery
   (`separated_readme_review.py:228`, `merged_call_receipt = None` in the `explicit_separated` branch
   is the existing precedent for "no merged receipt when identities diverge").

**Tests:** `tests/unit/test_separated_readme_review.py` — see `RED_TEST_PLAN.md` for the full fixture
list. The existing `test_merged_false_missing_premise_fails_closed_without_repeating_call`
(line 1443) must keep passing **unchanged** when `factual_fallback_client` is not supplied (default
`None`) — it documents the zero-fallback-client fail-closed default this design preserves.

## 6. `src/readme_agent/specialists/merged_readme_review_contracts.py`

Add the new receipt model, same frozen-`V1` convention as `MergedReviewCallReceiptV1`
(lines 26-39):

```python
class FacetRecoveryV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    facet: Literal["blind_quality", "factual_plan"]
    triggered: bool
    reason: Literal[
        "request_ceiling_exceeded", "truncated_response", "malformed_arguments",
        "transport_failure", "top_level_schema_failure", "grounding_failure",
    ]
    attempts: int = Field(ge=1, le=2)
    resolved: bool
    token_usage: list[Usage] = Field(default_factory=list)
    latency_ms: list[float] = Field(default_factory=list)


class QwenReviewRecoveryReceiptV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    merged_call_outcome: Literal[
        "success", "request_ceiling_exceeded", "truncated_response", "malformed_arguments",
        "transport_failure", "top_level_schema_failure",
    ]
    blind_facet_recovery: FacetRecoveryV1 | None = None
    factual_facet_recovery: FacetRecoveryV1 | None = None
    final_disposition: Literal["resolved", "resolved_partial", "system_failure", "fail_closed"]
    total_physical_calls: int = Field(ge=1, le=5)
```

`Usage` here is the existing `readme_agent.llm.schema.Usage` (imported, not redefined). No secrets
(requirement 14): the receipt carries only counts, enum labels, and durations — no headers, no raw
provider payloads, matching the existing `MergedReviewCallReceiptV1` pattern of hashes/IDs only.

**Tests:** a construction/validation test asserting `total_physical_calls <= 5` is enforced by the
`Field(le=5)` bound, and that `final_disposition="resolved"` requires both recoveries `None`.

## 7. `src/readme_agent/specialists/readme_review_reducer.py`

Add an optional field to `CombinedReadmeReviewV1` is **not** needed here — the receipt lives on
`MergedReviewExecutionV1` (specialist-internal) and should be surfaced through
`SeparatedReadmeReviewResultV1` instead (below), keeping `CombinedReadmeReviewV1`'s existing
`_review_assurance_and_receipt_are_consistent` validator (`merged_readme_review_contracts.py:56-81`)
untouched — that validator's job is identity/receipt binding, not recovery bookkeeping.

## 8. `src/readme_agent/specialists/readme_review_reducer.py` :: `SeparatedReadmeReviewResultV1`

Add one optional field (line 27-34):

```python
class SeparatedReadmeReviewResultV1(IndependentReadmeReviewResultV1):
    blind_quality_review: RoleReviewRecordV1
    factual_plan_review: RoleReviewRecordV1
    combined_review: CombinedReadmeReviewV1
    grounding_retry_history: list[dict]
    review_recovery_receipt: QwenReviewRecoveryReceiptV1 | None = None  # new
    review_contract_version: str = Field(default="2", frozen=True)
```

`build_compatibility_result` (line 142-175) gains one new parameter threading the receipt through
from `execution.recovery_receipt` (`merged_readme_review.py` §5.6 above). Default `None` — the
`explicit_separated` branch of `run_separated_readme_review` never sets it (no merged call, nothing
to recover), satisfying requirement 10 by construction.

**Tests:** `tests/unit/test_separated_readme_review.py::test_default_merged_client_makes_one_call_and_binds_two_grounded_facets`
gains one assertion: `result.review_recovery_receipt is None` on the clean-success path.

## 9. `src/readme_agent/specialists/separated_readme_review.py` (the wiring fix)

Lines 104-107, currently:

```python
merged_client = build_live_merged_review_client(env.llm_base_url(), env.llm_api_key())
blind_fallback_client = build_live_role_review_clients(
    env.llm_base_url(), env.llm_api_key()
)[0]
```

becomes:

```python
merged_client = build_live_merged_review_client(env.llm_base_url(), env.llm_api_key())
blind_fallback_client, factual_fallback_client = build_live_role_review_clients(
    env.llm_base_url(), env.llm_api_key()
)
```

and the `execute_merged_readme_review(...)` call at line 232 gains
`factual_fallback_client=factual_fallback_client`. This is the single line that today silently
discards the client this whole design exists to use.

Also add the new `factual_fallback_client: AnalysisClientLike | None = None` parameter to
`run_separated_readme_review`'s own signature (line 86-92, alongside `blind_fallback_client`) for
callers (tests, and any future explicit wiring) that want to inject a fake without going through
`env.llm_base_url()`.

**Tests:** `tests/unit/test_separated_readme_review.py` — see `RED_TEST_PLAN.md`.

## 10. Non-interference check (requirement 11) — no code change, a test only

Add one test asserting that a `SYSTEM_FAILURE` verdict produced by exhausted recovery
(`FAIL_CLOSED`/`SYSTEM_FAILURE` terminal states) is never re-labeled `REJECT_REPAIRABLE` by anything
downstream of `run_separated_readme_review`, and that `action_dispatch.py:101`'s
`depth < repair.MAX_REPAIR_ATTEMPTS` check is never invoked as a side effect of a recovery path —
i.e., recovery exhaustion surfaces as the existing `SYSTEM_FAILURE` verdict shape
(`BlindQualityReviewResultV1`/`FactualPlanReviewResultV1`'s existing `SYSTEM_FAILURE` branch,
`readme_review_roles.py:127-133` and `171-172`), which the supervisor already routes differently from
a repairable rejection. No new supervisor code; this is a regression guard on an existing invariant.

## Summary table

| File | Change type | New symbols |
|---|---|---|
| `errors.py` | additive | `MergedReviewSchemaError`, `LLMTruncatedResponseError`, `MergedReviewRequestTooLargeError` |
| `llm/schema.py` | additive | `LLMResponseMeta.finish_reason`, `LLMResponseMeta.latency_ms` |
| `llm/verifier_client.py` | modify | latency timing, `finish_reason` classification |
| `llm/merged_readme_review.py` | additive | `enforce_merged_review_request_ceiling` |
| `specialists/merged_readme_review.py` | modify (core) | `factual_fallback_client` param, guarded call, `_recover_blind_facet`/`_recover_factual_facet`, `recovery_receipt` field |
| `specialists/merged_readme_review_contracts.py` | additive | `FacetRecoveryV1`, `QwenReviewRecoveryReceiptV1` |
| `specialists/readme_review_reducer.py` | additive | `SeparatedReadmeReviewResultV1.review_recovery_receipt` |
| `specialists/separated_readme_review.py` | modify (2 lines + 1 param) | wire `factual_fallback_client` through |
