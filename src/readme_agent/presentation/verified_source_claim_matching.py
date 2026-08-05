"""Match presentation-equivalent inherited and candidate claims."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.document_plan import SourceClaimResolutionV1
from readme_agent.readme.presentation_lint_text import strip_emoji_decorations
from readme_agent.readme.source_claim_assurance import accepted_source_claim_fact_ids

_PRESENTATION_MARKS = re.compile(r"[*_~]+")


def presentation_equivalence_key(value: str) -> str:
    """Normalize presentation-only decoration without weakening factual comparison."""

    without_decorations = strip_emoji_decorations(value)
    return " ".join(_PRESENTATION_MARKS.sub("", without_decorations).split()).casefold()


def index_equivalent_candidate_claims(
    candidate_bytes: bytes,
    candidate_claims: list[ReadmeMaterialClaimAssessmentV1],
) -> dict[str, list[ReadmeMaterialClaimAssessmentV1]]:
    """Index candidate claims by their presentation-equivalence key."""

    candidates: dict[str, list[ReadmeMaterialClaimAssessmentV1]] = {}
    for claim in candidate_claims:
        text = candidate_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
        candidates.setdefault(presentation_equivalence_key(text), []).append(claim)
    return candidates


def equivalent_source_claim_resolution(
    source_claim: ReadmeMaterialClaimAssessmentV1,
    source_claim_text: str,
    candidate_bytes: bytes,
    candidates: dict[str, list[ReadmeMaterialClaimAssessmentV1]],
    facts: ProductFactsV2,
) -> SourceClaimResolutionV1 | None:
    """Resolve one exact presentation-only rewrite when both claims share accepted facts."""

    fact_ids = sorted(accepted_source_claim_fact_ids(source_claim_text, facts))
    equivalent = candidates.get(presentation_equivalence_key(source_claim_text), [])
    if len(equivalent) != 1 or not fact_ids:
        return None
    candidate_claim = equivalent[0]
    candidate_text = candidate_bytes[
        candidate_claim.source_byte_start : candidate_claim.source_byte_end
    ].decode("utf-8")
    candidate_fact_ids = sorted(accepted_source_claim_fact_ids(candidate_text, facts))
    if set(candidate_fact_ids) != set(fact_ids):
        return None
    return SourceClaimResolutionV1(
        claim_id=source_claim.claim_id,
        source_byte_start=source_claim.source_byte_start,
        source_byte_end=source_claim.source_byte_end,
        content_sha256=source_claim.content_sha256,
        resolution="verified_equivalence",
        fact_ids=fact_ids,
        candidate_claim_id=candidate_claim.claim_id,
        candidate_byte_start=candidate_claim.source_byte_start,
        candidate_byte_end=candidate_claim.source_byte_end,
        candidate_content_sha256=candidate_claim.content_sha256,
        evidence=[
            f"source-content-sha256:{source_claim.content_sha256}",
            f"candidate-content-sha256:{candidate_claim.content_sha256}",
            *(f"accepted-fact:{fact_id}" for fact_id in fact_ids),
        ],
        rationale=(
            "Bind this exact presentation-only rewrite to one exact candidate claim with the "
            "same accepted fact set."
        ),
    )
