"""ERROR severity: encodes the corrected decision #9 (docs/presentation-
standard.md dimension 9) -- a commercial (.com) mention must stay singular in
structure (no multi-link "resources" list block) and factual in tone. Checked
against the *final* README text regardless of whether this run rendered
anything (VAL-006, decision #9).

Verified against real evidence before being narrowed to list-item density
rather than raw occurrence count: pdf/java's real, already-good README
mentions products.aspose.com twice -- once inline ("API-compatible with
[...]"), once in an exemplary closing paragraph -- and must not be flagged;
aspose-3d-foss/...Java's bot-authored resources section, which lists five
separate commercial links as bullet items, must be.
"""

import re

from readme_agent.readme.gap_detector import commercial_com_link_matches
from readme_agent.readme.presentation_report import product_explanation_offset
from readme_agent.validation.context import ValidationContext
from readme_agent.validation.result import RuleResult

NAME = "commercial_mention_discipline"

_LIST_ITEM_RE = re.compile(r"^\s*[-*]\s")
_PROMOTIONAL_LANGUAGE_RE = re.compile(
    r"\b(buy now|unlock|best[- ]in[- ]class|act now|limited time|don'?t miss|"
    r"world[- ]class|industry[- ]leading|revolutionary|game[- ]chang\w*)\b",
    re.IGNORECASE,
)


def _is_list_item_line(text: str, offset: int) -> bool:
    line_start = text.rfind("\n", 0, offset) + 1
    line_end = text.find("\n", offset)
    if line_end == -1:
        line_end = len(text)
    return bool(_LIST_ITEM_RE.match(text[line_start:line_end]))


def check(ctx: ValidationContext) -> RuleResult:
    matches = commercial_com_link_matches(ctx.readme_text)
    if not matches:
        return RuleResult(NAME, True, "ERROR", "no commercial link present -- nothing to check")

    list_item_hits = [m for m in matches if _is_list_item_line(ctx.readme_text, m.start())]
    if len(list_item_hits) >= 2:
        return RuleResult(
            NAME,
            False,
            "ERROR",
            f"{len(list_item_hits)} commercial links formatted as list items -- decision #9 "
            "requires a single factual mention, not a link list",
        )

    near_text = "\n".join(ctx.readme_text[max(0, m.start() - 100) : m.end() + 100] for m in matches)
    promo_hits = _PROMOTIONAL_LANGUAGE_RE.findall(near_text)
    if promo_hits:
        return RuleResult(
            NAME,
            False,
            "ERROR",
            f"promotional language near a commercial mention: {', '.join(promo_hits)}",
        )

    explain_offset = product_explanation_offset(ctx.readme_text)
    halfway = len(ctx.readme_text) // 2
    ok_position = all(
        (explain_offset is not None and explain_offset < m.start() < explain_offset + 500)
        or m.start() >= halfway
        for m in matches
    )
    if not ok_position:
        return RuleResult(
            NAME,
            False,
            "ERROR",
            "commercial mention is not directly under the opening description or in a closing "
            "section",
        )

    return RuleResult(NAME, True, "ERROR", "commercial mention is factual and correctly placed")
