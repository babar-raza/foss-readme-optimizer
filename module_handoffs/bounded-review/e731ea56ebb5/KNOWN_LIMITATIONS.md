KNOWN_LIMITATIONS — stated plainly, not downplayed

## Confirmed pre-integration blocker (found after this document was first written)

See `PILOT_VERIFICATION_AND_KNOWN_BUG.md` in this directory. `_valid_claims_and_gaps()`'s claim
filter (`claim.stage == "candidate" and claim.survives_in_candidate`) never matches any claim
against real production `claim_accountability` data, because the real builder
(`readme/claim_accountability.py`) unconditionally sets `survives_in_candidate=None` for every
`stage="candidate"` claim. Result: zero factual packets, zero factual coverage, on every real
candidate, until fixed. This is qualitatively different from the heuristic/best-effort
limitations below — it is a confirmed functional defect with an exact one-line fix, not a
tradeoff or an edge case. Fix before integrating the factual-review path.

## The API-inventory classifier is a heuristic, not a general solution

`_classify_sections()` decides `mechanical_api_inventory` from two signals only: whether the
section's `section_path` (split on `/`/`-`) intersects a small fixed keyword set (`{"api",
"reference","methods","classes","endpoints","properties","parameters"}` by default, caller-
overridable) and whether table/fence characters dominate the section by a fixed threshold ratio
(0.6 by default, caller-overridable). This can misclassify an unusual section either way: a
genuinely narrative "API Philosophy" section that happens to contain a large example table could
be wrongly excluded from visitor review, and a genuinely mechanical reference section using an
unconventional heading ("Method Catalog", "Surface Map") without a keyword match would not be
excluded when it probably should be. The tests pin the *documented* behavior of this heuristic
against the synthetic fixture; they do not and cannot prove it generalizes to arbitrary real
READMEs. Codex should feed this richer signal at integration time — `document_plan` operation
categories or `ProductFactsV2`'s own `api.public_surface` field presence are both plausible
stronger signals not available inside this module (which deliberately has no access to anything
beyond `candidate_text`/`claim_accountability`/`product_facts`/`candidate_content_provenance`).

## The section -> section-authoring-cluster-id mapping is best-effort and optional

`route_selective_repairs()`'s `required_section_authoring_clusters` field is populated only when
the caller supplies an explicit `section_path -> cluster_id` map via `section_cluster_map`; this
module has no way to derive that mapping itself, since no deterministic heading-to-cluster-id
rule exists anywhere in the code this module was built against (`section_authoring_contracts.py`
identifies clusters by `target_section_id`, a value produced upstream by whatever process built
the `SectionAuthoringDocumentV1`, not derivable from a bare Markdown heading string). Callers
that don't supply this map simply get an empty tuple for this field — silently omitted from the
type's perspective (it's an optional, defaulted field), but the caller should be aware the
mapping was never attempted, not that it was attempted and came up empty.

## The single-file constraint is a real cost, not a nonissue

The task instructed a single writable production file
(`src/readme_agent/specialists/bounded_review_packets.py`), which the codebase's own governance
(`plans/GOVERNANCE.md`, "no monoliths", ~300-line split guidance) would not normally allow. The
file is ~1,780 lines. It is internally organized by concern (models grouped by
packet/coverage/result/aggregate/repair/cache; the structural parser is a self-contained section;
helper functions are grouped near their primary caller), and this organization is intended to
make a future split straightforward, not to disguise the size. Suggested seam lines for Codex if
splitting at integration time: `bounded_review_packet_types.py` (models: `AtomicUnitV1` through
`RepairPlanV1`), `bounded_review_structural_parsing.py` (`_build_raw_units` and everything it
depends on through `build_atomic_units`), `bounded_review_planning.py`
(`plan_bounded_review_packets` and its private `_build_factual_packets`/`_build_visitor_packets`
helpers), `bounded_review_validation.py` (`validate_packet_result`/`aggregate_packet_results`/
`build_coverage_ledger`/`validate_coverage_ledger`), `bounded_review_repair_and_cache.py`
(`route_selective_repairs` through `invalidated_packet_ids`). This split was not done here
because the task granted exactly one writable production file path.

## Packetization trades size-failures for call-count (stated in the design plan, restated here)

Bounding packets by `budget_chars` eliminates truncation-by-size failures by construction, but it
necessarily increases the number of independent reviewer calls per candidate — and per the
`qwen3-next-identity` investigation, each call is an independent, temperature-0-nondeterministic
roll. More calls means more chances for cross-packet disagreement (the `CONFLICT` aggregate
state exists specifically because this is a real, not hypothetical, consequence), and more
provider spend per candidate. This module makes that tradeoff *visible and fail-closed* — it
does not, and structurally cannot, eliminate it. Nothing in this module reduces the number of
reviewer calls a large candidate needs; it only bounds each call's payload and makes the multi-
call result honestly reconcilable.

## Byte-offset-vs-character-offset handling is implemented but only lightly exercised

The module correctly converts caller-supplied UTF-8 byte offsets (`ReadmeClaimAccountabilityV1.
source_byte_start/end`, `CandidateContentProvenanceV1.candidate_byte_start/end`) into Python
character offsets via a precomputed cumulative-byte-length table and `bisect` (see
`_byte_offset_table`/`_char_span_from_byte_span`), rather than assuming byte offsets equal
character offsets. The synthetic test fixture is pure ASCII by construction (documented in
`fixture-provenance.json`), so this conversion is exercised as an identity mapping in every test
— the conversion logic itself was written to be correct for non-ASCII candidates, but no test in
this suite actually exercises a candidate containing multi-byte UTF-8 characters at a claim/
provenance boundary. Flagged honestly as reduced (not absent) confidence in this one code path.

## do_not_claim entries are included in full in every factual packet, not filtered per section

The design's phrase "relevant do_not_claim entries" was implemented as "the entire caller-
supplied `do_not_claim` list, unfiltered, in every factual packet" rather than attempting a
per-section relevance filter. `do_not_claim_payloads()` upstream already bounds this list to at
most 24 entries (only genuinely conflicting/unresolved-conflict facts), so the marginal payload
cost of including the whole list in every packet is small, and including it universally is
strictly safer than a relevance heuristic that might wrongly exclude a warning that turns out to
matter for a given section. Recorded as a deliberate simplification, not an oversight.

## The paragraph/list structural parser does not detect a table or fence starting without a
## preceding blank line

`_build_raw_units()`'s paragraph/list scanner breaks out of a contiguous non-blank run only when
it encounters a heading or a fence-opening line; it does not specially detect a table's header
row appearing on the very next line after ordinary prose with no blank-line separator (a CommonMark
"lazy continuation" edge case for GFM-style tables). Well-formed Markdown conventionally blank-
line-separates block types, and the synthetic fixture does so throughout; a real-world candidate
that violates this convention could have a table row folded into a preceding paragraph unit
instead of recognized as its own atomic table unit. This does not risk splitting a real table —
at worst it over-includes a table's first row inside an adjacent paragraph unit — but is recorded
as an unexercised edge case.
