"""Validate actual README candidate assertions against selected product facts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlencode

from readme_agent.facts.gating import TechnicalClaimV1
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.markdown_structure import parse_markdown_structure
from readme_agent.readme.markers import find_span
from readme_agent.validation.rules.talking_points import missing_talking_points

_LICENSE_LINE = re.compile(r"^\s*-\s+\*\*License:\*\*\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True)
class CandidateClaimValidation:
    claims: list[TechnicalClaimV1]
    valid: bool
    errors: list[str]


def _allowed_documentation_urls(value: object) -> set[str]:
    allowed: set[str] = set()
    if not isinstance(value, list):
        return allowed
    for item in value:
        if isinstance(item, str):
            allowed.add(item)
            continue
        if not isinstance(item, dict):
            continue
        utm = item.get("utm")
        for key in ("url", "family_url"):
            url = item.get(key)
            if not isinstance(url, str):
                continue
            allowed.add(url)
            if isinstance(utm, dict) and all(
                isinstance(name, str) and isinstance(setting, str) for name, setting in utm.items()
            ):
                separator = "&" if "?" in url else "?"
                allowed.add(url + separator + urlencode(utm))
    return allowed


def _relationship_prose(content: str) -> str:
    return "\n".join(
        line
        for line in content.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "-", "<!--"))
    )


def validate_candidate_claims(
    candidate_text: str,
    facts: ProductFactsV2,
) -> CandidateClaimValidation:
    """Compare assertions inside the owned resources span with cited fact values."""

    span = find_span(candidate_text, "resources")
    if span is None:
        return CandidateClaimValidation([], False, ["candidate has no owned resources span"])
    content = span.content
    claims: list[TechnicalClaimV1] = []
    errors: list[str] = []

    license_match = _LICENSE_LINE.search(content)
    if license_match is not None:
        actual_license = license_match.group(1).strip()
        license_fact = facts.selected_fact("product.license")
        claims.append(
            TechnicalClaimV1(
                claim_id="readme.resources.product_license",
                surface_id="readme.license",
                text=f"License: {actual_license}",
                fact_ids=[license_fact.fact_id],
            )
        )
        if actual_license != license_fact.value:
            errors.append(
                f"candidate license {actual_license!r} does not match selected fact "
                f"{license_fact.value!r}"
            )

    link_targets = sorted(set(parse_markdown_structure(content).link_targets))
    if link_targets:
        links_fact = facts.selected_fact("documentation.links")
        claims.append(
            TechnicalClaimV1(
                claim_id="readme.resources.documentation_links",
                surface_id="readme.resources",
                text="Documentation links: " + ", ".join(link_targets),
                fact_ids=[links_fact.fact_id],
            )
        )
        unsupported = sorted(set(link_targets) - _allowed_documentation_urls(links_fact.value))
        if unsupported:
            errors.append(f"candidate contains URLs absent from selected facts: {unsupported}")

    prose = _relationship_prose(content)
    if prose:
        relationship_fact = facts.selected_fact("relationship.commercial_foss")
        claims.append(
            TechnicalClaimV1(
                claim_id="readme.resources.commercial_foss_relationship",
                surface_id="readme.relationship",
                text=prose,
                fact_ids=[relationship_fact.fact_id],
            )
        )
        required = relationship_fact.value if isinstance(relationship_fact.value, list) else []
        missing = missing_talking_points(prose, required)
        if missing:
            errors.append(f"candidate relationship prose misses talking points: {missing}")

    if not claims:
        errors.append("candidate resources span contains no fact-backed technical claim")
    return CandidateClaimValidation(claims, not errors, errors)
