INTEGRATION — proposed binding points, without editing anything

This module makes no provider calls and is not wired into anything. Everything below is a
proposal for Codex, the integration authority, to evaluate — nothing here was implemented.

## Proposed existing call sites

- `src/readme_agent/specialists/separated_readme_review.py::run_separated_readme_review()` — the
  current single-call-per-facet entry point. It already builds
  `factual_packet = build_factual_review_packet(org_repo, candidate_readme_text, product_facts_v2,
  presentation_plan)` and `visitor_contract = build_presentation_visitor_contract(...)` before
  calling either the merged reviewer (`execute_merged_readme_review`) or the separated
  `blind_client`/`factual_client` pair via `run_grounded_role()`. This is the natural place for a
  size-triggered branch: when `len(candidate_readme_text.encode("utf-8"))` (or the already-built
  `factual_packet`'s own serialized size) exceeds the measured ceiling documented in
  `plans/investigations/owner_audit/qwen_context_budget/REPORT.md`, call
  `plan_bounded_review_packets(...)` instead of the current single-call path, dispatch one
  reviewer call per packet (reusing the existing `blind_client`/`factual_client`/merged-review
  machinery, `run_grounded_role()`, and grounding validators per packet), collect results into
  `BoundedPacketResultV1` instances, and call `aggregate_packet_results()` in place of the
  current `combine_review_verdicts()` path.
- `src/readme_agent/specialists/readme_presentation_review.py::review_candidate_node()` — the
  LangGraph node that currently calls `run_separated_readme_review()` once (via
  `separated_review_runner`) inside `run_independent_review_with_repair_loop()`. This is the
  natural place to bind a `RepairPlanV1`'s narrow `targets` into the existing repair-loop's
  `regenerate_review_context()`/`build_repaired_review_context()` machinery, replacing (or
  gating) the current whole-candidate repair regeneration with a section-scoped one when the
  aggregate came from a packetized review. The existing `repair_attempt`/`max_repair_rounds`-style
  bound already present in that loop is the natural place to also honor `RepairPlanV1.
  repair_permitted` and, critically, to check `RepairPlanV1.requires_deterministic_remediation`
  **before** issuing another reviewer call at all (see "How the retry policy should key off the
  aggregate states" below).

Both call sites already have direct access to everything `plan_bounded_review_packets()` needs:
`candidate_readme_text`, `presentation_plan["readme_document_plan"]` (a `ReadmeDocumentPlanV1`),
`presentation_plan["claim_map"]` (needs mapping to `ReadmeClaimAccountabilityMapV1` — see "Inputs
Codex will need to assemble" below), and `product_facts_v2` (a `ProductFactsV2`).

## Inputs Codex will need to assemble that are not already sitting in one place

- **`claim_accountability: ReadmeClaimAccountabilityMapV1`.** `run_separated_readme_review()`
  currently reads `presentation_plan.get("claim_map")`, which is a *different* type
  (`ReadmeClaimAccountabilityMapV1` per `document_plan.py::ReadmeDocumentPlanV1.
  claim_accountability`, distinct from whatever `claim_map` shape `build_readme_claim_map()`
  produces elsewhere in the pipeline — verify which one is actually present on the
  `presentation_plan` dict passed to `run_separated_readme_review()` before wiring this in; the
  module was built against `readme.claim_accountability_models.
  ReadmeClaimAccountabilityMapV1` specifically, matching `ReadmeDocumentPlanV1.
  claim_accountability`'s declared type).
- **`do_not_claim`.** This module takes it as an already-projected `Sequence[Mapping[str, Any]]`
  matching `agentic_composition_inputs.py::do_not_claim_payloads()`'s output shape — it does not
  call that function itself (see the module docstring's note on why: no `product_facts.py`
  coupling beyond what's already imported). Codex should call `do_not_claim_payloads(product_
  facts_v2)` at the call site and pass the result straight through.
- **`factual_prompt_sha256`/`visitor_prompt_sha256`.** Pass-through hash binding, per this
  module's "reads no prompt text itself" design (AGENTS.md's prompts-folder-only rule). Codex
  should pass whatever `prompt_registry.prompt_hash(prompt_id)` values the existing factual/
  visitor prompts already resolve to (`_FACTUAL_PROMPT_ID = "factual_readme_plan_review"`,
  `_BLIND_PROMPT_ID = "blind_readme_quality_review"` in `separated_readme_review.py` today) — or
  new prompt IDs if a packet-scoped prompt variant is authored under `prompts/`.
- **`budget_chars`.** Should come from the measured ceiling in `qwen_context_budget/REPORT.md`
  (currently documented as ~200KB request / ~60,000 provider prompt tokens), converted to a
  conservative character budget per packet with headroom for the surrounding prompt/schema
  overhead this module does not itself account for (its `budget_chars` bounds only the
  packet payload text+facts, not the full prompt envelope a live call would send).

## BLOCKED vs INCOMPLETE vs CONFLICT — how the retry policy should key off them

This is the part Codex's retry policy must get right; getting it wrong reintroduces the exact
cost/flakiness problem this module exists to prevent.

- **`INCOMPLETE`** — some required packet has no result yet, or its result failed structural
  validation (stale hash, invalid span, etc.). **Safe to retry.** This is the only aggregate
  state where issuing more reviewer calls is the correct next action — specifically, calls for
  the packets named in `aggregate.missing_packet_ids`/`.invalid_packet_ids`.
- **`CONFLICT`** — two or more packets that the coverage ledger records as intentionally
  overlapping (today: only visitor neighbor-context pairs) returned different verdicts.
  **Narrow-repair-then-retry**, not whole-candidate retry: `route_selective_repairs()` will
  return targets scoped to `aggregate.conflicting_packet_ids` only. A sensible policy is to
  re-run just those specific packets (their content is unchanged, so this is genuinely re-rolling
  the provider's known nondeterminism at temperature 0, not fixing a data problem) up to
  `max_repair_rounds`, and fail closed (never auto-ACCEPT) if conflicts persist past the bound.
- **`REJECTED`** — every required packet is present and structurally valid, but at least one
  reviewer said no. **Narrow repair via `route_selective_repairs()`**, whose targets are scoped
  to exactly the rejected/invalid/conflicting packets — this is the module's realization of the
  task's "selective repair routing" requirement. Codex's existing two-round repair bound
  (`max_repair_rounds`) maps directly onto this module's `current_round`/`max_repair_rounds`
  parameters; `RepairPlanV1.repair_permitted` is represented but not enforced by this module —
  the calling state machine still owns the actual decision to issue (or not issue) the next
  round.
- **`BLOCKED`** — **must never trigger more LLM calls.** This is the load-bearing distinction
  from `INCOMPLETE`. It means `plan.unpacketizable` is non-empty (a referential gap or an
  oversized unit that could not be packetized at all) — the reviewer layer was never given a
  chance to see the affected content in the first place, so no amount of re-prompting or
  re-rolling can resolve it. `route_selective_repairs()` signals this explicitly via
  `RepairPlanV1.requires_deterministic_remediation=True` with targets drawn from `plan.
  unpacketizable` (every target's `packet_id=None`, since these were never packetized). The
  correct caller behavior is to surface this as a **deterministic data-repair task** (fix the
  broken `accepted_fact_ids`/`fact_ids` reference upstream, or raise `budget_chars`/split the
  oversized unit's source content) — a `BLOCKED_FACT_CONFLICT`/`BLOCKED_MISSING_EVIDENCE`-style
  terminal state in whatever durable lifecycle state machine calls this module, not a retry.
- **`ACCEPT`** — every required packet present, valid, and `verdict=="ACCEPT"`, no conflicts, not
  blocked. Safe to promote to whatever "independent review passed" state the calling pipeline
  already has for the whole-candidate path today.

## The portfolio dashboard

No specific dashboard file was identified as a clear binding point during read-only research
(the portfolio proof engine under `src/readme_agent/supervisor/portfolio_proof_engine/` presents
whole-candidate 30/30 rubric results, not packet-level detail). A reasonable extension point:
when a candidate's review used the packetized path, surface `AggregateVerdictV1.overall` plus
packet counts (`len(plan.factual_packets)`, `len(plan.visitor_packets)`,
`len(plan.unpacketizable)`) alongside the existing whole-candidate verdict, so a human reviewing
portfolio evidence can tell at a glance whether a given repository's review went through the
single-call or packetized path and why (BLOCKED vs a normal repair round). This is a suggestion,
not a researched, ready-to-implement design — Codex should treat it as a starting point only.

## What Codex still needs to build (not attempted here, out of this module's scope)

- The actual per-packet reviewer dispatch loop (calling the existing `blind_client`/
  `factual_client`/merged-review machinery once per packet, building `BoundedPacketResultV1`
  from each raw LLM response).
- The size-triggered branch decision (single-call vs packetized) at the two call sites above.
- Threading `RepairPlanV1` targets into the existing repair-context regeneration
  (`build_repaired_review_context()`), likely requiring that function to accept a bounded
  section-scoped edit request rather than always regenerating the whole candidate.
- Persisting `BoundedReviewPlanV1`/packet results as durable evidence (this module returns pure
  in-memory objects; it does not write to `runs/` or call `write_redacted_json` itself, matching
  every other pure-planning module in this codebase — persistence is an integration concern).
- Deciding where `packet_cache_key()`/`is_reusable_cache_entry()`/`invalidated_packet_ids()` slot
  into the existing cache directory conventions (`section_authoring_cache.py`/
  `trusted_fidelity_cache.py` are the closest analogues to mirror for a new `bounded_review_
  packet_cache.py`-style persistence layer, itself out of this module's writable scope).
