"""Bind compiled template spans and removed source claims to explicit evidence."""

from __future__ import annotations

import hashlib
import re
from collections import Counter

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.template_schema import PresentationTemplateInputV1
from readme_agent.presentation.verified_source_policy_resolution import source_policy_resolution
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.document_plan import CandidateContentProvenanceV1, SourceClaimResolutionV1
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.document_templates import installation_text
from readme_agent.readme.example_assurance_validation import (
    additional_examples_disclosure_fact_ids,
)
from readme_agent.readme.fact_grounding import literal_fact_ids
from readme_agent.readme.presentation_lint_text import strip_emoji_decorations
from readme_agent.readme.source_claim_policy import SourceClaimPolicyCorrectionV1
from readme_agent.readme.source_claim_risk import (
    SourceClaimObligation,
    applicable_product_overview_fact_ids,
    classify_source_claim_risk,
    obligation_any_fact_fields,
    obligation_provenance_prefixes,
    obligation_required_fact_fields,
)

_CLAIM_LEVEL_SLOTS = {
    "additional_examples",
    "api_reference",
    "contributing",
    "development_and_testing",
    "installation",
    "scope_and_limitations",
    "security",
    "third_party_notices",
}
_STRUCTURAL_SHELL = re.compile(
    r"(?is)^(?:optional dependency groups declared by the package:|"
    r"install the package published for this repository:|"
    r"the coordinate was verified against maven central\.|"
    r"the package was verified against nuget\.|"
    r"add the module published for this repository:|"
    r"the module was verified through the go module proxy\.|"
    r"build the verified repository revision from source:|"
    r"explore additional examples for common product workflows\.|"
    r"the repository registers these mcp tools:|"
    r"validate a proposed change with the checked-in repository scripts:|"
    r"<details>\s*<summary>[^<]+</summary>|</details>|"
    r"- \[browse all [^]]+\]\([^)]+\))\s*$"
)
_PRESENTATION_MARKS = re.compile(r"[*_~]+")


def _raise_unresolved_preserve(required: bool, claim_id: str) -> None:
    if required:
        raise ValueError(
            "preserve disposition lost a source claim without exact fact-bound replacement "
            f"candidate content: {claim_id}"
        )


def _presentation_equivalence_key(value: str) -> str:
    without_decorations = strip_emoji_decorations(value)
    return " ".join(_PRESENTATION_MARKS.sub("", without_decorations).split()).casefold()


