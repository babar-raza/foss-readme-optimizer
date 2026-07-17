"""Post-hoc evidence proof: the re-derived facts_hash matches the hash
embedded in the current span, when one exists. N/A (passes trivially) when
there's no existing span to compare against yet."""

from readme_agent.validation.context import ValidationContext
from readme_agent.validation.result import RuleResult

NAME = "idempotency"


def check(ctx: ValidationContext) -> RuleResult:
    if ctx.embedded_hash is None:
        return RuleResult(NAME, True, "ERROR", "no existing span to compare against")
    if ctx.embedded_hash == ctx.facts_hash:
        return RuleResult(NAME, True, "ERROR", "embedded hash matches the re-derived facts_hash")
    return RuleResult(
        NAME,
        False,
        "ERROR",
        f"embedded hash {ctx.embedded_hash!r} != re-derived facts_hash {ctx.facts_hash!r}",
    )
