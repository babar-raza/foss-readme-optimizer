"""Decide when registry-bound facts already have equivalent source-access proof."""

from __future__ import annotations

import re

_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def bounded_portfolio_facts_preflight_satisfied(args: object) -> bool:
    """Return true only after the portfolio scheduler fetched the exact remote HEAD.

    The FACTS_READY ceiling is contractually zero-LLM and executes no later capability. The
    registry scheduler loads durable state and obtains the member's live remote HEAD before it
    delegates here, so repeating the GitHub API and LLM-model preflight adds no assurance. Every
    single-repository or later-stage invocation retains the normal fail-closed preflight.
    """

    source_revision = getattr(args, "_portfolio_source_revision", None)
    return bool(
        getattr(args, "_portfolio_member", False)
        and getattr(args, "execution_profile", None) == "local_poc"
        and getattr(args, "max_readme_poc_stage", None) == "FACTS_READY"
        and isinstance(source_revision, str)
        and _GIT_SHA_RE.fullmatch(source_revision)
    )


__all__ = ["bounded_portfolio_facts_preflight_satisfied"]
