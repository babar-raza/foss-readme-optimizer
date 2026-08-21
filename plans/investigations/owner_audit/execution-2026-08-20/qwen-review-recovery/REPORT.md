# OPT-QWEN-REVIEW-RECOVERY-DESIGN

Implementation-ready repair design for Qwen author/reviewer reliability through
`llm.professionalize.com`, scoped to the merged README review call.

- **Pin:** `aa998102191c530af4dca3a6895d62a4027a613e` (verified `git rev-parse HEAD` at design time;
  working tree clean).
- **Mode:** design only. No tracked files modified, nothing committed, no live LLM/Docker/full-suite
  execution. All output confined to
  `runs/owner_audit_staging/qwen-review-recovery-aa9981021/`.
- **Method:** read the real merged-review implementation and its existing tests; no simulation.

## 1. What exists today

The merged-review call is already live and already partially self-healing:

- `src/readme_agent/specialists/merged_readme_review.py::execute_merged_readme_review` makes **one**
  physical call (`client.analyze(messages)`, line 74) and projects its two facets (`quality`,
  `factual`) through the same deterministic grounding pipeline (`run_grounded_role`,
  `review_role_execution.py`) used by the fully separated reviewers.
- `LiveMergedReadmeReviewClient` (`llm/reviewer_client.py:102-127`) is deliberately configured with
  `transport_max_attempts=1, response_max_attempts=1` — the merged call intentionally does **not**
  retry itself, because retrying a large-context call wastes tokens on an already-failed shape. The
  recovery layer this design adds is what that configuration is implicitly waiting for.
- A **blind-quality** fallback already exists: if the blind facet fails grounding
  (`GroundedRoleFailure`), `execute_merged_readme_review` catches it and re-runs blind-quality in
  isolation via `blind_fallback_client` (lines 93-129), recording a `fallback_event` into
  `grounding_history`. Test: `test_merged_cross_role_quality_leakage_uses_one_isolated_blind_fallback`
  (`tests/unit/test_separated_readme_review.py:1402`).
- `normalize_redundant_role_fields` (`review_role_execution.py:57-164`) already derives
  `failed_criteria` / `sections_affected` / `required_repair` / canonical `finding_id`s from
  `findings` deterministically — Qwen is never asked to repeat them. **Requirement 7 is already
  satisfied**; the recovery design must reuse this, not duplicate it.
- Candidate anchors, selected facts, and evidence IDs are recomputed from `candidate_text` /
  `product_facts` on every `run_grounded_role` call (`build_candidate_review_anchors`,
  `factual_review_packet.py`). Because these are recomputed from the *same* parameters passed
  through unchanged, **requirement 8 is satisfied by parameter identity**, not new machinery — the
  patch map's job is to make sure recovery calls receive the identical `candidate_text` /
  `product_facts` / `visitor_contract` the merged call used.
- `MAX_REPAIR_ATTEMPTS = 2` (`src/readme_agent/supervisor/repair.py:31`, enforced
  `action_dispatch.py:101`) already caps candidate-repair cycles. **Requirement 11 requires no new
  cap** — only a non-interference invariant (recovery must never manufacture a spurious
  `REJECT_REPAIRABLE` that consumes this budget).
- The 3,000 / 6,000 output-token budgets requirement 3 asks for **already exist** as
  `BLIND_REVIEW_MAX_TOKENS = 3_000` and `FACTUAL_REVIEW_MAX_TOKENS = 6_000`
  (`llm/reviewer_client.py:18-19`), applied by `build_live_role_review_clients`
  (`reviewer_client.py:169-193`). The 90s per-call timeout (requirement 12) is already the default
  on every `Live*ReviewClient` constructor. **No new constants needed for either.**
- The factual fallback client is **already constructed and silently discarded**:
  `separated_readme_review.py:104-107` calls
  `build_live_role_review_clients(...)` and takes only `[0]` (blind), throwing away `[1]` (factual).
  This is the sharpest gap in the whole design — the fix is a one-line change plus a new parameter
  threaded through, not new client machinery.

## 2. The actual gap

`execute_merged_readme_review` wraps **nothing** around the single `client.analyze(messages)` call
at line 74, and only catches `GroundedRoleFailure` for the blind facet afterward. Concretely, today:

| Failure | Where it currently surfaces | Current recovery |
|---|---|---|
| `finish_reason=length` (truncation) | Buried inside a string message from `_parse_response` (`verifier_client.py:199-208`); no structured signal | None — propagates as a bare `LLMError`, kills the whole review |
| Malformed tool arguments | `LLMError` from `_parse_response` JSON decode, or pydantic `ValidationError` inside `_parse_role_result` | None for the top-level `client.analyze()` call; partial (blind only) once past it |
| Top-level schema failure (`quality`/`factual` keys missing) | `merged_readme_review.py:75-76`, raised directly | **None** — always fatal, single physical call already spent |
| Transport failure | `LLMInfrastructureError` from `verifier_client.py:_request` (`transport_max_attempts=1`, so no gateway-level retry either) | None |
| Factual grounding failure | `GroundedRoleFailure` from `run_grounded_role(..., max_attempts_override=1)` for the factual facet (`merged_readme_review.py:81-89`) | **None** — uncaught, unlike the symmetric blind-quality path a few lines below |

This design closes all five gaps with one recovery dispatcher, reusing every existing typed
contract, grounding retry loop, and budget constant instead of inventing parallel ones.

## 3. Design summary

1. **Pre-flight request-ceiling guard** (new, requirement 13): before the normal merged call, size
   the assembled messages. If they exceed 200 KB / ~60,000 estimated input tokens, skip the merged
   call entirely (0 normal calls spent on a request already known to be doomed) and go straight to
   two-facet recovery.
2. **Normal call, now guarded**: wrap `client.analyze(messages)` in a `try/except` that classifies
   the failure into one of: `success`, `truncated_response` (new typed error), `malformed_arguments`
   (existing `LLMError`), `transport_failure` (existing `LLMInfrastructureError`),
   `top_level_schema_failure` (existing check, now a typed `MergedReviewSchemaError`),
   `blind_grounding_failure` / `factual_grounding_failure` (existing `GroundedRoleFailure`, now
   caught symmetrically for both facets).
3. **Facet-scoped recovery dispatch**: a new `_recover_unresolved_facets` step decides, from the
   classification, which of `{blind, factual}` are *unresolved* (both, for anything before facet
   parsing; exactly one, for a single `GroundedRoleFailure`) and calls only the matching separated
   client(s) — `build_live_role_review_clients()`, both halves now wired through.
4. **Bounded recovery grounding**: every recovery-path `run_grounded_role` call passes
   `max_attempts_override=2` (1 initial + 1 compact grounding retry) regardless of role, capping the
   physical-call arithmetic below.
5. **Typed receipt** (new `QwenReviewRecoveryReceiptV1`): records the merged-call outcome, which
   facet(s) recovered and why, each attempt's token usage and latency, and the final disposition.
   Persisted alongside the existing `MergedReviewCallReceiptV1` — `None` whenever the merged call
   succeeded outright (no recovery attempted), so the existing zero-provider-call no-op reuse path
   (`loop.py:317-363`) is untouched and never produces one.

### Call-count arithmetic (requirements 5, 6)

| Scenario | Calls | Why |
|---|---|---|
| Merged call succeeds, both facets ground cleanly | **1** | Normal path, unchanged |
| Pre-flight ceiling trips | up to **4** | 0 (merged skipped) + up to 2 (blind: initial + compact retry) + up to 2 (factual: initial + compact retry) → really capped at 4, tighter than the worst case below |
| One facet ungrounded (e.g. only factual) | up to **3** | 1 (merged) + up to 2 (factual recovery, `max_attempts_override=2`) |
| Both facets unresolved (top-level schema / transport / truncation / malformed args) | up to **5** | 1 (merged, failed) + up to 2 (blind recovery) + up to 2 (factual recovery) |
| Accepted, unchanged candidate rerun | **0** | Never reaches `execute_merged_readme_review`; short-circuited by the existing `AGENT_APPROVED → NO_OP_PROVEN` promotion (`loop.py:317-363`) |

Worst case is exactly **5**, matching requirement 6. Normal-path maximum is exactly **1**, matching
requirement 5. No scenario repeats an *unchanged* full merged request (requirement 4/10): recovery
always uses the smaller, role-scoped separated prompts, never the merged prompt again.

## 4. Requirements traceability

