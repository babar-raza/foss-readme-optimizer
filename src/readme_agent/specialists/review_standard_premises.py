"""Reject blind-review premises contradicted by exact presentation standards."""

from __future__ import annotations

import re


def _configured_standards(visitor_contract: dict) -> dict[str, dict]:
    return {
        str(item.get("standard_id")): item.get("parameters") or {}
        for item in visitor_contract.get("configured_standards", [])
        if isinstance(item, dict)
    }


def _h2_body(candidate_text: str, title: str) -> str:
    heading = re.search(rf"(?mi)^##[ \t]+{re.escape(title)}[ \t]*$", candidate_text)
    if heading is None:
        return ""
    next_h2 = re.search(r"(?m)^##[ \t]+", candidate_text[heading.end() :])
    end = len(candidate_text) if next_h2 is None else heading.end() + next_h2.start()
    return candidate_text[heading.end() : end]


def _mermaid_source(candidate_text: str) -> str:
    blocks = re.findall(r"(?ms)^```mermaid[ \t]*\r?\n(.*?)^```[ \t]*$", candidate_text)
    return blocks[0] if len(blocks) == 1 else ""


def _mermaid_role_count(source: str, role: str) -> int:
    prefix = {"input": "I", "capability": "C", "output": "O"}[role]
    return len(
        re.findall(
            rf'(?m)^[ \t]*(?:{re.escape(role)}_\d+|{prefix}\d+)\["',
            source,
        )
    )


def _has_directional_connector(source: str) -> bool:
    return bool(re.search(r"(?:-->|<-->|==>|-.->)", source))


def _enterprise_scope_context_is_configured(
    candidate_text: str,
    section: str,
    standard: dict,
) -> bool:
    required_section = str(standard.get("required_section") or "")
    if section.strip().casefold() != required_section.strip().casefold():
        return False
    body = _h2_body(candidate_text, required_section).casefold()
    return bool(
        "enterprise edition" in body
        and "products.aspose.com" in body
        and any(
            phrase in body
            for phrase in (
                "separate product",
                "foss implementation",
                "api or feature parity",
                "scope",
            )
        )
    )


def validate_configured_standard_premise(
    *,
    finding_id: str,
    section: str,
    premise: str,
    candidate_text: str,
    visitor_contract: dict,
) -> list[str]:
    """Return contradictions that are mechanically decidable from the exact candidate."""

    standards = _configured_standards(visitor_contract)
    errors: list[str] = []

    example_standard = standards.get("readme.primary_example") or {}
    claims_collapsed_examples_are_wrong = "secondary examples" in premise and (
        "move secondary examples out" in premise or ("collapsed" in premise and "violat" in premise)
    )
    if (
        claims_collapsed_examples_are_wrong
        and example_standard.get("secondary_examples") == "collapsed_below_primary"
        and "<details>" in _h2_body(candidate_text, section).casefold()
    ):
        errors.append(f"{finding_id}:collapsed-example premise contradicts configured presentation")

    mermaid_standard = standards.get("readme.at_a_glance_mermaid") or {}
    mermaid = _mermaid_source(candidate_text)
    claims_directional = "directional arrow" in premise or "directional workflow" in premise
    if (
        claims_directional
        and mermaid_standard.get("directional_workflow") is False
        and mermaid
        and not _has_directional_connector(mermaid)
    ):
        errors.append(f"{finding_id}:Mermaid-direction premise contradicts parsed connectors")

    claims_missing_roles = (
        any(phrase in premise for phrase in ("does not show", "fewer than"))
        and "capabilit" in premise
        and ("input" in premise or "output" in premise)
    )
    if mermaid and claims_missing_roles:
        role_counts_satisfy = (
            _mermaid_role_count(mermaid, "input") >= int(mermaid_standard.get("minimum_inputs", 1))
            and _mermaid_role_count(mermaid, "capability")
            >= int(mermaid_standard.get("minimum_capabilities", 1))
            and _mermaid_role_count(mermaid, "output")
            >= int(mermaid_standard.get("minimum_outputs", 1))
        )
        if role_counts_satisfy:
            errors.append(f"{finding_id}:Mermaid-role-count premise contradicts parsed candidate")

    enterprise_standard = standards.get("readme.enterprise_edition_terminology") or {}
    claims_promotional_instead_of_scope = (
        "promotional link" in premise
        or ("rather than" in premise and "scope" in premise)
        or ("rather than" in premise and "compatibility" in premise)
    )
    if claims_promotional_instead_of_scope and _enterprise_scope_context_is_configured(
        candidate_text,
        section,
        enterprise_standard,
    ):
        errors.append(
            f"{finding_id}:Enterprise-scope premise contradicts configured candidate context"
        )
    return errors
