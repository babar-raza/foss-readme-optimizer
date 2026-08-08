"""Classify removed source README claims against golden-contract obligations."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.presentation_lint_text import strip_emoji_decorations
from readme_agent.readme.source_claim_obligations import (
    SourceClaimObligation,
    applicable_product_overview_fact_ids,
    obligation_any_fact_fields,
    obligation_provenance_prefixes,
    obligation_required_fact_fields,
    obligation_required_standard_ids,
    obligation_requires_source_entailment,
)

__all__ = [
    "SourceClaimObligation",
    "applicable_product_overview_fact_ids",
    "obligation_any_fact_fields",
    "obligation_provenance_prefixes",
    "obligation_requires_source_entailment",
    "obligation_required_fact_fields",
    "obligation_required_standard_ids",
]

SourceClaimRiskClass = Literal[
    "mandatory_fact_resolution",
    "optional_explicit_deferral",
    "governed_valid_omission",
]
_OTHER_PLATFORMS_HEADING = re.compile(r"other platforms(?: \(official [^)]+\))?")


class SourceClaimRiskV1(BaseModel):
    """Deterministic publication obligation for one exact inherited claim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    risk_class: SourceClaimRiskClass
    obligation_id: SourceClaimObligation | None = None
    heading_path: list[str]
    rationale: str


def _normalized(value: str) -> str:
    return " ".join(strip_emoji_decorations(value).casefold().split())