| # | Requirement | Satisfied by |
|---|---|---|
| 1 | Preserve single merged call | Unchanged `client.analyze(messages)` call site; only wrapped, not replaced |
| 2 | Detect 5 failure modes | New `LLMTruncatedResponseError`, `MergedReviewSchemaError`; existing `LLMError`, `LLMInfrastructureError`, `GroundedRoleFailure` reused and now all caught |
| 3 | 3,000 / 6,000 token budgets | Already `BLIND_REVIEW_MAX_TOKENS`/`FACTUAL_REVIEW_MAX_TOKENS` — recovery reuses `build_live_role_review_clients()` unchanged |
| 4 | Recover only unresolved facets | New `_recover_unresolved_facets` dispatch keyed on failure classification |
| 5 | Max 1 normal call | Unchanged call site; ceiling guard skips rather than repeats it |
| 6 | Max 5 worst-case calls | `max_attempts_override=2` on every recovery-path `run_grounded_role` call — see arithmetic above |
| 7 | Materialize redundant fields deterministically | Already `normalize_redundant_role_fields` — reused unchanged |
| 8 | Preserve anchors/facts/claims/evidence IDs | Recovery calls receive identical `candidate_text`/`product_facts`/`visitor_contract` params — preserved by construction, verified by a new invariant test |
| 9 | Typed receipt (failure, recovery, tokens, latency, disposition) | New `QwenReviewRecoveryReceiptV1`; new `latency_ms` field on `LLMResponseMeta` |
| 10 | Zero calls on accepted unchanged rerun | Already true (`loop.py:317-363`); new receipt is `None` on that path by construction, verified by a non-regression test |
| 11 | Max 2 targeted candidate repairs | Already `MAX_REPAIR_ATTEMPTS = 2`; design adds a non-interference invariant only |
| 12 | 90s per-call timeout | Already the default on every `Live*ReviewClient` |
| 13 | 200 KB / ~60k input tokens | New pre-flight `enforce_merged_review_request_ceiling` guard |
| 14 | No secrets in logs/evidence | Receipt carries hashes (`sha256`) and provider `request_id`/`model` only, matching the existing `MergedReviewCallReceiptV1` pattern — no header/API-key fields anywhere in scope |

## 5. Non-goals / explicitly out of scope

- No change to the separated-review path (`explicit_separated=True` branch of
  `run_separated_readme_review`) — it already has no merged call to recover.
- No change to `MAX_REPAIR_ATTEMPTS` or the supervisor repair loop's own logic.
- No new feature flag or config toggle: recovery activates purely on the presence of
  `blind_fallback_client`/`factual_fallback_client`, exactly like the existing blind-only fallback
  today — same opt-in shape, now symmetric.
- Stage 5 / Docker-unavailable failures (`plans/master.md` Changelog, 2026-08-20) are a **different**
  failure domain (container-registry acquisition during `FACTS_COLLECTING`) and are not addressed by
  this design; they were investigated only to confirm they're unrelated.

## 6. Risks / open questions

- `_recover_unresolved_facets` must not let a recovered facet's `RoleReviewRecordV1.identity` collide
  with the merged identity in a way `combine_review_verdicts`'s `merged_identity_valid`/
  `separated_identity_valid` checks (`readme_review_reducer.py:81-105`) reject as neither shape —
  the patch map below routes each recovered facet through the *same* isolated-fallback identity
  shape the existing blind fallback already uses (`_BLIND_ACTOR_ID`/`_BLIND_PROMPT_ID`, and a new
  symmetric `_FACTUAL_ACTOR_ID`/`_FACTUAL_PROMPT_ID` for factual), so `merged_call_receipt` becomes
  `None` whenever *either* facet recovers — consistent with today's blind-only behavior.
- The 200 KB / ~60k-token pre-flight ceiling is a heuristic (chars/4 token estimate); it should be
  calibrated against real request sizes once live traffic is available — flagged in
  `IMPLEMENTATION_PATCH_MAP.md`.
- `finish_reason` is not currently exposed on successful (non-erroring) responses either; this design
  adds it to `LLMResponseMeta` for *all* responses so a syntactically-valid-but-truncated response
  (rare, but possible if truncation lands exactly on a valid close-brace) can still be flagged in the
  receipt even though it didn't raise.

## 7. Rollout

Implementation-ready but not implemented. Suggested sequencing for whoever picks this up:
1. Schema/exception additions (`llm/schema.py`, `errors.py`) — additive, zero call-site risk.
2. `verifier_client.py` `finish_reason`/`latency_ms` capture — additive.
3. Pre-flight ceiling guard — additive, new function, opt-in call site.
4. `execute_merged_readme_review` recovery dispatcher + `factual_fallback_client` wiring — the one
   behavior-changing patch; every RED test in `RED_TEST_PLAN.md` targets this.
5. `separated_readme_review.py` two-line wiring fix (stop discarding `[1]`).
6. Receipt persistence wiring into `CombinedReadmeReviewV1`.

See `IMPLEMENTATION_PATCH_MAP.md` for exact functions, `RED_TEST_PLAN.md` for fixtures and test
names, `FAILURE_STATE_MACHINE.json` for the full transition table, `REQUEST_OUTPUT_BUDGET.json` for
every numeric ceiling, and `RUNNER_COST_MODEL.json` for the 33-repository wall-time estimate.
