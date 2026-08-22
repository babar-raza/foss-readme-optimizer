# Interface reference

Module: `src/readme_agent/validation/public_candidate_quality.py`
(not registered anywhere — import it explicitly).

## Entry point

```python
def evaluate_public_candidate_quality(
    candidate_text: str,
    *,
    facts: ProductFactsV2 | None = None,
    claim_accountability: ReadmeClaimAccountabilityMapV1 | None = None,
) -> PublicQualityReportV1
```

Pure function. Identical inputs always produce a byte-identical `PublicQualityReportV1`, including
`report_hash`. `facts`/`claim_accountability` are both optional; supplying either enables the
`claim_grounding_negative_fact` check (otherwise it is entirely absent from `checks_run`, never
run-with-zero-findings).

## Models (frozen pydantic V1, `extra="forbid"`)

```python
class PublicQualitySpanV1:
    start: int              # character offset into candidate_text, >= 0
    end: int                # > start
    text: str                # candidate_text[start:end], self-verifying

class PublicQualityLocationV1:
    section_path: str        # heading breadcrumb, e.g. "Key Capabilities > COLLADA export"
                              # ("(preamble)" if before any heading)
    span: PublicQualitySpanV1

PublicQualityCategory = Literal[
    "cross_section_contradiction", "process_leakage", "malformed_prose",
    "claim_grounding", "structural_quality",
]
PublicQualitySeverity = Literal["critical", "warning"]
PublicQualityConfidence = Literal[
    "structured_evidence",   # backed by a supplied fact/claim record (highest)
    "exact_symbol",           # exact deterministic token/pattern match (reused-lint findings,
                               # malformed_duplicate_language, and Tier B all use this)
    "phrase_discriminator",   # fuzzy phrase match anchored by a shared discriminator token
    "phrase_generic",         # fuzzy phrase match with no shared anchor (lowest)
]
PublicQualityPolarity = Literal["positive_implementation", "explicit_constraint"]
PublicQualityDirection = Literal["read", "write"]

class PublicQualityFindingV1:
    finding_id: str           # "public_quality.<check_id>.<12-hex-fingerprint>"
    check_id: str              # e.g. "contradiction_capability_symbol"
    category: PublicQualityCategory
    severity: PublicQualitySeverity
    confidence: PublicQualityConfidence
    blocking: bool             # separate axis from severity -- see mapping table below
    locations: tuple[PublicQualityLocationV1, ...]   # 2 for contradictions (claim + limitation), 1 otherwise
    subject: str | None         # e.g. the shared symbol/discriminator
    operation: str | None        # currently unset by every check (reserved for future use)
    direction: PublicQualityDirection | None   # currently unset by every check
    polarity: PublicQualityPolarity | None
    conflicting_ids: tuple[str, ...]     # fact_id(s) in conflict for Tier A findings, else empty
    evidence_refs: tuple[StructuredFactCoordinateV1, ...]   # currently always empty -- reserved
    message: str
    repair_target: str          # narrow, human-readable pointer to what to fix

class PublicQualityCountsV1:
    cross_section_contradiction: int
    process_leakage: int
    malformed_prose: int
    claim_grounding: int
    structural_quality: int
    critical: int
    warning: int
    blocking: int
    advisory: int

class PublicQualityReportV1:
    schema_version: Literal[1]
    checks_version: int          # == PUBLIC_QUALITY_CHECKS_VERSION at evaluation time
    candidate_sha256: str         # sha256 of candidate_text
    checks_run: tuple[str, ...]    # sorted; a check absent here = "not evaluated", not "passed"
    findings: tuple[PublicQualityFindingV1, ...]   # sorted by (section_path, start, end, check_id)
    counts: PublicQualityCountsV1
    report_hash: str               # sha256 of self, excluding this field
```

Note: `operation`/`direction`/`evidence_refs` are typed on the model per the brief's required field
list but not yet populated by any check — they're there for a future check (or a future revision of
an existing one) to fill in without a schema change. Don't infer "empty" as a bug.

## check_id → category → confidence → blocking/severity mapping

| check_id | category | confidence (when it fires) | blocking | severity |
|---|---|---|---|---|
| `claim_grounding_negative_fact` | claim_grounding | structured_evidence | always True | critical |
| `contradiction_capability_symbol` | cross_section_contradiction | exact_symbol | always True | critical |
| `contradiction_capability_phrase` | cross_section_contradiction | phrase_discriminator | True | critical |
| `contradiction_capability_phrase` | cross_section_contradiction | phrase_generic | False | warning |
| `process_leakage` | process_leakage | exact_symbol | mirrors reused finding's severity | critical or warning |
| `malformed_low_information_prose` | malformed_prose | exact_symbol | mirrors reused finding's severity | critical or warning |
| `malformed_duplicate_language` | malformed_prose | exact_symbol | always True | critical |
| `empty_or_placeholder_section` | malformed_prose | phrase_generic | always False | warning |
| `structural_size_outlier` | structural_quality | phrase_generic | always False | warning |
| `structural_detail_density` | structural_quality | phrase_generic | always False | warning |

`process_leakage`/`malformed_low_information_prose` inherit `blocking`/`severity` directly from the
underlying `PresentationLintFindingV1.severity` (`"critical"` → `blocking=True`, `"warning"` →
`blocking=False`) rather than a fixed value, since that reused detector already makes its own
severity call per finding.

## Required inputs for full coverage

- `candidate_text: str` — required, the candidate README markdown.
- `facts: ProductFactsV2 | None` — from `readme_agent.facts.schema_v2`. Needed for
  `claim_grounding_negative_fact`. A complete `ProductFactsV2` requires all 16
  `REQUIRED_PRODUCT_FIELDS` to be selected (see `schema_v2.py`) — the test file's `_facts()` helper
  shows a minimal way to build one with stub facts for fields the caller doesn't care about.
- `claim_accountability: ReadmeClaimAccountabilityMapV1 | None` — from
  `readme_agent.readme.claim_accountability_models`. Accepted by the signature and reserved for a
  future claim_grounding check variant; **not yet consulted by any check body** — only `facts` is
  currently read inside `_check_claim_grounding_negative_fact`. Flagged in `KNOWN_LIMITATIONS.md`.