def _is_atomic_license_claim(value: str) -> bool:
    words = re.findall(r"[a-z0-9]+", value)
    sentences = [item for item in re.split(r"[.!?]+", value) if item.strip()]
    return bool(
        len(sentences) == 1
        and len(words) <= 24
        and (
            value.startswith("mit license")
            or "licensed under" in value
            or "released under" in value
            or value.startswith("license:")
        )
    )


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

    if not primary and folded.startswith("[!["):
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="header_badges",
            heading_path=path,
            rationale="Inherited badges require the fact-bound configured header badge slot.",
        )
    if primary == "navigation":
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="navigation",
            heading_path=path,
            rationale="Inherited navigation requires the configured canonical navigation slot.",
        )
    if primary == "at a glance":
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="at_a_glance",
            heading_path=path,
            rationale=(
                "Inherited visual product claims require the fact-bound canonical at-a-glance slot."
            ),
        )
    if _OTHER_PLATFORMS_HEADING.fullmatch(primary):
        return SourceClaimRiskV1(
            risk_class="governed_valid_omission",
            obligation_id="contextual_product_relationship",
            heading_path=path,
            rationale=(
                "A redundant platform-promotion block may be omitted only behind the "
                "fact-bound contextual product-relationship replacement."
            ),
        )
    if (
        "aspose" in folded
        and "foss" in folded
        and any(marker in folded for marker in ("enterprise edition", "commercial edition"))
    ):
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="contextual_product_relationship",
            heading_path=path,
            rationale=(
                "Explicit Aspose FOSS and Enterprise relationship prose requires the selected "
                "commercial/FOSS relationship fact and its exact candidate slot."
            ),
        )
    if primary == "license" or primary.endswith(" license") or _is_atomic_license_claim(folded):
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="license",
            heading_path=path,
            rationale="License disclosure is a mandatory golden-contract obligation.",
        )
    if re.search(
        r"\b(?:python|java|node(?:\.js)?|typescript|rust|go)\s+(?:version\s+)?v?\d",
        folded,
    ) or re.search(r"(?:^|\s)(?:\.net|net)\s*(?:core\s*)?\d", folded):
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="compatibility",
            heading_path=path,
            rationale=(
                "Runtime and platform-version claims require exact selected compatibility facts; "
                "generic product-overview facts cannot replace them."
            ),
        )
    if (
        "third-party" in primary
        or "third party" in primary
        or folded.startswith("third-party notices")
    ):
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="third_party_notices",
            heading_path=path,
            rationale="Third-party attribution is a mandatory golden-contract obligation.",
        )
    if any(
        marker in folded
        for marker in (
            "coming soon",
            "not supported",
            "unsupported",
            "does not support",
            "cannot ",
            "currently supports only",
        )
    ) and not (
        "installation" in primary
        or "getting started" in primary
        or "quick start" in primary
        or "quickstart" in primary
        or primary == "additional examples"
        or "api" in primary
        or "documentation" in primary
        or primary == "resources"
        or any(token in primary for token in ("build", "developer", "test"))
    ):
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="scope_and_limitations",
            heading_path=path,
            rationale="Claim-level limitations cannot be deferred under a feature heading.",
        )
    if primary.startswith("about "):
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            heading_path=path,
            rationale=(
                "Maintainer-authored product detail requires claim-specific evidence; a generic "
                "overview cannot silently replace it."
            ),
        )
    if "installation" in primary or "getting started" in primary:
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="verified_installation",
            heading_path=path,
            rationale="Installation claims require an exact verified-acquisition replacement.",
        )
    if primary in {"requirements", "dependencies", "prerequisites"}:
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="dependency_requirements",
            heading_path=path,
            rationale=(
                "Dependency and optional-extra claims require exact manifest or repository "
                "evidence in the canonical installation section."
            ),
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
    if any(token in primary for token in ("feature", "capabilit", "format")):
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="major_capabilities",
            heading_path=path,
            rationale=(
                "Granular feature and format claims require claim-specific repository evidence; "
                "a broad capability slot cannot replace them."
            ),
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
    if primary == "additional examples" or primary.endswith(" examples"):
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="additional_examples",
            heading_path=path,
            rationale=(
                "Inherited additional examples require the repository-inventory-backed "
                "additional-examples slot."
            ),
        )
    if "api" in primary and folded in {
        "<details> <summary>view the supported public api surface</summary>",
        "</details>",
    }:
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="api_structure",
            heading_path=path,
            rationale=(
                "The exact API disclosure shell requires the configured API-reference slot, "
                "not a fabricated product fact."
            ),
        )
    if "api" in primary:
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="api_public_surface",
            heading_path=path,
            rationale=(
                "Inherited API detail requires the repository-source-backed public API slot."
            ),
        )
    if "documentation" in primary or primary in {"resources", "documentation & resources"}:
        support_claim = any(
            marker in folded for marker in ("open an issue", "bug", "feature request", "support")
        )
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="support_routes" if support_claim else "documentation_resources",
            heading_path=path,
            rationale=(
                "Inherited support guidance requires a real fact-bound support slot."
                if support_claim
                else (
                    "Inherited documentation guidance requires a real fact-bound documentation "
                    "slot."
                )
            ),
        )
    if "mcp" in primary:
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            heading_path=path,
            rationale=(
                "MCP tools, setup, and dependency detail require a dedicated repository-source "
                "fact before they may be rewritten or omitted from protected content."
            ),
        )
    if "security" in primary:
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="security_guidance",
            heading_path=path,
            rationale=(
                "Security guidance is mandatory and requires dedicated repository-source "
                "evidence; generic overview prose cannot replace it."
            ),
        )
    if "contribut" in primary:
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="contribution_guidance",
            heading_path=path,
            rationale=(
                "Contribution instructions require repository-owned workflow evidence; generic "
                "product overview prose cannot replace them."
            ),
        )
    if primary == "repository map":
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="repository_map",
            heading_path=path,
            rationale=(
                "Repository-layout detail requires an inventory-bound replacement and cannot be "
                "discharged by generic product overview prose."
            ),
        )
    if "third-party" in folded and "notice" in folded:
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="third_party_notices",
            heading_path=path,
            rationale="Third-party notice links require the repository-owned notices-file slot.",
        )
    if "golden" in primary:
        return SourceClaimRiskV1(
            risk_class="optional_explicit_deferral",
            heading_path=path,
            rationale=(
                "Internal golden-test workflow detail may be withheld from the visitor README "
                "only with an exact deferred source record."
            ),
        )
    if any(token in primary for token in ("build", "develop", "test")):
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="development_commands",
            heading_path=path,
            rationale=(
                "Build and test commands require manifest or task-runner evidence before they "
                "may be rewritten or omitted from protected content."
            ),
        )
    if any(token in primary for token in ("acknowledgment", "attribution")):
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            heading_path=path,
            rationale=(
                "Maintainer-authored acknowledgment and attribution require exact ownership or "
                "repository evidence and cannot be replaced by product prose."
            ),
        )
    if any(
        token in primary
        for token in (
            "api",
            "architecture",
            "resource",
            "example",
            "development",
            "testing",
            "workflow",
            "golden",
        )
    ):
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            heading_path=path,
            rationale=(
                "API, architecture, resource, example, and workflow details require exact "
                "repository evidence; generic overview prose is not equivalent."
            ),
        )
    if not primary:
        return SourceClaimRiskV1(
            risk_class="mandatory_fact_resolution",
            obligation_id="product_overview",
            heading_path=path,
            rationale=(
                "Inherited opening prose requires the complete fact-bound title and summary slots."
            ),
        )
    return SourceClaimRiskV1(
        risk_class="mandatory_fact_resolution",
        heading_path=path,
        rationale=(
            "Otherwise-unclassified product claims require claim-specific evidence or an "
            "authoritative owner; generic product-overview substitution is prohibited."
        ),
    )
