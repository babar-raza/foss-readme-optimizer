"""Build typed visitor-facing phrases from selected product facts."""

from __future__ import annotations

import re
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.facts.compatibility_rendering import (
    compatibility_phrases,
    ecosystem_display_label,
    ecosystem_label_items,
)
from readme_agent.facts.composer_factpack import ComposerFactpack
from readme_agent.facts.limitation_rendering import limitation_phrases
from readme_agent.facts.product_identity import canonical_aspose_family_name
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2

_ACCEPTED_STATES = {"verified", "policy_approved"}
_FAMILY_LABELS = {
    "3d": "Aspose.3D",
    "cells": "Aspose.Cells",
    "pdf": "Aspose.PDF",
}
_INTERNAL_TOKEN_RE = re.compile(
    r"(?:[a-z0-9]+_[a-z0-9_]+|[a-z0-9]+(?:-[a-z0-9]+)+/[A-Za-z0-9._-]+|://)",
    flags=re.IGNORECASE,
)
_KEY_VALUE_RE = re.compile(r"^[a-z][a-z0-9_]*\s*[:=]")
_VISITOR_REQUIRED_FIELDS = {
    "product.audience",
    "product.problems_solved",
    "product.capabilities",
    "product.formats",
}
_INTERPRETIVE_FIELDS = {"product.audience", "product.problems_solved"}


