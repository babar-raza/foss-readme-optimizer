"""Ordered rule pipeline + aggregation. All 8 rules run on every invocation,
including the idempotent (hash-matches) and zero-gap paths -- idempotency only
ever decides whether the *LLM* gets called, never whether validation runs.
"""

from readme_agent.validation.context import ValidationContext
from readme_agent.validation.result import RuleResult
from readme_agent.validation.rules import (
    change_boundary,
    idempotency,
    link_whitelist,
    prohibited_terms,
    prominence,
    referential_integrity,
    talking_points,
    word_count,
)

RULES = (
    word_count,
    prohibited_terms,
    link_whitelist,
    change_boundary,
    talking_points,
    referential_integrity,
    idempotency,
    prominence,
)


def run_all(ctx: ValidationContext) -> list[RuleResult]:
    return [rule.check(ctx) for rule in RULES]


def hard_failures(results: list[RuleResult]) -> list[RuleResult]:
    return [r for r in results if r.severity == "ERROR" and not r.passed]


def passed(results: list[RuleResult]) -> bool:
    return not hard_failures(results)
