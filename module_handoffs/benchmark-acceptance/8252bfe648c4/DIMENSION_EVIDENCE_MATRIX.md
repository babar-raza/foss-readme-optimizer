# Dimension evidence matrix

Source of truth for dimension identity/disposition: `data/aspose_benchmark_quality_profile.json`
(17 dimensions), consumed unmodified via `comparison.dimensions` (each already validated by
`CandidateBenchmarkDimensionV1`). This module never redefines a dimension_id or disposition.

| dimension_id | disposition | this module's verdict source | relevant `PublicQualityCategory` (blocking-only) |
|---|---|---|---|
| information_coverage | accepted | global gates + category map | claim_grounding, cross_section_contradiction |
| product_specificity | accepted | global gates + category map | claim_grounding, cross_section_contradiction |
| structure_and_navigation | adapted | global gates + category map | structural_quality, malformed_prose |
| branding_and_visuals | adapted | global gates + category map | structural_quality |
| capability_depth | adapted | global gates + category map | claim_grounding, cross_section_contradiction, structural_quality |
| installation_and_dependencies | adapted | global gates + category map | claim_grounding, malformed_prose |
| source_derived_examples | adapted | global gates + category map | claim_grounding, malformed_prose |
| api_reference_depth | adapted | global gates + category map | structural_quality, malformed_prose |
| documentation_and_resources | accepted | global gates + category map | malformed_prose, structural_quality |
| limitations | accepted | global gates + category map | malformed_prose, claim_grounding |
| development_and_testing | adapted | global gates + category map | process_leakage, malformed_prose |
| licensing | accepted | global gates + category map | claim_grounding |
| inherited_content_accountability | adapted | global gates + category map | malformed_prose, cross_section_contradiction |
| public_tone_and_process_hygiene | accepted | global gates + category map | process_leakage |
| benchmark_claim_authority | quarantined | hardcoded `QUARANTINED`, no evidence consulted | n/a |
| benchmark_item_verdicts | quarantined | hardcoded `QUARANTINED`, no evidence consulted | n/a |
| upstream_site_workflow_metadata | not_applicable | hardcoded `NOT_APPLICABLE`, no evidence consulted | n/a |

## Global gates (apply uniformly to every applicable -- `accepted`/`adapted` -- dimension)

Any of the following forces every applicable dimension to `UNKNOWN` (via the shared `blocked` flag)
and adds an entry to `hard_disqualifiers`:

1. `candidate_sha256` does not match `sha256_hex(candidate_markdown)`.
2. `comparison.candidate_sha256`, `deterministic_evidence.candidate_sha256`,
   `factual_review_evidence.candidate_sha256`, `visitor_review_evidence.candidate_sha256`, or
   `rubric_evidence.candidate_sha256` does not match the recomputed candidate hash.
3. `factual_review_evidence.identity.role != "factual_plan_reviewer"` or
   `visitor_review_evidence.identity.role != "blind_quality_reviewer"`.
4. The freshly recomputed on-disk profile hash does not match `comparison.benchmark_profile_sha256`.
5. `factual_review_evidence.verdict != "ACCEPT"` or `visitor_review_evidence.verdict != "ACCEPT"`.
6. `rubric_evidence.outcome.hard_disqualifier_count > 0`.
7. `rubric_evidence.outcome.accepted is True` together with a nonzero `hard_disqualifier_count`
   (internally-inconsistent rubric evidence).
8. A supplied `reference_excerpts` entry crosses both the sequence-ratio and Jaccard-ratio
   similarity thresholds against `candidate_markdown`.

## Category-level gate (applies only when no global gate fired)

For each applicable dimension, any `deterministic_evidence` finding with `blocking=True` whose
`category` intersects the dimension's row in `_DIMENSION_QUALITY_CATEGORIES` above forces that
specific dimension's verdict to `FAIL` (not the whole evaluation).

If neither gate fires for a dimension, its verdict is `PASS`.
