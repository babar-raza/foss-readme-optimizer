"""Classify removed source README claims against golden-contract obligations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.presentation_lint_text import strip_emoji_decorations

SourceClaimRiskClass = Literal[
    "mandatory_fact_resolution",
    "optional_explicit_deferral",
    "governed_valid_omission",
]
SourceClaimObligation = Literal[
    "product_overview",
    "major_capabilities",
    "verified_installation",
    "primary_example",
    "scope_and_limitations",
    "third_party_notices",
    "license",
    "contextual_product_relationship",
]

_OBLIGATION_FACT_FIELDS: dict[SourceClaimObligation, frozenset[str]] = {
    "product_overview": frozenset({"product.identity"}),
    "major_capabilities": frozenset({"product.capabilities"}),
    "verified_installation": frozenset(
        {"installation.verified_acquisition", "installation.coordinates"}
    ),
    "primary_example": frozenset({"example.minimal"}),
    "scope_and_limitations": frozenset({"product.limitations"}),
    "third_party_notices": frozenset({"repository.third_party_notices"}),
    "license": frozenset({"product.license"}),
    "contextual_product_relationship": frozenset({"relationship.commercial_foss"}),
}
_OBLIGATION_ANY_FACT_FIELDS: dict[SourceClaimObligation, frozenset[str]] = {
    "product_overview": frozenset(
        {"product.audience", "product.problems_solved", "product.capabilities"}
    )
}
_OBLIGATION_PROVENANCE_PREFIXES: dict[SourceClaimObligation, tuple[str, ...]] = {
    "product_overview": ("template.title", "template.summary"),
    "major_capabilities": ("template.section.key_capabilities",),
    "verified_installation": ("template.section.installation",),
    "primary_example": ("template.section.quick_start",),
    "scope_and_limitations": ("template.section.scope_and_limitations",),
    "third_party_notices": ("template.section.third_party_notices",),
    "license": ("template.section.license",),
    "contextual_product_relationship": ("template.section.scope_and_limitations",),
}


def obligation_required_fact_fields(obligation: SourceClaimObligation) -> frozenset[str]:
    """Return fact fields every replacement for this obligation must cite."""

    return _OBLIGATION_FACT_FIELDS[obligation]


def obligation_any_fact_fields(obligation: SourceClaimObligation) -> frozenset[str]:
    """Return a field group from which at least one citation is required."""

    return _OBLIGATION_ANY_FACT_FIELDS.get(obligation, frozenset())


def obligation_provenance_prefixes(obligation: SourceClaimObligation) -> tuple[str, ...]:
    """Return exact golden-slot prefixes allowed to replace this obligation."""

    return _OBLIGATION_PROVENANCE_PREFIXES[obligation]


class SourceClaimRiskV1(BaseModel):
    """Deterministic publication obligation for one exact inherited claim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    risk_class: SourceClaimRiskClass
    obligation_id: SourceClaimObligation | None = None
    heading_path: list[str]
    rationale: str


def _normalized(value: str) -> str:
    return " ".join(strip_emoji_decorations(value).casefold().split())


def _heading_path(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
) -> list[str]:
    character_start = len(document.encode("utf-8")[: claim.source_byte_start].decode("utf-8"))
    return [
        _normalized(heading.title)
        for heading in parse_headings(document)
        if heading.heading_end <= character_start < heading.section_end
    ]


def classify_source_claim_risk(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
) -> SourceClaimRiskV1:
    """Return the fail-closed risk class derived from heading ancestry and claim shape."""

    path = _heading_path(document, claim)
    sections = path[1:] if path else []
    primary = sections[0] if sections else ""
    text = document.encode("utf-8")[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
    folded = _normalized(text)

    if "other platforms" in primary:
        return SourceClaimRiskV1(
            risk_class="governed_valid_omission",
            obligation_id="contextual_product_relationship",
            heading_path=path,
            rationale=(
                "A redundant platform-promotion block may be omitted only behind the "
                "fact-bound contextual product-relationship replacement."
            ),
        )
    if "third-party" in primary or "third party" in primary or "third-party" in folded:
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="third_party_notices",
            heading_path=path,
            rationale="Third-party attribution is a mandatory golden-contract obligation.",
        )
    if primary == "license" or primary.endswith(" license"):
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="license",
            heading_path=path,
            rationale="License disclosure is a mandatory golden-contract obligation.",
        )
    if "installation" in primary or "getting started" in primary:
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="verified_installation",
            heading_path=path,
            rationale="Installation claims require an exact verified-acquisition replacement.",
        )
    if (
        "limitation" in primary
        or "boundar" in primary
        or primary in {"scope", "scope and limitations"}
    ):
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="scope_and_limitations",
            heading_path=path,
            rationale="Limitations cannot be deferred or silently removed.",
        )
    if any(token in primary for token in ("feature", "capabilit")):
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="major_capabilities",
            heading_path=path,
            rationale="Major product capabilities require a repository-fact replacement.",
        )
    if "quick start" in primary or "quickstart" in primary:
        if len(sections) == 1:
            return SourceClaimRiskV1(
                risk_class="mandatory_fact_resolution",
                obligation_id="primary_example",
                heading_path=path,
                rationale="The primary quick-start example is a mandatory verified obligation.",
            )
        return SourceClaimRiskV1(
            risk_class="optional_explicit_deferral",
            heading_path=path,
            rationale="A secondary quick-start example may be deferred with exact evidence.",
        )
    if "mcp" in primary:
        return SourceClaimRiskV1(
            risk_class="optional_explicit_deferral",
            heading_path=path,
            rationale=(
                "MCP tools, setup, and dependency detail require a dedicated repository-source "
                "fact before they may be rewritten or omitted from protected content."
            ),
        )
    if "security" in primary:
        return SourceClaimRiskV1(
            risk_class="optional_explicit_deferral",
            heading_path=path,
            rationale=(
                "Security guidance requires dedicated repository-source evidence; generic "
                "product overview or capability prose cannot replace it."
            ),
        )
    if "contribut" in primary:
        return SourceClaimRiskV1(
            risk_class="optional_explicit_deferral",
            heading_path=path,
            rationale=(
                "Contribution instructions require repository-owned workflow evidence; generic "
                "product overview prose cannot replace them."
            ),
        )
    if primary == "repository map":
        return SourceClaimRiskV1(
            risk_class="optional_explicit_deferral",
            heading_path=path,
            rationale=(
                "Repository-layout detail requires an inventory-bound replacement and cannot be "
                "discharged by generic product overview prose."
            ),
        )
    if any(token in primary for token in ("build", "developer", "test")):
        return SourceClaimRiskV1(
            risk_class="optional_explicit_deferral",
            heading_path=path,
            rationale=(
                "Build and test commands require manifest or task-runner evidence before they "
                "may be rewritten or omitted from protected content."
            ),
        )
    if any(
        token in primary
        for token in ("api", "example", "development", "testing", "workflow", "golden")
    ):
        return SourceClaimRiskV1(
            risk_class="optional_explicit_deferral",
            heading_path=path,
            rationale=(
                "Exhaustive API, secondary-example, or historical workflow detail may be "
                "deferred while the exact source claim remains visible in evidence."
            ),
        )
    return SourceClaimRiskV1(
        risk_class="mandatory_fact_resolution",
        obligation_id="product_overview",
        heading_path=path,
        rationale=(
            "Opening and otherwise-unclassified product claims fail closed behind the verified "
            "product-overview obligation."
        ),
    )
