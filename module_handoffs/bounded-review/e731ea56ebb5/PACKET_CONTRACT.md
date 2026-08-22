PACKET_CONTRACT — exact data shapes

All types below live in `src/readme_agent/specialists/bounded_review_packets.py`. Every model is
a frozen, `extra="forbid"` pydantic v2 model. Field lists here match the source exactly at commit
`79afee7bf51e8e16d88d7e33650da8bcf7f93d24`; if this drifts, the source file is authoritative —
read it directly rather than trusting a stale copy of this document.

## Atomic units

`AtomicUnitV1` — one structural, never-split Markdown block:

- `unit_id: str` — stable within one plan, e.g. `unit-0007-fence`.
- `kind: Literal["heading","paragraph","fence","table","list"]`
- `section_path: str` — e.g. `"installation"`, `"api-reference/classes"`, `"front-matter"`
  (content before any level-2 heading), disambiguated with a `~2`/`~3` suffix on a non-adjacent
  repeat of the same heading text.
- `char_start`, `char_end: int` — Python character offsets into `candidate_text` (not UTF-8 byte
  offsets; see `_byte_offset_table`/`_char_span_from_byte_span` for the conversion the module
  does internally when consuming byte-offset-based caller inputs).
- `line_start`, `line_end: int` — 1-indexed.
- `claim_ids: tuple[str, ...]` — every valid (referentially-resolved) claim fully contained in
  this unit's span.
- `provenance_ids: tuple[str, ...]` — every `CandidateContentProvenanceV1` entry whose span
  overlaps this unit (informational; provenance is not merge-protected the way claims are).

Built by `build_atomic_units(candidate_text, claim_accountability, product_facts,
candidate_content_provenance=())`.

## Section classification

`SectionClassificationV1`: `section_path`, `char_start`, `char_end`,
`classification: Literal["standard","mechanical_api_inventory"]`, `justification: str`.

Heuristic (both defaults are module constants, both caller-overridable): a section is
`mechanical_api_inventory` when its `section_path` (split on `/` and `-`) intersects
`DEFAULT_API_INVENTORY_HEADING_KEYWORDS = {"api","reference","methods","classes","endpoints",
"properties","parameters"}` **and** table/fence characters are >=
`DEFAULT_API_INVENTORY_TABLE_FENCE_THRESHOLD = 0.6` of the section's total characters.

## Unpacketizable records — never a silent omission

`UnpacketizableRecordV1`: `record_id`, `reason: Literal["unresolved_fact_reference",
"oversized_unit"]`, `section_path`, `char_start`, `char_end`, `detail: str`, plus a
reason-matched field group enforced by a cross-field validator:

- `unresolved_fact_reference`: `claim_id` and/or `provenance_id` (at least one), `missing_fact_id`
  (required). `unit_kind`/`required_min_budget` must be `None`.
- `oversized_unit`: `unit_kind`, `required_min_budget: int` (both required). `claim_id`/
  `provenance_id`/`missing_fact_id` must be `None`.

## Packets

`BoundedFactualPacketV1`:

- `packet_id: str` — `pkt-factual-<order:04d>-<section-slug>-<packet_sha256[:12]>`.
- `stable_slot_id: str` — `factual:<section_path>:<local_index:02d>` — content-hash-independent,
  used for cross-plan diffing by `invalidated_packet_ids()`.
- `facet: Literal["factual"]`, `order: int` (0-indexed, per-facet global sequence).
- `candidate_sha256`, `char_start/end`, `line_start/end` — echoed/informational fields, **not**
  hashed into `packet_sha256` (see "What is and is not hashed" below).
