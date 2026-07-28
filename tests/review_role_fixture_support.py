"""Build schema-valid grounded ACCEPT responses from real reviewer prompt inputs."""

from __future__ import annotations

import json

from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.readme.fact_grounding import fact_strings


def _section(text: str, start: str, end: str) -> str:
    try:
        return text.split(start, 1)[1].split(end, 1)[0].strip()
    except IndexError as exc:
        raise AssertionError(f"fixture reviewer could not find prompt section {start!r}") from exc


def _blind_accept(user_content: str) -> dict:
    candidate = _section(user_content, "Candidate README:\n", "\n\nReview only")
    span = next((line.strip() for line in candidate.splitlines() if line.strip()), "")
    if not span:
        raise AssertionError("fixture blind reviewer received an empty candidate")
    return {
        "verdict": "ACCEPT",
        "reasoning": "The exact title span supports visible-document acceptance.",
        "failed_criteria": [],
        "sections_affected": [],
        "required_repair": "",
        "findings": [
            {
                "finding_id": "quality.fixture-title",
                "kind": "quality",
                "criterion": "clarity",
                "section": "title",
                "claim": "The candidate has a clear product title.",
                "quoted_candidate_span": span,
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
    candidate = _section(user_content, "Candidate README:\n", "\n\nAccepted ProductFactsV2:")
    facts = json.loads(
        _section(user_content, "Accepted ProductFactsV2:\n", "\n\nBounded presentation plan:")
    )
    by_id = {
        str(fact["fact_id"]): fact
        for fact in facts.get("facts", [])
        if isinstance(fact, dict) and fact.get("fact_id")
    }
    for fact_id in facts.get("selected_fact_ids", {}).values():
        fact = by_id.get(str(fact_id))
        if fact is None or fact.get("verification_state") not in {"verified", "policy_approved"}:
            continue
        source_location = str((fact.get("source") or {}).get("location", ""))
        if not source_location:
            continue
        for phrase in fact_strings(fact.get("value")):
            if len(phrase.strip()) >= 4 and phrase.casefold() in candidate.casefold():
                start = candidate.casefold().index(phrase.casefold())
                exact_span = candidate[start : start + len(phrase)]
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
                            "evidence_excerpt": phrase,
                            "evidence_location": source_location,
                            "expected_polarity": "positive_implementation",
                            "observed_polarity": "positive_implementation",
                            "polarity_result": "supports",
                            "required_repair": "",
                        }
                    ],
                }
    raise AssertionError("fixture factual reviewer found no selected literal fact in candidate")


class GroundedAcceptingRoleReviewClient:
    """Return role-specific grounded acceptance through the production result seam."""

    def __init__(self, *args, **kwargs):
        pass

    def analyze(self, messages: list[dict]) -> AnalysisResult:
        system_content = str(messages[0]["content"])
        user_content = str(messages[-1]["content"])
        parsed = (
            _blind_accept(user_content)
            if "blind visitor-quality reviewer" in system_content
            else _factual_accept(user_content)
        )
        return AnalysisResult(parsed=parsed, meta=LLMResponseMeta(model="fixture-reviewer"))


def grounded_accepting_role_clients(*args, **kwargs):
    """Build two independent instances so role-call state cannot leak."""

    return GroundedAcceptingRoleReviewClient(), GroundedAcceptingRoleReviewClient()
