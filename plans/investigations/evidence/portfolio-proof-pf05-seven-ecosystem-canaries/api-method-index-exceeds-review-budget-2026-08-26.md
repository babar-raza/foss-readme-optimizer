# PF05-APIREF-SCALE-001 — a genuinely large, non-duplicated API surface exceeds the bounded-review packet budget

## Status

Root-caused. Not repaired: the correct fix is a scale/curation policy change to
a document-contract-bound presentation module, which needs deliberate
product-level thought about what stays visible, not a quick patch.

## Symptom

`aspose-3d-foss/Aspose.3D-FOSS-for-.NET` blocks:

```
RuntimeError: bounded review is structurally blocked:
('unpacketizable-oversized-factual-unit-0048-table',)
```

## What is different from the earlier, already-fixed API-index bug

`604983413` (this session) fixed inherited members being restated on every
subclass -- confirmed *not* the cause here: the fresh candidate has **zero**
inherited rows in its API Method Index. This repository's surface is
genuinely large without duplication: 1079 distinct rows, 123,712 characters,
in one `## API Method Index` section -- larger than the entire rest of the
158,474-character candidate combined.

## Root cause

`bounded_review_structure.py::_build_raw_units()` treats one contiguous
Markdown table (header row through the last consecutive `| ... |` row) as one
indivisible atomic unit -- a deliberate design choice, not a bug: splitting a
table mid-row would break the coherence a reviewer needs to verify a claim
against its row. `_greedy_group_units()` therefore can never place this table
in any packet, because a single unit larger than the whole budget (120,000
characters, `bounded_review_contracts.DEFAULT_BOUNDED_PACKET_BUDGET_CHARS`)
cannot fit even alone.

The budget itself is not a safe lever: it has no scale-justifying comment, but
120,000 characters (~30-40k tokens at typical English density) lines up with
headroom under the LLM gateway's real usable context ceiling (recorded
elsewhere: ~71k tokens for qwen3-next, well before prompt/schema overhead).
Raising it risks trading a controlled, deterministic rejection for a live
provider context-overflow failure -- a worse outcome, not a better one.

## Correct repair direction

idea.md's own language already anticipates this: "top APIs" (not every API)
stay visible, and "long API inventories may be collapsed without dropping,
rewriting, or approving inherited content." The API Method Index producer
(`presentation/verified_template_api_method_index.py`) should apply a
scale-appropriate cap -- a bounded top-N set of members, with the remainder
still reachable via the existing "complete API reference under Documentation &
Resources" pointer the template already promises -- rather than emitting every
verified member unconditionally. That is a genuine curation-policy decision
(what counts as "top"), not a size-only truncation, and needs product-level
judgment about the cutoff.

## Why it was not fixed here

The correct fix touches `presentation/verified_template_api_method_index.py`,
which matches the document contract's `presentation/verified_*.py` glob, so
editing it invalidates every cached composition plan portfolio-wide. It also
requires a real curation decision (what "top" means, how large a cap), not a
mechanical patch, and a fleet pass was in flight when this was found.
