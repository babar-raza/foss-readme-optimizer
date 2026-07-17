"""Hard gate: the LLM's claimed license/URL must match ground truth and what
was actually rendered -- consistent with never trusting the LLM's
self-reported claims at face value anywhere else in this design."""

from readme_agent.validation.context import ValidationContext
from readme_agent.validation.result import RuleResult

NAME = "referential_integrity"


def check(ctx: ValidationContext) -> RuleResult:
    if ctx.llm_response is None:
        return RuleResult(NAME, True, "ERROR", "no LLM response this run -- nothing to check")

    claims = ctx.llm_response.claims
    problems = []

    if claims.license_name and ctx.detected_license and claims.license_name != ctx.detected_license:
        problems.append(
            f"claimed license {claims.license_name!r} != detected license {ctx.detected_license!r}"
        )

    if claims.commercial_link_url:
        com_url = ctx.policy.required_elements.products_com_link.url
        if claims.commercial_link_url != com_url:
            problems.append(
                f"claimed commercial link {claims.commercial_link_url!r} != "
                f"policy's canonical URL {com_url!r}"
            )

    if not problems:
        return RuleResult(NAME, True, "ERROR", "LLM claims match ground truth and policy")
    return RuleResult(NAME, False, "ERROR", "; ".join(problems))
