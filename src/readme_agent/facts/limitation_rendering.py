"""Render verified limitation items without discarding public API identifiers."""

from __future__ import annotations

import re

_INTERNAL_TOKEN_RE = re.compile(
    r"(?:[a-z0-9]+_[a-z0-9_]+|[a-z0-9]+(?:-[a-z0-9]+)+/[A-Za-z0-9._-]+|://)",
    flags=re.IGNORECASE,
)
_INTERNAL_PATH_RE = re.compile(
    r"(?:[a-z0-9]+(?:-[a-z0-9]+)+/[A-Za-z0-9._-]+|(?:^|\s)\.{0,2}/\S+)",
    flags=re.IGNORECASE,
)
_KEY_VALUE_RE = re.compile(r"^[a-z][a-z0-9_]*\s*[:=]")


def _is_visitor_limitation_phrase(value: str) -> bool:
    phrase = value.strip()
    return bool(
        phrase
        and "\n" not in phrase
        and "://" not in phrase
        and _INTERNAL_TOKEN_RE.fullmatch(phrase) is None
        and not _KEY_VALUE_RE.search(phrase)
        and not _INTERNAL_PATH_RE.search(phrase)
        and not any(character in phrase for character in "{}[]")
        and len(re.findall(r"[A-Za-z0-9]+", phrase)) >= 2
    )


def limitation_phrases(value: object) -> list[str]:
    """Return every safe limitation phrase, or none when any item is malformed."""

    rows = value if isinstance(value, list) else [value]
    phrases: list[str] = []
    for row in rows:
        statement = row.get("statement") if isinstance(row, dict) else row
        if not isinstance(statement, str) or not _is_visitor_limitation_phrase(statement):
            return []
        phrases.append(statement.strip())
    return [
        re.sub(r"\breportlab\b", "ReportLab", phrase, flags=re.IGNORECASE) for phrase in phrases
    ]
