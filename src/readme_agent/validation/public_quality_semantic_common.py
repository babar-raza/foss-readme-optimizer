"""Shared semantic cues for public-quality contradiction checks."""

from __future__ import annotations

import re

from readme_agent.readme.capability_semantics import identifier_discriminators
from readme_agent.validation.public_quality_contracts import PublicQualityDirection

# ---------------------------------------------------------------------------------------------
# Shared cue patterns (generic English polarity/scope cues -- no product/family branching)
# ---------------------------------------------------------------------------------------------

_POSITIVE_CUE = re.compile(
    r"(?i)\b(?:support(?:s|ed|ing)?|provide[sd]?|providing|implement(?:s|ed|ing)?|enable[sd]?|"
    r"enabling|allow(?:s|ed|ing)?|return(?:s|ed|ing)?|creat(?:e[sd]?|ing)|export(?:s|ed|ing)?|"
    r"import(?:s|ed|ing)?|convert(?:s|ed|ing)?|render(?:s|ed|ing)?|generat(?:e[sd]?|ing)|"
    r"sav(?:e[sd]?|ing)|load(?:s|ed|ing)?|pars(?:e[sd]?|ing)|reads?|reading|writ(?:e[sd]?|ing)|"
    r"calls?\b.*\boperation\b)\b"
)
_NEGATIVE_CUE = re.compile(
    r"(?i)\b(?:not\s+(?:currently\s+)?(?:support(?:ed)?|implement(?:ed)?|available|reachable)|"
    r"unsupported|no\s+support\s+for|NotImplementedError|not\s+yet\s+(?:supported|implemented)|"
    r"unavailable|limit(?:ed)?\s+to|restrict(?:ed)?\s+to|remain(?:s)?\s+incomplete|"
    r"out\s+of\s+scope|only\b.{0,80}\bsupported)\b"
)
_SCOPE_QUALIFIER = re.compile(
    r"(?i)\b(?:through\s+the\s+public\s+api|in\s+this\s+build|in\s+this\s+edition|"
    r"on\s+this\s+platform)\b"
)
# Independently defined, publicly-scoped equivalent of capability_semantics.py's private
# _READ_DIRECTION/_WRITE_DIRECTION (same vocabulary; that pair is module-private there, and
# AGENTS.md disallows depending on another module's `_`-private helpers).
_READ_CUE = re.compile(
    r"(?i)\b(?:read(?:s|ing)?|load(?:s|ing)?|import(?:s|ing)?|open(?:s|ing)?|pars(?:e|es|ing))\b"
)
_WRITE_CUE = re.compile(
    r"(?i)\b(?:writ(?:e|es|ing)|sav(?:e|es|ing)|export(?:s|ing)?|generat(?:e|es|ing))\b"
)
_BACKTICK_SYMBOL = re.compile(
    r"`([A-Za-z_][A-Za-z0-9_.]*)(?:\([^`\r\n]*\))?(?:\s*->\s*[^`\r\n]+)?`"
)
_INLINE_CODE_SPAN = re.compile(r"`[^`\r\n]+`")
_URL = re.compile(r"https?://\S+")
_WORD = re.compile(r"[A-Za-z]+")
_IDENTIFIER_TOKEN = re.compile(r"`[^`\r\n]+`|\b[a-z]+(?:_[a-z0-9]+)+\b")
_SAFE_DOUBLES = frozenset({"that", "had", "has", "was"})
_INFLECTION_SUFFIXES = ("ing", "ed", "es")
_PLACEHOLDER_BODY = re.compile(r"(?i)^(?:tbd|coming soon\.?|lorem ipsum.*|n/a)$")
# "Saving formats other than PDF ... are not implemented" narrows the negative claim AWAY FROM
# PDF, not onto it -- an explicit exception clause removes its named discriminator(s) from the
# negative statement's subject before matching, so a broad "everything except X" limitation does
# not fire against every unrelated positive claim that happens to mention X (found via the
# manual precision dry-run against real committed candidates; see WORKLOG.md).
_EXCEPTION_CLAUSE = re.compile(
    r"(?i)\b(?:other\s+than|except(?:ing)?|excluding|besides)\s+"
    r"([A-Za-z0-9][A-Za-z0-9/+.\-, ()]{0,60}?)(?=[.;]|\)?\s+(?:are|is|were|was)\b|$)"
)
# Conditional runtime-dependency prose ("if `X` is installed ... / if `X` is unavailable ...")
# describes branching behavior, not an unconditional capability claim -- also found via the
# manual precision dry-run.
_CONDITIONAL_MARKER = re.compile(
    r"(?i)\bif\s+(?:the\s+)?[`\"']?[\w.]+[`\"']?\s+is\s+"
    r"(?:installed|not\s+installed|available|unavailable|not\s+available|present|absent)\b"
)


def _excepted_discriminators(value: str) -> frozenset[str]:
    excepted: set[str] = set()
    for match in _EXCEPTION_CLAUSE.finditer(value):
        excepted |= identifier_discriminators(match.group(1))
    return frozenset(excepted)


def _spans_overlap(index: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= index < end for start, end in spans)


def _direction(value: str) -> PublicQualityDirection | None:
    reads = _READ_CUE.search(value) is not None
    writes = _WRITE_CUE.search(value) is not None
    if reads and not writes:
        return "read"
    if writes and not reads:
        return "write"
    return None


def _opposite_direction(left: str, right: str) -> bool:
    left_direction = _direction(left)
    right_direction = _direction(right)
    return (
        left_direction is not None
        and right_direction is not None
        and left_direction != right_direction
    )
