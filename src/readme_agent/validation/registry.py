"""Ordered rule pipeline + aggregation. All rules run on every invocation,
including the idempotent (hash-matches) and zero-gap paths -- idempotency only
ever decides whether the *LLM* gets called, never whether validation runs.
`product_first_opening` and `commercial_mention_discipline` (Phase 21) are the
first two rules that check the *whole* README, not just content rendered this
run -- a zero-gap, hash-matched repo can still fail one of them.
"""

from readme_agent.validation.context import ValidationContext
from readme_agent.validation.result import RuleResult
from readme_agent.validation.rules import (
    change_boundary,
    commercial_mention_discipline,
    idempotency,
    link_whitelist,
    product_first_opening,
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
    product_first_opening,
    commercial_mention_discipline,
)


def run_all(ctx: ValidationContext) -> list[RuleResult]:
    return [rule.check(ctx) for rule in RULES]


def hard_failures(results: list[RuleResult]) -> list[RuleResult]:
    return [r for r in results if r.severity == "ERROR" and not r.passed]


def passed(results: list[RuleResult]) -> bool:
    return not hard_failures(results)
