"""Ordered rule pipeline + aggregation. All rules run on every invocation,
including the idempotent (hash-matches) and zero-gap paths -- idempotency only
ever decides whether the *LLM* gets called, never whether validation runs.
`product_first_opening` and `commercial_mention_discipline` (Phase 21) are the
first two rules that check the *whole* README, not just content rendered this
run -- a zero-gap, hash-matched repo can still fail one of them.
"""

import hashlib
import inspect

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

# VER-004: bump whenever a rule module's pass/fail logic changes in a way that
# could affect previously-accepted content (a stricter/looser check, a new
# rule added/removed) -- folded into readme/facts.py::_HASH_FIELDS, the same
# "manually bumped for a contract change the file hash can't see" convention
# GENERATION_SCHEMA_VERSION already establishes. A pure refactor/comment/
# whitespace edit with no behavioral change does not need a bump.
#
# _RULES_SOURCE_HASH_AT_VERSION is a forget-proofing tripwire, not the actual
# staleness mechanism: test_validation_registry.py recomputes RULES' current
# source hash and fails loudly if it no longer matches this recorded value,
# forcing a conscious "does this need a version bump" decision on every rule
# edit instead of a silent miss. Update it (via the helper below) whenever you
# touch a rule module, whether or not VALIDATION_RULESET_VERSION also moves.
VALIDATION_RULESET_VERSION = "1"
_RULES_SOURCE_HASH_AT_VERSION = "bc10867cfe6316ba021d3578486011683e6f15762efba5d2fe94c64c1e35f499"


def compute_rules_source_hash() -> str:
    """The live hash `test_validation_registry.py`'s tripwire test compares
    against `_RULES_SOURCE_HASH_AT_VERSION` -- never used at runtime by
    `durable_skip` itself (that's `VALIDATION_RULESET_VERSION`'s job, deliberately
    cheap and manually-controlled); this one is deliberately over-sensitive
    (any source change, including whitespace) since it's a one-time,
    human-reviewed CI gate, not a live per-request comparison."""
    source = "".join(inspect.getsource(rule) for rule in RULES)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def run_all(ctx: ValidationContext) -> list[RuleResult]:
    return [rule.check(ctx) for rule in RULES]


def hard_failures(results: list[RuleResult]) -> list[RuleResult]:
    return [r for r in results if r.severity == "ERROR" and not r.passed]


def passed(results: list[RuleResult]) -> bool:
    return not hard_failures(results)