- `section_path`, `unit_text: str`, `covered_unit_ids: tuple[str, ...]` (>=1).
- `claim_ids`, `accepted_fact_ids: tuple[str, ...]` (sorted).
- `facts: tuple[dict[str, Any], ...]` — `composition_fact_payloads()` output, sorted by
  `fact_id`, scoped to exactly the facts reachable from this packet's own `claim_ids`/overlapping
  provenance (minimality — see root cause #3 in REPORT.md).
- `do_not_claim: tuple[dict[str, Any], ...]` — the full caller-supplied projection, unfiltered
  (see KNOWN_LIMITATIONS.md).
- `provenance_ids: tuple[str, ...]` (sorted).
- `prompt_contract_hash: str` — echoes caller-supplied `factual_prompt_sha256`.
- `input_contract_hash: str` — `sha256_hex(_ALGORITHM_CONTRACT_VERSION)`, static per algorithm
  version.
- `packet_sha256: str`.

`BoundedVisitorPacketV1`:

- Same `packet_id`/`stable_slot_id`/`facet`("visitor")/`order`/`candidate_sha256`/position/
  `section_path` shape.
- `section_text: str` — the packet's own primary prose (no fact corpus).
- `neighbor_context_before`, `neighbor_context_after: str` — bounded by caller `neighbor_
  context_chars` (default `DEFAULT_NEIGHBOR_CONTEXT_CHARS = 400`), populated only at a section's
  first/last sub-packet respectively when an adjacent eligible section exists.
- `covered_unit_ids`, `prompt_contract_hash`, `input_contract_hash`, `packet_sha256`.

### What is and is not hashed into `packet_sha256`

`_packet_sha256(payload)` = `_canonical_hash({**payload, "_algorithm_contract_version":
_ALGORITHM_CONTRACT_VERSION})`. `payload` is the packet's *substantive* fields only —
deliberately **excludes** `candidate_sha256` and all four position fields (`char_start`,
`char_end`, `line_start`, `line_end`). Both are still present as ordinary fields on the
constructed packet object (used by `validate_packet_result()`'s staleness/echo checks) but do
not participate in the packet's own content-identity hash. This was a real bug found and fixed
during development — see REPORT.md's "Real bugs found and fixed" section for the full story of
why this exclusion is load-bearing, not cosmetic.

## Plan

`BoundedReviewPlanV1`: `schema_version`, `candidate_sha256`, `plan_hash`, `budget_chars: int`
(>0), `factual_packets: tuple[BoundedFactualPacketV1, ...]`, `visitor_packets: tuple[
BoundedVisitorPacketV1, ...]`, `unpacketizable: tuple[UnpacketizableRecordV1, ...]`.
`.canonical_hash()` = sorted-key JSON sha256 of the full model dump.

`plan_hash` = `_canonical_hash({"algorithm_contract_version", "candidate_sha256",
"document_plan_candidate_sha256", "facts_hash", "claim_accountability_hash", "budget_chars",
"neighbor_context_chars"})`, where `claim_accountability_hash` comes from
`_order_invariant_claim_accountability_hash()` — **not** the reused model's own
`.canonical_hash()` method, because that method's `sort_keys=True` only sorts dict keys, not the
`claims` list itself (the other real bug found and fixed — see REPORT.md).

Built by `plan_bounded_review_packets(*, candidate_text, document_plan, claim_accountability,
product_facts, budget_chars, factual_prompt_sha256, visitor_prompt_sha256, do_not_claim=(),
candidate_content_provenance=(), neighbor_context_chars=400,
api_inventory_heading_keywords=DEFAULT_API_INVENTORY_HEADING_KEYWORDS,
api_inventory_table_fence_threshold=DEFAULT_API_INVENTORY_TABLE_FENCE_THRESHOLD)`. Raises
`BoundedReviewInputMismatchError` on any candidate/facts/plan hash mismatch or non-positive
`budget_chars`.

## Coverage ledger

`CoverageSpanV1`: `unit_id`, `section_path`, `char_start`, `char_end`, `unit_kind`,
`covering_packet_ids: tuple[str, ...]` (empty means uncovered).

`ExcludedSpanV1`: `unit_id`, `section_path`, `char_start`, `char_end`, `classification: str`,
`justification: str`.

`CoverageOverlapV1`: `subject: str`, `packet_ids: tuple[str, ...]` (>=2, cross-field-validated),
`reason: str`. In practice the only overlap producer today is visitor neighbor-context
duplication between section-adjacent visitor packets — `subject` reads
`"visitor-neighbor-context:<prev_section_path>-><section_path>"`.

`CoverageLedgerV1`: `candidate_sha256`, `plan_hash`, `visitor_spans: tuple[CoverageSpanV1, ...]`
(one entry per non-excluded atomic unit, regardless of claim content), `factual_spans: tuple[
CoverageSpanV1, ...]` (one entry per atomic unit carrying >=1 `claim_id`), `excluded_spans`,
`overlaps`, `blocking_record_ids: tuple[str, ...]` (mirrors `plan.unpacketizable` record IDs).
`.canonical_hash()` available.

Built by `build_coverage_ledger(plan, *, atomic_units, api_inventory_heading_keywords=...,
api_inventory_table_fence_threshold=...)` — pass the **same** heuristic overrides used to build
`plan`, since the ledger recomputes section classification from `atomic_units` rather than
reading it back off the plan (the plan does not carry classification as a field).

`CoverageValidationV1` (from `validate_coverage_ledger(ledger)`, never raises): `is_complete:
bool`, `has_blocking_gaps: bool` (`= bool(ledger.blocking_record_ids)`),
`unassigned_visitor_span_ids`, `unassigned_factual_span_ids: tuple[str, ...]`.

## Result envelope

`BoundedPacketResultV1`: `packet_id`, `facet: Literal["factual","visitor"]`, `candidate_sha256`,
`packet_sha256`, `prompt_contract_hash`, `input_contract_hash` (all four echoed for staleness
checking), `verdict: BoundedPacketVerdict` (= the reused `FactualPlanVerdict` literal —
`"ACCEPT" | "REJECT_REPAIRABLE" | "BLOCKED_FACT_CONFLICT" | "BLOCKED_MISSING_EVIDENCE" |
"SYSTEM_FAILURE"`), `reasoning: str`, `failed_criteria: tuple[str, ...]`, `required_repair: str`,
`findings: tuple[GroundedReviewFindingV1, ...]` (the reused, unmodified type). Cross-field
validator mirrors `FactualPlanReviewResultV1`/`BlindQualityReviewResultV1` — see REPORT.md
redesign point 6.

`PacketResultValidationV1` (from `validate_packet_result(plan, result)`, never raises): `valid:
bool`, `errors: tuple[str, ...]`. Checks (in order): packet exists in plan; `facet`/
`candidate_sha256`/`packet_sha256`/`prompt_contract_hash`/`input_contract_hash` all match the
plan's packet; every finding's `quoted_candidate_span` occurs in the packet's own declared text
(`unit_text` for factual, `neighbor_context_before + section_text + neighbor_context_after` for
visitor); every finding's `section` equals the packet's `section_path`; every finding's `fact_id`
(when present) is one of the packet's own `accepted_fact_ids`.

## Aggregate verdict

`AggregateVerdictV1`: `candidate_sha256`, `plan_hash`, `overall: Literal["ACCEPT","INCOMPLETE",
"REJECTED","CONFLICT","BLOCKED"]`, `accepted_packet_ids`, `missing_packet_ids`,
`invalid_packet_ids`, `rejected_packet_ids`, `conflicting_packet_ids`,
`blocking_record_ids: tuple[str, ...]`, `details: tuple[str, ...]`. `.canonical_hash()`
available.

`aggregate_packet_results(plan, coverage_ledger, results)` (never raises) evaluates, in this
exact order:

1. `BLOCKED` — if `plan.unpacketizable` is non-empty or the ledger's own blocking-gap check is
   true. `blocking_record_ids` set; `missing_packet_ids` also reported (informational).
2. `INCOMPLETE` — if any required packet_id (union of `factual_packets`/`visitor_packets`
   packet_ids) is missing from `results`, or present but `validate_packet_result()` marks it
   invalid.
3. `CONFLICT` — if any `coverage_ledger.overlaps` entry has >=2 of its packets present in
   `results` with more than one distinct `verdict` among them.
4. `REJECTED` — if every required packet is present/valid/non-conflicting but at least one
   `verdict != "ACCEPT"`.
5. `ACCEPT` — only when every required packet is present, valid, `verdict == "ACCEPT"`, with no
   conflicts, and not blocked. The default is never `ACCEPT` — every earlier branch must be
   explicitly ruled out first.

## Repair plan

`RepairTargetV1`: `packet_id: str | None` (`None` only for `BLOCKED`-sourced targets, which were
never packetized), `facet: Literal["factual","visitor"] | None`, `section_path`, `char_start`,
`char_end`, `claim_ids`, `fact_ids: tuple[str, ...]`, `issue_summary: str`, `required_section_
authoring_clusters: tuple[str, ...]` (best-effort, via an optional caller-supplied
`section_path -> cluster_id` map).

`RepairPlanV1`: `candidate_sha256`, `plan_hash`, `round_number: int`, `max_repair_rounds: int`,
`repair_permitted: bool` (`= current_round < max_repair_rounds` — represented, never enforced by
this module), `requires_deterministic_remediation: bool` (`True` only when the aggregate was
`BLOCKED`), `targets: tuple[RepairTargetV1, ...]`. `.canonical_hash()` available.

`route_selective_repairs(plan, aggregate, results, *, current_round, max_repair_rounds,
section_cluster_map=None)` — pure data production, no mutation, no retry loop, no call issuance.
When `aggregate.overall == "BLOCKED"`, targets come from `plan.unpacketizable` (every
`packet_id=None`). Otherwise, targets come from the union of `aggregate.invalid_packet_ids`,
`.rejected_packet_ids`, `.conflicting_packet_ids` — never the whole candidate.

## Cache identity

- `packet_cache_key(packet, *, model, schema_sha256, facts_hash, provenance_hash,
  sampling_parameters=None) -> str` — sha256 of sorted-key JSON over `packet_id`,
  `packet_sha256`, `facet`, `model`, `schema_sha256`, `facts_hash`, `provenance_hash`,
  `sampling_parameters`. `packet.packet_sha256` already embeds `_ALGORITHM_CONTRACT_VERSION`, so
  an algorithm change invalidates through the key without a separate version field here.
- `is_reusable_cache_entry(result) -> bool` — `False` only for `verdict == "SYSTEM_FAILURE"`.
- `invalidated_packet_ids(old_plan, new_plan) -> frozenset[str]` — matches packets by
  `stable_slot_id`; a slot whose `packet_sha256` changed (or that is new/removed) is invalidated;
  a visitor slot additionally invalidates its immediate section-order neighbors (their neighbor-
  context text is now stale even if their own primary content did not change).
- `canonical_json(value: BaseModel) -> str` — shared deterministic serialization helper
  (`json.dumps(model_dump(mode="json"), sort_keys=True, separators=(",",":"),
  ensure_ascii=False)`), used by every byte-identity test in the suite.
