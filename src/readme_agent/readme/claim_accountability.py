"""Inventory inherited and generated README claims against facts and ownership."""

from __future__ import annotations

import hashlib
import re
from collections import Counter

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment_claims import (
    ClaimDisposition,
    ReadmeMaterialClaimAssessmentV1,
    assess_material_claims,
)
from readme_agent.readme.claim_accountability_models import (
    ClaimOrigin,
    ClaimStage,
    ExpectedClaimDisposition,
    ReadmeClaimAccountabilityMapV1,
    ReadmeClaimAccountabilityV1,
)
from readme_agent.readme.claim_map import ReadmeClaimMapV1

_CORRECTION_DISPOSITIONS = {"rewrite", "repair", "remove_update", "replace_generic"}
_MARKDOWN_MARKS = re.compile(r"[`*_>#\[\]()]")


def _normalized_unit(value: str) -> str:
    lines = [line for line in value.strip().splitlines() if not line.strip().startswith("```")]
    collapsed = " ".join(line.strip().lstrip("-+* ") for line in lines)
    return " ".join(_MARKDOWN_MARKS.sub("", collapsed).casefold().split())


def _accepted_literal_facts(claim_text: str, facts: ProductFactsV2) -> set[str]:
    normalized_claim = _normalized_unit(claim_text)
    accepted = set()
    for fact_id in facts.selected_fact_ids.values():
        fact = facts.fact_by_id(fact_id)
        if (
            fact.verification_state
            not in {
                "verified",
                "policy_approved",
            }
            or fact.has_unresolved_conflict
        ):
            continue
        values = []
        view = visitor_fact_render_view(facts, fact.field)
        if view is not None:
            values.extend(view.phrases)
        if fact.field == "example.minimal" and isinstance(fact.value, dict):
            code = fact.value.get("code")
            if isinstance(code, str):
                values.append(code)
        if normalized_claim and any(
            normalized_claim == _normalized_unit(value)
            for value in values
            if isinstance(value, str)
        ):
            accepted.add(fact_id)
    return accepted


def _overlapping_candidate_fact_ids(
    claim: ReadmeMaterialClaimAssessmentV1,
    candidate_text: str,
    claim_map: ReadmeClaimMapV1,
) -> set[str]:
    bindings = [
        binding
        for binding in claim_map.claims
        if binding.coordinate_space == "candidate_utf8"
        and binding.byte_start < claim.source_byte_end
        and claim.source_byte_start < binding.byte_end
    ]
    if not bindings:
        return set()
    claim_bytes = candidate_text.encode("utf-8")[claim.source_byte_start : claim.source_byte_end]
    covered = bytearray(len(claim_bytes))
    for binding in bindings:
        start = max(binding.byte_start, claim.source_byte_start) - claim.source_byte_start
        end = min(binding.byte_end, claim.source_byte_end) - claim.source_byte_start
        covered[start:end] = b"\x01" * (end - start)
    uncovered = bytes(byte for index, byte in enumerate(claim_bytes) if not covered[index]).decode(
        "utf-8", errors="ignore"
    )
    if any(character.isalnum() for character in _MARKDOWN_MARKS.sub("", uncovered)):
        return set()
    return {binding.fact_id for binding in bindings}


def _expected_disposition(
    *,
    stage: ClaimStage,
    origin: ClaimOrigin,
    current: ClaimDisposition,
    accepted_fact_ids: set[str],
    survives_in_candidate: bool | None,
) -> tuple[ExpectedClaimDisposition, bool, str]:
    if current == "investigate":
        return (
            "explicit_uncertainty",
            True,
            "Instruction-like or unresolved source content remains explicitly untrusted.",
        )
    if current in _CORRECTION_DISPOSITIONS:
        return (
            "required_correction",
            True,
            "The assessment requires a bounded correction before factual approval.",
        )
    if accepted_fact_ids:
        return (
            "accepted_fact",
            True,
            "Exact content is bound to at least one selected accepted fact.",
        )
    if stage == "source" and survives_in_candidate is False:
        return (
            "unjustified_loss",
            False,
            "Preserved source knowledge disappeared without a correction or omission authority.",
        )
    if stage == "candidate" and origin == "generated":
        return (
            "unbound_generated",
            False,
            "Generated material has no accepted fact binding and requires correction or omission.",
        )
    return (
        "authoritative_owner_validation",
        False,
        "Byte preservation is not factual approval; "
        "an authoritative owner or fact is still required.",
    )


