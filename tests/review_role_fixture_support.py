"""Build schema-valid grounded ACCEPT responses from real reviewer prompt inputs."""

from __future__ import annotations

import json
from collections.abc import Iterable

from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.readme.fact_grounding import fact_strings


def _section(text: str, start: str, end: str) -> str:
    try:
        return text.split(start, 1)[1].split(end, 1)[0].strip()
    except IndexError as exc:
        raise AssertionError(f"fixture reviewer could not find prompt section {start!r}") from exc


def _blind_candidate_anchor(user_content: str) -> tuple[str, str | None]:
    catalog_start = "Complete candidate README block catalog, in source order:\n"
    catalog_end = "\n\nAuthoritative parser-derived mechanical observations:"
    if catalog_start in user_content:
        catalog = json.loads(_section(user_content, catalog_start, catalog_end))
        if not isinstance(catalog, list) or not catalog:
            raise AssertionError("fixture blind reviewer received an empty candidate catalog")
        first = catalog[0]
        # `compact_candidate_anchor_catalog()` (specialists/factual_review_projection.py),
        # the only producer of this prompt field for both merged and bounded/role
        # review, has always returned `[anchor_id, text]` pairs, not
        # `{"anchor_id": ..., "text": ...}` dicts -- this file's own
        # `_merged_accept_payload` already parses it that way. Never reached
        # through role review until bounded routing widened beyond an oversize
        # escape hatch (`fix(review): route by rubric evidence, not candidate
        # size`, 6591c6cc2).
        if not isinstance(first, list) or len(first) != 2:
            raise AssertionError("fixture blind reviewer received a malformed candidate catalog")
        anchor_id, span = str(first[0]), str(first[1])
        if not span.strip() or not anchor_id:
            raise AssertionError("fixture blind reviewer received an incomplete candidate anchor")
        return span, anchor_id

    candidate = _section(user_content, "Candidate README:\n", "\n\nReview only")
    span = next((line.strip() for line in candidate.splitlines() if line.strip()), "")
    return span, None


def _blind_accept(user_content: str) -> dict:
    span, anchor_id = _blind_candidate_anchor(user_content)
    if not span:
        raise AssertionError("fixture blind reviewer received an empty candidate")
    return {
        "verdict": "ACCEPT",
        "reasoning": "The exact span supports visible-document acceptance.",
        "failed_criteria": [],
        "sections_affected": [],
        "required_repair": "",
        "findings": [
            {
                "finding_id": "quality.fixture-span",
                "kind": "quality",
                # `bounded_visitor_scope.py`'s per-section `_CRITERIA_BY_ROOT`/
                # `_DEFAULT_CRITERIA` narrows which criteria a bounded-review call may use --
                # this fixture answers for whichever candidate anchor happens to be under
                # review (not just the title), so it must pick a criterion every root
                # allows. `markdown_integrity` is the one criterion present in every entry
                # of `_CRITERIA_BY_ROOT` (including "navigation", which excludes "clarity")
                # and in `_DEFAULT_CRITERIA` -- the fixed "clarity" this used to hardcode
                # was outside "navigation"'s bounded scope, forcing a grounding retry this
                # fixture has no branch for (VER-012).
                "criterion": "markdown_integrity",
                "section": "content",
                "claim": "The candidate span uses well-formed Markdown.",
                "quoted_candidate_span": span,
                "candidate_anchor_id": anchor_id,
                "disposition": "supports_acceptance",
                "fact_id": None,
                "evidence_excerpt": None,
                "evidence_location": None,
                "expected_polarity": None,
                "observed_polarity": None,
                "polarity_result": "not_applicable",
                "required_repair": "",
            }
        ],
    }


def _factual_accept(user_content: str) -> dict:
    new_packet = "Selected accepted fact evidence packet:\n"
    new_plan = "Compact plan, source-preservation, and candidate-claim packet:\n"
    if new_packet in user_content:
        candidate = _section(user_content, "Candidate README:\n", f"\n\n{new_packet.rstrip()}")
        facts = json.loads(_section(user_content, new_packet, f"\n\n{new_plan.rstrip()}"))
        plan = json.loads(
            _section(
                user_content,
                new_plan,
                "\n\nReview factual grounding and plan-to-candidate agreement",
            )
        )
        for claim in plan.get("candidate_claims", []):
            if not isinstance(claim, dict):
                continue
            if claim.get("verification_state") not in {"verified", "policy_approved"}:
                continue
            if claim.get("unresolved_conflicts"):
                continue
            exact_span = str(claim.get("claim_text", ""))
            evidence_excerpt = str(claim.get("evidence_excerpt", ""))
            evidence_location = str(claim.get("evidence_location", ""))
            fact_id = str(claim.get("fact_id", ""))
            if (
                exact_span
                and exact_span in candidate
                and evidence_excerpt
                and evidence_location
                and fact_id
            ):
                return _supported_factual_response(
                    exact_span=exact_span,
                    fact_id=fact_id,
                    evidence_excerpt=evidence_excerpt,
                    evidence_location=evidence_location,
                )
        literal_response = _selected_fact_response(candidate, facts)
        if literal_response is not None:
            return literal_response
        raise AssertionError(
            "fixture factual reviewer found neither a prebound claim nor a selected literal fact"
        )

    candidate = _section(user_content, "Candidate README:\n", "\n\nAccepted ProductFactsV2:")
    facts = json.loads(
        _section(user_content, "Accepted ProductFactsV2:\n", "\n\nBounded presentation plan:")
    )
    literal_response = _selected_fact_response(candidate, facts)
    if literal_response is not None:
        return literal_response
    raise AssertionError("fixture factual reviewer found no selected literal fact in candidate")


