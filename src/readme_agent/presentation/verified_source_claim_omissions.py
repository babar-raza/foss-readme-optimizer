"""Recognize exact inherited shells governed by deterministic omission policy."""

from __future__ import annotations

import re


def governed_source_omission(claim_text: str) -> tuple[str, str] | None:
    """Return the evidence kind and rationale for one governed legacy shell."""

    folded = claim_text.strip().casefold()
    if re.search(r"official\s+aspose\s+project|100\s*%\s+free", folded):
        return (
            "presentation-policy-correction",
            "Omit this exact promotional source unit under the product-first presentation "
            "contract; replacement content is separately fact-bound.",
        )
    if folded.startswith("quick links:"):
        return (
            "redundant-navigation-shell",
            "Omit this exact quick-link shell because the compiled candidate contains one "
            "complete list-based Navigation section.",
        )
    if folded.startswith("[![ci]"):
        return (
            "superseded-badge-shell",
            "Replace this exact inherited badge shell with the one-row fact-bound badge set.",
        )
    if folded.startswith("pypi release page (maintainers):"):
        return (
            "maintainer-only-link",
            "Omit this exact maintainer-only release-management URL.",
        )
    return None