def build_template_provenance(
    candidate: str,
    template_input: PresentationTemplateInputV1,
    facts: ProductFactsV2,
) -> list[CandidateContentProvenanceV1]:
    """Bind each exact compiled span to its accepted facts and standards."""

    bindings: list[CandidateContentProvenanceV1] = []
    cursor = 0

    def bind(identifier: str, markdown: str, fact_ids: list[str], standard_ids: list[str]) -> None:
        nonlocal cursor
        text = markdown.strip()
        start_character = candidate.find(text, cursor)
        if start_character < 0:
            raise ValueError(f"compiled template content is absent: {identifier}")
        end_character = start_character + len(text)
        bindings.append(
            CandidateContentProvenanceV1(
                provenance_id=identifier,
                candidate_byte_start=len(candidate[:start_character].encode("utf-8")),
                candidate_byte_end=len(candidate[:end_character].encode("utf-8")),
                fact_ids=fact_ids,
                configured_standard_ids=standard_ids,
                rationale="Bind one exact compiled slot to its accepted inputs.",
            )
        )
        cursor = end_character

    bind(
        "template.title",
        template_input.title.markdown,
        template_input.title.fact_ids,
        template_input.title.standard_ids,
    )
    bind(
        "template.badges",
        template_input.badges.markdown,
        template_input.badges.fact_ids,
        template_input.badges.standard_ids,
    )
    bind(
        "template.summary",
        template_input.summary.markdown,
        template_input.summary.fact_ids,
        template_input.summary.standard_ids,
    )
    navigation = next(
        heading for heading in parse_headings(candidate) if heading.title.casefold() == "navigation"
    )
    navigation_body = candidate[navigation.heading_end : navigation.section_end].strip()
    bind("template.navigation", navigation_body, [], ["readme.navigation"])
    for slot, content in template_input.sections.items():
        if content.source_kind == "omitted":
            continue
        if slot in _CLAIM_LEVEL_SLOTS:
            text = content.markdown.strip()
            start_character = candidate.find(text, cursor)
            if start_character < 0:
                raise ValueError(f"compiled template content is absent: template.section.{slot}")
            base_byte = len(candidate[:start_character].encode("utf-8"))
            if slot == "installation":
                verified_installation = installation_text(
                    facts,
                    template_input.org_repo,
                    template_input.source_revision,
                )
                if verified_installation is not None:
                    exact = verified_installation.strip()
                    if text.count(exact) != 1:
                        raise ValueError(
                            "compiled installation does not contain exactly one verified "
                            "acquisition block"
                        )
                    relative_start = text.index(exact)
                    relative_end = relative_start + len(exact)
                    accepted_fact_ids = [
                        facts.selected_fact(field).fact_id
                        for field in (
                            "installation.coordinates",
                            "installation.verified_acquisition",
                        )
                        if facts.selected_fact(field).verification_state
                        in {"verified", "policy_approved"}
                        and not facts.selected_fact(field).has_unresolved_conflict
                    ]
                    bindings.append(
                        CandidateContentProvenanceV1(
                            provenance_id=("template.section.installation.verified_acquisition"),
                            candidate_byte_start=base_byte
                            + len(text[:relative_start].encode("utf-8")),
                            candidate_byte_end=base_byte + len(text[:relative_end].encode("utf-8")),
                            fact_ids=accepted_fact_ids,
                            configured_standard_ids=["readme.verified_acquisition"],
                            rationale=(
                                "Bind the exact deterministic acquisition block to its "
                                "accepted coordinate and acquisition facts."
                            ),
                        )
                    )
            for claim in assess_material_claims(text):
                claim_text = text.encode("utf-8")[
                    claim.source_byte_start : claim.source_byte_end
                ].decode("utf-8")
                fact_ids = literal_fact_ids(claim_text, facts, content.fact_ids)
                if slot == "additional_examples" and not fact_ids:
                    fact_ids = additional_examples_disclosure_fact_ids(claim_text, facts)
                standard_ids = (
                    content.standard_ids
                    if fact_ids or _STRUCTURAL_SHELL.fullmatch(claim_text.strip())
                    else []
                )
                if not fact_ids and not standard_ids:
                    continue
                bindings.append(
                    CandidateContentProvenanceV1(
                        provenance_id=f"template.section.{slot}.{claim.claim_id}",
                        candidate_byte_start=base_byte + claim.source_byte_start,
                        candidate_byte_end=base_byte + claim.source_byte_end,
                        fact_ids=fact_ids,
                        configured_standard_ids=standard_ids,
                        rationale="Bind one exact optional-section claim to accepted inputs.",
                    )
                )
            cursor = start_character + len(text)
            continue
        bind(f"template.section.{slot}", content.markdown, content.fact_ids, content.standard_ids)
    return bindings


def _accepted_obligation_bindings(
    obligation: SourceClaimObligation,
    facts: ProductFactsV2,
    provenance: list[CandidateContentProvenanceV1],
    *,
    exact_source_fact_ids: list[str] | None = None,
) -> tuple[list[CandidateContentProvenanceV1], list[str]] | None:
    prefixes = obligation_provenance_prefixes(obligation)
    required_fields = obligation_required_fact_fields(obligation)
    any_fields = obligation_any_fact_fields(obligation)
    bindings = [
        binding
        for binding in provenance
        if any(
            binding.provenance_id == prefix or binding.provenance_id.startswith(f"{prefix}.")
            for prefix in prefixes
        )
    ]
    if not bindings:
        return None
    if obligation == "product_overview" and not all(
        any(
            binding.provenance_id == prefix or binding.provenance_id.startswith(f"{prefix}.")
            for binding in bindings
        )
        for prefix in prefixes
    ):
        return None
    bound_fact_ids = {fact_id for binding in bindings for fact_id in binding.fact_ids}
    required_resolution_fact_ids = set(exact_source_fact_ids or [])
    if obligation == "product_overview":
        required_resolution_fact_ids.update(applicable_product_overview_fact_ids(facts))
    if exact_source_fact_ids is not None:
        if not exact_source_fact_ids and obligation != "product_overview":
            return None
        if obligation == "product_overview":
            missing_fact_ids = required_resolution_fact_ids - bound_fact_ids
            supplemental = [
                binding
                for binding in provenance
                if missing_fact_ids.intersection(binding.fact_ids) and binding not in bindings
            ]
            bindings.extend(supplemental)
            bound_fact_ids.update(
                fact_id for binding in supplemental for fact_id in binding.fact_ids
            )
        if not required_resolution_fact_ids.issubset(bound_fact_ids):
            return None
        resolution_fact_ids = sorted(required_resolution_fact_ids)
    else:
        if obligation == "product_overview":
            missing_fact_ids = required_resolution_fact_ids - bound_fact_ids
            supplemental = [
                binding
                for binding in provenance
                if missing_fact_ids.intersection(binding.fact_ids) and binding not in bindings
            ]
            bindings.extend(supplemental)
            bound_fact_ids.update(
                fact_id for binding in supplemental for fact_id in binding.fact_ids
            )
            if not required_resolution_fact_ids.issubset(bound_fact_ids):
                return None
            resolution_fact_ids = sorted(required_resolution_fact_ids)
        else:
            resolution_fact_ids = sorted(bound_fact_ids)
    accepted_fields: set[str] = set()
    for fact_id in sorted(bound_fact_ids):
        fact = facts.fact_by_id(fact_id)
        if (
            facts.selected_fact_ids.get(fact.field) != fact_id
            or fact.verification_state not in {"verified", "policy_approved"}
            or fact.has_unresolved_conflict
        ):
            return None
        accepted_fields.add(fact.field)
    if not required_fields.issubset(accepted_fields) or (
        any_fields and not any_fields.intersection(accepted_fields)
    ):
        return None
    return bindings, resolution_fact_ids


