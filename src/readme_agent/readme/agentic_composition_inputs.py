"""Build canonical input bindings for initial and reviewer-directed composition."""

from __future__ import annotations

import hashlib
import json

from readme_agent.readme.agentic_composition_models import ReadmeCompositionRepairRequestV1


def independent_repair_hints(request: ReadmeCompositionRepairRequestV1 | None) -> str:
    """Render one stable, source-bound reviewer instruction block."""

    if request is None:
        return ""
    return (
        "INDEPENDENT REVIEW REPAIR. The prior candidate was rejected. "
        "Address only the bounded findings below, preserve the named content, "
        "and still obey every deterministic section disposition and fact-ID constraint:\n"
        + json.dumps(request.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
    )


def composition_input_payload(
    *,
    org_repo: str,
    source_text: str,
    facts_payload: list[dict],
    assessment_payload: dict,
    phrase_options: list[dict],
    authoring_hints: str,
) -> dict:
    """Return the exact canonical payload whose hash binds an authoring plan."""

    return {
        "org_repo": org_repo,
        "source_text": source_text,
        "accepted_facts": facts_payload,
        "assessment": assessment_payload,
        "overview_phrase_options": phrase_options,
        "repair_hints_section": authoring_hints,
    }


def composition_input_sha256(payload: dict) -> str:
    """Hash a canonical authoring input without relying on serialization order."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
