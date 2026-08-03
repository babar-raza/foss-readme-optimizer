"""Select distinct, verified destinations and fallback signals for README badges."""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlsplit, urlunsplit

from readme_agent.facts.render_views import ecosystem_display_label
from readme_agent.facts.schema_v2 import ProductFactsV2

_ACCEPTED_STATES = {"verified", "policy_approved"}


def normalized_badge_target(target_url: str | None) -> str | None:
    """Return the comparison key for one badge destination."""

    if target_url is None or not target_url.strip():
        return None
    parsed = urlsplit(target_url.strip())
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold(),
            path,
            parsed.query,
            parsed.fragment,
        )
    )


def badge_target_is_already_used(
    existing_targets: Iterable[str | None],
    candidate_target: str | None,
) -> bool:
    """Report whether a candidate repeats an existing semantic destination."""

    candidate = normalized_badge_target(candidate_target)
    return candidate is not None and candidate in {
        normalized
        for target in existing_targets
        if (normalized := normalized_badge_target(target)) is not None
    }


def _safe_badge_value(value: object) -> str | None:
    text = " ".join(str(value).split()).strip()
    if not text or any(token in text for token in ("<!--", "[", "]", "(", ")", "`")):
        return None
    return text[:64].rstrip()


def verified_compatibility_badge_signal(
    facts: ProductFactsV2,
) -> tuple[str, list[str]] | None:
    """Return a visitor-facing runtime requirement backed by the selected fact."""

    try:
        compatibility = facts.selected_fact("product.compatibility")
    except KeyError:
        return None
    if (
        compatibility.verification_state not in _ACCEPTED_STATES
        or compatibility.has_unresolved_conflict
    ):
        return None
    rows = compatibility.value if isinstance(compatibility.value, list) else [compatibility.value]
    row = next((item for item in rows if isinstance(item, dict)), None)
    if row is None:
        return None
    minimum = _safe_badge_value(row.get("minimum_runtime"))
    if not minimum:
        return None
    runtime = _safe_badge_value(row.get("runtime_label"))
    if not runtime:
        ecosystem = str(row.get("ecosystem") or "").strip()
        runtime = ecosystem_display_label(ecosystem) if ecosystem else None
    value = f"{runtime} {minimum}" if runtime else minimum
    return value, [compatibility.fact_id]
