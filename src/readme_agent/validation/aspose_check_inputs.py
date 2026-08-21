"""Adapt candidate inputs for qualified Aspose checks without changing vendored code."""

from __future__ import annotations

import re
from typing import Any

_MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^()\s]+\)")


def qualified_check_inputs(name: str, available: dict[str, Any]) -> dict[str, Any]:
    """Return check-specific inputs that remove a proven upstream false-positive source."""

    if name != "check_format_name_casing" or "readme_text" not in available:
        return available
    # Badge/image alt text is accessibility metadata, not README prose.  Repository slugs in
    # contributor badges legitimately contain lowercase platform tokens (for example
    # ``example-net/...-for-NET``), while the visible product name uses ``.NET``.  The upstream
    # check strips link targets but retains image alt text, incorrectly reporting those two
    # tokens as conflicting prose.  Remove only complete Markdown images; ordinary link labels
    # and every actual prose occurrence remain available to the casing check.
    adapted = dict(available)
    adapted["readme_text"] = _MARKDOWN_IMAGE_RE.sub("", str(available["readme_text"]))
    return adapted
