"""Deterministic fact precedence, conflict recording, and field selection."""

from __future__ import annotations

import json
from collections import defaultdict

from readme_agent.facts.root_role_schema import PackageRootRoleInventoryV1
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    ConflictStatus,
    FactConflictV2,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.license.auditor import classify_license_text

_SOURCE_PRECEDENCE = {
    "mechanical_repository": 1,
    "mechanical_manifest": 1,
    "mechanical_test": 1,
    "external_registry": 1,
    "approved_policy": 2,
    "release": 3,
    "approved_documentation": 3,
    "agent_drafted": 3,
    "readme_claim": 4,
}

_VERIFICATION_PRECEDENCE = {
    "verified": 0,
    "policy_approved": 0,
    "conflicting": 1,
    "unverified": 2,
    "blocked": 3,
    "missing": 4,
}


def source_precedence(source: FactSourceV2) -> int:
    return _SOURCE_PRECEDENCE[source.source_type]


def _canonical_value(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _canonical_fact_value(field_name: str, value) -> str:
    if field_name == "product.license" and isinstance(value, str):
        value = classify_license_text(value) or value.strip()
    return _canonical_value(value)


def _missing_fact(field_name: str, source: FactSourceV2, surfaces: list[str]) -> FactRecordV2:
    return FactRecordV2(
        fact_id=descriptive_fact_id(field_name, "missing"),
        field=field_name,
        value=None,
        source=source,
        verification_state="missing",
        authoritative_owner="repository-owner",
        confidence=0.0,
        affected_surfaces=surfaces,
    )


def resolve_product_facts(
    org_repo: str,
    candidates: list[FactRecordV2],
    *,
    missing_source: FactSourceV2,
    required_fields: tuple[str, ...] = REQUIRED_PRODUCT_FIELDS,
    missing_field_surfaces: dict[str, list[str]] | None = None,
    package_root_roles: PackageRootRoleInventoryV1 | None = None,
) -> ProductFactsV2:
    """Resolve candidates without discarding lower-precedence provenance.

    A lower-precedence disagreement is retained as ``resolved_by_precedence``.
    Different values at the same highest precedence are unresolved and block
    only their affected surfaces.
    """

    grouped: dict[str, list[FactRecordV2]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.field].append(candidate)

    output: list[FactRecordV2] = []
    selected: dict[str, str] = {}
    surface_defaults = missing_field_surfaces or {}

    for field_name in required_fields:
        field_candidates = grouped.pop(field_name, [])
        if not field_candidates:
            missing = _missing_fact(
                field_name,
                missing_source,
                surface_defaults.get(field_name, ["unclassified"]),
            )
            output.append(missing)
            selected[field_name] = missing.fact_id
            continue

        ranked = sorted(
            field_candidates,
            key=lambda fact: (
                source_precedence(fact.source),
                _VERIFICATION_PRECEDENCE[fact.verification_state],
                fact.fact_id,
            ),
        )
        winner = ranked[0]
        winner_rank = source_precedence(winner.source)
        conflicts = list(winner.conflicts)
        unresolved = False
        for competitor in ranked[1:]:
            # A blocked/missing observation describes an unavailable evidence
            # path, not a competing factual assertion. Preserve it for
            # provenance without turning it into a false value conflict when
            # another source at the same precedence proves the field.
            if competitor.verification_state in {"blocked", "missing"}:
                continue
            if _canonical_fact_value(field_name, competitor.value) == _canonical_fact_value(
                field_name, winner.value
            ):
                continue
            same_rank = source_precedence(competitor.source) == winner_rank
            status: ConflictStatus = "unresolved" if same_rank else "resolved_by_precedence"
            unresolved = unresolved or same_rank
            conflicts.append(
                FactConflictV2(
                    conflicting_fact_id=competitor.fact_id,
                    conflicting_value=competitor.value,
                    conflicting_source=competitor.source,
                    status=status,
                    reason=(
                        "same-precedence authoritative sources disagree"
                        if same_rank
                        else "higher-precedence source selected deterministically"
                    ),
                    authoritative_owner=winner.authoritative_owner,
                    affected_surfaces=sorted(
                        set(winner.affected_surfaces) | set(competitor.affected_surfaces)
                    ),
                )
            )
        winner = FactRecordV2.model_validate(
            {
                **winner.model_dump(mode="python"),
                "conflicts": conflicts,
                "verification_state": ("conflicting" if unresolved else winner.verification_state),
            }
        )
        output.extend([winner, *ranked[1:]])
        selected[field_name] = winner.fact_id

    # Preserve additional non-mandatory fact families and select their highest-precedence
    # candidate too, so extensions do not require a schema rewrite.
    for field_name, field_candidates in sorted(grouped.items()):
        ranked = sorted(
            field_candidates,
            key=lambda fact: (
                source_precedence(fact.source),
                _VERIFICATION_PRECEDENCE[fact.verification_state],
                fact.fact_id,
            ),
        )
        output.extend(ranked)
        selected[field_name] = ranked[0].fact_id

    return ProductFactsV2(
        org_repo=org_repo,
        facts=output,
        selected_fact_ids=selected,
        package_root_roles=package_root_roles,
    )
