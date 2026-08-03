"""Project factual-review evidence into bounded LLM-facing context."""

import hashlib
import json
from typing import Any

_EVIDENCE_ASSESSMENT_PROMPT_KEYS = (
    "claim_text",
    "expected_polarity",
    "observed_polarity",
    "source_path",
    "line_number",
    "anchor",
    "exact_excerpt",
    "accepted",
)


def compact_evidence_assessments(value: object) -> list[dict[str, Any]]:
    """Retain citable evidence without context windows, timestamps, or receipts."""

    if not isinstance(value, list):
        return []
    return [
        {key: item[key] for key in _EVIDENCE_ASSESSMENT_PROMPT_KEYS if key in item}
        for item in value
        if isinstance(item, dict)
    ]


def claim_polarity(fact: dict[str, Any]) -> tuple[str, str, str]:
    """Return the selected fact's compact accepted polarity disposition."""

    accepted = next(
        (
            item
            for item in fact.get("evidence_assessments") or []
            if isinstance(item, dict) and item.get("accepted")
        ),
        None,
    )
    if accepted is None:
        return "positive_implementation", "positive_implementation", "supports"
    expected = str(accepted.get("expected_polarity") or "positive_implementation")
    observed = str(accepted.get("observed_polarity") or expected)
    return expected, observed, "supports" if expected == observed else "contradicts"


def compact_plan_context(
    *,
    surface_plan: dict[str, Any],
    source_sections: list[dict[str, Any]],
    operations: list[dict[str, Any]],
    candidate_claims: list[dict[str, Any]],
) -> dict[str, Any]:
    """Keep review authority while removing producer evidence duplicated by selected facts."""

    surface_artifact = json.dumps(
        surface_plan,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    compact_surface: dict[str, Any] = {
        key: surface_plan[key]
        for key in (
            "schema_version",
            "content_assurance",
            "org_repo",
            "immutable_base_revision",
            "facts_hash",
            "source_sha256",
            "archetype",
            "candidate_sha256",
        )
        if key in surface_plan
    }
    compact_surface["full_artifact_sha256"] = hashlib.sha256(surface_artifact).hexdigest()
    compact_surface["findings"] = [
        {
            key: finding[key]
            for key in ("finding_id", "dimension", "surface_id", "disposition", "summary")
            if key in finding
        }
        for finding in surface_plan.get("findings") or []
        if isinstance(finding, dict)
    ]
    compact_surface["actions"] = [
        {
            key: item
            for key, item in action.items()
            if key
            in {
                "action_id",
                "surface_id",
                "region_id",
                "disposition",
                "fact_ids",
                "ownership_class",
                "proposed_operation",
                "patch_sha256",
            }
        }
        for action in surface_plan.get("actions") or []
        if isinstance(action, dict)
    ]
    claim_artifact = json.dumps(
        candidate_claims,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    accountable = [claim for claim in candidate_claims if _is_accountable_claim(claim)]
    exceptions = [claim for claim in candidate_claims if not _is_accountable_claim(claim)]
    return {
        "surface_plan": compact_surface,
        "source_sections": _compact_source_sections(source_sections),
        "operations": [
            {
                key: operation[key]
                for key in (
                    "operation_id",
                    "operation",
                    "fact_ids",
                    "protected_content_treatment",
                )
            }
            for operation in operations
        ],
        "claim_accountability": {
            "full_artifact_sha256": hashlib.sha256(claim_artifact).hexdigest(),
            "total_claim_count": len(candidate_claims),
            "accountable_claim_count": len(accountable),
            "exception_claim_count": len(exceptions),
            "coverage_by_fact": _claim_coverage(accountable, key="fact_id"),
            "exception_claims": [dict(claim) for claim in exceptions],
        },
    }


def _is_accountable_claim(claim: dict[str, Any]) -> bool:
    return (
        claim.get("verification_state") in {"verified", "policy_approved"}
        and claim.get("accountability_disposition") == "accepted_fact"
        and claim.get("polarity_result") == "supports"
        and bool(claim.get("expected_polarity"))
        and bool(claim.get("observed_polarity"))
        and bool(claim.get("fact_id"))
        and not claim.get("unresolved_conflicts")
    )


def _claim_coverage(claims: list[dict[str, Any]], *, key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        groups.setdefault(str(claim[key]), []).append(claim)
    return [
        {
            key: group_id,
            "claim_count": len(group),
            "section_ids": sorted({_claim_section_id(claim) for claim in group}),
        }
        for group_id, group in sorted(groups.items())
    ]


def _compact_source_sections(source_sections: list[dict[str, Any]]) -> dict[str, Any]:
    artifact = json.dumps(
        source_sections,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    disposition_counts: dict[str, int] = {}
    protected_fragment_ids: set[str] = set()
    detailed_sections: list[dict[str, Any]] = []
    for section in source_sections:
        disposition = str(section.get("disposition") or "unspecified")
        disposition_counts[disposition] = disposition_counts.get(disposition, 0) + 1
        protected_fragment_ids.update(
            str(fragment_id) for fragment_id in section.get("protected_fragment_ids") or []
        )
        if disposition != "preserve":
            detailed_sections.append(
                {
                    key: section[key]
                    for key in (
                        "section_id",
                        "heading",
                        "disposition",
                        "fact_ids",
                        "protected_fragment_ids",
                    )
                    if key in section
                }
            )
    protected_artifact = "\x00".join(sorted(protected_fragment_ids)).encode("utf-8")
    return {
        "full_artifact_sha256": hashlib.sha256(artifact).hexdigest(),
        "total_section_count": len(source_sections),
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "protected_fragment_count": len(protected_fragment_ids),
        "protected_fragment_ids_sha256": hashlib.sha256(protected_artifact).hexdigest(),
        "detailed_non_preserve_sections": detailed_sections,
    }


def _claim_section_id(claim: dict[str, Any]) -> str:
    return str(claim["operation_id"]).split(".claim:", 1)[0]
