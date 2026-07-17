"""Flat phrase list, word-boundary, case-insensitive -- checked only against
content this run actually rendered, never pre-existing README content we
don't control (see aspose.org's forbidden_claims_check.py comparison in the
plan for why the heavier capability-claim-scanner style wasn't reused)."""

import re

from readme_agent.validation.context import ValidationContext
from readme_agent.validation.result import RuleResult

NAME = "prohibited_terms"


def check(ctx: ValidationContext) -> RuleResult:
    rendered_text = "\n".join(ctx.rendered_spans.values())
    if not rendered_text:
        return RuleResult(NAME, True, "ERROR", "no rendered content this run -- nothing to check")

    hits = []
    for term in ctx.policy.block.prohibited_terms:
        if re.search(rf"\b{re.escape(term)}\b", rendered_text, re.IGNORECASE):
            hits.append(term)

    if not hits:
        return RuleResult(NAME, True, "ERROR", "no prohibited terms found")
    return RuleResult(NAME, False, "ERROR", f"prohibited terms found: {', '.join(hits)}")
