COVERAGE_INVARIANTS — what the coverage ledger proves, and how

## The claim

For one `(plan, atomic_units)` pair built from the same `candidate_text`/`claim_accountability`/
`product_facts`/`candidate_content_provenance`, `build_coverage_ledger()` produces a
`CoverageLedgerV1` that, when passed to `validate_coverage_ledger()`, proves:

1. Every visitor-eligible atomic unit (i.e. every unit not belonging to a
   `mechanical_api_inventory`-classified section) is assigned to at least one visitor packet.
2. Every claim-bearing atomic unit (i.e. every unit carrying >=1 `claim_id`) is assigned to at
   least one factual packet.
3. Every unit excluded from visitor coverage carries an explicit, non-empty classification and
   justification — never a silent drop.
4. Intentional multi-packet coverage of the same content (visitor neighbor-context duplication)
   is named, not hidden.
5. The whole ledger is bound to the exact `candidate_sha256` and `plan_hash` it was built from,
   so a stale ledger can never be silently reused against a different plan.

## How the proof is constructed (mechanically, not just asserted)

`build_coverage_ledger(plan, *, atomic_units, ...)`:

1. Groups `atomic_units` into consecutive same-`section_path` runs (`_group_into_sections`) and
   recomputes each section's `mechanical_api_inventory`/`standard` classification
   (`_classify_sections`), using the **same** heuristic keyword set/threshold the caller used to
   build `plan` (pass matching overrides — see PACKET_CONTRACT.md).
2. For every atomic unit whose section is `mechanical_api_inventory`, emits one `ExcludedSpanV1`
   (invariant 3 above) and does **not** add it to the visitor-coverage dict at all.
3. For every other atomic unit, seeds a `visitor_covering[unit_id] = []` entry.
4. For every atomic unit carrying `claim_ids`, seeds a `factual_covering[unit_id] = []` entry
   (independent of that unit's section classification — a claim-bearing unit inside a
   `mechanical_api_inventory` section still gets a factual-coverage seed, satisfying "remains
   eligible for factual packet coverage when it carries claim IDs").
5. Walks every packet in `plan.factual_packets`/`plan.visitor_packets` and, for each `unit_id` in
   that packet's own `covered_unit_ids`, appends the packet's `packet_id` to the matching seeded
   list (if the unit_id was seeded for that facet at all — a packet can never "cover" a unit that
   wasn't eligible for that facet in the first place, by construction, since packets are only
   ever built from eligible units).
6. Converts both dicts into sorted `CoverageSpanV1` tuples (sorted by `unit_id`, `covering_
   packet_ids` sorted too) — this is what makes `validate_coverage_ledger()`'s "is every span's
   `covering_packet_ids` non-empty" check a direct, mechanical proof of invariants 1/2, not an
   assumption.
7. Walks `plan.visitor_packets` in `order` and, for every adjacent pair where the later packet's
   `neighbor_context_before` is non-empty, emits one `CoverageOverlapV1` naming both packet_ids
   (invariant 4).
8. Sets `blocking_record_ids = sorted(record.record_id for record in plan.unpacketizable)`
   (invariant 5's blocking-gap half — see `has_blocking_gaps` below).

`validate_coverage_ledger(ledger)` then mechanically checks, without recomputing anything from
the candidate: `is_complete = not any span with empty covering_packet_ids among visitor_spans or
factual_spans`; `has_blocking_gaps = bool(ledger.blocking_record_ids)`.

## Why `is_complete` and `has_blocking_gaps` are reported independently

This is the coverage-ledger side of redesign point 5 (BLOCKED vs INCOMPLETE — see REPORT.md). A
ledger can be `is_complete=True` (every span that needed a packet got one) while simultaneously
`has_blocking_gaps=True` (the underlying plan still carries `unpacketizable` records for claims/
provenance that could never be packetized at all, because their fact reference never resolved).
Coverage completeness and structural reviewability are genuinely different questions:
completeness asks "did every unit that *could* be assigned get assigned," while blocking-gap
status asks "is there residual, un-packetizable data damage that no reviewer call can resolve."
`aggregate_packet_results()` checks blocking-gap status first and unconditionally, specifically
because a complete-looking coverage ledger must never be allowed to imply the plan is safe to
review — that would silently launder a referential-gap problem into an apparent "just needs more
calls" state, exactly the confusion redesign point 5 exists to prevent.

## What is deliberately NOT proven by this ledger

- **Reviewer quality.** The ledger proves every required span was *assigned to a packet*, not
  that a live reviewer call against that packet would produce a good verdict. That is
  empirically observable only with live reviewer runs, explicitly out of this module's scope.
- **Semantic completeness of the API-inventory exclusion heuristic.** A section that should have
  been classified `mechanical_api_inventory` but wasn't (or vice versa) will still produce a
  self-consistent ledger — the ledger proves the *heuristic's own output* was fully accounted
  for, not that the heuristic itself was correct for every possible README. See
  KNOWN_LIMITATIONS.md.
- **Provenance coverage as its own tracked category.** Unlike claims, `candidate_content_
  provenance` entries do not get their own `CoverageSpanV1` collection — they are attached to
  factual packets by section/span overlap (see PACKET_CONTRACT.md) and contribute to a unit's
  factual-eligibility, but the ledger's completeness proof is stated in terms of claim-bearing
  units, not provenance entries directly. A provenance-only unit (no claim, but inside a
  provenance span) is still correctly included in `factual_covering` by construction (the
  eligibility check in `_build_factual_packets` is `unit.claim_ids or overlapping_provenance
  (unit)`), so provenance-only coverage is not silently dropped — it just is not named as a
  distinct invariant with its own field in `CoverageLedgerV1`, since the task's coverage
  requirement is phrased specifically in terms of "every factual claim span."
