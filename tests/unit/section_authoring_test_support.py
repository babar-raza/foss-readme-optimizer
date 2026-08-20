"""Shared ProductFactsV2 fixture builders for the section-authoring test suite.

Mirrors `test_composer_factpack.py::_ready_product_facts`'s pattern: every
`REQUIRED_PRODUCT_FIELDS` entry gets a default verified fact so the object passes
`ProductFactsV2`'s referential-completeness validator, with per-field overrides and
`extra_facts` for whatever one test needs to vary. Not a test file itself (no
`test_` prefix) -- imported by the section-authoring test modules.
"""

from __future__ import annotations

from readme_agent.facts.evidence_polarity import EvidencePolarityAssessmentV1
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactConflictV2,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)

SOURCE_REVISION = "a" * 40


def build_fact_source(location: str = "repository://org/repo") -> FactSourceV2:
    return FactSourceV2(
        source_type="mechanical_repository",
        location=location,
        source_revision=SOURCE_REVISION,
    )


def build_conflict(*, conflicting_fact_id: str, status: str = "unresolved") -> FactConflictV2:
    return FactConflictV2(
        conflicting_fact_id=conflicting_fact_id,
        conflicting_value="a competing value",
        conflicting_source=build_fact_source(),
        status=status,
        reason="two sources disagree",
        authoritative_owner="repository-owner",
        affected_surfaces=["readme"],
    )


def build_evidence_assessment(
    fact_id: str,
    *,
    field: str,
    accepted: bool = True,
    observed_polarity: str = "positive_implementation",
) -> EvidencePolarityAssessmentV1:
    expected_polarity = (
        "explicit_constraint" if field == "product.limitations" else "positive_implementation"
    )
    return EvidencePolarityAssessmentV1(
        fact_id=fact_id,
        claim_text="the candidate claim text",
        expected_polarity=expected_polarity,
        observed_polarity=observed_polarity,
        source_path="src/example.py",
        source_revision=SOURCE_REVISION,
        line_number=1,
        anchor="def example",
        exact_excerpt="def example():",
        context_excerpt="def example():\n    pass",
        accepted=accepted,
        reason="matches the accepted claim",
    )


def build_fact(
    fact_id: str,
    field: str,
    value: object,
    *,
    verification_state: str = "verified",
    conflicts: list[FactConflictV2] | None = None,
    evidence_assessments: list[EvidencePolarityAssessmentV1] | None = None,
    supporting_fact_ids: list[str] | None = None,
) -> FactRecordV2:
    return FactRecordV2(
        fact_id=fact_id,
        field=field,
        value=value,
        source=build_fact_source(),
        verification_state=verification_state,
        authoritative_owner="repository-owner",
        confidence=1.0,
        conflicts=conflicts or [],
        affected_surfaces=["readme"],
        evidence_assessments=evidence_assessments,
        supporting_fact_ids=supporting_fact_ids or [],
    )


def build_product_facts_v2(
    org_repo: str = "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
    *,
    field_values: dict[str, object] | None = None,
    extra_facts: list[FactRecordV2] | None = None,
) -> ProductFactsV2:
    """A fully valid ProductFactsV2 with every required field selected and `verified`,
    plus any `extra_facts` (e.g. a deliberately unverified/conflicting/stubbed fact a
    specific test needs) appended and left out of `selected_fact_ids`."""

    field_values = field_values or {}
    required_facts = [
        FactRecordV2(
            fact_id=descriptive_fact_id(field, "fixture"),
            field=field,
            value=field_values.get(field, f"{field} placeholder value"),
            source=build_fact_source(f"repository://{org_repo}"),
            verification_state="verified",
            authoritative_owner="repository-owner",
            confidence=1.0,
            affected_surfaces=["readme"],
        )
        for field in REQUIRED_PRODUCT_FIELDS
    ]
    return ProductFactsV2(
        org_repo=org_repo,
        facts=required_facts + list(extra_facts or []),
        selected_fact_ids={
            field: descriptive_fact_id(field, "fixture") for field in REQUIRED_PRODUCT_FIELDS
        },
    )
