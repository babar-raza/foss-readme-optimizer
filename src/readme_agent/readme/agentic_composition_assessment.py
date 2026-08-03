"""Project deterministic README assessment into bounded composition context."""

from readme_agent.readme.assessment import ReadmeAssessmentV1


def planning_sections(assessment: ReadmeAssessmentV1):
    """Bound agentic output to structural or materially actionable sections."""

    return [
        section
        for section in assessment.sections
        if section.level <= 2 or section.disposition != "preserve"
    ]


def planning_assessment_payload(assessment: ReadmeAssessmentV1) -> dict:
    """Project section authority without copying claim evidence into the prompt.

    The full assessment remains bound by ``full_assessment_sha256`` and the
    serialized plan's ``assessment_hash``. Deterministic validation and independent
    review consume material-claim evidence from the complete assessment.
    """

    return {
        "schema_version": assessment.schema_version,
        "org_repo": assessment.org_repo,
        "immutable_base_revision": assessment.immutable_base_revision,
        "source_sha256": assessment.source_sha256,
        "facts_hash": assessment.facts_hash,
        "full_assessment_sha256": assessment.canonical_hash(),
        "material_claim_count": len(assessment.material_claims),
        "untrusted_repository_instruction_count": len(assessment.untrusted_repository_instructions),
        "sections": [
            {
                "section_id": section.section_id,
                "heading": section.heading,
                "level": section.level,
                "source_byte_start": section.source_byte_start,
                "source_byte_end": section.source_byte_end,
                "disposition": section.disposition,
                "fact_ids": section.fact_ids,
                "protected_fragment_count": len(section.protected_fragment_ids),
                **(
                    {"evidence": section.evidence, "rationale": section.rationale}
                    if section.disposition != "preserve"
                    else {}
                ),
            }
            for section in planning_sections(assessment)
        ],
    }