def _build_source_claim_resolutions(
    source_text: str,
    candidate: str,
    facts: ProductFactsV2,
    candidate_content_provenance: list[CandidateContentProvenanceV1] | None = None,
    *,
    preserved_source_ranges: list[tuple[int, int]] | None = None,
    authoritative_correction_ranges: list[tuple[int, int]] | None = None,
    presentation_policy_corrections: list[SourceClaimPolicyCorrectionV1] | None = None,
    fail_on_unresolved_preserve: bool = True,
) -> list[SourceClaimResolutionV1]:
    """Resolve removed claims by risk; mandatory claims fail closed without verified slots."""

    source_claims = assess_material_claims(source_text)
    candidate_claims = assess_material_claims(candidate)
    candidate_hashes = Counter(claim.content_sha256 for claim in candidate_claims)
    raw_candidate_occurrences = Counter(
        {
            claim.content_sha256: candidate.count(
                source_text.encode("utf-8")[claim.source_byte_start : claim.source_byte_end].decode(
                    "utf-8"
                )
            )
            for claim in source_claims
        }
    )
    candidate_bytes = candidate.encode("utf-8")
    selected_fact_ids = list(facts.selected_fact_ids.values())
    equivalence_candidates: dict[str, list] = {}
    for candidate_claim in candidate_claims:
        candidate_text = candidate_bytes[
            candidate_claim.source_byte_start : candidate_claim.source_byte_end
        ].decode("utf-8")
        equivalence_candidates.setdefault(_presentation_equivalence_key(candidate_text), []).append(
            candidate_claim
        )
    resolutions: list[SourceClaimResolutionV1] = []
    source_bytes = source_text.encode("utf-8")
    preserve_ranges = preserved_source_ranges or []
    correction_ranges = authoritative_correction_ranges or []
    policy_corrections = presentation_policy_corrections or []
    for claim in source_claims:
        if raw_candidate_occurrences[claim.content_sha256] > 0:
            raw_candidate_occurrences[claim.content_sha256] -= 1
            if candidate_hashes[claim.content_sha256] > 0:
                candidate_hashes[claim.content_sha256] -= 1
            continue
        survives = candidate_hashes[claim.content_sha256] > 0
        if survives:
            candidate_hashes[claim.content_sha256] -= 1
            continue
        claim_text = source_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
        policy_resolution = source_policy_resolution(claim, policy_corrections)
        if policy_resolution is not None:
            resolutions.append(policy_resolution)
            continue
        fact_ids = literal_fact_ids(claim_text, facts, selected_fact_ids)
        equivalent = equivalence_candidates.get(_presentation_equivalence_key(claim_text), [])
        if len(equivalent) == 1 and fact_ids:
            candidate_claim = equivalent[0]
            candidate_text = candidate_bytes[
                candidate_claim.source_byte_start : candidate_claim.source_byte_end
            ].decode("utf-8")
            candidate_fact_ids = literal_fact_ids(candidate_text, facts, selected_fact_ids)
            if set(candidate_fact_ids) == set(fact_ids):
                resolutions.append(
                    SourceClaimResolutionV1(
                        claim_id=claim.claim_id,
                        source_byte_start=claim.source_byte_start,
                        source_byte_end=claim.source_byte_end,
                        content_sha256=claim.content_sha256,
                        resolution="verified_equivalence",
                        fact_ids=sorted(fact_ids),
                        candidate_claim_id=candidate_claim.claim_id,
                        candidate_byte_start=candidate_claim.source_byte_start,
                        candidate_byte_end=candidate_claim.source_byte_end,
                        candidate_content_sha256=candidate_claim.content_sha256,
                        evidence=[
                            f"source-content-sha256:{claim.content_sha256}",
                            f"candidate-content-sha256:{candidate_claim.content_sha256}",
                            *(f"accepted-fact:{fact_id}" for fact_id in sorted(fact_ids)),
                        ],
                        rationale=(
                            "Bind this exact presentation-only rewrite to one exact candidate "
                            "claim with the same accepted fact set."
                        ),
                    )
                )
                continue
        preserve_required = claim.disposition == "preserve" and any(
            claim.source_byte_start < end and start < claim.source_byte_end
            for start, end in preserve_ranges
        )
        correction_required = claim.disposition in {
            "investigate",
            "remove_update",
            "repair",
            "replace_generic",
            "rewrite",
        } and any(
            claim.source_byte_start < end and start < claim.source_byte_end
            for start, end in correction_ranges
        )
        if preserve_required:
            _raise_unresolved_preserve(fail_on_unresolved_preserve, claim.claim_id)
            continue
        folded = claim_text.strip().casefold()
        risk = (
            classify_source_claim_risk(source_text, claim)
            if candidate_content_provenance is not None
            else None
        )
        if risk is not None and risk.risk_class == "governed_valid_omission":
            assert candidate_content_provenance is not None
            accepted = _accepted_obligation_bindings(
                "contextual_product_relationship",
                facts,
                candidate_content_provenance,
            )
            if accepted is None:
                _raise_unresolved_preserve(
                    preserve_required and fail_on_unresolved_preserve,
                    claim.claim_id,
                )
                continue
            bindings, replacement_fact_ids = accepted
            replacement_ids = sorted(binding.provenance_id for binding in bindings)
            resolutions.append(
                SourceClaimResolutionV1(
                    claim_id=claim.claim_id,
                    source_byte_start=claim.source_byte_start,
                    source_byte_end=claim.source_byte_end,
                    content_sha256=claim.content_sha256,
                    resolution="verified_omission",
                    obligation_id="contextual_product_relationship",
                    fact_ids=replacement_fact_ids,
                    replacement_provenance_ids=replacement_ids,
                    evidence=[
                        f"source-claim:{claim.claim_id}",
                        f"source-content-sha256:{claim.content_sha256}",
                        "obligation:contextual_product_relationship",
                        *(f"candidate-provenance:{item}" for item in replacement_ids),
                        *(f"accepted-fact:{item}" for item in replacement_fact_ids),
                    ],
                    rationale=risk.rationale,
                )
            )
            continue
        if re.search(r"official\s+aspose\s+project|100\s*%\s+free", folded):
            rationale = (
                "Omit this exact promotional source unit under the product-first presentation "
                "contract; replacement content is separately fact-bound."
            )
            evidence_kind = "presentation-policy-correction"
        elif folded.startswith("quick links:"):
            rationale = (
                "Omit this exact quick-link shell because the compiled candidate contains one "
                "complete list-based Navigation section."
            )
            evidence_kind = "redundant-navigation-shell"
        elif folded.startswith("[![ci]"):
            rationale = (
                "Replace this exact inherited badge shell with the one-row fact-bound badge set."
            )
            evidence_kind = "superseded-badge-shell"
        elif folded.startswith("pypi release page (maintainers):"):
            rationale = "Omit this exact maintainer-only release-management URL."
            evidence_kind = "maintainer-only-link"
        else:
            # Legacy renderers do not emit exact slot provenance. They must keep unresolved
            # source loss blocking instead of inheriting this verified-template fast path.
            if candidate_content_provenance is None:
                _raise_unresolved_preserve(
                    preserve_required and fail_on_unresolved_preserve,
                    claim.claim_id,
                )
                continue
            if risk is None:
                _raise_unresolved_preserve(
                    preserve_required and fail_on_unresolved_preserve,
                    claim.claim_id,
                )
                continue
            if not correction_required:
                continue
            if risk.risk_class == "optional_explicit_deferral":
                _raise_unresolved_preserve(
                    preserve_required and fail_on_unresolved_preserve,
                    claim.claim_id,
                )
                resolutions.append(
                    SourceClaimResolutionV1(
                        claim_id=claim.claim_id,
                        source_byte_start=claim.source_byte_start,
                        source_byte_end=claim.source_byte_end,
                        content_sha256=claim.content_sha256,
                        resolution="deferred_verification",
                        evidence=[
                            f"source-claim:{claim.claim_id}",
                            f"source-content-sha256:{claim.content_sha256}",
                            f"candidate-content-sha256:{hashlib.sha256(candidate_bytes).hexdigest()}",
                            "risk-policy:optional-inherited-detail-deferred-v1",
                        ],
                        rationale=risk.rationale,
                    )
                )
                continue
            if risk.obligation_id is None:
                _raise_unresolved_preserve(
                    preserve_required and fail_on_unresolved_preserve,
                    claim.claim_id,
                )
                continue
            accepted = _accepted_obligation_bindings(
                risk.obligation_id,
                facts,
                candidate_content_provenance,
                exact_source_fact_ids=(fact_ids or None if correction_required else fact_ids),
            )
            if accepted is None:
                _raise_unresolved_preserve(
                    preserve_required and fail_on_unresolved_preserve,
                    claim.claim_id,
                )
                continue
            bindings, replacement_fact_ids = accepted
            replacement_ids = sorted(binding.provenance_id for binding in bindings)
            rationale = (
                f"{risk.rationale} The exact replacement slot is bound to selected, "
                "accepted repository facts under an explicit hash-bound correction range."
            )
            resolutions.append(
                SourceClaimResolutionV1(
                    claim_id=claim.claim_id,
                    source_byte_start=claim.source_byte_start,
                    source_byte_end=claim.source_byte_end,
                    content_sha256=claim.content_sha256,
                    resolution="verified_obligation_replacement",
                    obligation_id=risk.obligation_id,
                    fact_ids=replacement_fact_ids,
                    replacement_provenance_ids=replacement_ids,
                    evidence=[
                        f"source-claim:{claim.claim_id}",
                        f"source-content-sha256:{claim.content_sha256}",
                        f"obligation:{risk.obligation_id}",
                        f"authority:deterministic-claim-disposition:{claim.disposition}",
                        *(f"candidate-provenance:{item}" for item in replacement_ids),
                        *(f"accepted-fact:{item}" for item in replacement_fact_ids),
                    ],
                    rationale=rationale,
                )
            )
            continue
        resolutions.append(
            SourceClaimResolutionV1(
                claim_id=claim.claim_id,
                source_byte_start=claim.source_byte_start,
                source_byte_end=claim.source_byte_end,
                content_sha256=claim.content_sha256,
                resolution="verified_omission",
                evidence=[
                    f"source-claim:{claim.claim_id}",
                    f"source-content-sha256:{claim.content_sha256}",
                    f"disposition:{evidence_kind}",
                    f"facts-sha256:{facts.canonical_hash()}",
                ],
                rationale=rationale,
            )
        )
    return resolutions


