"""Applies only to LLM-authored relationship prose -- deterministically
rendered links/license lines don't have a "word count" concept."""

from readme_agent.validation.context import ValidationContext
from readme_agent.validation.result import RuleResult

NAME = "word_count"


def check(ctx: ValidationContext) -> RuleResult:
    if ctx.llm_response is None:
        return RuleResult(NAME, True, "ERROR", "no LLM-authored prose this run -- nothing to check")

    count = len(ctx.llm_response.relationship_paragraph.split())
    limit = ctx.policy.block.word_limit
    if limit.min <= count <= limit.max:
        return RuleResult(NAME, True, "ERROR", f"{count} words within [{limit.min}, {limit.max}]")
    return RuleResult(
        NAME, False, "ERROR", f"{count} words outside policy range [{limit.min}, {limit.max}]"
    )
