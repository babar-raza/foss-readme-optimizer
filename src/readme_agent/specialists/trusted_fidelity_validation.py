"""Ground trusted fidelity-review output in exact source and candidate spans."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import cast

from pydantic import ValidationError

from readme_agent.errors import LLMError
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.verification_prompts import build_role_grounding_retry_message
from readme_agent.readme.trusted_composition_candidate_validation import (
    normalize_enterprise_edition_terminology,
    strip_readme_comments,
)
from readme_agent.specialists.review_role_execution import AnalysisClientLike
from readme_agent.specialists.trusted_transform_review_models import (
    TrustedFidelityReviewResultV1,
)

_MAX_ATTEMPTS = 2
_PROMPT_ID = "trusted_readme_fidelity_review"
_EMPTY_SENTINELS = frozenset({"none", "n/a", "not applicable", "no repair required"})
_MARKDOWN_LINK = re.compile(r"(?<!!)\[(?P<label>[^\]]+)\]\((?P<url>[^)\s]+)(?:\s+\"[^\"]*\")?\)")
_LOCAL_LINK = re.compile(r"(?<!!)\[(?P<label>[^\]]+)\]\(#[^)]+\)")
_BOLD_TEXT = re.compile(r"\*\*(?P<label>[^*]+)\*\*")


class TrustedFidelityRoleFailure(LLMError):
    """Fidelity failure that retains evidence from every bounded attempt."""

    def __init__(self, message: str, *, retry_history: tuple[dict, ...]) -> None:
        super().__init__(message)
        self.retry_history = retry_history


def normalize_trusted_fidelity_output(
    value: object,
    graph: TrustedReadmeFactGraphV1 | None = None,
    candidate_text: str | None = None,
    *,
    allow_unsupported_additions: bool = True,
) -> object:
    """Canonicalize redundancy and downgrade ungrounded preservation to a repairable loss."""

    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    facts = {fact.fact_id: fact for fact in graph.inherited_facts} if graph is not None else {}
    standard_ids = (
        {standard.standard_id for standard in graph.configured_standards}
        if graph is not None
        else set()
    )
    no_comments = "readme.no_comments" in standard_ids
    allow_link_removal = "readme.contextual_links" in standard_ids
    allow_enterprise_terminology = "readme.enterprise_edition_terminology" in standard_ids
    allow_navigation_links = "readme.navigation" in standard_ids
    forbid_promotional_blockquotes = bool(
        graph is not None
        and any(
            standard.standard_id == "readme.contextual_links"
            and bool(standard.parameters.get("forbid_blockquotes"))
            for standard in graph.configured_standards
        )
    )
    source_checks = []
    for raw_check in normalized.get("source_checks", []):
        if not isinstance(raw_check, dict):
            source_checks.append(raw_check)
            continue
        check = dict(raw_check)
        fact = facts.get(str(check.get("fact_id", "")))
        if fact is not None and str(check.get("source_quote", "")) not in fact.value:
            check["source_quote"] = fact.value
        if candidate_text is not None:
            authorized_quote = (
                _authorized_candidate_quote(
                    fact.value,
                    candidate_text,
                    no_comments=no_comments,
                    allow_link_removal=allow_link_removal,
                    allow_enterprise_terminology=allow_enterprise_terminology,
                    allow_navigation_links=allow_navigation_links,
                )
                if fact is not None
                else None
            )
            if (
                authorized_quote is None
                and fact is not None
                and fact.material_kind == "blockquote"
                and forbid_promotional_blockquotes
            ):
                authorized_quote = _represented_promotional_blockquote(
                    fact.value,
                    candidate_text,
                    allow_enterprise_terminology=allow_enterprise_terminology,
                )
            if authorized_quote is not None:
                check["candidate_quote"] = authorized_quote
                check["outcome"] = "preserved_or_represented"
                check["required_repair"] = ""
            candidate_quote = str(check.get("candidate_quote", ""))
            if candidate_quote and candidate_quote not in candidate_text:
                check["candidate_quote"] = ""
                if check.get("outcome") == "preserved_or_represented":
                    check["outcome"] = "lost_or_distorted"
            if (
                not str(check.get("candidate_quote", ""))
                and check.get("outcome") == "preserved_or_represented"
            ):
                check["outcome"] = "lost_or_distorted"
        if check.get("outcome") == "preserved_or_represented":
            check["required_repair"] = ""
        if (
            check.get("outcome") == "lost_or_distorted"
            and not str(check.get("required_repair", "")).strip()
            and str(check.get("fact_id", "")).strip()
        ):
            check["required_repair"] = (
                f"Restore or accurately represent inherited source unit {check['fact_id']}."
            )
        if (
            check.get("outcome") == "lost_or_distorted"
            and fact is not None
            and fact.material_kind == "code"
            and no_comments
        ):
            check["required_repair"] = (
                f"Restore the executable statements from inherited source unit {check['fact_id']} "
                "while omitting all comments and docstrings."
            )
        source_checks.append(check)
    normalized["source_checks"] = source_checks
    if str(normalized.get("required_repair", "")).strip().lower() in _EMPTY_SENTINELS:
        normalized["required_repair"] = ""
    defects = [
        item
        for item in source_checks
        if isinstance(item, dict) and item.get("outcome") == "lost_or_distorted"
    ]
    additions = [
        item
        for item in (
            normalized.get("unsupported_additions", []) if allow_unsupported_additions else []
        )
        if isinstance(item, dict)
        and not (
            candidate_text is not None
            and any(
                _authorized_source_derivation(
                    str(item.get("quoted_candidate_span", "")),
                    fact.value,
                    no_comments=no_comments,
                    allow_link_removal=allow_link_removal,
                    allow_enterprise_terminology=allow_enterprise_terminology,
                    allow_navigation_links=allow_navigation_links,
                )
                for fact in facts.values()
            )
        )
    ]
    normalized["unsupported_additions"] = additions
    if normalized.get("verdict") == "ACCEPT" and (defects or additions):
        normalized["verdict"] = "REJECT_REPAIRABLE"
    if normalized.get("verdict") != "SYSTEM_FAILURE" and not defects and not additions:
        normalized["verdict"] = "ACCEPT"
        normalized["failed_criteria"] = []
        normalized["sections_affected"] = []
        normalized["required_repair"] = ""
    if normalized.get("verdict") == "REJECT_REPAIRABLE":
        normalized["failed_criteria"] = ["inheritance_fidelity"] if defects or additions else []
        normalized["sections_affected"] = list(
            dict.fromkeys(
                str(item["section"])
                for item in [*defects, *additions]
                if str(item.get("section", "")).strip()
            )
        )
        normalized["required_repair"] = " ".join(
            dict.fromkeys(
                str(item["required_repair"]).strip()
                for item in [*defects, *additions]
                if str(item.get("required_repair", "")).strip()
            )
        )
    return normalized


def _authorized_candidate_quote(
    source_text: str,
    candidate_text: str,
    *,
    no_comments: bool,
    allow_link_removal: bool,
    allow_enterprise_terminology: bool,
    allow_navigation_links: bool,
) -> str | None:
    """Bind source text after only configured global transformations."""

    source_lines = _canonical_visible_lines(
        source_text,
        no_comments=no_comments,
        allow_link_removal=allow_link_removal,
        allow_enterprise_terminology=allow_enterprise_terminology,
        allow_navigation_links=allow_navigation_links,
    )
    if not source_lines:
        return None
    candidate_source_lines = candidate_text.splitlines(keepends=True)
    candidate_records = [
        (line_number, canonical)
        for line_number, line in enumerate(candidate_source_lines)
        if (
            canonical := _canonical_visible_line(
                line,
                allow_link_removal=allow_link_removal,
                allow_enterprise_terminology=allow_enterprise_terminology,
                allow_navigation_links=allow_navigation_links,
            )
        )
    ]
    candidate_lines = [canonical for _line_number, canonical in candidate_records]
    width = len(source_lines)
    for start in range(0, len(candidate_lines) - width + 1):
        if candidate_lines[start : start + width] == source_lines:
            source_start = candidate_records[start][0]
            source_end = candidate_records[start + width - 1][0]
            return "".join(candidate_source_lines[source_start : source_end + 1])
    return None


def _authorized_source_derivation(
    candidate_span: str,
    source_text: str,
    *,
    no_comments: bool,
    allow_link_removal: bool,
    allow_enterprise_terminology: bool,
    allow_navigation_links: bool,
) -> bool:
    """Return whether a cited addition is source text under allowed normalization."""

    if allow_navigation_links:
        navigation = _LOCAL_LINK.search(candidate_span)
        source_heading = re.fullmatch(r"\s*#{1,6}[ \t]+(.+?)\s*", source_text)
        if (
            navigation is not None
            and source_heading is not None
            and _canonical_navigation_label(navigation.group("label"))
            == _canonical_navigation_label(source_heading.group(1))
        ):
            return True
    candidate_lines = _canonical_visible_lines(
        candidate_span,
        no_comments=no_comments,
        allow_link_removal=allow_link_removal,
        allow_enterprise_terminology=allow_enterprise_terminology,
        allow_navigation_links=allow_navigation_links,
    )
    source_lines = _canonical_visible_lines(
        source_text,
        no_comments=no_comments,
        allow_link_removal=allow_link_removal,
        allow_enterprise_terminology=allow_enterprise_terminology,
        allow_navigation_links=allow_navigation_links,
    )
    if not candidate_lines or not source_lines:
        return False
    candidate_value = "\n".join(candidate_lines)
    source_value = "\n".join(source_lines)
    return candidate_value in source_value


def _canonical_navigation_label(value: str) -> str:
    return " ".join(value.split()).casefold()


def _canonical_visible_lines(
    text: str,
    *,
    no_comments: bool,
    allow_link_removal: bool,
    allow_enterprise_terminology: bool,
    allow_navigation_links: bool,
) -> list[str]:
    normalized = strip_readme_comments(text) if no_comments else text
    return [
        canonical
        for line in normalized.splitlines()
        if (
            canonical := _canonical_visible_line(
                line,
                allow_link_removal=allow_link_removal,
                allow_enterprise_terminology=allow_enterprise_terminology,
                allow_navigation_links=allow_navigation_links,
            )
        )
    ]


def _canonical_visible_line(
    line: str,
    *,
    allow_link_removal: bool,
    allow_enterprise_terminology: bool,
    allow_navigation_links: bool,
) -> str:
    normalized = (
        normalize_enterprise_edition_terminology(line) if allow_enterprise_terminology else line
    )
    if allow_link_removal:
        normalized = _MARKDOWN_LINK.sub(lambda match: match.group("label"), normalized)
    if allow_navigation_links:
        normalized = _LOCAL_LINK.sub(lambda match: match.group("label"), normalized)
    return " ".join(normalized.split()).casefold()


def _represented_promotional_blockquote(
    source_text: str,
    candidate_text: str,
    *,
    allow_enterprise_terminology: bool,
) -> str | None:
    """Prove concrete identities survived after removing a forbidden promotional callout."""

    labels = [
        match.group("label").strip()
        for match in [*_MARKDOWN_LINK.finditer(source_text), *_BOLD_TEXT.finditer(source_text)]
        if match.group("label").strip()
    ]
    for domain in ("aspose.org", "aspose.com"):
        if domain in source_text.casefold():
            labels.append(domain)
    if allow_enterprise_terminology and re.search(
        r"(?i)\b(?:commercial|on[- ]premise)\s+(?:product|edition)\b",
        source_text,
    ):
        labels.append("Enterprise Edition")
    required = tuple(dict.fromkeys(labels))
    candidate_folded = candidate_text.casefold()
    if not required or any(label.casefold() not in candidate_folded for label in required):
        return None
    first = required[0]
    start = candidate_folded.find(first.casefold())
    return candidate_text[start : start + len(first)]


def validate_trusted_fidelity_result(
    result: TrustedFidelityReviewResultV1,
    graph: TrustedReadmeFactGraphV1,
    candidate_text: str,
    *,
    allow_unsupported_additions: bool = True,
) -> tuple[str, ...]:
    """Reject incomplete inventories, invented quotes, and wrong verdict direction."""

    if result.verdict == "SYSTEM_FAILURE":
        return ()
    errors: list[str] = []
    facts = {fact.fact_id: fact for fact in graph.inherited_facts}
    check_ids = [item.fact_id for item in result.source_checks]
    if len(check_ids) != len(set(check_ids)):
        errors.append("duplicate inherited fact checks")
    if set(check_ids) != set(facts):
        missing = sorted(set(facts) - set(check_ids))
        unknown = sorted(set(check_ids) - set(facts))
        errors.append(f"source-check inventory mismatch: missing={missing}, unknown={unknown}")
    for check in result.source_checks:
        fact = facts.get(check.fact_id)
        if fact is None:
            continue
        if check.source_quote not in fact.value:
            errors.append(f"{check.fact_id}: source quote is absent from inherited source")
        if check.candidate_quote and check.candidate_quote not in candidate_text:
            errors.append(f"{check.fact_id}: candidate quote is absent")
    for addition in result.unsupported_additions:
        if addition.quoted_candidate_span not in candidate_text:
            errors.append(f"{addition.finding_id}: candidate quote is absent")
    if result.unsupported_additions and not allow_unsupported_additions:
        errors.append("unsupported additions are outside this fact-only review part")
    defects = any(item.outcome == "lost_or_distorted" for item in result.source_checks) or bool(
        result.unsupported_additions
    )
    if result.verdict == "ACCEPT" and defects:
        errors.append("fidelity ACCEPT contradicts grounded defects")
    if result.verdict == "REJECT_REPAIRABLE" and not defects:
        errors.append("fidelity rejection has no grounded defect")
    return tuple(errors)


def run_trusted_fidelity_role(
    *,
    client: AnalysisClientLike,
    messages: list[dict],
    graph: TrustedReadmeFactGraphV1,
    candidate_text: str,
    allow_unsupported_additions: bool = True,
    authorization_graph: TrustedReadmeFactGraphV1 | None = None,
) -> tuple[TrustedFidelityReviewResultV1, tuple[dict, ...]]:
    """Run one fidelity role with one bounded deterministic-grounding correction."""

    current_messages = list(messages)
    history: list[dict] = []
    required_fact_ids = tuple(fact.fact_id for fact in graph.inherited_facts)
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        constrained_analyze = getattr(client, "analyze_fidelity", None)
        analysis: AnalysisResult = (
            cast(Callable[[list[dict], tuple[str, ...]], AnalysisResult], constrained_analyze)(
                current_messages,
                required_fact_ids,
            )
            if callable(constrained_analyze)
            else client.analyze(current_messages)
        )
        try:
            parsed = TrustedFidelityReviewResultV1.model_validate(
                normalize_trusted_fidelity_output(
                    analysis.parsed,
                    graph=authorization_graph or graph,
                    candidate_text=candidate_text,
                    allow_unsupported_additions=allow_unsupported_additions,
                )
            )
            errors = validate_trusted_fidelity_result(
                parsed,
                graph,
                candidate_text,
                allow_unsupported_additions=allow_unsupported_additions,
            )
        except ValidationError as exc:
            parsed = None
            errors = (f"trusted fidelity output contract violation: {exc}",)
        history.append(
            {
                "role": "inheritance_fidelity",
                "attempt": attempt,
                "valid": not errors,
                "errors": list(errors),
            }
        )
        if parsed is not None and not errors:
            return parsed, tuple(history)
        if attempt == _MAX_ATTEMPTS:
            raise TrustedFidelityRoleFailure(
                f"inheritance fidelity reviewer repeatedly returned ungrounded output: {errors}",
                retry_history=tuple(history),
            )
        reconciliation = json.dumps(
            {
                "validation_errors": errors,
                "required_source_units": [
                    {
                        "fact_id": fact.fact_id,
                        "exact_source_text": fact.value,
                    }
                    for fact in graph.inherited_facts
                ],
                "exact_candidate_segment_text": candidate_text,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        current_messages = [
            *messages,
            build_role_grounding_retry_message(_PROMPT_ID, reconciliation),
        ]
    raise AssertionError("trusted fidelity retry loop must return or raise")
