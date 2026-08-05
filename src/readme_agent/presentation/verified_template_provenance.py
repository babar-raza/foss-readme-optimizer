"""Bind compiled template spans to explicit evidence."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.template_schema import PresentationTemplateInputV1
from readme_agent.presentation.verified_source_claim_resolutions import (
    build_source_claim_resolutions,
    probe_source_claim_resolutions_for_composition,
)
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.document_templates import installation_text
from readme_agent.readme.example_assurance_validation import (
    additional_examples_disclosure_fact_ids,
)
from readme_agent.readme.fact_grounding import literal_fact_ids
from readme_agent.readme.source_claim_risk import classify_source_claim_risk

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
                if slot == "scope_and_limitations":
                    relationship_risk = classify_source_claim_risk(text, claim)
                    if relationship_risk.obligation_id == "contextual_product_relationship":
                        relationship = facts.selected_fact("relationship.commercial_foss")
                        if (
                            relationship.verification_state in {"verified", "policy_approved"}
                            and not relationship.has_unresolved_conflict
                        ):
                            fact_ids = sorted({*fact_ids, relationship.fact_id})
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


__all__ = [
    "build_source_claim_resolutions",
    "build_template_provenance",
    "probe_source_claim_resolutions_for_composition",
]
