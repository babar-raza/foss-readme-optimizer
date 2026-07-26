"""Build typed visitor-facing phrases from selected product facts."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2

_ACCEPTED_STATES = {"verified", "policy_approved"}
_ECOSYSTEM_LABELS = {
    "cpp": "C++",
    "dotnet": ".NET",
    "go": "Go",
    "java": "Java",
    "net": ".NET",
    "python": "Python",
    "rust": "Rust",
    "typescript": "TypeScript",
}


class VisitorFactRenderViewV1(BaseModel):
    """Fact-bound prose fragments that are safe to offer to an author."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: str
    field: str
    phrases: list[str]


def _text_phrases(value: object) -> list[str]:
    values = value if isinstance(value, list) else [value]
    return [str(item).strip() for item in values if isinstance(item, str) and item.strip()]


def _identity_phrases(value: object) -> list[str]:
    if not isinstance(value, dict):
        return []
    names = value.get("manifest_names")
    if isinstance(names, list):
        return [str(name).strip() for name in names if str(name).strip()]
    return []


def _compatibility_phrases(value: object) -> list[str]:
    rows = value if isinstance(value, list) else [value]
    phrases: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ecosystem = str(row.get("ecosystem") or row.get("platform") or "").strip().lower()
        runtime = str(row.get("minimum_runtime") or "").strip()
        label = _ECOSYSTEM_LABELS.get(ecosystem)
        if label and runtime:
            phrases.append(f"Requires {label} {runtime} or later.")
    return phrases


def _no_direct_prose(_value: object) -> list[str]:
    """Keep internal policy codes and structured contracts out of authored prose."""

    return []


_FIELD_RENDERERS: dict[str, Callable[[object], list[str]]] = {
    "product.audience": _text_phrases,
    "product.problems_solved": _text_phrases,
    "product.capabilities": _text_phrases,
    "product.formats": _text_phrases,
    "product.limitations": _text_phrases,
    "product.identity": _identity_phrases,
    "product.compatibility": _compatibility_phrases,
    "installation.verified_acquisition": _no_direct_prose,
    "relationship.commercial_foss": _no_direct_prose,
    "support.routes": _no_direct_prose,
}


def visitor_fact_render_view(
    facts: ProductFactsV2,
    field: str,
) -> VisitorFactRenderViewV1 | None:
    """Return a safe render view for one accepted selected fact, if supported."""

    renderer = _FIELD_RENDERERS.get(field)
    if renderer is None:
        return None
    fact: FactRecordV2 = facts.selected_fact(field)
    if fact.verification_state not in _ACCEPTED_STATES or fact.has_unresolved_conflict:
        return None
    phrases = list(dict.fromkeys(renderer(fact.value)))
    return VisitorFactRenderViewV1(
        fact_id=fact.fact_id,
        field=field,
        phrases=phrases,
    )
