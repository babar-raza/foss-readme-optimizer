"""Build canonical input bindings for initial and reviewer-directed composition."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from readme_agent.facts.prompt_projection import prompt_fact_value
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_models import ReadmeCompositionRepairRequestV1

_MAX_PROMPT_API_ITEMS = 16
_MAX_PROMPT_ASSET_PATHS = 5


def compact_prompt_fact_value(field: str, value: Any) -> Any:
    """Keep author/reviewer evidence useful without copying native inventories.

    The full fact value remains checksum-bound in ``ProductFactsV2``. This view is
    deliberately lossy: it exposes representative public symbols and asset counts,
    while source trees, per-file hashes, and verifier transcripts stay in evidence.
    """

    projected = prompt_fact_value(field, value)
    if field == "api.public_surface" and isinstance(projected, dict):
        modules = projected.get("modules") or []
        classes = projected.get("classes") or []
        exports = _unique_strings(
            export
            for module in modules
            if isinstance(module, dict)
            for export in module.get("exports") or []
        )
        class_names = _unique_strings(
            item.get("name") for item in classes if isinstance(item, dict)
        )
        member_surfaces = _unique_strings(
            member.get("surface") or member.get("name")
            for item in classes
            if isinstance(item, dict)
            for member in item.get("members") or []
            if isinstance(member, dict)
        )
        return {
            "module_names": _unique_strings(
                module.get("module") for module in modules if isinstance(module, dict)
            )[:_MAX_PROMPT_API_ITEMS],
            "representative_exports": exports[:_MAX_PROMPT_API_ITEMS],
            "representative_classes": class_names[:_MAX_PROMPT_API_ITEMS],
            "representative_member_surfaces": member_surfaces[:_MAX_PROMPT_API_ITEMS],
            "inventory_counts": {
                "modules": len(modules),
                "exports": len(exports),
                "classes": len(classes),
                "member_surfaces": len(member_surfaces),
            },
            "projection_bounded": any(
                count > _MAX_PROMPT_API_ITEMS
                for count in (len(exports), len(class_names), len(member_surfaces))
            ),
        }
    if field == "development.assets" and isinstance(projected, dict):
        compact_groups: dict[str, dict[str, Any]] = {}
        for group_name, group in projected.items():
            if not isinstance(group, dict):
                continue
            paths = [
                str(item.get("path"))
                for item in group.get("representative_paths") or []
                if isinstance(item, dict) and item.get("path")
            ]
            compact_groups[str(group_name)] = {
                "count": group.get("count"),
                "inventory_sha256": group.get("inventory_sha256"),
                "representative_paths": paths[:_MAX_PROMPT_ASSET_PATHS],
            }
        return compact_groups
    if field == "example.minimal" and isinstance(projected, dict):
        package = projected.get("python_package")
        compact_package = None
        if isinstance(package, dict):
            compact_package = {
                key: package.get(key)
                for key in (
                    "distribution_name",
                    "version",
                    "requires_python",
                    "canonical_import",
                )
                if package.get(key) is not None
            }
        return {
            key: projected.get(key)
            for key in (
                "language",
                "code",
                "verification_outcome",
                "verification_detail",
                "verified_public_symbols",
                "input_fixture_bindings",
            )
            if projected.get(key) is not None
        } | ({"python_package": compact_package} if compact_package else {})
    return projected


def _unique_strings(values: Iterable[object]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value is not None and str(value)))


def composition_fact_payloads(
    facts: ProductFactsV2,
    accepted_fact_ids: set[str],
) -> list[dict]:
    """Project accepted facts into a compact authoring packet.

    The complete provenance graph and native-tool receipts remain authoritative in
    ``ProductFactsV2`` and the evidence bundle. The model needs only selected values,
    compact provenance, and stable citation IDs; sending compiled-consumer transcripts
    duplicates evidence and can add hundreds of thousands of prompt tokens.
    """

    return [
        {
            "fact_id": fact.fact_id,
            "field": fact.field,
            "value": compact_prompt_fact_value(fact.field, fact.value),
            "source": {
                "source_type": fact.source.source_type,
                "location": fact.source.location,
                "source_revision": fact.source.source_revision,
            },
            "supporting_fact_ids": fact.supporting_fact_ids,
        }
        for fact in facts.facts
        if fact.fact_id in accepted_fact_ids
    ]


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
