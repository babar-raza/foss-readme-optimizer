"""Every link in content rendered this run must resolve to a whitelisted domain."""

import re
from urllib.parse import urlparse

from readme_agent.validation.context import ValidationContext
from readme_agent.validation.result import RuleResult

NAME = "link_whitelist"
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\((https?://[^\s)]+)\)")


def check(ctx: ValidationContext) -> RuleResult:
    rendered_text = "\n".join(ctx.rendered_spans.values())
    if not rendered_text:
        return RuleResult(NAME, True, "ERROR", "no rendered content this run -- nothing to check")

    offenders = []
    for url in _MD_LINK_RE.findall(rendered_text):
        domain = urlparse(url).netloc
        if domain not in ctx.policy.block.link_whitelist_domains:
            offenders.append(domain)

    if not offenders:
        return RuleResult(NAME, True, "ERROR", "all rendered links are on the whitelist")
    return RuleResult(
        NAME, False, "ERROR", f"off-whitelist domains: {', '.join(sorted(set(offenders)))}"
    )
