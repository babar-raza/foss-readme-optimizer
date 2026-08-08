"""Validate reviewer findings against exact candidate spans and accepted fact evidence."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Literal
from urllib.parse import urlsplit

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.readme.agentic_composition_inputs import compact_prompt_fact_value
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.fact_grounding import fact_strings
from readme_agent.readme.presentation_contract import PRESENTATION_ENTERPRISE_LINK_SECTION
from readme_agent.specialists.factual_review_projection import (
    compact_candidate_anchor_catalog,
    compact_review_fact,
)
from readme_agent.specialists.review_mechanical_observations import (
    MechanicalCheckId,
    MechanicalValue,
    build_candidate_mechanical_observations,
    quick_start_fence_count,
    quick_start_max_nonblank_code_lines,
    visible_header_badge_row_count,
)
from readme_agent.specialists.review_standard_premises import (
    validate_configured_standard_premise,
)

FindingKind = Literal["quality", "factual"]
FindingPolarityResult = Literal["not_applicable", "supports", "contradicts", "missing"]
FindingDisposition = Literal["supports_acceptance", "requires_repair", "blocks"]
EvidencePolarity = Literal[
    "positive_implementation",
    "explicit_constraint",
    "ambiguous_occurrence",
]
BLIND_QUALITY_CRITERIA = (
    "clarity",
    "product_specificity",
    "hierarchy",
    "navigation",
    "installation_presentation",
    "example_presentation",
    "preservation",
    "visible_duplication",
    "internal_terminology",
    "promotional_balance",
    "markdown_integrity",
    "template_genericity",
)
BLIND_GROUNDING_CONTRACT_VERSION = "blind-grounding-v30-mechanical-premise-specificity"
_MARKDOWN_LINK = re.compile(r"(?<!!)\[(?P<label>[^\]]+)\]\((?P<url>https?://[^)\s]+)")


class GroundedReviewFindingV1(BaseModel):
    """One review premise with inspectable candidate and fact anchors."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    finding_id: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    kind: FindingKind
    criterion: str = Field(min_length=1)
    section: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    quoted_candidate_span: str = Field(min_length=1)
    candidate_anchor_id: str | None = Field(
        default=None,
        pattern=r"^candidate\.anchor\.[0-9a-f]{20}\.[0-9]+$",
    )
    disposition: FindingDisposition
    fact_id: str | None = None
    evidence_excerpt: str | None = None
    evidence_location: str | None = None
    expected_polarity: EvidencePolarity | None = None
    observed_polarity: EvidencePolarity | None = None
    polarity_result: FindingPolarityResult
    mechanical_check_id: MechanicalCheckId | None = None
    reported_observed_value: MechanicalValue | None = None
    required_repair: str = ""

    @model_validator(mode="after")
    def _shape_matches_kind(self) -> GroundedReviewFindingV1:
        if self.kind == "quality":
            if any(
                value is not None
                for value in (
                    self.fact_id,
                    self.evidence_excerpt,
                    self.evidence_location,
                    self.expected_polarity,
                    self.observed_polarity,
                )
            ):
                raise ValueError("quality finding cannot carry factual evidence fields")
            if self.polarity_result != "not_applicable":
                raise ValueError("quality finding polarity must be not_applicable")
            if self.disposition == "blocks":
                raise ValueError("quality finding cannot block on factual evidence")
            if (self.mechanical_check_id is None) != (self.reported_observed_value is None):
                raise ValueError(
                    "quality mechanical check ID and reported observed value must appear together"
                )
        elif self.mechanical_check_id is not None or self.reported_observed_value is not None:
            raise ValueError("factual finding cannot carry mechanical observation fields")
        elif self.polarity_result == "missing":
            if (
                self.fact_id is not None
                or self.evidence_excerpt is not None
                or self.evidence_location is not None
            ):
                raise ValueError("missing-evidence finding cannot cite a fact or evidence excerpt")
            if self.disposition != "blocks":
                raise ValueError("missing-evidence finding must block")
        elif self.fact_id is None or not self.evidence_excerpt or not self.evidence_location:
            raise ValueError(
                "supported/contradicted factual finding requires fact, evidence, and location"
            )
        elif self.polarity_result == "supports" and self.disposition == "blocks":
            raise ValueError("supported factual finding cannot block")
        elif self.polarity_result == "contradicts" and self.disposition != "blocks":
            raise ValueError("contradicted factual finding must block")
        if self.disposition == "requires_repair" and not self.required_repair.strip():
            raise ValueError("repair finding requires a bounded repair instruction")
        if self.disposition != "requires_repair" and self.required_repair.strip():
            raise ValueError("only repair findings may carry repair instructions")
        return self


