"""Reject blind-review premises contradicted by exact presentation standards."""

from __future__ import annotations

import re

from readme_agent.readme.capability_semantics import is_action_led_capability_title
from readme_agent.specialists.review_standard_mermaid_premises import (
    validate_mermaid_standard_premise,
)

REVIEW_STANDARD_PREMISE_CONTRACT_VERSION = 8


def _configured_standards(visitor_contract: dict) -> dict[str, dict]:
    return {
        str(item.get("standard_id")): item.get("parameters") or {}
        for item in visitor_contract.get("configured_standards", [])
        if isinstance(item, dict)
    }


def _section_slug(section: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", section.casefold()).strip("-")


def _h2_body(candidate_text: str, title: str) -> str:
    heading = re.search(rf"(?mi)^##[ \t]+{re.escape(title)}[ \t]*$", candidate_text)
    if heading is None:
        return ""
    next_h2 = re.search(r"(?m)^##[ \t]+", candidate_text[heading.end() :])
    end = len(candidate_text) if next_h2 is None else heading.end() + next_h2.start()
    return candidate_text[heading.end() : end]


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


def _api_reference_is_structurally_complete(candidate_text: str) -> bool:
    body = _h2_body(candidate_text, "API Reference")
    return bool(
        re.search(
            r"(?ms)<details>\s*<summary>View public API by namespace</summary>.*?"
            r"^### [^\r\n]+ Namespace \(`[^`]+`\)\s*$.*?"
            r"^\| Type \| Description \|\s*$.*?</details>",
            body,
        )
    )


def _details_are_balanced(body: str) -> bool:
    return body.casefold().count("<details>") == body.casefold().count("</details>") > 0


def _secondary_examples_contract_is_satisfied(candidate_text: str) -> bool:
    quick_start = _h2_body(candidate_text, "Quick Start")
    additional = _h2_body(candidate_text, "Additional Examples")
    return bool(
        re.search(r"(?ms)^```[^\r\n]*\r?\n.+?^```[ \t]*$", quick_start)
        and _details_are_balanced(additional)
        and re.search(r"(?mi)^<summary>[^\r\n]*additional examples[^\r\n]*</summary>$", additional)
    )


def _secondary_examples_intro_is_workflow_preview(candidate_text: str) -> bool:
    additional = _h2_body(candidate_text, "Additional Examples")
    intro = additional.split("<details>", maxsplit=1)[0].strip()
    words = re.findall(r"[A-Za-z0-9]+", intro)
    return bool(
        len(words) >= 12
        and "example" in intro.casefold()
        and re.search(r"(?i)\b(?:demonstrate|show|cover|include|explore)\b", intro)
    )


def _capability_rows_meet_value_contract(candidate_text: str) -> bool:
    body = _h2_body(candidate_text, "Key Capabilities")
    rows = [line.strip() for line in body.splitlines() if line.strip().startswith("- **")]
    if not rows:
        return False
    pattern = re.compile(r"^- \*\*(?P<title>[^*]+)\*\* - (?P<explanation>.+[.!?])$")
    for row in rows:
        match = pattern.fullmatch(row)
        if match is None:
            return False
        title_words = re.findall(r"[A-Za-z0-9]+", match.group("title"))
        explanation_words = re.findall(r"[A-Za-z0-9]+", match.group("explanation"))
        if len(title_words) < 2 or len(explanation_words) < 10:
            return False
    return True


def _capability_rows_are_action_led(candidate_text: str) -> bool:
    body = _h2_body(candidate_text, "Key Capabilities")
    titles = re.findall(r"(?m)^- \*\*(?P<title>[^*]+)\*\*\s+-\s+.+$", body)
    return bool(titles) and all(is_action_led_capability_title(title) for title in titles)


def _capability_rows_name_the_public_product(candidate_text: str) -> bool:
    """Confirm every capability explanation is explicitly bound to the H1 product."""

    title_match = re.search(r"(?m)^# (?P<title>[^\r\n]+)$", candidate_text)
    if title_match is None:
        return False
    product_name = re.sub(r"\s+\[!\[.*$", "", title_match.group("title")).strip()
    body = _h2_body(candidate_text, "Key Capabilities")
    rows = [line.strip() for line in body.splitlines() if line.strip().startswith("- **")]
    return bool(product_name and rows) and all(product_name in row for row in rows)


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
    premise = premise.casefold()

    section_slug = _section_slug(section)
    api_reference_premise = section_slug == "api-reference" and any(
        phrase in premise
        for phrase in (
            "contains no visible content",
            "collapsed <details> block that contains no",
            "placeholder `<details>` block without content",
            "without populating the table",
            "do not leave an empty `<details>` block",
            "incomplete and unclosed details block",
            "contains no actual namespace table content",
            "replace the incomplete `<details>` block",
            "placeholder reference to 'documentation & resources'",
            "actual namespace table or direct api listing",
            "lacks a structured navigable listing",
        )
    )
    api_standard = standards.get("readme.api_reference") or {}
    if (
        api_reference_premise
        and api_standard.get("complete_namespace_tables") is True
        and _api_reference_is_structurally_complete(candidate_text)
    ):
        errors.append(
            f"{finding_id}:API-reference premise contradicts complete collapsed namespace tables"
        )

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
    claims_secondary_structure_missing = (
        any(
            term in premise
            for term in ("without", "lacks", "not collapsed", "uncollapsed", "remove")
        )
        and any(
            term in premise
            for term in ("primary", "secondary", "workflow-preview", "<details>", "collapsed")
        )
    ) or any(
        phrase in premise
        for phrase in (
            "secondary examples are not collapsed",
            "uncollapsed <details> block",
            "lacks a primary example",
            "has no workflow preview",
            "without a workflow-preview intro",
            "html <details> block, which violates markdown integrity",
            "markdown-only collapsible structure",
        )
    )
    if (
        claims_secondary_structure_missing
        and example_standard.get("secondary_examples") == "collapsed_below_primary"
        and example_standard.get("secondary_examples_intro") == "workflow_preview"
        and _secondary_examples_contract_is_satisfied(candidate_text)
    ):
        errors.append(
            f"{finding_id}:secondary-example premise contradicts parsed full-document contract"
        )
    claims_workflow_preview_is_raw = any(
        phrase in premise
        for phrase in (
            "lacks a natural, developer-facing overview",
            "reads like a raw task list",
            "rather than a task list",
            "lacks a workflow preview",
        )
    )
    if (
        section_slug == "additional-examples"
        and claims_workflow_preview_is_raw
        and example_standard.get("secondary_examples_intro") == "workflow_preview"
        and _secondary_examples_intro_is_workflow_preview(candidate_text)
    ):
        errors.append(
            f"{finding_id}:secondary-example intro premise contradicts parsed workflow preview"
        )

    capability_standard = standards.get("readme.key_capabilities") or {}
    claims_bare_capability_labels = any(
        phrase in premise
        for phrase in (
            "bare feature label",
            "bare capability label",
            "not action-led",
            "does not start with a strong action verb",
        )
    )
    claims_capability_value_defect = any(
        term in premise
        for term in (
            "value",
            "outcome",
            "explanation",
            "implementation",
            "terminology",
            "raw inventory",
            "fragment",
        )
    )
    if (
        section_slug == "key-capabilities"
        and claims_bare_capability_labels
        and not claims_capability_value_defect
        and capability_standard.get("action_led_same_line_rows") is True
        and _capability_rows_are_action_led(candidate_text)
    ):
        errors.append(
            f"{finding_id}:bare-label premise contradicts parsed action-led capability rows"
        )
    claims_capability_rows_lack_value = (
        any(term in premise for term in ("lack", "vague", "fragment", "raw inventory", "internal"))
        and any(
            term in premise
            for term in ("value", "outcome", "capabilit", "implementation", "terminology")
        )
    ) or any(
        phrase in premise
        for phrase in (
            "incomplete sentence fragments",
            "omit the developer-facing outcome",
            "raw inventory list",
            "not just a description of api usage",
            "uses internal terminology",
            "instead of verified product vocabulary",
        )
    )
    if (
        section_slug == "key-capabilities"
        and claims_capability_rows_lack_value
        and capability_standard.get("action_led_same_line_rows") is True
        and capability_standard.get("developer_value_explanation") == "required"
        and _capability_rows_meet_value_contract(candidate_text)
    ):
        errors.append(
            f"{finding_id}:capability-value premise contradicts parsed complete same-line rows"
        )
    claims_capability_rows_are_generic = any(
        phrase in premise
        for phrase in (
            "generic class inventory",
            "generic inventory",
            "class inventory fragment",
            "instead of concrete developer-facing",
            "using verified product vocabulary",
            "lacks product-specific",
        )
    )
    if (
        section_slug == "key-capabilities"
        and claims_capability_rows_are_generic
        and capability_standard.get("action_led_same_line_rows") is True
        and capability_standard.get("developer_value_explanation") == "required"
        and _capability_rows_are_action_led(candidate_text)
        and _capability_rows_meet_value_contract(candidate_text)
        and _capability_rows_name_the_public_product(candidate_text)
    ):
        errors.append(
            f"{finding_id}:generic-capability premise contradicts product-bound action-led rows"
        )

    errors.extend(
        validate_mermaid_standard_premise(
            finding_id=finding_id,
            premise=premise,
            candidate_text=candidate_text,
            standard=standards.get("readme.at_a_glance_mermaid") or {},
        )
    )

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


__all__ = ["REVIEW_STANDARD_PREMISE_CONTRACT_VERSION", "validate_configured_standard_premise"]
