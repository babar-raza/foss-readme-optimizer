"""Register repository-bound detail collectors for curated README retention."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.curated_constraint_evidence import source_limitations
from readme_agent.facts.curated_python_evidence import (
    example_inventory,
    python_optional_extras,
    python_public_surface,
)
from readme_agent.facts.curated_repository_assets import (
    development_assets,
    repository_ci,
    third_party_notices,
)
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id

_CollectorResult = tuple[object, list[str]]


def _source(
    source_type: str,
    locations: list[str],
    source_revision: str | None,
    observed_at: str | None,
) -> FactSourceV2:
    return FactSourceV2(
        source_type=source_type,  # type: ignore[arg-type]
        location="repository://" + ",".join(locations),
        source_revision=source_revision,
        retrieved_at=observed_at,
    )


def _fact(
    field: str,
    qualifier: str,
    value: object,
    *,
    source_type: str,
    locations: list[str],
    source_revision: str | None,
    observed_at: str | None,
) -> FactRecordV2:
    return FactRecordV2(
        fact_id=descriptive_fact_id(field, qualifier),
        field=field,
        value=value,
        source=_source(source_type, locations, source_revision, observed_at),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=SURFACE_DEPENDENCIES[field],
    )


def curated_repository_fact_candidates(
    root: Path,
    source_revision: str | None,
    observed_at: str | None,
) -> list[FactRecordV2]:
    """Return conservative, mechanically evidenced detail facts from one snapshot."""

    collectors = (
        (
            "installation.optional_extras",
            "python-manifest",
            "mechanical_manifest",
            python_optional_extras,
        ),
        ("api.public_surface", "python-exports", "mechanical_repository", python_public_surface),
        (
            "repository.examples",
            "repository-inventory",
            "mechanical_repository",
            example_inventory,
        ),
        (
            "development.assets",
            "repository-inventory",
            "mechanical_repository",
            development_assets,
        ),
        (
            "repository.third_party_notices",
            "root-notices-file",
            "mechanical_repository",
            third_party_notices,
        ),
        ("repository.ci", "canonical-workflow", "mechanical_repository", repository_ci),
        (
            "product.limitations",
            "executable-constraints",
            "mechanical_repository",
            source_limitations,
        ),
    )
    facts: list[FactRecordV2] = []
    for field, qualifier, source_type, collector in collectors:
        result: _CollectorResult | None = collector(root)
        if result is None:
            continue
        value, locations = result
        facts.append(
            _fact(
                field,
                qualifier,
                value,
                source_type=source_type,
                locations=locations,
                source_revision=source_revision,
                observed_at=observed_at,
            )
        )
    return facts
