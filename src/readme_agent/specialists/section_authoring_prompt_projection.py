"""Project full section facts into an assurance-neutral authoring view."""

from __future__ import annotations

from typing import Any

from readme_agent.specialists.section_authoring_contracts import SectionAuthoringFactV1


def _rows(value: object) -> list[dict[str, Any]]:
    candidates = value if isinstance(value, list) else [value]
    return [item for item in candidates if isinstance(item, dict)]


def _unique_text(rows: list[dict[str, Any]], key: str) -> list[str]:
    return sorted(
        {
            str(row[key]).strip()
            for row in rows
            if isinstance(row.get(key), str) and str(row[key]).strip()
        }
    )


def public_product_name_from_value(value: object) -> str | None:
    """Return an exact public name from the canonical identity value."""

    if not isinstance(value, dict):
        return None
    product_name = str(value.get("product_name") or "").strip()
    platform = str(value.get("platform") or value.get("ecosystem") or "").strip()
    rendered = " ".join(part for part in (product_name, "FOSS", "for", platform.title()) if part)
    return rendered or None


def public_product_name(fact: SectionAuthoringFactV1) -> str | None:
    """Return the exact public name exposed to the authoring provider."""

    if fact.field != "product.identity":
        return None
    return public_product_name_from_value(fact.value)


def _project_value(fact: SectionAuthoringFactV1) -> object:
    value = fact.value
    if fact.field == "product.identity" and isinstance(value, dict):
        platform = str(value.get("platform") or value.get("ecosystem") or "").strip()
        return {
            "public_product_name": public_product_name(fact),
            "family": value.get("family"),
            "platform": platform,
        }
    if fact.field == "installation.verified_acquisition" and isinstance(value, dict):
        return {
            "ecosystem": value.get("ecosystem"),
            "acquisition_method": value.get("method"),
        }
    if fact.field == "installation.coordinates":
        rows = _rows(value)
        return {
            "declared_coordinate_count": len(rows),
            "ecosystems": _unique_text(rows, "ecosystem"),
            "root_roles": _unique_text(rows, "root_role"),
        }
    if fact.field == "product.compatibility":
        rows = _rows(value)
        return {
            "ecosystems": _unique_text(rows, "ecosystem"),
            "runtime_labels": _unique_text(rows, "runtime_label"),
            "compatibility_kinds": _unique_text(rows, "compatibility_kind"),
        }
    if fact.field == "example.minimal" and isinstance(value, dict):
        demonstrated_operations: list[str] = []
        if value.get("class_name") and "=" in str(value.get("code") or ""):
            demonstrated_operations.append("instantiate one public API object")
        return {
            "language": value.get("language"),
            "purpose": "introductory public API usage",
            "demonstrated_operations": demonstrated_operations,
        }
    if fact.field == "api.public_surface" and isinstance(value, dict):
        modules = value.get("modules") or []
        classes = value.get("classes") or value.get("representative_classes") or []
        return {
            "has_public_surface": bool(modules or classes),
        }
    return value


def authoring_fact_prompt_payload(
    fact: SectionAuthoringFactV1,
    *,
    fact_id_alias: str | None = None,
) -> dict[str, object]:
    """Return the bounded model-facing view while preserving full facts in the packet.

    The provider does not need immutable revisions, evidence locations, raw package/API
    identifiers, or verification-receipt prose. Those values remain checksum-bound in the full
    packet and are enforced by deterministic code after the response returns.
    """

    return {
        "fact_id": fact_id_alias or fact.fact_id,
        "field": fact.field,
        "value": _project_value(fact),
        "polarity": fact.polarity,
    }


__all__ = [
    "authoring_fact_prompt_payload",
    "public_product_name",
    "public_product_name_from_value",
]
