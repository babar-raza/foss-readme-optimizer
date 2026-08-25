"""Withhold exact compiler-rejected inherited examples behind verified replacements."""

from __future__ import annotations

import hashlib

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    SourceClaimResolutionV1,
)
from readme_agent.readme.source_claim_example_equivalence import fenced_source_code
from readme_agent.readme.source_claim_risk import SourceClaimRiskV1


def compiler_rejected_source_example_resolution(
    claim: ReadmeMaterialClaimAssessmentV1,
    claim_text: str,
    candidate_bytes: bytes,
    risk: SourceClaimRiskV1,
    facts: ProductFactsV2,
    accepted_primary: tuple[list[CandidateContentProvenanceV1], list[str]] | None,
    *,
    correction_candidate_claim_ids: frozenset[str],
) -> SourceClaimResolutionV1 | None:
    """Omit one exact failed compiled example only after a verified replacement exists."""

    if (
        claim.claim_id not in correction_candidate_claim_ids
        or risk.risk_class != "mandatory_fact_resolution"
        or risk.obligation_id != "primary_example"
        or accepted_primary is None
    ):
        return None
    fenced = fenced_source_code(claim_text)
    if fenced is None or fenced[0] == "python" or fenced[1].encode("utf-8") in candidate_bytes:
        return None
    if hashlib.sha256(claim_text.encode("utf-8")).hexdigest() != claim.content_sha256:
        raise ValueError("source example bytes do not match the assessed claim hash")
    examples_id = facts.selected_fact_ids.get("repository.examples")
    minimal_id = facts.selected_fact_ids.get("example.minimal")
    if examples_id is None or minimal_id is None:
        return None
    examples = facts.fact_by_id(examples_id)
    minimal = facts.fact_by_id(minimal_id)
    if (
        examples.verification_state != "verified"
        or examples.has_unresolved_conflict
        or examples.source.source_revision is None
        or not isinstance(examples.value, dict)
        or minimal.verification_state != "verified"
        or minimal.has_unresolved_conflict
        or minimal.source.source_revision != examples.source.source_revision
        or not isinstance(minimal.value, dict)
        or minimal.value.get("verification_outcome")
        not in {"SOURCE_BUILD_VERIFIED", "SOURCE_TREE_VERIFIED"}
    ):
        return None
    withheld = examples.value.get("withheld_inline_examples")
    if not isinstance(withheld, list):
        return None
    language, code = fenced
    exact = [
        item
        for item in withheld
        if isinstance(item, dict) and item.get("language") == language and item.get("code") == code
    ]
    if len(exact) != 1:
        return None
    rejected = exact[0]
    reason = rejected.get("validation_reason")
    example_sha256 = rejected.get("compiled_consumer_example_sha256")
    diagnostic_sha256 = rejected.get("compiler_diagnostic_sha256")
    if (
        rejected.get("static_api_verified") is not False
        or rejected.get("execution_verified") is not False
        or rejected.get("verification_outcome") != "BUILD_FAILED"
        or example_sha256 != hashlib.sha256(code.encode("utf-8")).hexdigest()
        or not isinstance(diagnostic_sha256, str)
        or len(diagnostic_sha256) != 64
        or not isinstance(reason, str)
        or not reason.strip()
    ):
        return None
    bindings, replacement_fact_ids = accepted_primary
    if minimal_id not in replacement_fact_ids:
        return None
    replacement_ids = sorted(binding.provenance_id for binding in bindings)
    fact_ids = sorted({examples_id, *replacement_fact_ids})
    return SourceClaimResolutionV1(
        claim_id=claim.claim_id,
        source_byte_start=claim.source_byte_start,
        source_byte_end=claim.source_byte_end,
        content_sha256=claim.content_sha256,
        resolution="verified_omission",
        obligation_id="primary_example",
        fact_ids=fact_ids,
        replacement_provenance_ids=replacement_ids,
        evidence=[
            f"source-claim:{claim.claim_id}",
            f"source-content-sha256:{claim.content_sha256}",
            f"candidate-content-sha256:{hashlib.sha256(candidate_bytes).hexdigest()}",
            f"snapshot-revision:{examples.source.source_revision}",
            f"compiler-outcome:{rejected['verification_outcome']}",
            f"compiler-diagnostic-sha256:{diagnostic_sha256}",
            *(f"accepted-fact:{item}" for item in fact_ids),
            *(f"candidate-provenance:{item}" for item in replacement_ids),
            "disposition:compiler-rejected-source-example-withheld-v1",
        ],
        rationale=(
            "The exact inherited compiled example failed isolated compilation at this source "
            "revision and is withheld without generalizing the failure. The candidate primary "
            "example is independently source-build verified."
        ),
    )


__all__ = ["compiler_rejected_source_example_resolution"]
