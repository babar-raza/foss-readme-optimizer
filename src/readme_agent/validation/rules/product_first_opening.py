"""ERROR severity: the README opening must explain the product before any
commercial mention (BIZ-001, RDM-002 -- both P0). Checked against the *final*
README text regardless of whether this run rendered anything, unlike the
legacy four-element gap check, which only governs what gets additively
rendered into a gap.
"""

from readme_agent.readme.gap_detector import first_commercial_link_index
from readme_agent.readme.presentation_report import product_explanation_offset
from readme_agent.validation.context import ValidationContext
from readme_agent.validation.result import RuleResult

NAME = "product_first_opening"


def check(ctx: ValidationContext) -> RuleResult:
    commercial_idx = first_commercial_link_index(ctx.readme_text)
    if commercial_idx is None:
        return RuleResult(NAME, True, "ERROR", "no commercial link present -- nothing to check")

    explain_offset = product_explanation_offset(ctx.readme_text)
    if explain_offset is not None and explain_offset < commercial_idx:
        return RuleResult(NAME, True, "ERROR", "product explained before the first commercial link")
    if explain_offset is None:
        return RuleResult(
            NAME,
            False,
            "ERROR",
            "a commercial link is present but the opening does not explain the product first",
        )
    return RuleResult(
        NAME, False, "ERROR", "a commercial link appears before the product is explained"
    )
