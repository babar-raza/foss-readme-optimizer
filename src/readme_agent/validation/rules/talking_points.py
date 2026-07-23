"""Cross-checks the LLM's self-reported talking_points_covered against a
deterministic keyword heuristic on the actual prose -- self-report is never
trusted at face value anywhere in this design."""

import re

from readme_agent.validation.context import ValidationContext
from readme_agent.validation.result import RuleResult

NAME = "talking_points"

_KEYWORDS = {
    "open_source_scope": re.compile(
        r"\b(open[- ]source|open[- ]sourced|foss|free,? open)\b", re.IGNORECASE
    ),
    "commercial_upgrade_path": re.compile(
        r"\b(commercial|upgrade|full-featured|broader|paid|premium)\b", re.IGNORECASE
    ),
}


def missing_talking_points(text: str, required: list[str]) -> list[str]:
    """Return required talking points not evidenced by the actual prose."""

    return [point for point in required if point in _KEYWORDS and not _KEYWORDS[point].search(text)]


def check(ctx: ValidationContext) -> RuleResult:
    if ctx.llm_response is None:
        return RuleResult(NAME, True, "ERROR", "no LLM-authored prose this run -- nothing to check")

    required = ctx.policy.required_elements.relationship_explained.talking_points
    claimed = set(ctx.llm_response.talking_points_covered)

    missing_claim = [tp for tp in required if tp not in claimed]
    if missing_claim:
        return RuleResult(
            NAME, False, "ERROR", f"LLM did not claim to cover required points: {missing_claim}"
        )

    prose = ctx.llm_response.relationship_paragraph
    mismatches = missing_talking_points(prose, sorted(claimed))
    if mismatches:
        return RuleResult(
            NAME,
            False,
            "ERROR",
            f"LLM claimed to cover {mismatches} but the prose doesn't contain "
            "the expected language for it -- self-report not trusted",
        )
    return RuleResult(NAME, True, "ERROR", "claimed talking points verified against the prose")