class VisitorFactRenderViewV1(BaseModel):
    """Fact-bound prose fragments that are safe to offer to an author."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: str
    field: str
    phrases: list[str]
    citation_fact_ids: list[str] = Field(min_length=1)


def _is_visitor_phrase(value: str) -> bool:
    phrase = value.strip()
    return bool(
        phrase
        and "\n" not in phrase
        and not _INTERNAL_TOKEN_RE.search(phrase)
        and not _KEY_VALUE_RE.search(phrase)
        and not any(character in phrase for character in "{}[]")
    )


def _text_phrases(value: object) -> list[str]:
    values = value if isinstance(value, list) else [value]
    return [
        str(item).strip() for item in values if isinstance(item, str) and _is_visitor_phrase(item)
    ]


def _sentence_phrases(value: object) -> list[str]:
    return [
        phrase for phrase in _text_phrases(value) if len(re.findall(r"[A-Za-z0-9]+", phrase)) >= 2
    ]


def _natural_join(values: list[str]) -> str:
    if len(values) < 2:
        return "".join(values)
    if len(values) == 2:
        return " and ".join(values)
    return ", ".join(values[:-1]) + f", and {values[-1]}"


def _format_phrases(value: object) -> list[str]:
    """Turn manifest-style format inventories into concise visitor prose."""

    phrases = _text_phrases(value)
    rendered: list[str] = []
    for phrase in phrases:
        match = re.fullmatch(
            r"(?i)(load|read|import|save|write|export|supported|support|input|output)"
            r"\s+formats?\s*:\s*(.+)",
            phrase.rstrip("."),
        )
        if match is None:
            rendered.append(phrase)
            continue
        formats = [
            item.strip()
            for item in match.group(2).split(",")
            if item.strip() and item.strip().casefold() != "auto"
        ]
        if not formats:
            continue
        verb = {
            "load": "Reads",
            "read": "Reads",
            "import": "Imports",
            "save": "Writes",
            "write": "Writes",
            "export": "Exports",
            "supported": "Supports",
            "support": "Supports",
            "input": "Reads",
            "output": "Writes",
        }[match.group(1).casefold()]
        rendered.append(f"{verb} {_natural_join(formats)} files")
    return rendered


def _audience_phrases(value: object) -> list[str]:
    phrases = _sentence_phrases(value)
    normalized: list[str] = []
    for phrase in phrases:
        for ecosystem, label in ecosystem_label_items():
            phrase = re.sub(
                rf"\busing\s+{re.escape(ecosystem)}\b",
                f"using {label}",
                phrase,
                flags=re.IGNORECASE,
            )
        normalized.append(phrase)
    return normalized


def _identity_phrases(value: object) -> list[str]:
    if not isinstance(value, dict):
        return []
    product_name = str(value.get("product_name") or "").strip()
    family_key = str(value.get("family") or "").strip().lower()
    canonical_product_name = canonical_aspose_family_name(product_name)
    family = (
        canonical_product_name
        or (product_name if _is_visitor_phrase(product_name) else None)
        or _FAMILY_LABELS.get(family_key)
    )
    if family is None and family_key:
        family = family_key.replace("-", " ").replace("_", " ").title()
    ecosystem = str(value.get("ecosystem") or value.get("platform") or "").strip().lower()
    platform = ecosystem_display_label(ecosystem) if ecosystem else None
    return [f"{family} FOSS for {platform}"] if family and platform else []


def _acquisition_manifest_path(facts: ProductFactsV2) -> str | None:
    """Resolve the manifest that owns the package users actually acquire."""

    acquisition = facts.selected_fact("installation.verified_acquisition")
    coordinates = facts.selected_fact("installation.coordinates")
    if (
        acquisition.verification_state not in _ACCEPTED_STATES
        or coordinates.verification_state not in _ACCEPTED_STATES
        or not isinstance(acquisition.value, dict)
    ):
        return None
    coordinate = acquisition.value.get("coordinate")
    if not isinstance(coordinate, dict):
        return None
    rows = coordinates.value if isinstance(coordinates.value, list) else [coordinates.value]
    coordinate_name = str(coordinate.get("name") or "").casefold()
    coordinate_group = str(coordinate.get("group_id") or "").casefold()
    coordinate_artifact = str(coordinate.get("artifact_id") or "").casefold()
    for row in rows:
        if not isinstance(row, dict):
            continue
        name_matches = coordinate_name and str(row.get("name") or "").casefold() == coordinate_name
        maven_matches = (
            coordinate_group
            and coordinate_artifact
            and str(row.get("group_id") or "").casefold() == coordinate_group
            and str(row.get("artifact_id") or "").casefold() == coordinate_artifact
        )
        if name_matches or maven_matches:
            manifest_path = str(row.get("manifest_path") or "").strip()
            return manifest_path or None
    return None


def _acquired_package_compatibility(facts: ProductFactsV2, value: object) -> object:
    manifest_path = _acquisition_manifest_path(facts)
    if manifest_path is None or not isinstance(value, list):
        return value
    matched = [
        row
        for row in value
        if isinstance(row, dict) and str(row.get("manifest_path") or "") == manifest_path
    ]
    return matched or value


def _no_direct_prose(_value: object) -> list[str]:
    """Keep internal policy codes and structured contracts out of authored prose."""

    return []


_FIELD_RENDERERS: dict[str, Callable[[object], list[str]]] = {
    "product.audience": _audience_phrases,
    "product.problems_solved": _sentence_phrases,
    "product.capabilities": _text_phrases,
    "product.formats": _format_phrases,
    "product.limitations": limitation_phrases,
    "product.identity": _identity_phrases,
    "product.compatibility": compatibility_phrases,
    "installation.verified_acquisition": _no_direct_prose,
    "relationship.commercial_foss": _no_direct_prose,
    "support.routes": _no_direct_prose,
}


def visitor_fact_render_view(
    facts: ProductFactsV2,
    field: str,
) -> VisitorFactRenderViewV1 | None:
    """Return a safe render view for one accepted selected fact, if supported."""

    renderer = _FIELD_RENDERERS.get(field)
    if renderer is None:
        return None
    fact: FactRecordV2 = facts.selected_fact(field)
    if fact.verification_state not in _ACCEPTED_STATES or fact.has_unresolved_conflict:
        return None
    if (
        field in _INTERPRETIVE_FIELDS
        and fact.source.source_type == "agent_drafted"
        and not fact.supporting_fact_ids
    ):
        return None
    value = (
        _acquired_package_compatibility(facts, fact.value)
        if field == "product.compatibility"
        else fact.value
    )
    phrases = list(dict.fromkeys(renderer(value)))
    if field in _VISITOR_REQUIRED_FIELDS and not phrases:
        return None
    return VisitorFactRenderViewV1(
        fact_id=fact.fact_id,
        field=field,
        phrases=phrases,
        citation_fact_ids=list(dict.fromkeys([fact.fact_id, *fact.supporting_fact_ids])),
    )


class AsposeEvidenceCitationV1(BaseModel):
    """A grounding citation into the T4 aspose.org detector evidence --
    distinct from a ProductFactsV2 `fact_id` citation, since this evidence
    has no FactRecordV2 counterpart yet."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    detector: str
    family: str
    platform: str
    source_id: str


