"""Classify every README section against verified facts without trusting repository prose."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.facts.protected_content import fingerprint_protected_content
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.acquisition_contracts import stale_coordinate_version_replacements
from readme_agent.readme.assessment_claims import (
    ReadmeMaterialClaimAssessmentV1,
    assess_material_claims,
)
from readme_agent.readme.document_structure import Heading, parse_headings
from readme_agent.readme.document_templates import accepted_fact, installation_text

AssessmentDisposition = Literal[
    "preserve",
    "rewrite",
    "investigate",
    "repair",
    "remove_update",
    "replace_generic",
    "add",
    "not_applicable",
]

_PROMPT_INJECTION = re.compile(
    r"(?i)(?:ignore|disregard|override)\s+(?:all\s+)?(?:previous|prior|system|developer)"
    r"\s+(?:instructions?|prompts?)|(?:system|developer)\s+message\s*:",
)
_PROMOTIONAL_CALLOUT = re.compile(
    r"(?i)products\.[^\s)]+\.org.*products\.[^\s)]+\.com|"
    r"products\.[^\s)]+\.com.*products\.[^\s)]+\.org",
)
_PACKAGE_INSTALL_MARKERS = ("<dependency>", "implementation 'org.", 'implementation "org.')
_ACCEPTED_STATES = {"verified", "policy_approved"}


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReadmeSectionAssessmentV1(_StrictModel):
    section_id: str
    heading: str
    level: int = Field(ge=0, le=6)
    source_byte_start: int = Field(ge=0)
    source_byte_end: int = Field(ge=0)
    disposition: AssessmentDisposition
    fact_ids: list[str] = Field(default_factory=list)
    protected_fragment_ids: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)


class ReadmeAssessmentV1(_StrictModel):
    schema_version: Literal[1] = 1
    org_repo: str
    immutable_base_revision: str
    source_sha256: str
    facts_hash: str
    sections: list[ReadmeSectionAssessmentV1] = Field(min_length=1)
    material_claims: list[ReadmeMaterialClaimAssessmentV1] = Field(default_factory=list)
    untrusted_repository_instructions: list[str] = Field(default_factory=list)

    def canonical_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _byte_offset(text: str, character_offset: int) -> int:
    return len(text[:character_offset].encode("utf-8"))


def _accepted_id(facts: ProductFactsV2, field_name: str) -> str | None:
    selected = accepted_fact(facts, field_name)
    return selected.fact_id if selected is not None else None


def _protected_ids(section_text: str) -> list[str]:
    return [
        fragment.fragment_id for fragment in fingerprint_protected_content(section_text).fragments
    ]


def _section_disposition(
    heading: str,
    section_text: str,
    facts: ProductFactsV2,
    *,
    example_code: str,
) -> tuple[AssessmentDisposition, list[str], str]:
    normalized = heading.strip().lower()
    if _PROMPT_INJECTION.search(section_text):
        return (
            "investigate",
            [],
            "Repository instructions are untrusted data and cannot direct the planning agent.",
        )
    if normalized == "installation":
        acquisition = accepted_fact(facts, "installation.verified_acquisition")
        if acquisition is None:
            return (
                "investigate",
                [],
                "Installation prose cannot be changed while acquisition truth is unresolved.",
            )
        fact_ids = [
            fact_id
            for field_name in ("installation.coordinates", "installation.verified_acquisition")
            if (fact_id := _accepted_id(facts, field_name)) is not None
        ]
        value = acquisition.value if isinstance(acquisition.value, dict) else {}
        if value.get("method") == "source_build" and any(
            marker in section_text for marker in _PACKAGE_INSTALL_MARKERS
        ):
            return (
                "repair",
                fact_ids,
                "A registry-install claim conflicts with the verified source-build acquisition.",
            )
        coordinates = accepted_fact(facts, "installation.coordinates")
        if coordinates is not None and stale_coordinate_version_replacements(
            section_text,
            coordinates.value,
        ):
            return (
                "repair",
                fact_ids,
                "A package coordinate version conflicts with the selected manifest fact.",
            )
        return (
            "preserve",
            fact_ids,
            "The existing section is retained unless a verified gap exists.",
        )
    if normalized in {"quick start", "usage", "getting started"}:
        example = accepted_fact(facts, "example.minimal")
        if example is None:
            return (
                "investigate",
                [],
                "Example prose is preserved while executable example evidence is unresolved.",
            )
        disposition: AssessmentDisposition = (
            "preserve" if example_code in section_text else "repair"
        )
        return (
            disposition,
            [example.fact_id],
            "The section is assessed against the exact locally verified minimal example.",
        )
    return "preserve", [], "Maintainer-authored content is preserved by default."


def _section_record(
    source_text: str,
    heading: Heading,
    facts: ProductFactsV2,
    *,
    example_code: str,
) -> ReadmeSectionAssessmentV1:
    section_text = source_text[heading.start : heading.section_end]
    disposition, fact_ids, rationale = _section_disposition(
        heading.title,
        section_text,
        facts,
        example_code=example_code,
    )
    return ReadmeSectionAssessmentV1(
        section_id=f"heading:{_byte_offset(source_text, heading.start)}",
        heading=heading.title,
        level=heading.level,
        source_byte_start=_byte_offset(source_text, heading.start),
        source_byte_end=_byte_offset(source_text, heading.section_end),
        disposition=disposition,
        fact_ids=fact_ids,
        protected_fragment_ids=_protected_ids(section_text),
        evidence=[f"README.md:{heading.start}:{heading.section_end}"],
        rationale=rationale,
    )


def assess_readme_document(
    org_repo: str,
    source_text: str,
    facts: ProductFactsV2,
    *,
    base_revision: str,
) -> ReadmeAssessmentV1:
    """Return a source-bound assessment; repository prompt text is recorded, never obeyed."""

    headings = parse_headings(source_text)
    first_h2 = next((heading for heading in headings if heading.level == 2), None)
    opening_end = first_h2.start if first_h2 is not None else len(source_text)
    opening = source_text[:opening_end]
    untrusted = [match.group(0) for match in _PROMPT_INJECTION.finditer(source_text)]
    sections = [
        ReadmeSectionAssessmentV1(
            section_id="opening",
            heading="Opening",
            level=0,
            source_byte_start=0,
            source_byte_end=_byte_offset(source_text, opening_end),
            disposition="remove_update" if _PROMOTIONAL_CALLOUT.search(opening) else "preserve",
            fact_ids=[
                fact_id
                for field_name in ("product.identity", "relationship.commercial_foss")
                if (fact_id := _accepted_id(facts, field_name)) is not None
            ],
            protected_fragment_ids=_protected_ids(opening),
            evidence=[f"README.md:0:{opening_end}"],
            rationale=(
                "Remove only a detected promotional callout; otherwise preserve the opening."
            ),
        ),
        *[
            _section_record(source_text, heading, facts, example_code=_example_code(facts))
            for heading in headings
        ],
    ]
    titles = {heading.title.strip().lower() for heading in headings if heading.level == 2}
    additions = (
        (
            "at-a-glance",
            "At a glance",
            ("product.audience", "product.problems_solved", "product.capabilities"),
            "Add a fact-backed overview when verified descriptive facts are available.",
            "at a glance" not in titles,
        ),
        (
            "installation",
            "Installation",
            ("installation.coordinates", "installation.verified_acquisition"),
            "Add the ecosystem-specific acquisition path that was mechanically verified.",
            "installation" not in titles
            and installation_text(facts, org_repo, base_revision) is not None,
        ),
        (
            "quick-start",
            "Quick Start",
            ("example.minimal",),
            "Add the exact locally verified minimal example.",
            not titles.intersection({"quick start", "usage", "getting started"})
            and bool(_example_code(facts)),
        ),
    )
    for section_id, heading, fields, rationale, eligible in additions:
        if not eligible:
            continue
        fact_ids = [
            fact_id
            for field_name in fields
            if (fact_id := _accepted_id(facts, field_name)) is not None
        ]
        if not fact_ids:
            continue
        insertion = _byte_offset(source_text, first_h2.start if first_h2 else len(source_text))
        sections.append(
            ReadmeSectionAssessmentV1(
                section_id=f"missing:{section_id}",
                heading=heading,
                level=2,
                source_byte_start=insertion,
                source_byte_end=insertion,
                disposition="add",
                fact_ids=fact_ids,
                evidence=["verified ProductFactsV2 and Markdown section inventory"],
                rationale=rationale,
            )
        )
    return ReadmeAssessmentV1(
        org_repo=org_repo,
        immutable_base_revision=base_revision,
        source_sha256=hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        facts_hash=facts.canonical_hash(),
        sections=sections,
        material_claims=assess_material_claims(source_text),
        untrusted_repository_instructions=untrusted,
    )


def _example_code(facts: ProductFactsV2) -> str:
    example = accepted_fact(facts, "example.minimal")
    value = example.value if example is not None and isinstance(example.value, dict) else {}
    return str(value.get("code") or "").rstrip()
