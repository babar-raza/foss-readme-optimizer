# REPORT — standalone bounded-review packetizer

## What this is

A single, standalone, provider-free module —
`src/readme_agent/specialists/bounded_review_packets.py` — that plans deterministic, bounded
review packets for a README candidate too large to review safely in one call, validates
packet-scoped reviewer results, reduces them to one fail-closed aggregate verdict, and routes
narrow repair targets. It performs **zero** provider/LLM/network calls. It is **not** registered
in any specialist registry and is **not** wired into any existing review orchestration — Codex
remains the sole integration authority, per the task's explicit instructions.

Companion test suite: `tests/unit/test_bounded_review_packets.py` (26 tests), against a synthetic
~162KB candidate fixture at `tests/fixtures/bounded_review_packets/candidate.md`.

## Why this exists (root-cause analysis, from the design plan)

Large README candidates (the committed real proof candidate at
`plans/investigations/evidence/qwen-section-engine-integration/candidate.md` is 163,049 bytes)
sometimes fail or look inconsistent across review reruns. Three independent causes:

1. **Size.** The existing factual/visitor reviewers send the whole candidate plus the whole fact
   corpus in one call, against a *measured* ceiling
   (`plans/investigations/owner_audit/qwen_context_budget/REPORT.md`: ~200KB / ~60k input tokens,
   a 4,000-token output cap, with truncation observed exactly at that output cap). No prompt
   tuning fixes an oversized payload — it is architectural.
2. **Per-call nondeterminism, independent of size.** This provider's tool-call arguments are
   nondeterministic even at temperature 0 (`qwen3-next-identity` memory / prior investigation).
   Splitting one call into N packets means N independent rolls, not N deterministic
   sub-problems — a packetizer that ignores this "fixes" the size symptom while leaving, or
   worsening, the consistency symptom (more independent calls means more chances for
   cross-packet disagreement).
3. **Signal dilution.** Sending the full fact corpus with every claim increases hallucination
   surface area independent of raw byte count.

A fourth, **self-inflicted** failure mode is the one this module exists specifically to rule
out: a packetizer whose own planning layer is accidentally nondeterministic (unsorted
collections, Python's randomized `hash()`, trusting caller-supplied array order, an algorithm
change that doesn't reflect in content hashes) would add a *third* failure mode on top of the
first two — and this one would be fully within this module's control to prevent. See "Real bugs
found and fixed" below: two genuine instances of exactly this failure mode were caught by the
test suite during development and fixed before commit.

## What this module can and cannot fix (stated honestly, not oversold)

**Can:** eliminate size-driven truncation failures by construction (bounded packets); shrink
signal dilution (per-packet minimal fact payloads, reusing the codebase's own
`composition_fact_payloads` compaction); make its own layer 100% reproducible; make result
*validation* structural (hash/span/fact-ID containment) rather than text-based, so it is robust
to LLM prose varying run to run; fail closed by distinguishing "waiting on more calls"
(`INCOMPLETE`) from "structurally unreviewable" (`BLOCKED`) so a caller doesn't retry-loop
against an unresolvable state.

**Cannot:** make the underlying LLM deterministic, or guarantee overlapping packets never
disagree. Cross-packet conflict is handled by failing closed and narrowing the repair target
(`CONFLICT` aggregate state), not by eliminating the possibility — this is an honest limit, not
a claim this module secretly resolves.

## The six redesign points and where each landed

1. **Canonical-hash discipline as a hard implementation rule.** `_canonical_hash()` (sorted-key
   JSON sha256) is the module's only hashing primitive, and every collection fed into it is
   sorted by an explicit key first — never bare `set`/`dict` iteration order, never
   `PYTHONHASHSEED`-sensitive. Proven by `test_deterministic_across_two_independent_runs` and
   `test_shuffled_input_order_invariance`.
2. **Input normalization at the planning boundary.** `_valid_claims_and_gaps()` /
   `_valid_provenance_and_gaps()` sort claims by `(source_byte_start, claim_id)` and provenance
   by `(candidate_byte_start, provenance_id)` before anything is derived from them, regardless of
   caller-supplied array order. Proven by `test_shuffled_input_order_invariance` (claims,
   provenance, and `do_not_claim` all reversed → byte-identical `canonical_json(plan)`).
3. **`_ALGORITHM_CONTRACT_VERSION` folded into `packet_sha256` itself.** `_packet_sha256()`
   unconditionally adds it to the hashed payload (not only into the separate cache-key wrapper),
   so a future packetization-algorithm change cannot silently reuse a content-identical-looking
   cached result produced under different semantics. Proven by
   `test_algorithm_contract_version_change_changes_every_packet_sha256`.
4. **Two distinct kinds of "bad input."** A candidate/facts/plan hash mismatch raises
   `BoundedReviewInputMismatchError` at construction time (`test_contract_violation_raises_on_hash_mismatch`,
   `test_plan_raises_on_mismatched_candidate_facts_plan_triple`). A claim's or
   provenance entry's unresolvable `accepted_fact_ids`/`fact_ids` reference becomes an
   `UnpacketizableRecordV1(reason="unresolved_fact_reference")` for that one record —
   the plan still returns successfully (`test_referential_gap_is_localized_not_a_crash`).
5. **`BLOCKED` distinct from `INCOMPLETE`.** `aggregate_packet_results()` checks blocking-gap
   status *first*, before any packet-presence/validity check — `BLOCKED` even when every present
   packet result is ACCEPT (`test_blocked_differs_from_incomplete_and_routes_deterministic_remediation`).
   `route_selective_repairs()` sets `requires_deterministic_remediation=True` and
   draws targets from `plan.unpacketizable` (not from reviewer output) exactly when
   `aggregate.overall == "BLOCKED"` — this is the operational payoff: it tells a caller that more
   LLM calls will not help. `INCOMPLETE` (missing/invalid packet result, safe to retry) is a
   genuinely different, separately tested path
   (`test_missing_packet_result_yields_incomplete_never_accept`).
6. **Packet-level result envelope mirrors the existing cross-field validators.**
   `BoundedPacketResultV1._verdict_payload()` reimplements
   `FactualPlanReviewResultV1._verdict_payload()`'s rules field-for-field (ACCEPT requires a
   `supports_acceptance` finding, `BLOCKED_*` requires a `blocks` finding, etc.), plus the
   facet-appropriate `kind`/`criterion` restriction mirroring `BlindQualityReviewResultV1`.
   `test_inconsistent_envelope_rejected_by_own_validator` proves a shape violation (ACCEPT with
   only a `blocks` finding) is rejected by pydantic at construction, never reaching aggregation.