def _selected_fact_ids(facts: dict) -> Iterable[str]:
    # Two real, independently valid production shapes reach this helper: the merged-review
    # path's full `ProductFactsV2.selected_fact_ids` (dict[field, fact_id]), and a bounded
    # per-section factual packet's own `accepted_fact_ids` (list[fact_id] already scoped to
    # that packet -- `bounded_review_execution_factual.py::execute_factual_packet()`'s
    # `fact_context`). Neither key implies the other is absent, so check the packet-scoped
    # list first (it is the narrower, more specific set when present).
    accepted = facts.get("accepted_fact_ids")
    if accepted is not None:
        return accepted
    return facts.get("selected_fact_ids", {}).values()


def _accepted_facts(facts: dict) -> list[dict]:
    by_id = {
        str(fact["fact_id"]): fact
        for fact in facts.get("selected_facts", facts.get("facts", []))
        if isinstance(fact, dict) and fact.get("fact_id")
    }
    return [
        by_id[str(fact_id)]
        for fact_id in _selected_fact_ids(facts)
        if str(fact_id) in by_id
        and by_id[str(fact_id)].get("verification_state") in {"verified", "policy_approved"}
    ]


def _selected_fact_response(candidate: str, facts: dict) -> dict | None:
    accepted = _accepted_facts(facts)
    for fact in accepted:
        source_location = str(
            fact.get("evidence_location") or (fact.get("source") or {}).get("location", "")
        )
        if not source_location:
            continue
        for phrase in fact_strings(fact.get("value")):
            if len(phrase.strip()) >= 4 and phrase.casefold() in candidate.casefold():
                start = candidate.casefold().index(phrase.casefold())
                exact_span = candidate[start : start + len(phrase)]
                return _supported_factual_response(
                    exact_span=exact_span,
                    fact_id=str(fact["fact_id"]),
                    evidence_excerpt=phrase,
                    evidence_location=source_location,
                )
    # No accepted fact's own literal value phrase appears verbatim in this candidate span --
    # expected for a generic template bullet with no fact-specific wording (e.g. a "Process
    # Supported Content" summary line). Grounding validates `quoted_candidate_span` (must be a
    # literal candidate substring) and `evidence_excerpt` (must relate to the cited fact's own
    # evidence) as two independent checks (`review_finding_grounding.py::
    # validate_review_findings`) that need not overlap with each other. Fall back to any
    # literal candidate line plus the fact's own source location, which
    # `_fact_evidence_strings()` always includes verbatim in its evidence set -- a guaranteed
    # exact match regardless of the fact's value shape.
    exact_span = next((line.strip() for line in candidate.splitlines() if line.strip()), "")
    if not exact_span:
        return None
    for fact in accepted:
        source_location = str(
            fact.get("evidence_location") or (fact.get("source") or {}).get("location", "")
        )
        if source_location:
            return _supported_factual_response(
                exact_span=exact_span,
                fact_id=str(fact["fact_id"]),
                evidence_excerpt=source_location,
                evidence_location=source_location,
            )
    return None


def _supported_factual_response(
    *,
    exact_span: str,
    fact_id: str,
    evidence_excerpt: str,
    evidence_location: str,
) -> dict:
    return {
        "verdict": "ACCEPT",
        "reasoning": "The exact candidate span is supported by the selected fact.",
        "failed_criteria": [],
        "sections_affected": [],
        "required_repair": "",
        "findings": [
            {
                "finding_id": "factual.fixture-supported",
                "kind": "factual",
                "criterion": "factuality",
                "section": "candidate",
                "claim": "The candidate contains a selected accepted fact.",
                "quoted_candidate_span": exact_span,
                "disposition": "supports_acceptance",
                "fact_id": fact_id,
                "evidence_excerpt": evidence_excerpt,
                "evidence_location": evidence_location,
                "expected_polarity": "positive_implementation",
                "observed_polarity": "positive_implementation",
                "polarity_result": "supports",
                "required_repair": "",
            }
        ],
    }


class GroundedAcceptingRoleReviewClient:
    """Return role-specific grounded acceptance through the production result seam."""

    def __init__(self, *args, **kwargs):
        pass

    def analyze(self, messages: list[dict]) -> AnalysisResult:
        system_content = str(messages[0]["content"])
        blind = "blind visitor-quality reviewer" in system_content
        expected_sections = (
            ("Complete candidate README block catalog", "Candidate README:")
            if blind
            else ("Selected accepted fact evidence packet", "Accepted ProductFactsV2:")
        )
        user_content = next(
            (
                str(message.get("content", ""))
                for message in reversed(messages[1:])
                if any(section in str(message.get("content", "")) for section in expected_sections)
            ),
            "",
        )
        if not user_content:
            raise AssertionError("fixture reviewer could not find its typed review input")
        parsed = _blind_accept(user_content) if blind else _factual_accept(user_content)
        return AnalysisResult(parsed=parsed, meta=LLMResponseMeta(model="fixture-reviewer"))


def grounded_accepting_role_clients(*args, **kwargs):
    """Build two independent instances so role-call state cannot leak."""

    return GroundedAcceptingRoleReviewClient(), GroundedAcceptingRoleReviewClient()
