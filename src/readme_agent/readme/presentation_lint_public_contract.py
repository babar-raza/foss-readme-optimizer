"""Enforce portfolio-wide visitor-facing language and structure contracts."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.presentation_lint_models import PresentationLintFindingV1
from readme_agent.readme.presentation_lint_text import (
    exact_span,
    line_span,
    make_finding,
    visible_lines,
)
from readme_agent.readme.presentation_similarity import semantically_repeats
from readme_agent.readme.public_text import (
    canonical_abbreviations_from_facts,
    heading_is_title_case,
    public_text_corrections,
)

RULE_IDS = (
    "api_identifier_not_fact_exact",
    "generic_preservation_heading",
    "heading_not_title_case",
    "internal_assurance_commentary",
    "noncanonical_technical_abbreviation",
    "capability_description_repeats_title",
    "generic_capability_description",
    "unnatural_enterprise_link",
)

_INTERNAL_ASSURANCE = re.compile(
    r"(?i)(?:exact source revision|immutable repository revision|source revision in an isolated|"
    r"network[- ]disabled verification|matching (?:pypi|registry) receipt|"
    r"verification environment|inventoried at the source revision|"
    r"syntax and static public api checked|not executed or syntax checked|"
    r"execution_verified|provider call|evidence collector|"
    r"verified (?:export|package) namespace|additional verified members?|"
    r"currently installed from source)"
)
_ENTERPRISE_LINK = re.compile(
    r"\[(?P<label>[^\]]+)\]\((?P<url>https?://(?:www\.)?products\.aspose\.com/[^)]+)\)",
    re.IGNORECASE,
)
_CAPABILITY_ROW = re.compile(r"^- \*\*(?P<title>[^*]+)\*\* - (?P<body>.+)$")
_GENERIC_CAPABILITY_DESCRIPTION = re.compile(
    r"(?i)^apply the operation through the product(?:'s|s) public api\.?$"
)
_API_NAMESPACE_HEADING = re.compile(r"^### [^\r\n]+ Namespace \(`(?P<identifier>[^`]+)`\)\s*$")


def _accepted_api_identifiers(facts: ProductFactsV2 | None) -> set[str]:
    if facts is None:
        return set()
    try:
        fact = facts.selected_fact("api.public_surface")
    except KeyError:
        return set()
    if (
        fact.verification_state not in {"verified", "policy_approved"}
        or fact.has_unresolved_conflict
        or not isinstance(fact.value, dict)
    ):
        return set()
    identifiers: set[str] = set()
    for collection in (fact.value.get("modules"), fact.value.get("classes")):
        if not isinstance(collection, list):
            continue
        for item in collection:
            if isinstance(item, dict) and str(item.get("module") or "").strip():
                identifiers.add(str(item["module"]).strip())
    return identifiers


def lint_public_contract(
    text: str,
    facts: ProductFactsV2 | None = None,
) -> list[PresentationLintFindingV1]:
    """Return violations of the global public README language contract."""

    findings: list[PresentationLintFindingV1] = []
    canonical_terms = canonical_abbreviations_from_facts(facts)
    accepted_api_identifiers = _accepted_api_identifiers(facts)
    for heading in parse_headings(text):
        if not heading_is_title_case(heading.title, canonical_terms):
            findings.append(
                make_finding(
                    "heading_not_title_case",
                    "Every public README heading must use canonical title case.",
                    [exact_span(text, heading.start, heading.heading_end)],
                )
            )
        if heading.title.strip().casefold() == "preserved repository details":
            findings.append(
                make_finding(
                    "generic_preservation_heading",
                    "Source knowledge must be reconciled into its canonical visitor section.",
                    [exact_span(text, heading.start, heading.heading_end)],
                )
            )
    for line in visible_lines(text):
        api_heading = _API_NAMESPACE_HEADING.match(line.text)
        if (
            api_heading
            and accepted_api_identifiers
            and api_heading.group("identifier") not in accepted_api_identifiers
        ):
            start = line.start + api_heading.start("identifier")
            end = line.start + api_heading.end("identifier")
            findings.append(
                make_finding(
                    "api_identifier_not_fact_exact",
                    "Public API identifiers must preserve fact-derived spelling and casing.",
                    [exact_span(text, start, end)],
                )
            )
        capability_row = _CAPABILITY_ROW.match(line.text)
        if capability_row:
            title = capability_row.group("title").strip().rstrip(".")
            first_sentence = capability_row.group("body").split(". ", 1)[0].strip().rstrip(".")
            if semantically_repeats(title, first_sentence, threshold=0.9):
                findings.append(
                    make_finding(
                        "capability_description_repeats_title",
                        "Key-capability explanations must add visitor-facing detail.",
                        [line_span(text, line)],
                    )
                )
            if _GENERIC_CAPABILITY_DESCRIPTION.fullmatch(capability_row.group("body").strip()):
                findings.append(
                    make_finding(
                        "generic_capability_description",
                        "Key-capability explanations must describe a concrete product behavior.",
                        [line_span(text, line)],
                    )
                )
        if _INTERNAL_ASSURANCE.search(line.text):
            findings.append(
                make_finding(
                    "internal_assurance_commentary",
                    "Internal verification narration must not appear in a public README.",
                    [line_span(text, line)],
                )
            )
        for match in _ENTERPRISE_LINK.finditer(line.text):
            label = match.group("label").casefold()
            if "enterprise edition" not in label or "full-featured" not in label:
                findings.append(
                    make_finding(
                        "unnatural_enterprise_link",
                        "Aspose.com product links require a natural, informative Enterprise "
                        "Edition anchor.",
                        [
                            exact_span(
                                text,
                                line.start + match.start(),
                                line.start + match.end(),
                            )
                        ],
                    )
                )
    for correction in public_text_corrections(text, canonical_terms):
        if correction.standard_id != "readme.technical_abbreviation_case":
            continue
        findings.append(
            make_finding(
                "noncanonical_technical_abbreviation",
                "Technical abbreviations must use canonical uppercase casing.",
                [exact_span(text, correction.character_start, correction.character_end)],
            )
        )
    return findings


__all__ = ["RULE_IDS", "lint_public_contract"]
