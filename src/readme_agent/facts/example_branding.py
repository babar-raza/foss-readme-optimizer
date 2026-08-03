"""Normalize human-facing product display literals in verified examples."""

from __future__ import annotations

import re

from readme_agent.facts.render_views import ecosystem_display_label
from readme_agent.facts.schema_v2 import ProductFactsV2

_QUOTED_LITERAL = re.compile(
    r"""(?P<prefix>(?<![A-Za-z0-9_])(?:[rRuUbBfF]{0,2}))"""
    r"""(?P<literal>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')"""
)
_DISPLAY_CONTEXT = re.compile(r"[\s!?,.:;()\[\]{}]")


def full_product_display_name(facts: ProductFactsV2) -> str:
    """Return the verified portfolio display name for README prose and examples."""

    identity = facts.selected_fact("product.identity")
    if identity.verification_state not in {"verified", "policy_approved"}:
        raise ValueError("product identity must be accepted before example branding")
    value = identity.value if isinstance(identity.value, dict) else {}
    product_name = str(value.get("product_name") or "").strip()
    platform = str(value.get("platform") or value.get("ecosystem") or "").strip()
    if not product_name or not platform:
        raise ValueError("product identity lacks a product name or platform")
    product_name = re.sub(r"(?i)\s+FOSS(?:\s+for\s+.+)?$", "", product_name).strip()
    return f"{product_name} FOSS for {ecosystem_display_label(platform)}"


def normalize_example_display_literals(
    code: str,
    *,
    product_name: str,
    full_display_name: str,
) -> str:
    """Expand abbreviated product branding only inside natural-language string literals."""

    abbreviated = re.compile(
        rf"(?i)\b{re.escape(product_name)}\s+FOSS\b"
        rf"(?!\s+for\s+{re.escape(full_display_name.rsplit(' for ', 1)[-1])}\b)"
    )

    def replace(match: re.Match[str]) -> str:
        literal = match.group("literal")
        quote = literal[0]
        body = literal[1:-1]
        abbreviated_match = abbreviated.search(body)
        if abbreviated_match is None:
            return match.group(0)
        surrounding = body[: abbreviated_match.start()] + body[abbreviated_match.end() :]
        if not _DISPLAY_CONTEXT.search(surrounding):
            return match.group(0)
        normalized = abbreviated.sub(full_display_name, body)
        return f"{match.group('prefix')}{quote}{normalized}{quote}"

    return _QUOTED_LITERAL.sub(replace, code)
