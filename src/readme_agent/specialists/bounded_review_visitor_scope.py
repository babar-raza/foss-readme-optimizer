"""Define and enforce section-local authority for bounded visitor review packets."""

from __future__ import annotations

from collections.abc import Sequence

from readme_agent.specialists.review_finding_grounding import (
    BLIND_QUALITY_CRITERIA,
    GroundedReviewFindingV1,
)

_COMMON_CRITERIA = frozenset(
    {
        "clarity",
        "product_specificity",
        "internal_terminology",
        "markdown_integrity",
    }
)
_CRITERIA_BY_ROOT = {
    "front-matter": _COMMON_CRITERIA | {"hierarchy", "promotional_balance", "template_genericity"},
    "navigation": frozenset({"hierarchy", "navigation", "markdown_integrity"}),
    "at-a-glance": _COMMON_CRITERIA | {"hierarchy", "visible_duplication", "template_genericity"},
    "key-capabilities": _COMMON_CRITERIA
    | {"hierarchy", "visible_duplication", "template_genericity"},
    "installation": _COMMON_CRITERIA | {"installation_presentation"},
    "quick-start": _COMMON_CRITERIA | {"example_presentation", "visible_duplication"},
    "additional-examples": _COMMON_CRITERIA | {"example_presentation", "visible_duplication"},
    "development-and-testing": _COMMON_CRITERIA | {"example_presentation"},
    "scope-and-limitations": _COMMON_CRITERIA | {"promotional_balance", "visible_duplication"},
}
_DEFAULT_CRITERIA = _COMMON_CRITERIA | {
    "hierarchy",
    "visible_duplication",
    "template_genericity",
}
_MECHANICAL_CHECKS_BY_ROOT = {
    "front-matter": frozenset({"document.h1_blocks", "header.badge_rows"}),
    "navigation": frozenset({"document.duplicate_h2_headings", "document.required_h2_prefix"}),
    "quick-start": frozenset({"quick_start.fenced_blocks", "quick_start.max_nonblank_code_lines"}),
}
_COMMON_STANDARD_IDS = frozenset({"readme.no_comments", "readme.public_language"})
_STANDARD_IDS_BY_ROOT = {
    "front-matter": _COMMON_STANDARD_IDS | {"readme.header", "readme.badges"},
    "navigation": _COMMON_STANDARD_IDS | {"readme.navigation"},
    "at-a-glance": _COMMON_STANDARD_IDS | {"readme.at_a_glance_mermaid"},
    "quick-start": _COMMON_STANDARD_IDS | {"readme.primary_example"},
    "additional-examples": _COMMON_STANDARD_IDS | {"readme.primary_example"},
    "scope-and-limitations": _COMMON_STANDARD_IDS | {"readme.enterprise_edition_terminology"},
    "license": _COMMON_STANDARD_IDS | {"readme.license"},
}


def bounded_visitor_scope(
    section_path: str,
    *,
    neighbor_context_before: str,
    neighbor_context_after: str,
) -> dict:
    """Return the exact visitor authority for one target-section packet."""

    root = section_path.split("/", maxsplit=1)[0]
    applicable = _CRITERIA_BY_ROOT.get(root, _DEFAULT_CRITERIA)
    mechanical = _MECHANICAL_CHECKS_BY_ROOT.get(root, frozenset())
    return {
        "mode": "target_section_only",
        "target_section_path": section_path,
        "finding_evidence_scope": "target_section_anchors_only",
        "applicable_criteria": sorted(applicable),
        "out_of_scope_criteria": sorted(set(BLIND_QUALITY_CRITERIA) - applicable),
        "applicable_mechanical_check_ids": sorted(mechanical),
        "mechanical_observation_scope": "complete_candidate_context_only",
        "neighbor_context_before": neighbor_context_before,
        "neighbor_context_after": neighbor_context_after,
    }


def bounded_visitor_contract(visitor_contract: dict, section_path: str) -> dict:
    """Project the global visitor contract onto one packet's section authority."""

    root = section_path.split("/", maxsplit=1)[0]
    allowed_standard_ids = _STANDARD_IDS_BY_ROOT.get(root, _COMMON_STANDARD_IDS)
    standards = visitor_contract.get("configured_standards", [])
    projected_standards = [
        item
        for item in standards
        if isinstance(item, dict) and item.get("standard_id") in allowed_standard_ids
    ]
    if root == "additional-examples":
        projected_standards = [
            _secondary_example_standard(item)
            if item.get("standard_id") == "readme.primary_example"
            else item
            for item in projected_standards
        ]
    return {
        key: value for key, value in visitor_contract.items() if key != "configured_standards"
    } | {"configured_standards": projected_standards}


def _secondary_example_standard(item: dict) -> dict:
    """Keep only the primary-example fields that govern secondary examples."""

    parameters = item.get("parameters") or {}
    allowed = {
        "secondary_examples",
        "secondary_examples_intro",
        "public_internal_assurance",
        "duplicate_generic_headings",
    }
    return {
        **item,
        "parameters": {key: value for key, value in parameters.items() if key in allowed},
    }


def bounded_visitor_scope_errors(
    findings: Sequence[GroundedReviewFindingV1],
    *,
    applicable_criteria: frozenset[str],
    applicable_mechanical_check_ids: frozenset[str],
) -> list[str]:
    """Reject global criteria and mechanical checks outside one packet's authority."""

    errors: list[str] = []
    for finding in findings:
        if finding.criterion not in applicable_criteria:
            errors.append(
                f"{finding.finding_id}:criterion {finding.criterion} is outside bounded scope"
            )
        if (
            finding.mechanical_check_id is not None
            and finding.mechanical_check_id not in applicable_mechanical_check_ids
        ):
            errors.append(
                f"{finding.finding_id}:mechanical check {finding.mechanical_check_id} "
                "is outside bounded scope"
            )
    return errors


__all__ = [
    "bounded_visitor_contract",
    "bounded_visitor_scope",
    "bounded_visitor_scope_errors",
]