## Real bugs found and fixed while writing the tests

Two genuine determinism/cache-identity bugs were caught by the required tests during
development — recorded here in full because catching and fixing them is the actual point of a
redesign pass like this one, not a footnote:

1. **`plan_hash` was not order-invariant.** The first implementation folded the *existing*,
   reused `ReadmeClaimAccountabilityMapV1.canonical_hash()` directly into `plan_hash`. That
   method's `sort_keys=True` only sorts dict keys — it does not reorder the `claims` list. Caught
   by `test_shuffled_input_order_invariance`; fixed with
   `_order_invariant_claim_accountability_hash()`, which sorts each claim's dumped payload by
   `(source_byte_start, claim_id)` before hashing.
2. **`packet_sha256` embedded whole-document `candidate_sha256` and absolute position, both of
   which defeated selective invalidation.** The first implementation hashed the packet's own
   absolute `char_start`/`char_end`/`line_start`/`line_end` plus the whole document's
   `candidate_sha256` into `packet_sha256`. Any edit anywhere in the document therefore changed
   *every* packet's hash — once directly (via `candidate_sha256`), and, after removing that,
   again indirectly (any edit before a section shifts every later unit's absolute offsets even
   when its own text is unchanged). Caught by
   `test_editing_one_section_invalidates_only_that_sections_packets`, which failed twice for two
   different reasons — the task's own "if the same approach fails twice, stop and redesign"
   trigger. Fixed by excluding both `candidate_sha256` and the four position fields from the
   hashed payload while keeping them as ordinary (non-hashed) echoed fields on the packet, used
   directly by `validate_packet_result()`'s staleness check.

## Verification (all green)

```
pytest -q tests/unit/test_bounded_review_packets.py            # 26 passed
ruff check src/.../bounded_review_packets.py tests/.../test_bounded_review_packets.py   # clean
ruff format --check (same two files)                            # clean
mypy src/readme_agent/specialists/bounded_review_packets.py     # clean, no issues
```

Narrow regression subset (`test_readme_presentation_lint.py`, `test_section_authoring_document.py`)
showed 13/53 failures **inside the isolated clone only**, all `FileNotFoundError` on one
git-tracked, on-disk evidence file whose full path (298 chars) exceeds Windows' classic 260-char
MAX_PATH purely because of this isolation lane's own directory nesting. Re-run against the
primary checkout (shorter path): all 53 passed. See `KNOWN_LIMITATIONS.md` and
`TEST_RESULTS.json` for the full account — this is an environment artifact of the isolation
lane, not a regression caused by this module (which those two test files do not reference).

## Full account of files touched

See `CHANGED_FILES.txt` and `COMMITS.txt` in this directory. In summary: exactly one production
file (`src/readme_agent/specialists/bounded_review_packets.py`), one test file
(`tests/unit/test_bounded_review_packets.py`), and one new fixture directory
(`tests/fixtures/bounded_review_packets/`). No plan/graph/state-machine/existing-integration/
product-repo/`main` file was touched at any point.
