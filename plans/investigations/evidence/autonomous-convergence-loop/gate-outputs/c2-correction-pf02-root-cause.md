# Correction — the PF-02 root cause I published was not the proximate cause

An independent verification lane refuted the diagnosis recorded earlier in this cycle. It is right,
and I confirmed every step of its evidence directly before accepting it. The earlier diagnosis
stands as a real *contributing* condition but does **not** explain the observed
`candidate_changed: False`, and acting on it alone would have burned another cycle.

## What I published

That two of PF-02's four findings sit in `additional-examples`, which has no authoring slot, so
`_slot()` drops them and `rereview_authorized` — which requires every finding addressed — could
never be satisfied. Therefore the loop could not close.

## Why that is not the proximate cause

**1. `changed_operation_ids: []` was structurally forced, not evidence of an unchanged candidate.**
`planning/readme-document-plan.json` for this repository contains **exactly one** operation:

```
operation count: 1
   readme.verified-template.compile
```

`build_repair_receipt` computes `changed_operation_ids` by diffing operations. With one monolithic
compile operation, that list can only be non-empty if the compiled document changes — it carries no
independent signal about whether the repair did anything.

**2. The repair did run, and the cache key does bind the repair directive.**
Two distinct section-authoring cache entries exist for the same slot, `scope_and_limitations`:
`ab1ea94f8297.json` (canonical) and `e6d5e5b6b642.json` (repair variant). `packet.canonical_hash()`
hashes the whole packet including the mutated `section_objective` and `current_source_text`, so the
repair directive produced its own key rather than silently reusing the canonical one. That
possibility was worth ruling out and is now ruled out.

**3. The author was called and its output was discarded by deterministic acceptance.**
`e6d5e5b6b642.json`:

```json
"outcome.receipt.logical_call_count": 1,
"outcome.receipt.token_usage": [{"prompt_tokens": 6419, "completion_tokens": 139}],
"outcome.receipt.deterministically_rejected_unit_sha256": ["dbafe551…", "36764b99…"],
"outcome.result.units": [],
"outcome.result.omitted": [{"fact_id": "product.limitations:source-guidance",
                            "reason": "Authored unit crossed the deterministic format-rendering boundary."}]
```

Qwen produced 139 completion tokens and two units. The post-call deterministic validator rejected
**both**. `units` came back empty, and by explicit design the deterministic template then owns the
section — so it re-emitted the exact paragraph the reviewer had rejected. The canonical entry
`ab1ea94f8297.json` has the same shape (`units: []`), so `scope_and_limitations` has **never**
carried authored prose in this bundle.

## The actual root cause

**A correctly-routed, correctly-reauthored section still cannot change the candidate when
section-authoring acceptance discards every unit — and the repair loop has no signal for "the author
produced prose and the validator threw it away". It observes only a byte-identical candidate and
reroutes as if nothing had been attempted.**

The failure mode that matters is the missing signal, not the missing slot. `scope_and_limitations`
routed correctly and still went nowhere.

## What this changes

- The `additional-examples` slot gap (`ACL-REVIEW-REPAIR-SCOPE-MISMATCH`) is **still real** and
  still worth fixing — a finding dropped with no record is a genuine defect. But fixing it alone
  would not have unblocked PF-02, and the card must say so or it will be attempted first and
  disappoint.
- A new card is required for the missing signal: the repair receipt should distinguish "author
  produced nothing" / "author produced units that acceptance rejected" from "candidate unchanged",
  and the reroute reason should name which occurred.
- The producer/reviewer conflict on the deterministic `workflow_preview` intro is unchanged and
  independently true.

## Related finding from the same lane, verified

`specialists/review_standard_premises.py::validate_configured_standard_premise` already contains a
guard for exactly this producer/reviewer conflict — the `claims_workflow_preview_is_raw` branch,
which raises `secondary-example intro premise contradicts parsed workflow preview`. It matched
**none** of this run's four findings. The reviewer wrote "First paragraph **is** a raw task list";
the allowlist carries "read**s like** a raw task list". A brittle substring allowlist against
free-form model prose degrades silently to a no-op, and one verb of drift is enough.

## Method note

The refuted diagnosis was published in `logs/2026-08-29.md`, in the plan's card
`ACL-REVIEW-REPAIR-SCOPE-MISMATCH`, and in the reason string recorded on the `L8-PF-02` → `BLOCKED`
transition. All three are corrected. The transition reason is immutable in durable state, so the
correction is recorded here and in the log rather than by rewriting history — the original reason
remains as written, and this artifact is what a later reader must be pointed to.
