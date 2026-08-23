"""Normalize redundant reviewer fields before typed result validation."""

from __future__ import annotations

import re


def _normalized_finding_id(value: object) -> str:
    raw = str(value).strip().casefold()
    normalized = re.sub(r"[^a-z0-9_.-]+", "-", raw).strip("._-")
    if normalized and not normalized[0].isalpha():
        normalized = f"finding-{normalized}"
    return normalized or "finding"


def normalize_redundant_role_fields(role: str, value: object) -> object:
    """Derive redundant summaries from verdict and findings without changing either."""

    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    findings = normalized.get("findings")
    if isinstance(findings, list):
        normalized_items: list[object] = []
        finding_id_occurrences: dict[str, int] = {}
        for item in findings:
            if not isinstance(item, dict):
                normalized_items.append(item)
                continue
            normalized_item = dict(item)
            if isinstance(normalized_item.get("finding_id"), str):
                base_finding_id = _normalized_finding_id(normalized_item["finding_id"])
                occurrence = finding_id_occurrences.get(base_finding_id, 0) + 1
                finding_id_occurrences[base_finding_id] = occurrence
                normalized_item["finding_id"] = (
                    base_finding_id if occurrence == 1 else f"{base_finding_id}.{occurrence}"
                )
            if role == "blind_quality" and normalized_item.get("kind") == "quality":
                for field in (
                    "fact_id",
                    "evidence_excerpt",
                    "evidence_location",
                    "expected_polarity",
                    "observed_polarity",
                ):
                    item_value = normalized_item.get(field)
                    if item_value is None or (
                        isinstance(item_value, str) and not item_value.strip()
                    ):
                        normalized_item[field] = None
                polarity_result = normalized_item.get("polarity_result")
                if polarity_result is None or (
                    isinstance(polarity_result, str) and not polarity_result.strip()
                ):
                    normalized_item["polarity_result"] = "not_applicable"
                mechanical_check_id = normalized_item.get("mechanical_check_id")
                reported_value = normalized_item.get("reported_observed_value")
                has_mechanical_check = isinstance(mechanical_check_id, str) and bool(
                    mechanical_check_id.strip()
                )
                if has_mechanical_check != (reported_value is not None):
                    normalized_item["mechanical_check_id"] = None
                    normalized_item["reported_observed_value"] = None
            if role == "factual_plan" and normalized_item.get("kind") == "factual":
                if normalized_item.get("polarity_result") in {"missing", "contradicts"}:
                    normalized_item["disposition"] = "blocks"
                    normalized_item["required_repair"] = ""
            if normalized_item.get("disposition") != "requires_repair":
                normalized_item["required_repair"] = ""
            normalized_items.append(normalized_item)
        normalized["findings"] = normalized_items
    verdict = normalized.get("verdict")
    if verdict in {"ACCEPT", "SYSTEM_FAILURE"}:
        normalized["failed_criteria"] = []
        normalized["sections_affected"] = []
        normalized["required_repair"] = ""
        return normalized
    summarizable_verdicts = {
        "blind_quality": {"REJECT_REPAIRABLE"},
        "factual_plan": {
            "REJECT_REPAIRABLE",
            "BLOCKED_FACT_CONFLICT",
            "BLOCKED_MISSING_EVIDENCE",
        },
    }
    if verdict not in summarizable_verdicts.get(role, set()):
        return normalized
    findings = normalized.get("findings")
    if not isinstance(findings, list) or not findings:
        return normalized
    valid_findings = [item for item in findings if isinstance(item, dict)]
    if len(valid_findings) != len(findings):
        return normalized
    normalized_findings = []
    for item in valid_findings:
        normalized_item = dict(item)
        if (
            normalized_item.get("disposition") == "requires_repair"
            and not str(normalized_item.get("required_repair", "")).strip()
        ):
            section = str(normalized_item.get("section", "README section")).strip()
            claim = str(normalized_item.get("claim", "visible presentation defect")).strip()
            normalized_item["required_repair"] = (
                f"Repair the quoted {section} presentation defect: {claim}"
            )
        normalized_findings.append(normalized_item)
    normalized["findings"] = normalized_findings
    normalized["failed_criteria"] = list(
        dict.fromkeys(
            str(item["criterion"])
            for item in normalized_findings
            if str(item.get("criterion", "")).strip()
        )
    )
    normalized["sections_affected"] = list(
        dict.fromkeys(
            str(item["section"])
            for item in normalized_findings
            if str(item.get("section", "")).strip()
        )
    )
    normalized["required_repair"] = (
        " ".join(
            dict.fromkeys(
                str(item["required_repair"]).strip()
                for item in normalized_findings
                if item.get("disposition") == "requires_repair"
                and str(item.get("required_repair", "")).strip()
            )
        )
        if verdict == "REJECT_REPAIRABLE"
        else ""
    )
    return normalized


__all__ = ["normalize_redundant_role_fields"]