class EvidenceGroundedRenderViewV2(BaseModel):
    """T4 / RC1 ("grounding evidence stripped before composition"): a render
    view whose citations can point at EITHER a ProductFactsV2 `fact_id` OR
    an aspose.org detector-sourced evidence reference, so a phrase drawn
    from `ComposerFactpack.aspose_detections` (which
    `VisitorFactRenderViewV1` cannot cite -- it only knows `ProductFactsV2`)
    never silently loses its grounding on the way into future composition.
    Deliberately does not compose new prose for aspose-only fields (that is
    later composition work, T5+/T7-series) -- it only carries literal
    source text (a keyword, a claim sentence) forward with its citation
    intact.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    field: str
    phrases: list[str]
    product_fact_citations: list[str] = Field(default_factory=list)
    aspose_evidence_citations: list[AsposeEvidenceCitationV1] = Field(default_factory=list)

    @model_validator(mode="after")
    def _grounded(self) -> EvidenceGroundedRenderViewV2:
        if self.phrases and not (self.product_fact_citations or self.aspose_evidence_citations):
            raise ValueError("rendered phrases must carry at least one grounding citation")
        return self


def _aspose_seo_keywords_view(factpack: ComposerFactpack) -> EvidenceGroundedRenderViewV2 | None:
    keywords = factpack.aspose_detections.seo_keywords
    if not keywords.entry_found or not keywords.keywords:
        return None
    return EvidenceGroundedRenderViewV2(
        field="aspose.seo_keywords",
        phrases=list(keywords.keywords),
        aspose_evidence_citations=[
            AsposeEvidenceCitationV1(
                detector="detect_seo_keywords",
                family=factpack.family,
                platform=factpack.platform,
                source_id=f"keywords/{factpack.family}.json",
            )
        ],
    )


def _aspose_dependency_claims_view(
    factpack: ComposerFactpack,
) -> EvidenceGroundedRenderViewV2 | None:
    claims = factpack.aspose_detections.dependency_claims
    phrases = [
        str(claim["text"])
        for claim in claims.claims
        if isinstance(claim.get("text"), str) and claim["text"].strip()
    ]
    if not phrases:
        return None
    return EvidenceGroundedRenderViewV2(
        field="aspose.dependency_claims",
        phrases=phrases,
        aspose_evidence_citations=[
            AsposeEvidenceCitationV1(
                detector="detect_dependency_claims",
                family=factpack.family,
                platform=factpack.platform,
                source_id=f"knowledge/{factpack.family}/{factpack.platform}/merged/claims.json",
            )
        ],
    )


_ASPOSE_ONLY_RENDERERS: dict[
    str, Callable[[ComposerFactpack], EvidenceGroundedRenderViewV2 | None]
] = {
    "aspose.seo_keywords": _aspose_seo_keywords_view,
    "aspose.dependency_claims": _aspose_dependency_claims_view,
}


def evidence_grounded_render_view(
    factpack: ComposerFactpack,
    field: str,
) -> EvidenceGroundedRenderViewV2 | None:
    """Return a grounded render view for one field, drawing from
    `ComposerFactpack.product_facts` (delegating to `visitor_fact_render_view`
    for every field that view already covers, so it never loses any of V1's
    grounding) or `ComposerFactpack.aspose_detections` (for fields with no
    `ProductFactsV2` counterpart yet)."""

    if field in _FIELD_RENDERERS:
        v1_view = visitor_fact_render_view(factpack.product_facts, field)
        if v1_view is None:
            return None
        return EvidenceGroundedRenderViewV2(
            field=field,
            phrases=v1_view.phrases,
            product_fact_citations=list(v1_view.citation_fact_ids),
        )
    aspose_renderer = _ASPOSE_ONLY_RENDERERS.get(field)
    if aspose_renderer is None:
        return None
    return aspose_renderer(factpack)