def _claim_text(document: str, claim: ReadmeMaterialClaimAssessmentV1) -> str:
    return document.encode("utf-8")[claim.source_byte_start : claim.source_byte_end].decode("utf-8")


def build_readme_claim_accountability_map(
    *,
    org_repo: str,
    source_text: str,
    candidate_text: str,
    facts: ProductFactsV2,
    generated_claim_map: ReadmeClaimMapV1,
) -> ReadmeClaimAccountabilityMapV1:
    """Return one explicit expected disposition for every material claim."""

    source_claims = assess_material_claims(source_text)
    candidate_claims = assess_material_claims(candidate_text)
    remaining_inherited = Counter(claim.content_sha256 for claim in source_claims)
    candidate_origins: dict[str, ClaimOrigin] = {}
    for claim in candidate_claims:
        if remaining_inherited[claim.content_sha256] > 0:
            candidate_origins[claim.claim_id] = "inherited"
            remaining_inherited[claim.content_sha256] -= 1
        else:
            candidate_origins[claim.claim_id] = "generated"
    candidate_hashes = Counter(claim.content_sha256 for claim in candidate_claims)

    records = []
    for claim in source_claims:
        text = _claim_text(source_text, claim)
        fact_ids = _accepted_literal_facts(text, facts)
        survives = candidate_hashes[claim.content_sha256] > 0
        if survives:
            candidate_hashes[claim.content_sha256] -= 1
        expected, accountable, rationale = _expected_disposition(
            stage="source",
            origin="inherited",
            current=claim.disposition,
            accepted_fact_ids=fact_ids,
            survives_in_candidate=survives,
        )
        records.append(
            _record(
                claim,
                facts,
                stage="source",
                origin="inherited",
                fact_ids=fact_ids,
                survives=survives,
                expected=expected,
                accountable=accountable,
                rationale=rationale,
            )
        )
    for claim in candidate_claims:
        text = _claim_text(candidate_text, claim)
        fact_ids = _accepted_literal_facts(text, facts) | _overlapping_candidate_fact_ids(
            claim,
            candidate_text,
            generated_claim_map,
        )
        origin = candidate_origins[claim.claim_id]
        expected, accountable, rationale = _expected_disposition(
            stage="candidate",
            origin=origin,
            current=claim.disposition,
            accepted_fact_ids=fact_ids,
            survives_in_candidate=None,
        )
        records.append(
            _record(
                claim,
                facts,
                stage="candidate",
                origin=origin,
                fact_ids=fact_ids,
                survives=None,
                expected=expected,
                accountable=accountable,
                rationale=rationale,
            )
        )
    return ReadmeClaimAccountabilityMapV1(
        org_repo=org_repo,
        facts_hash=facts.canonical_hash(),
        source_sha256=hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        candidate_sha256=hashlib.sha256(candidate_text.encode("utf-8")).hexdigest(),
        claims=records,
    )


def _record(
    claim: ReadmeMaterialClaimAssessmentV1,
    facts: ProductFactsV2,
    *,
    stage: ClaimStage,
    origin: ClaimOrigin,
    fact_ids: set[str],
    survives: bool | None,
    expected: ExpectedClaimDisposition,
    accountable: bool,
    rationale: str,
) -> ReadmeClaimAccountabilityV1:
    return ReadmeClaimAccountabilityV1(
        claim_id=f"{stage}:{claim.claim_id}",
        stage=stage,
        origin=origin,
        source_byte_start=claim.source_byte_start,
        source_byte_end=claim.source_byte_end,
        content_sha256=claim.content_sha256,
        current_disposition=claim.disposition,
        accepted_fact_ids=sorted(fact_ids),
        authoritative_owners=sorted(
            {facts.fact_by_id(fact_id).authoritative_owner for fact_id in fact_ids}
        ),
        survives_in_candidate=survives,
        expected_disposition=expected,
        currently_accountable=accountable,
        rationale=rationale,
    )
