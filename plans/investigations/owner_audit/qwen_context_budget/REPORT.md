# Qwen3 Next context and reviewer budget audit

## Verdict

The optimizer is not blocked by Qwen3 Next's input context on the committed Python evidence set. It is blocked by an output contract that can expand beyond its fixed 4,000-token merged-review cap and by an incomplete recovery path.

At control commit `d71f38b6a050b5282f0ada314f9ee4de35950426`, a merged review uses exactly one transport attempt and one response attempt (`reviewer_client.py`, `MERGED_REVIEW_MAX_TOKENS = 4_000`). The current portfolio status records a real 3D failure at exactly 4,000 completion tokens with `finish_reason='length'` and unterminated tool JSON. `execute_merged_readme_review()` can fall back only after a *parsed quality facet* fails deterministic grounding. A malformed/truncated merged response raises before either facet is available; a factual grounding failure is evaluated first and also has no fallback.

This is a narrow repair. Keep the merged client, existing role clients, fact/plan projections, candidate anchors, grounding validators, hashes, reducer, repair loop, ledger, and no-op cache. Bound the existing output schema, deterministically materialize fields the runtime already owns, and use the already-existing separated role clients only for facets not safely recovered from the merged call.

## Scope and pins

- Audited implementation: `d71f38b6a050b5282f0ada314f9ee4de35950426`.
- Latest GitHub tip observed at completion: `91d9479b1e1fa12a9af41c1692b6f8f421db5f76`.
- `git diff d71f38b6..91d9479 -- src/readme_agent/llm src/readme_agent/specialists prompts/verification` is empty. Later commits therefore do not change these reviewer-budget findings.
- Historical exact token/latency evidence: committed `finalized-repository-readmes-v1` ledgers and the committed real-corpus failure/probe artifacts. Prompt content is not stored in ledgers; reconstructed byte counts use the exact `d71f38b6` production builders and committed candidate/fact/plan artifacts.
- Token estimates are explicitly `characters / 4`; provider-reported token counts are labeled exact. The exact trio measurements show Qwen tokenization here costs about 3.1-3.2 characters/token, so `chars/4` is optimistic.

## Measured trio

| Candidate | Merged request bytes | Message bytes | `chars/4` estimate | Exact historical prompt tokens | Completion | Latency |
|---|---:|---:|---:|---:|---:|---:|
| 3D Python | 155,647 | 146,382 | 38,902 | 47,022 | 1,485 | 33.740 s |
| Note Python | 82,190 | 72,939 | 20,535 | 25,401 | 1,165 | 24.903 s |
| Barcode Python | 55,761 | 48,128 | 13,939 | 17,690 | 1,743 | 32.696 s |

Across all ten committed successful Python merged-review ledgers: prompt tokens were 14,296-47,213 (median 25,353.5), completions 1,128-2,247 (median 1,470), and latency 24.903-46.649 s (median 30.221 s). Those successes do not prove determinism: the committed Qwen probe produced five distinct forced-tool outputs from five identical temperature-zero requests.

### Payload decomposition

| Component | 3D bytes | Note bytes | Barcode bytes | Keep? |
|---|---:|---:|---:|---|
| Candidate anchor catalog | 80,399 | 30,580 | 20,992 | Yes, complete visible-document coverage |
| Selected referenced fact context | 55,573 | 32,769 | 17,462 | Yes, fact/evidence/polarity/conflict authority |
| Compact plan context | 4,351 | 3,505 | 3,605 | Yes, operations, non-preserve sections, exceptions, hashes |
| Visitor contract | 2,765 | 2,787 | 2,765 | Yes, quality authority |
| Mechanical observations | 763 | 763 | 763 | Yes, parser-owned premises |
| Merged tool schema | 4,706 chars | same | same | Reduce redundant output fields |

The existing projections already do the important bulk reduction. For 3D, canonical full ProductFacts + document plan are about 2.06 MB; the LLM receives about 59.9 KB of fact + plan context. Replacing the projection with full artifacts would be a severe regression.

The anchor catalog is not duplicate candidate content in the merged request; it is the only complete candidate representation. The separated factual prompt, by contrast, includes both the full candidate and its anchor catalog. Reconstructed 3D requests are 99,931 bytes for blind plus 227,118 bytes for factual, versus 155,647 bytes merged. Therefore separated review is a recovery path, not the default.

## Material coverage that cannot be dropped

Keep all of the following:

1. Every candidate block anchor, in source order. Quality and unsupported-claim detection need complete candidate visibility.
2. Every selected fact referenced by an operation, source section, surface action, or candidate claim, including verification state, accepted evidence polarity, location, and unresolved conflicts.
3. Every exception/non-accountable candidate claim. Dropping these would hide the exact claims most likely to require a block.
4. Per-fact claim coverage counts and section IDs; full-artifact hashes; all non-preserve source-section dispositions; all operations and their fact IDs.
5. Deterministic validation before review. The LLM is not a substitute for complete claim-accountability validation.

