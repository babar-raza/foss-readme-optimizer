# Reproduction

Run from the optimizer repository root. All commands are read-only unless explicitly implementing the separate repair.

## Confirm pins and unchanged reviewer path

```bash
git show -s --format='%H %cI %s' d71f38b6
git show -s --format='%H %cI %s' 91d9479
git diff --name-only d71f38b6 91d9479 -- \
  src/readme_agent/llm src/readme_agent/specialists prompts/verification
```

Expected reviewer-path diff: empty.

## Confirm the cap and attempt policy

```bash
git show d71f38b6:src/readme_agent/llm/reviewer_client.py | \
  rg -n 'MERGED_REVIEW_MAX_TOKENS|transport_max_attempts|response_max_attempts'
git show d71f38b6:src/readme_agent/specialists/merged_readme_review.py | \
  rg -n 'client.analyze|factual_result|GroundedRoleFailure|blind_fallback'
```

Expected: 4,000 tokens, one transport attempt, one response attempt; fallback catches only blind `GroundedRoleFailure` after parsing.

## Confirm exact truncation evidence

```bash
git show d71f38b6:plans/status.md | rg -n "finish_reason='length'|completion_tokens=4000"
git show d71f38b6:tests/unit/test_verifier_client.py | sed -n '270,286p'
```

## Read exact historical provider metrics

```bash
for ledger in plans/investigations/evidence/finalized-repository-readmes-v1/repositories/python/*/llm-call-ledger.jsonl; do
  jq -c 'select(.job=="merged_readme_review" and .disposition=="provider_call") |
    {org_repo,prompt_tokens,completion_tokens,latency_ms,outcome}' "$ledger"
done
```

The trio exact rows are reproduced in `BUDGET_MATRIX.json`. The ten-row distribution was computed from those committed integer fields.

## Rebuild prompt sizes

Use the `d71f38b6` source tree and project environment. For each finalized 3D/Note/Barcode directory:

1. Read `README.md`, `ORIGINAL-README.md`, `product-facts.json`, `readme-document-plan.json`, and `claim-map.json`.
2. Build `presentation_plan = {"readme_document_plan": document_plan, "claim_map": claim_map}`.
3. Call `build_factual_review_packet()`; serialize `fact_context()` and `plan_context()` with sorted keys and compact separators.
4. Build the visitor contract from candidate H2 headings and call `build_merged_readme_review_messages()`.
5. Canonically serialize the exact request with model `qwen3-next`, the merged schema, forced function name, temperature `0.0`, and `max_tokens=4000`.
6. Record Python character count and UTF-8 byte count. Label `round(chars/4)` as an estimate, not tokenizer truth.

These steps produced request byte counts 155,647 (3D), 82,190 (Note), and 55,761 (Barcode). Minor differences indicate a different commit, prompt registry root, or fixture.

## Confirm projection behavior

```bash
git show d71f38b6:src/readme_agent/specialists/factual_review_packet.py | sed -n '90,142p'
git show d71f38b6:src/readme_agent/specialists/factual_review_projection.py | sed -n '131,220p'
git show d71f38b6:src/readme_agent/specialists/review_candidate_anchors.py | sed -n '118,175p'
git show d71f38b6:src/readme_agent/specialists/review_role_execution.py | sed -n '263,348p'
```

Observe: full selected facts are projected; accountable claims become counts/coverage; candidate spans and supported evidence are deterministically rebound after model output.

## Confirm Qwen output behavior

```bash
jq '.probes' plans/investigations/evidence/llm-probe/qwen-output-limits-20260818.json
```

Expected: forced named tools 5/5 valid; forced-tool temperature-zero outputs 5 distinct/5; 6,982 tokens succeeds in 135.82 s; 8,000 truncates in 154.29 s.

## Verify this audit bundle

```bash
cd work/owner_audit/qwen_context_budget
sha256sum -c SHA256SUMS
python -m json.tool BUDGET_MATRIX.json >/dev/null
```
