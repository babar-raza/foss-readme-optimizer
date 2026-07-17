"""WARNING-severity, non-blocking: flags a required element that's technically
present somewhere in the README but outside a "prominent zone." Directly
targets the pdf/Go finding from the 2026-07-17 audit -- one correctly-formed
commercial link, buried as the very last line of a 1890-line file, serving no
one. Starting heuristic (first ~2000 chars or before the first ## heading),
not a precisely validated threshold.
"""

import re

from readme_agent.validation.context import ValidationContext
from readme_agent.validation.result import RuleResult

NAME = "prominence"
PROMINENT_ZONE_CHARS = 2000

_CHECKS = {
    "products_org_link": re.compile(r"products\.aspose\.org", re.IGNORECASE),
    "products_com_link": re.compile(r"products\.aspose\.com", re.IGNORECASE),
}


def _prominent_zone_end(text: str) -> int:
    heading_match = re.search(r"^##[^#]", text, re.MULTILINE)
    heading_end = heading_match.start() if heading_match else len(text)
    return min(PROMINENT_ZONE_CHARS, max(heading_end, 1))


def check(ctx: ValidationContext) -> RuleResult:
    zone_end = _prominent_zone_end(ctx.readme_text)
    buried = []
    for element, pattern in _CHECKS.items():
        if getattr(ctx.pre_render_gap_report, element) is False:
            continue  # it's a gap, not our concern here -- rendering handles it
        match = pattern.search(ctx.readme_text)
        if match and match.start() > zone_end:
            buried.append(element)

    if not buried:
        return RuleResult(NAME, True, "WARNING", "present elements are within the prominent zone")
    return RuleResult(
        NAME,
        False,
        "WARNING",
        f"present but not prominent (outside first {PROMINENT_ZONE_CHARS} chars / "
        f"first ## heading): {buried}",
    )