One accuracy gap should be repaired within the existing `factual_review_projection.py`: the prompt says candidate claims are prebound in the compact packet, but `compact_plan_context()` retains detailed records only for exception claims and reduces all accountable claims to counts by fact. A smallest complete projection should add a bounded per-claim ledger using existing claim IDs/fact IDs/fields/operation IDs and candidate-anchor identity (or exact short claim text). Do not send the 611 KB 3D full claim records. Measured alternatives are 38,719 chars for 3D without claim text or 53,621 chars with it; the no-text form plus anchor identity is the better budget.

## Dead or duplicated output material

The model currently has to repeat data that deterministic code already derives:

- `quoted_candidate_span` is overwritten from `candidate_anchor_id` by `bind_candidate_review_anchors()`.
- For supported selected factual findings, evidence excerpt, location, expected polarity, observed polarity, and `polarity_result` are overwritten by `_reconcile_supported_factual_evidence()`.
- `failed_criteria`, `sections_affected`, and top-level `required_repair` are recomputed from findings by `normalize_redundant_role_fields()`.
- Free-form reasoning is diagnostic; structured findings control lifecycle state.

The schema still requires these fields. Although merged findings are capped at four per facet, several strings/arrays remain unbounded and each finding permits a 1,200-character copied quote plus a 700-character repair. The contract therefore has no finite worst-case output size below 4,000 tokens.

## Smallest bounded repair plan

1. **Compact the existing shared role schema.** Require verdict and structured findings. Keep at most four findings/facet. Limit reasoning to 600 characters, claim to 300, repair to 400, identifiers/sections to their current small bounds, and every array to four entries. Make copied span and supported-evidence fields optional/null in the transport schema, then materialize them with the existing anchor/evidence reconcilers before Pydantic validation and persistence. Keep the persisted role contracts unchanged.
2. **Retain one merged attempt.** `max_tokens=4_000`, `transport_max_attempts=1`, `response_max_attempts=1`, 90-second timeout. Do not retry an unchanged truncated request.
3. **Fallback by unresolved facet.** On response-invalid `LLMError` (invalid JSON, missing tool call, wrong function, wrong top-level facets) run both existing isolated roles. On factual grounding failure, reuse the parsed/grounded quality result if available and run only factual isolated review. On quality grounding failure, preserve the already-grounded factual result and use the existing blind fallback. Infrastructure/auth/timeouts remain fail-closed; they do not silently fan out.
4. **Bound fallback clients.** One transport/response attempt per role call, plus at most one existing compact grounding correction for that facet. Maximum reviewer calls: normal 1; malformed merged recovery 3 without grounding correction; absolute bounded worst case 5. Record the merged failure and each fallback call in the existing call ledger and persist no merged receipt when facets came from different calls.
5. **Add compact per-claim accountability.** Extend the existing plan projection; do not create a parallel packet or reviewer architecture.
6. **Requalify on sealed fixtures.** 3D, Note, Barcode, PSD/README-only, and the largest current README. Promotion requires no truncation, complete factual coverage, grounded findings, exact call accounting, and a zero-call unchanged rerun.

## Stage budgets for GitHub runners

| Stage | Normal ceiling | Recovery ceiling | Failure behavior |
|---|---:|---:|---|
| Merged input | 200 KB request and 60,000 provider prompt tokens | none | fail visibly before provider if exceeded; record component sizes |
| Merged output | 4,000 tokens, 1 call, 90 s | none | classify response-invalid vs infrastructure |
| Blind fallback | 3,000 tokens, 1 call, 90 s | 1 compact grounding correction | grounded result or SYSTEM_FAILURE |
| Factual fallback | 6,000 tokens, 1 call, 90 s | 1 compact grounding correction | grounded result or SYSTEM_FAILURE |
| Reviewer total | 1 provider call normally | maximum 5 calls / 360 s review wall | no further same-input retry |
| Unchanged accepted rerun | 0 provider calls | none | reuse only if all existing dependency/hash/semantic checks pass |

The 200 KB/60k input limit covers the committed trio with headroom and should be measured, not guessed, for the portfolio maximum. It does not authorize truncating anchors or facts. An over-budget request must remain a visible system failure until the existing projection is made smaller without losing coverage.

## Cache and repeatability

The accepted-bundle/no-op machinery is already the right resource control. Committed proofs bind source revision, facts, prompts, template, reviewer standard, control plane, semantic verdict/no-op, and artifact checksums and show zero new provider calls on unchanged reuse. Any prompt, schema, projection, or fallback change must change the existing reviewer-standard/dependency hashes, intentionally invalidating stale approvals once. After reapproval, identical reruns should again be zero-call.

Temperature zero is not byte deterministic for Qwen forced-tool output. Repeatability must therefore mean deterministic inputs, bounded attempts, deterministic grounding/materialization/reduction, content-addressed evidence, and cached accepted outcomes—not identical raw model bytes.

## Production decision

Do not raise the merged cap alone. The probe showed 6,982-token free-form output can succeed but took 135.82 seconds, while 8,000 tokens truncated at 154.29 seconds; the current merged client times out at 90 seconds. Compacting the output contract and adding facet-aware fallback is both faster and safer than paying for a larger unbounded answer.
