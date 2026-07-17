"""The actual "no changes outside the owned spans" proof: strip every owned
span out of the current README and confirm what's left is byte-identical to
the baseline -- a fixed trim-and-compare, not a heuristic diff, made possible
by markers.remove_span being the exact inverse of upsert_span's insertion.
"""

from readme_agent.readme.markers import SPAN_NAMES, remove_span
from readme_agent.validation.context import ValidationContext
from readme_agent.validation.result import RuleResult

NAME = "change_boundary"


def check(ctx: ValidationContext) -> RuleResult:
    stripped = ctx.readme_text
    for span_name in SPAN_NAMES:
        stripped = remove_span(stripped, span_name)

    if stripped == ctx.baseline_readme_text:
        return RuleResult(NAME, True, "ERROR", "no changes outside the owned spans")
    return RuleResult(
        NAME,
        False,
        "ERROR",
        "content outside the owned spans differs from baseline after stripping "
        "the spans -- something touched README content this tool doesn't own",
    )