class FindingGroundingResultV1(BaseModel):
    """Deterministic validation result for one role response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    valid: bool
    errors: list[str]
    checked_finding_ids: list[str]


def _fact_evidence_strings(fact: dict) -> set[str]:
    values = {
        str(fact.get("value", "")),
        str((fact.get("source") or {}).get("location", "")),
    }
    for assessment in fact.get("evidence_assessments") or []:
        values.update(
            {
                str(assessment.get("anchor", "")),
                str(assessment.get("exact_excerpt", "")),
                str(assessment.get("context_excerpt", "")),
            }
        )
    return {value for value in values if value}


def _accepted_literal_fact_ids(finding: GroundedReviewFindingV1, product_facts: dict) -> list[str]:
    text = f"{finding.claim}\n{finding.quoted_candidate_span}".casefold()
    by_fact_id = {
        str(fact.get("fact_id")): fact
        for fact in product_facts.get("facts", [])
        if isinstance(fact, dict) and fact.get("fact_id")
    }
    matches: list[str] = []
    for fact_id in set(product_facts.get("selected_fact_ids", {}).values()):
        fact = by_fact_id.get(fact_id)
        if fact is None:
            continue
        if fact.get("verification_state") not in {"verified", "policy_approved"}:
            continue
        if any(conflict.get("status") == "unresolved" for conflict in fact.get("conflicts", [])):
            continue
        if any(
            len(phrase.strip()) >= 4 and phrase.strip().casefold() in text
            for phrase in fact_strings(fact.get("value"))
        ):
            matches.append(fact_id)
    return sorted(matches)


def validate_review_findings(
    *,
    candidate_text: str,
    product_facts: dict | None,
    findings: list[GroundedReviewFindingV1],
    visitor_contract: dict | None = None,
) -> FindingGroundingResultV1:
    """Reject invented spans, unknown facts, evidence mismatch, and wrong polarity."""

    errors: list[str] = []
    by_fact_id = {
        str(fact.get("fact_id")): fact
        for fact in (product_facts or {}).get("facts", [])
        if isinstance(fact, dict) and fact.get("fact_id")
    }
    selected = set((product_facts or {}).get("selected_fact_ids", {}).values())
    mechanical_observations = {
        observation.check_id: observation
        for observation in build_candidate_mechanical_observations(
            candidate_text,
            visitor_contract or {},
        )
    }
    seen: set[str] = set()
    for finding in findings:
        if finding.finding_id in seen:
            errors.append(f"{finding.finding_id}:duplicate finding ID")
        seen.add(finding.finding_id)
        if finding.quoted_candidate_span not in candidate_text:
            errors.append(f"{finding.finding_id}:quoted candidate span is absent")
        if finding.kind != "factual":
            if finding.kind == "quality" and finding.criterion not in BLIND_QUALITY_CRITERIA:
                errors.append(
                    f"{finding.finding_id}:criterion is outside blind visible-quality authority"
                )
            if finding.kind == "quality":
                errors.extend(
                    _validate_quality_finding(
                        finding,
                        candidate_text,
                        visitor_contract or {},
                        mechanical_observations,
                    )
                )
            continue
        if finding.polarity_result == "missing":
            contradicted_by = _accepted_literal_fact_ids(finding, product_facts or {})
            if contradicted_by:
                errors.append(
                    f"{finding.finding_id}:missing-evidence premise contradicts accepted facts "
                    f"{contradicted_by}"
                )
            continue
        assert finding.fact_id is not None
        fact = by_fact_id.get(finding.fact_id)
        if fact is None:
            errors.append(f"{finding.finding_id}:unknown fact ID {finding.fact_id}")
            continue
        if finding.fact_id not in selected:
            errors.append(f"{finding.finding_id}:fact ID is not selected")
        if fact.get("verification_state") not in {"verified", "policy_approved"}:
            errors.append(f"{finding.finding_id}:fact is not accepted")
        if any(conflict.get("status") == "unresolved" for conflict in fact.get("conflicts", [])):
            errors.append(f"{finding.finding_id}:fact has unresolved conflict")
        source_location = str((fact.get("source") or {}).get("location", ""))
        if finding.evidence_location != source_location:
            errors.append(f"{finding.finding_id}:evidence location disagrees with cited fact")
        evidence_excerpt = finding.evidence_excerpt
        assert evidence_excerpt is not None
        evidence = _fact_evidence_strings(fact)
        if not any(evidence_excerpt in value or value in evidence_excerpt for value in evidence):
            errors.append(f"{finding.finding_id}:evidence excerpt is not bound to cited fact")
        assessments = fact.get("evidence_assessments") or []
        matching = [
            item
            for item in assessments
            if evidence_excerpt
            in {
                str(item.get("anchor", "")),
                str(item.get("exact_excerpt", "")),
                str(item.get("context_excerpt", "")),
            }
        ]
        if matching:
            assessment = matching[0]
            if finding.expected_polarity != assessment.get("expected_polarity"):
                errors.append(f"{finding.finding_id}:expected polarity disagrees with evidence")
            if finding.observed_polarity != assessment.get("observed_polarity"):
                errors.append(f"{finding.finding_id}:observed polarity disagrees with evidence")
            derived = "supports" if assessment.get("accepted") else "contradicts"
            if finding.polarity_result != derived:
                errors.append(f"{finding.finding_id}:polarity result has wrong direction")
        elif (
            finding.expected_polarity != "positive_implementation"
            or finding.observed_polarity != "positive_implementation"
            or finding.polarity_result != "supports"
        ):
            errors.append(
                f"{finding.finding_id}:accepted evidence without an assessment must support"
            )
    return FindingGroundingResultV1(
        valid=not errors,
        errors=errors,
        checked_finding_ids=sorted(seen),
    )


def _validate_quality_finding(
    finding: GroundedReviewFindingV1,
    candidate_text: str,
    visitor_contract: dict,
    mechanical_observations: dict,
) -> list[str]:
    """Reject visible-quality premises contradicted by their quote or configured contract."""

    if finding.disposition != "requires_repair":
        return []
    errors: list[str] = []
    premise = f"{finding.claim}\n{finding.required_repair}".casefold()
    errors.extend(
        validate_configured_standard_premise(
            finding_id=finding.finding_id,
            section=finding.section,
            premise=premise,
            candidate_text=candidate_text,
            visitor_contract=visitor_contract,
        )
    )
    quote = finding.quoted_candidate_span
    removes_prose_block = bool(
        re.search(r"\b(?:remove|delete|omit)\b[^\n.]*\b(?:paragraph|prose|sentence)\b", premise)
    )
    first_quoted_line = next(
        (line.lstrip() for line in quote.splitlines() if line.strip()),
        "",
    )
    heading_only_quote = bool(re.fullmatch(r"#{1,6}[ \t]+[^\r\n]+", quote.strip()))
    if not _quality_quote_matches_named_section(candidate_text, finding.section, quote):
        errors.append(f"{finding.finding_id}:quoted span is outside the named candidate section")
    block_dependent_premise = any(
        term in premise
        for term in (
            "appears twice",
            "appears before",
            "appears after",
            "contains enterprise edition",
            "duplicate",
            "duplicated",
            "must be placed",
            "not in the license section",
            "remove the section",
            "section order",
            "required h2 prefix",
        )
    ) or bool(
        re.search(
            r"\b(?:missing|lacks?|without|insufficient(?:ly)?|"
            r"does not(?:\s+\w+){0,3}\s+contain)\b[^\n.]{0,160}"
            r"\b(?:content|context|detail|limitations?|enterprise edition)\b",
            premise,
        )
    )
    if heading_only_quote and block_dependent_premise:
        errors.append(
            f"{finding.finding_id}:heading-only quote cannot prove the claimed section content"
        )
    if removes_prose_block and re.match(r"^#{1,6}[ \t]+", first_quoted_line):
        errors.append(
            f"{finding.finding_id}:repair quote identifies a heading instead of the prose to remove"
        )
    claims_missing_blank_line = bool(
        re.search(r"\bmissing (?:the )?(?:required )?blank line\b", premise)
        or "no blank line" in premise
    )
    if claims_missing_blank_line and "\n\n" in quote.replace("\r\n", "\n"):
        errors.append(f"{finding.finding_id}:blank-line premise contradicts quoted span")
    elif claims_missing_blank_line and _fenced_block_has_following_blank_line(
        candidate_text,
        quote,
    ):
        errors.append(f"{finding.finding_id}:blank-line premise contradicts candidate structure")
    list_present = any(line.lstrip().startswith(("- ", "* ", "+ ")) for line in quote.splitlines())
    if list_present and (
        "plain text labels instead of a proper markdown list" in premise
        or "lack leading hyphens" in premise
        or "use proper markdown list syntax" in premise
    ):
        errors.append(f"{finding.finding_id}:list-syntax premise contradicts quoted span")
    standards = {
        str(item.get("standard_id")): item.get("parameters") or {}
        for item in visitor_contract.get("configured_standards", [])
        if isinstance(item, dict)
    }
    brand_header = standards.get("readme.header")
    if brand_header is not None and brand_header.get("brand_contract_version"):
        claims_missing_h1 = (
            "lacks an h1" in premise
            or "missing an h1" in premise
            or "add an undecorated h1" in premise
            or "add the h1" in premise
        )
        if claims_missing_h1 and re.match(r"\A(?:\ufeff)?# [^\r\n]+", candidate_text):
            errors.append(f"{finding.finding_id}:H1 premise contradicts visible candidate")
        visible_h1 = re.match(r"\A(?:\ufeff)?# (?P<title>[^\r\n]+)", candidate_text)
        claims_h1_emoji = "h1" in premise and "emoji" in premise
        if (
            claims_h1_emoji
            and visible_h1 is not None
            and re.fullmatch(r"[A-Za-z0-9 .+#&()/-]+", visible_h1.group("title"))
        ):
            errors.append(f"{finding.finding_id}:H1 emoji premise contradicts visible candidate")
        badges = standards.get("readme.badges") or {}
        required_core_row = str(badges.get("required_core_row", ""))
        claims_missing_header_spacing = (
            "missing blank line" in premise or "insert a blank line after the h1" in premise
        )
        visible_header = re.match(
            r"\A(?:\ufeff)?# [^\r\n]+\r?\n\r?\n([^\r\n]+)",
            candidate_text,
        )
        if (
            claims_missing_header_spacing
            and visible_header is not None
            and (
                visible_header.group(1).lstrip().startswith(("[![", "!["))
                or (required_core_row and visible_header.group(1).strip() == required_core_row)
            )
        ):
            errors.append(
                f"{finding.finding_id}:header-spacing premise contradicts configured header"
            )
        claims_opening_duplicates_visual = (
            "first paragraph after badges" in premise
            and "at a glance" in premise
            and ("duplicate" in premise or "duplication" in premise)
        )
        if claims_opening_duplicates_visual and not _at_a_glance_contains_prose(candidate_text):
            errors.append(
                f"{finding.finding_id}:opening-versus-visual premise contradicts global contract"
            )
    if "readme.badges" in standards and "badge" in premise:
        badge_standard = standards.get("readme.badges") or {}
        required_core_row = str(badge_standard.get("required_core_row", ""))
        configured_badge_rows = badge_standard.get("badge_rows")
        claims_badge_row_overflow = (
            "exceeding the allowed badge_rows" in premise
            or "exceeding the allowed badge rows" in premise
            or "exceeds the allowed badge_rows" in premise
            or "exceeds the allowed badge rows" in premise
            or "violating the configured badge standard" in premise
            or (
                "badge row" in premise
                and ("exceeding" in premise or "exceeds" in premise)
                and ("configured maximum" in premise or "maximum of" in premise)
            )
        )
        if (
            claims_badge_row_overflow
            and isinstance(configured_badge_rows, int)
            and visible_header_badge_row_count(candidate_text) <= configured_badge_rows
        ):
            errors.append(f"{finding.finding_id}:badge-row premise contradicts visible candidate")
        allowed_badge_kinds = {
            str(kind).casefold() for kind in badge_standard.get("allowed_badge_kinds", [])
        }
        rejects_allowed_contributors_badge = (
            "contributors badge" in premise
            and "contributors" in allowed_badge_kinds
            and visible_header_badge_row_count(candidate_text) <= int(configured_badge_rows or 1)
        )
        if rejects_allowed_contributors_badge:
            errors.append(
                f"{finding.finding_id}:contributors-badge premise contradicts configured kinds"
            )
        claims_nonempty_title_attribute = (
            "non-empty title attribute" in premise or "nonempty title attribute" in premise
        )
        if claims_nonempty_title_attribute and not _has_markdown_link_title(quote):
            errors.append(f"{finding.finding_id}:badge-title premise contradicts parsed Markdown")
        claims_duplicate_badge_row = (
            "badge row appears twice" in premise
            or "duplicated badge row" in premise
            or "duplicate badge row" in premise
        )
        if (
            claims_duplicate_badge_row
            and required_core_row
            and candidate_text.count(required_core_row) == 1
        ):
            errors.append(
                f"{finding.finding_id}:badge-duplication premise contradicts configured header"
            )
        title_badge = re.match(
            r"\A(?:\ufeff)?# [^\r\n]+\r?\n\r?\n(?:\[?!)\[[^\r\n]+",
            candidate_text,
        )
        rejects_valid_spacing = (
            "without a blank line" in premise
            or "without an intervening blank line" in premise
            or "immediately after the h1" in premise
            or bool(
                re.search(
                    r"\bwithout (?:an? )?(?:intervening )?blank line\b",
                    premise,
                )
            )
            or bool(
                re.search(
                    r"\bremove (?:the )?blank line\b[^\n.]{0,120}"
                    r"\b(?:h1|title)\b[^\n.]{0,120}\bbadge",
                    premise,
                )
            )
        )
        if title_badge is not None and rejects_valid_spacing:
            errors.append(
                f"{finding.finding_id}:badge-spacing premise contradicts configured header"
            )
        rejects_allowed_inherited_badges = (
            "extra ci badge row" in premise
            or "extra badge row" in premise
            or "keep only the two required core badges" in premise
            or "keep only the required core badges" in premise
        )
        if (
            rejects_allowed_inherited_badges
            and badge_standard.get("allow_inherited_badges_after_core") is True
            and required_core_row
            and candidate_text.count(required_core_row) == 1
        ):
            errors.append(
                f"{finding.finding_id}:inherited-badge premise contradicts configured header"
            )
    if "readme.navigation" in standards and "navigation" in premise:
        has_navigation = re.search(r"(?mi)^##[ \t]+navigation[ \t]*$", candidate_text)
        has_glance = re.search(r"(?mi)^##[ \t]+at a glance[ \t]*$", candidate_text)
        required_navigation_labels = tuple(
            str(label)
            for label in (standards.get("readme.navigation") or {}).get(
                "required_labels",
                [],
            )
        )
        claims_required_label_omission = (
            ("omit" in premise or "missing" in premise)
            and "required" in premise
            and "label" in premise
        )
        if (
            claims_required_label_omission
            and required_navigation_labels
            and all(
                re.search(
                    rf"(?mi)^\s*[-*+]\s+\[{re.escape(label)}\]\(#[^)]+\)\s*$",
                    candidate_text,
                )
                for label in required_navigation_labels
            )
        ):
            errors.append(f"{finding.finding_id}:required-navigation premise contradicts candidate")
        removes_applicable_label = any(
            re.search(
                rf"\b(?:remove|omit|drop|exclude)\b[^\n.]{{0,180}}"
                rf"\b{re.escape(label.casefold())}\b",
                premise,
            )
            for label in required_navigation_labels
        )
        if (
            removes_applicable_label
            and (standards.get("readme.navigation") or {}).get("complete_h2_list") is True
        ):
            errors.append(
                f"{finding.finding_id}:navigation removal contradicts applicable H2 contract"
            )
        demands_wrong_placement = (
            "missing" in premise
            or "add the required" in premise
            or "under the 'at a glance'" in premise
            or 'under the "at a glance"' in premise
        )
        if has_navigation and has_glance and demands_wrong_placement:
            errors.append(
                f"{finding.finding_id}:navigation premise contradicts configured H2 sections"
            )
        header = standards.get("readme.header") or {}
        prefix_only_premise = (
            "not in the required h2 prefix" in premise
            or "match the required h2 prefix" in premise
            or "only the required labels" in premise
            or "exceeds required labels" in premise
            or "includes non-standard labels" in premise
            or "includes non-standard section names" in premise
            or "more than the required" in premise
            or "must contain only the required" in premise
            or "not in the required set" in premise
            or "trim the navigation section to the required labels" in premise
            or "reduce the navigation section to the required labels" in premise
            or "non-required navigation labels" in premise
            or "retain only the required set" in premise
            or "exceeding the required set" in premise
            or "non-required h2 sections" in premise
            or "non-required sections" in premise
            or "violate the required sequence" in premise
            or bool(
                re.search(
                    r"\b(?:includes?|remove|omit|drop|exclude)\b[^\n.]{0,120}"
                    r"\bnon-required\b[^\n.]{0,120}\blabels?\b",
                    premise,
                )
            )
        )
        if prefix_only_premise and header.get("required_h2_prefix"):
            errors.append(f"{finding.finding_id}:navigation prefix-only premise is unconfigured")
        claims_duplicate_navigation = (
            "navigation section appears twice" in premise
            or "duplicate navigation section" in premise
            or "duplicated navigation section" in premise
        )
        if (
            claims_duplicate_navigation
            and len(re.findall(r"(?mi)^##[ \t]+navigation[ \t]*$", candidate_text)) == 1
        ):
            errors.append(
                f"{finding.finding_id}:navigation-duplication premise contradicts candidate"
            )
    mermaid_standard = standards.get("readme.at_a_glance_mermaid")
    if mermaid_standard is not None and "mermaid" in premise:
        if "subgraph" in premise and "without subgraphs" in premise:
            errors.append(f"{finding.finding_id}:Mermaid subgraph prohibition is unconfigured")
        maximum_nodes = mermaid_standard.get("max_nodes")
        if (
            isinstance(maximum_nodes, int)
            and "exceeds the max_nodes" in premise
            and _mermaid_node_count(candidate_text) <= maximum_nodes
        ):
            errors.append(f"{finding.finding_id}:Mermaid node-count premise contradicts candidate")
        rejects_compliant_detailed_flow = any(
            phrase in premise
            for phrase in (
                "paragraph-sized nodes",
                "generic labels",
                "clear inputs->product->capabilities->outputs flow",
                "clear inputs to product to capabilities to outputs flow",
            )
        ) or ("generic" in premise and "product" in premise and "node label" in premise)
        if rejects_compliant_detailed_flow and _detailed_mermaid_contract_satisfied(
            candidate_text,
            mermaid_standard,
        ):
            errors.append(
                f"{finding.finding_id}:Mermaid-detail premise contradicts configured candidate"
            )
        claims_generic_product_label = (
            "generic" in premise
            and "product" in premise
            and any(term in premise for term in ("label", "node"))
        )
        if (
            claims_generic_product_label
            and _mermaid_has_specific_product_label(candidate_text)
            and not _detailed_mermaid_contract_satisfied(candidate_text, mermaid_standard)
        ):
            errors.append(
                f"{finding.finding_id}:Mermaid-product-label premise contradicts "
                "visible candidate label"
            )
        claims_missing_grammar_roles = (
            "missing" in premise
            and "input" in premise
            and "product/api" in premise
            and "capabilit" in premise
            and "output" in premise
        )
        if claims_missing_grammar_roles and _detailed_mermaid_contract_satisfied(
            candidate_text,
            mermaid_standard,
        ):
            errors.append(
                f"{finding.finding_id}:Mermaid-grammar premise contradicts configured candidate"
            )
        claims_directional_workflow = (
            "uses a directional workflow" in premise
            or "replace directional mermaid" in premise
            or "directional arrows" in premise
            or (
                "directional" in premise
                and any(term in premise for term in ("workflow", "arrow", "flowchart lr"))
            )
        )
        if (
            claims_directional_workflow
            and mermaid_standard.get("directional_workflow") is False
            and _detailed_mermaid_contract_satisfied(candidate_text, mermaid_standard)
        ):
            errors.append(
                f"{finding.finding_id}:Mermaid-direction premise contradicts parsed candidate"
            )
    if (
        "quick start" in premise
        and (
            "two separate example" in premise
            or "duplicated example" in premise
            or "two separate fenced" in premise
            or "exceeding the maximum_fenced_blocks" in premise
        )
        and quick_start_fence_count(candidate_text) <= 1
    ):
        errors.append(f"{finding.finding_id}:Quick-start duplication premise contradicts candidate")
    primary_example_standard = standards.get("readme.primary_example")
    if primary_example_standard is not None and "quick start" in premise:
        maximum_fences = primary_example_standard.get("maximum_fenced_blocks")
        maximum_code_lines = primary_example_standard.get("maximum_nonblank_code_lines")
        rejects_bounded_primary_example = any(
            phrase in premise
            for phrase in (
                "simpler, more direct",
                "simpler and more direct",
                "too complex",
                "overly complex",
                "consolidate the quick start",
                "replace the 'quick start' minimal example with a simpler",
                'replace the "quick start" minimal example with a simpler',
            )
        )
        if (
            rejects_bounded_primary_example
            and isinstance(maximum_fences, int)
            and isinstance(maximum_code_lines, int)
            and quick_start_fence_count(candidate_text) <= maximum_fences
            and quick_start_max_nonblank_code_lines(candidate_text) <= maximum_code_lines
        ):
            errors.append(
                f"{finding.finding_id}:Quick-start complexity premise contradicts "
                "configured primary-example bounds"
            )
        claims_code_line_overflow = (
            "exceeds the maximum" in premise or "more than" in premise
        ) and "nonblank code line" in premise
        if (
            claims_code_line_overflow
            and isinstance(maximum_code_lines, int)
            and quick_start_max_nonblank_code_lines(candidate_text) <= maximum_code_lines
        ):
            errors.append(
                f"{finding.finding_id}:Quick-start line-count premise contradicts candidate"
            )
        claims_fence_overflow = "fenced code block" in premise and (
            "exceeding" in premise
            or "exceeds" in premise
            or bool(re.search(r"\b(?:contains?|has)\s+(?:two|\d+)\b", premise))
        )
        if (
            claims_fence_overflow
            and isinstance(maximum_fences, int)
            and quick_start_fence_count(candidate_text) <= maximum_fences
        ):
            errors.append(
                f"{finding.finding_id}:Quick-start fence-count premise contradicts candidate"
            )
    if "heading alias" in premise or "heading_alias" in premise:
        header = standards.get("readme.header") or {}
        aliases = {
            str(source).casefold(): str(target)
            for source, target in (header.get("heading_aliases") or {}).items()
        }
        if finding.section.casefold() not in aliases:
            errors.append(f"{finding.finding_id}:heading-alias premise is unconfigured")
    header = standards.get("readme.header") or {}
    if (
        "parenthes" in premise
        and header.get("heading_style") == "title_case_without_emoji"
        and "forbid_parentheses" not in header
    ):
        errors.append(f"{finding.finding_id}:heading-parentheses premise is unconfigured")
    license_standard = standards.get("readme.license")
    if license_standard is not None and finding.section.casefold() == "license":
        required_benefit_terms = tuple(
            str(term).casefold()
            for term in license_standard.get("required_benefit_terms", [])
            if str(term).strip()
        )
        quote_text = quote.casefold()
        rejects_required_benefits = "promotional language" in premise and (
            "simple license reference" in premise or "single sentence" in premise
        )
        if (
            license_standard.get("benefits_summary") == "required"
            and rejects_required_benefits
            and required_benefit_terms
            and all(term in quote_text for term in required_benefit_terms)
        ):
            errors.append(
                f"{finding.finding_id}:license-benefits repair contradicts configured contract"
            )
    enterprise_standard = standards.get("readme.enterprise_edition_terminology")
    if enterprise_standard is not None and "enterprise edition" in premise:
        required_term = str(enterprise_standard.get("required_term", "Enterprise Edition"))
        required_section = str(enterprise_standard.get("required_section", ""))
        claims_missing_required_term = (
            "missing the required" in premise
            or "term is missing" in premise
            or "missing entirely" in premise
            or bool(
                re.search(
                    r"\bdoes not\b[^\n.]{0,40}\bcontain\b[^\n.]{0,160}"
                    r"\benterprise edition\b",
                    premise,
                )
            )
            or bool(
                re.search(
                    r"\bmissing (?:the )?required\b[^\n.]{0,160}\benterprise edition\b",
                    premise,
                )
            )
        )
        if (
            claims_missing_required_term
            and required_section
            and _section_contains(candidate_text, required_section, required_term)
        ):
            errors.append(
                f"{finding.finding_id}:Enterprise Edition term premise contradicts candidate"
            )
        opening_only = any(
            phrase in premise
            for phrase in (
                "first paragraph",
                "opening paragraph",
                "after the badge",
                "below the opening",
                "after the opening",
                "opening value proposition",
            )
        )
        if opening_only and required_term.casefold() in candidate_text.casefold():
            errors.append(
                f"{finding.finding_id}:Enterprise Edition opening-placement premise is unconfigured"
            )
        if (
            opening_only
            and required_section
            and required_term.casefold() in candidate_text.casefold()
            and _section_contains(candidate_text, required_section, required_term)
        ):
            errors.append(
                f"{finding.finding_id}:Enterprise Edition placement contradicts configured section"
            )
        claims_wrong_enterprise_placement = any(
            phrase in premise
            for phrase in (
                "must be placed below the fold",
                "must be placed in the scope",
                "not in the license section",
                "move enterprise edition",
            )
        )
        if (
            claims_wrong_enterprise_placement
            and required_section
            and _section_contains(candidate_text, required_section, required_term)
            and not _section_contains(candidate_text, "License", required_term)
        ):
            errors.append(
                f"{finding.finding_id}:Enterprise Edition placement already satisfies contract"
            )
        falsely_places_quote_in_license = (
            "misplaced in the license section" in premise or "from the license section" in premise
        )
        if (
            falsely_places_quote_in_license
            and required_section
            and _quality_quote_matches_named_section(candidate_text, required_section, quote)
            and not _quality_quote_matches_named_section(candidate_text, "License", quote)
        ):
            errors.append(
                f"{finding.finding_id}:claimed source section contradicts candidate structure"
            )
    claims_bare_url = "bare url" in premise or "bare-url" in premise
    quoted_descriptive_link = next(
        (
            match
            for match in _MARKDOWN_LINK.finditer(finding.quoted_candidate_span)
            if match.group("label").strip()
            and not match.group("label").strip().casefold().startswith(("http://", "https://"))
        ),
        None,
    )
    if (
        claims_bare_url
        and quoted_descriptive_link is not None
        and standards.get("readme.contextual_links") is None
    ):
        errors.append(f"{finding.finding_id}:bare-URL premise contradicts parsed Markdown")
    link_standard = standards.get("readme.contextual_links")
    if link_standard is not None:
        required_enterprise_url = str(link_standard.get("required_enterprise_url", ""))
        exact_enterprise_occurrences = link_standard.get("required_aspose_com_occurrences")
        enterprise_url_offsets = [
            match.start()
            for match in re.finditer(re.escape(required_enterprise_url), candidate_text)
            if required_enterprise_url
        ]
        enterprise_url_is_correctly_scoped = (
            exact_enterprise_occurrences == 1
            and len(enterprise_url_offsets) == 1
            and _h2_section_for_offset(candidate_text, enterprise_url_offsets[0])
            == PRESENTATION_ENTERPRISE_LINK_SECTION
        )
        claims_missing_enterprise_link = (
            "enterprise edition link is missing" in premise
            or "add the enterprise edition link" in premise
            or "replace placeholder text with the required enterprise edition link" in premise
            or "must include the required enterprise edition link" in premise
            or ("missing" in premise and "enterprise edition" in premise and "link" in premise)
        )
        if (
            claims_missing_enterprise_link
            and exact_enterprise_occurrences == 1
            and required_enterprise_url
            and required_enterprise_url in candidate_text
        ):
            errors.append(
                f"{finding.finding_id}:Enterprise link premise contradicts configured candidate"
            )
        quoted_enterprise_link = next(
            (
                match
                for match in _MARKDOWN_LINK.finditer(finding.quoted_candidate_span)
                if match.group("url") == required_enterprise_url
                and match.group("label").strip()
                and not match.group("label").strip().casefold().startswith(("http://", "https://"))
            ),
            None,
        )
        claims_bare_enterprise_url = (
            "bare url" in premise
            or "bare-url" in premise
            or ("descriptive link label" in premise and "enterprise edition" in premise)
        )
        rejects_descriptive_link_label = (
            "link label" in premise and "configured url" in premise
        ) or (claims_bare_enterprise_url and quoted_enterprise_link is not None)
        if (
            rejects_descriptive_link_label
            and isinstance(exact_enterprise_occurrences, int)
            and required_enterprise_url
            and candidate_text.count(required_enterprise_url) == exact_enterprise_occurrences
        ):
            errors.append(f"{finding.finding_id}:bare-URL premise contradicts configured candidate")
        demands_enterprise_link_outside_scope = (
            enterprise_url_is_correctly_scoped
            and not claims_missing_enterprise_link
            and not rejects_descriptive_link_label
            and "enterprise edition" in premise
            and "link" in premise
            and finding.section.casefold() != PRESENTATION_ENTERPRISE_LINK_SECTION.casefold()
        )
        if demands_enterprise_link_outside_scope:
            errors.append(
                f"{finding.finding_id}:Enterprise link placement contradicts configured scope"
            )
        if (
            "all links are hyperlinked" in premise
            or "all are plain text" in premise
            or "inconsistent link presentation" in premise
            or "conversion of plain labels" in premise
        ):
            errors.append(
                f"{finding.finding_id}:link-uniformity premise conflicts with contextual budget"
            )
        maximum = link_standard.get("max_total")
        domain_maxima = link_standard.get("domain_maxima") or {}
        domains = tuple(str(domain).casefold() for domain in domain_maxima)
        governed_link_count = sum(
            1
            for match in _MARKDOWN_LINK.finditer(candidate_text)
            if any(
                (host := urlsplit(match.group("url")).netloc.casefold()) == domain
                or host.endswith(f".{domain}")
                for domain in domains
            )
        )
        link_ceiling_premise = (
            "link budget" in premise
            or "contextual link" in premise
            or "allowed url" in premise
            or ("link" in premise and "at most" in premise)
        )
        if isinstance(maximum, int) and link_ceiling_premise:
            if governed_link_count <= maximum:
                errors.append(
                    f"{finding.finding_id}:link-budget premise contradicts configured maximum"
                )
    expected_mechanical_check = _mechanical_check_for_premise(finding, premise)
    if not errors or expected_mechanical_check == "document.duplicate_h2_headings":
        errors.extend(
            _validate_typed_mechanical_finding(
                finding,
                premise,
                mechanical_observations,
            )
        )
    return errors


def _quality_quote_matches_named_section(
    candidate_text: str,
    section: str,
    quote: str,
) -> bool:
    """Require a quality quote to occur inside the H2 it claims to describe."""

    normalized = section.strip().casefold()
    if normalized in {"", "header", "overview", "readme", "document"}:
        return True
    headings = [
        heading
        for heading in parse_headings(candidate_text)
        if heading.level == 2 and heading.title.strip().casefold() == normalized
    ]
    if not headings:
        return False
    offset = candidate_text.find(quote)
    while offset >= 0:
        if any(heading.start <= offset < heading.section_end for heading in headings):
            return True
        offset = candidate_text.find(quote, offset + 1)
    return False


def _validate_typed_mechanical_finding(
    finding: GroundedReviewFindingV1,
    premise: str,
    mechanical_observations: dict,
) -> list[str]:
    """Require parser ownership only when no earlier contract rule already disproves a finding."""

    expected_check = _mechanical_check_for_premise(finding, premise)
    if expected_check is not None and finding.mechanical_check_id is None:
        return [
            f"{finding.finding_id}:mechanical premise lacks required typed check {expected_check}"
        ]
    if expected_check is not None and finding.mechanical_check_id != expected_check:
        return [
            f"{finding.finding_id}:mechanical premise cites {finding.mechanical_check_id} "
            f"instead of {expected_check}"
        ]
    if finding.mechanical_check_id is None:
        return []
    if expected_check is None:
        return [
            f"{finding.finding_id}:mechanical premise cites unrelated check "
            f"{finding.mechanical_check_id}"
        ]
    observation = mechanical_observations.get(finding.mechanical_check_id)
    if observation is None:
        return [f"{finding.finding_id}:mechanical check is unavailable for configured candidate"]
    if finding.reported_observed_value != observation.observed_value:
        return [
            f"{finding.finding_id}:reported mechanical value "
            f"{finding.reported_observed_value!r} contradicts parser value "
            f"{observation.observed_value!r}"
        ]
    if finding.disposition == "requires_repair" and observation.compliant:
        return [
            f"{finding.finding_id}:mechanical repair premise contradicts compliant "
            f"{finding.mechanical_check_id} observation"
        ]
    return []


def _fenced_block_has_following_blank_line(candidate_text: str, quote: str) -> bool:
    """Return whether the cited code belongs to a fence followed by a blank line."""

    if not quote or quote not in candidate_text:
        return False
    lines = candidate_text.splitlines()
    for token in MarkdownIt("commonmark").parse(candidate_text):
        if token.type != "fence" or token.map is None:
            continue
        start_line, end_line = token.map
        fenced_source = "\n".join(lines[start_line:end_line])
        if quote not in fenced_source:
            continue
        return end_line < len(lines) and not lines[end_line].strip()
    return False


def _h2_section_for_offset(markdown: str, offset: int) -> str:
    """Return the nearest preceding H2 title for one candidate offset."""

    headings = list(re.finditer(r"(?m)^##[ \t]+(?P<title>.+?)[ \t]*$", markdown[:offset]))
    return "" if not headings else headings[-1].group("title").strip()


def _at_a_glance_contains_prose(markdown: str) -> bool:
    """Return whether At a glance contains prose outside its required Mermaid visual."""

    heading = re.search(r"(?mi)^##[ \t]+At a glance[ \t]*$", markdown)
    if heading is None:
        return False
    next_h2 = re.search(r"(?m)^##[ \t]+", markdown[heading.end() :])
    end = len(markdown) if next_h2 is None else heading.end() + next_h2.start()
    body = markdown[heading.end() : end]
    without_mermaid = re.sub(
        r"(?ms)^```mermaid[ \t]*\r?\n.*?^```[ \t]*$",
        "",
        body,
    )
    return bool(without_mermaid.strip())


def _mermaid_node_count(candidate_text: str) -> int:
    """Count declared Mermaid nodes without counting subgraphs or edges."""

    blocks = re.findall(r"(?ms)^```mermaid[ \t]*\r?\n(.*?)^```[ \t]*$", candidate_text)
    declarations: set[str] = set()
    for block in blocks:
        for line in block.splitlines():
            match = re.match(r"^[ \t]*(?P<node>[A-Za-z][A-Za-z0-9_-]*)[ \t]*(?:\[|\()", line)
            if match is not None:
                declarations.add(match.group("node"))
    return len(declarations)


def _mechanical_check_for_premise(
    finding: GroundedReviewFindingV1,
    premise: str,
) -> MechanicalCheckId | None:
    """Classify parser-owned structural premises independently of their conclusion wording."""

    if "badge" in premise and "row" in premise:
        return "header.badge_rows"
    if re.search(
        r"\b(?:(?:section|heading)\s+appears\s+twice|"
        r"(?:duplicate|duplicated)\s+(?:the\s+)?(?:h2\s+)?(?:section|heading))\b",
        premise,
    ):
        return "document.duplicate_h2_headings"
    if any(
        term in premise
        for term in (
            "missing h1",
            "missing an h1",
            "lacks h1",
            "lacks an h1",
            "h1 count",
            "multiple h1",
            "more than one h1",
        )
    ):
        return "document.h1_blocks"
    if any(
        term in premise
        for term in (
            "first h2",
            "first labeled section",
            "required h2 prefix",
            "required prefix order",
        )
    ):
        return "document.required_h2_prefix"
    if finding.section.casefold() == "quick start" or "quick start" in premise:
        # A reviewer commonly describes the containing fence before stating a line-count
        # violation.  The explicit measured quantity owns the premise; merely mentioning a
        # numbered fence must not steal a more specific nonblank-line citation.
        if "nonblank" in premise and "line" in premise:
            return "quick_start.max_nonblank_code_lines"
        quantified = bool(
            re.search(r"\b(?:two|three|four|\d+)\b", premise)
            or any(
                term in premise
                for term in (
                    "count",
                    "maximum",
                    "minimum",
                    "exceed",
                    "duplicate",
                    "more than one",
                )
            )
        )
        if quantified and ("fenc" in premise or "code block" in premise):
            return "quick_start.fenced_blocks"
    return None


def _section_contains(candidate_text: str, section_title: str, text: str) -> bool:
    """Return whether one literal occurs within the named H2 section."""

    heading = re.search(
        rf"(?mi)^##[ \t]+{re.escape(section_title)}[ \t]*$",
        candidate_text,
    )
    if heading is None:
        return False
    next_h2 = re.search(r"(?m)^##[ \t]+", candidate_text[heading.end() :])
    end = len(candidate_text) if next_h2 is None else heading.end() + next_h2.start()
    return text.casefold() in candidate_text[heading.end() : end].casefold()


def _has_markdown_link_title(markdown: str) -> bool:
    """Return whether parsed Markdown contains a non-empty link title attribute."""

    for token in MarkdownIt("commonmark").parse(markdown):
        if token.type != "inline":
            continue
        for child in token.children or []:
            if child.type == "link_open" and child.attrGet("title"):
                return True
    return False


def _detailed_mermaid_contract_satisfied(candidate_text: str, standard: dict) -> bool:
    """Recognize the configured four-zone grammar without judging factual assurance."""

    blocks = re.findall(r"(?ms)^```mermaid[ \t]*\r?\n(.*?)^```[ \t]*$", candidate_text)
    if len(blocks) != 1:
        return False
    source = blocks[0]
    if not all(
        source.count(zone) == 1
        for zone in ("subgraph Inputs", "subgraph Capabilities", "subgraph Outputs")
    ):
        return False
    modern_ids = bool(re.search(r'(?m)^[ \t]*input_\d+\["', source))
    input_id = r"input_\d+" if modern_ids else r"I\d+"
    product_id = "product" if modern_ids else "PRODUCT"
    capability_id = r"capability_\d+" if modern_ids else r"C\d+"
    output_id = r"output_\d+" if modern_ids else r"O\d+"
    labels = re.findall(
        rf"(?m)^[ \t]*(?:{input_id}|{product_id}|{capability_id}|{output_id})"
        r'\["([^"\r\n]+)"\][ \t]*$',
        source,
    )
    if not labels:
        return False
    maximum_label = standard.get("max_label_characters")
    if isinstance(maximum_label, int) and any(
        len(label.strip()) > maximum_label for label in labels
    ):
        return False
    maximum_nodes = standard.get("max_nodes")
    if isinstance(maximum_nodes, int) and len(labels) > maximum_nodes:
        return False
    directional = standard.get("directional_workflow")
    connectors = (
        ("-->",) if directional is True else ("---",) if directional is False else ("-->", "---")
    )
    minimum_inputs = int(standard.get("minimum_inputs", 1))
    minimum_capabilities = int(standard.get("minimum_capabilities", 1))
    minimum_outputs = int(standard.get("minimum_outputs", 1))
    output_count = len(re.findall(rf'(?m)^[ \t]*{output_id}\["', source))
    return bool(
        len(re.findall(rf'(?m)^[ \t]*{input_id}\["', source)) >= minimum_inputs
        and re.search(rf'(?m)^[ \t]*{product_id}\["[^"\r\n]+"\][ \t]*$', source)
        and len(re.findall(rf'(?m)^[ \t]*{capability_id}\["', source)) >= minimum_capabilities
        and output_count >= minimum_outputs
        and any(
            re.search(
                rf"(?m)^[ \t]*{input_id}[ \t]+{re.escape(connector)}"
                rf"[ \t]+{product_id}[ \t]*$",
                source,
            )
            and re.search(
                rf"(?m)^[ \t]*{product_id}[ \t]+{re.escape(connector)}"
                r"[ \t]+Capabilities[ \t]*$",
                source,
            )
            and (
                output_count == 0
                or re.search(
                    rf"(?m)^[ \t]*Capabilities[ \t]+{re.escape(connector)}"
                    r"[ \t]+Outputs[ \t]*$",
                    source,
                )
            )
            for connector in connectors
        )
    )


def _mermaid_has_specific_product_label(candidate_text: str) -> bool:
    """Distinguish the invisible Mermaid node ID from its visible product label."""

    blocks = re.findall(r"(?ms)^```mermaid[ \t]*\r?\n(.*?)^```[ \t]*$", candidate_text)
    if len(blocks) != 1:
        return False
    match = re.search(
        r'(?mi)^[ \t]*(?:product|PRODUCT)\["(?P<label>[^"\r\n]+)"\][ \t]*$',
        blocks[0],
    )
    if match is None:
        return False
    return match.group("label").strip().casefold() not in {
        "api",
        "product",
        "product api",
        "product/api",
    }


def grounding_retry_context(
    *,
    errors: list[str],
    candidate_text: str,
    product_facts: dict | None,
    findings: tuple[GroundedReviewFindingV1, ...] = (),
    visitor_contract: dict | None = None,
) -> str:
    """Return bounded reconciliation evidence without another producer verdict."""

    disproven_ids = deterministically_disproven_finding_ids(errors)
    selected_fact_ids = (product_facts or {}).get("selected_fact_ids", {})
    selected_ids = set(selected_fact_ids.values())
    finding_fact_ids = {finding.fact_id for finding in findings if finding.fact_id}
    relevant_fact_ids = finding_fact_ids or selected_ids
    accepted_fact_evidence = []
    for fact in (product_facts or {}).get("facts", []):
        if (
            not isinstance(fact, dict)
            or fact.get("fact_id") not in selected_ids
            or fact.get("fact_id") not in relevant_fact_ids
        ):
            continue
        accepted_fact_evidence.append(
            compact_review_fact(
                {
                    "fact_id": fact.get("fact_id"),
                    "field": fact.get("field"),
                    "value": compact_prompt_fact_value(
                        str(fact.get("field", "")), fact.get("value")
                    ),
                    "verification_state": fact.get("verification_state"),
                    "evidence_location": (fact.get("source") or {}).get("location"),
                    "evidence_assessments": fact.get("evidence_assessments") or [],
                    "unresolved_conflicts": [
                        conflict
                        for conflict in fact.get("conflicts") or []
                        if isinstance(conflict, dict) and conflict.get("status") == "unresolved"
                    ],
                }
            )
        )
    payload = {
        "validation_errors": errors,
        "candidate_sha256": hashlib.sha256(candidate_text.encode("utf-8")).hexdigest(),
        "candidate_size_bytes": len(candidate_text.encode("utf-8")),
        "candidate_anchor_catalog": compact_candidate_anchor_catalog(candidate_text),
        "invalid_findings": [
            (
                {
                    "finding_id": finding.finding_id,
                    "disposition": "deterministically_disproven",
                }
                if finding.finding_id in disproven_ids
                else {
                    "finding_id": finding.finding_id,
                    "claim": finding.claim,
                    "quoted_candidate_span": finding.quoted_candidate_span,
                    "candidate_anchor_id": finding.candidate_anchor_id,
                    "disposition": finding.disposition,
                    "fact_id": finding.fact_id,
                    "evidence_excerpt": finding.evidence_excerpt,
                    "evidence_location": finding.evidence_location,
                    "expected_polarity": finding.expected_polarity,
                    "observed_polarity": finding.observed_polarity,
                    "polarity_result": finding.polarity_result,
                    "required_repair": finding.required_repair,
                }
            )
            for finding in findings
        ],
        "visitor_contract": visitor_contract or {},
        "selected_fact_ids": {
            field: fact_id
            for field, fact_id in selected_fact_ids.items()
            if fact_id in relevant_fact_ids
        },
        "accepted_fact_evidence": accepted_fact_evidence,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def deterministically_disproven_finding_ids(errors: list[str]) -> set[str]:
    """Return finding IDs whose premises the deterministic contract disproves."""

    return {
        error.split(":", maxsplit=1)[0]
        for error in errors
        if any(marker in error for marker in ("contradicts", "conflicts with", "is unconfigured"))
    }