def build_source_claim_resolutions(
    source_text: str,
    candidate: str,
    facts: ProductFactsV2,
    candidate_content_provenance: list[CandidateContentProvenanceV1] | None = None,
    *,
    preserved_source_ranges: list[tuple[int, int]] | None = None,
    authoritative_correction_ranges: list[tuple[int, int]] | None = None,
    presentation_policy_corrections: list[SourceClaimPolicyCorrectionV1] | None = None,
) -> list[SourceClaimResolutionV1]:
    """Build final strict resolutions; unresolved leaf-preserve loss always raises."""

    return _build_source_claim_resolutions(
        source_text,
        candidate,
        facts,
        candidate_content_provenance,
        preserved_source_ranges=preserved_source_ranges,
        authoritative_correction_ranges=authoritative_correction_ranges,
        presentation_policy_corrections=presentation_policy_corrections,
        fail_on_unresolved_preserve=True,
    )


def probe_source_claim_resolutions_for_composition(
    source_text: str,
    candidate: str,
    facts: ProductFactsV2,
    candidate_content_provenance: list[CandidateContentProvenanceV1],
    *,
    preserved_source_ranges: list[tuple[int, int]],
    authoritative_correction_ranges: list[tuple[int, int]],
) -> list[SourceClaimResolutionV1]:
    """Probe replaceable claims before exact preservation; never use as final plan evidence."""

    return _build_source_claim_resolutions(
        source_text,
        candidate,
        facts,
        candidate_content_provenance,
        preserved_source_ranges=preserved_source_ranges,
        authoritative_correction_ranges=authoritative_correction_ranges,
        fail_on_unresolved_preserve=False,
    )
