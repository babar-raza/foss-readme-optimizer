"""Register repository-bound detail collectors for curated README retention."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.curated_python_dependencies import (
    python_capability_dependencies,
    python_distribution_evidence,
)
from readme_agent.facts.curated_python_evidence import (
    example_inventory,
    python_optional_extras,
    python_public_surface,
    python_source_format_directions,
)
from readme_agent.facts.curated_python_implementation import python_implementation_components
from readme_agent.facts.curated_python_import_shadowing import python_import_shadowing
from readme_agent.facts.curated_python_pdf_evidence import python_pdf_capability_details
from readme_agent.facts.curated_python_pdf_guidance import (
    python_pdf_public_guidance,
    python_pdf_verified_boundaries,
)
from readme_agent.facts.curated_repository_assets import (
    development_assets,
    repository_ci,
    third_party_notices,
)
from readme_agent.facts.curated_repository_guidance import (
    repository_contribution_guidance,
    repository_development_commands,
    repository_documentation_assets,
    repository_security_guidance,
    source_guidance_limitations,
)
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.python_golden_workflow import python_golden_workflow_fact
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
    affected_surfaces: list[str] | None = None,
) -> FactRecordV2:
    return FactRecordV2(
        fact_id=descriptive_fact_id(field, qualifier),
        field=field,
        value=value,
        source=_source(source_type, locations, source_revision, observed_at),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=affected_surfaces or SURFACE_DEPENDENCIES[field],
    )


def curated_repository_fact_candidates(
    root: Path,
    source_revision: str | None,
    observed_at: str | None,
    *,
    ecosystem: str | None = None,
) -> list[FactRecordV2]:
    """Return conservative, mechanically evidenced detail facts from one snapshot."""

    collectors = (
        (
            "installation.optional_extras",
            "python-manifest",
            "mechanical_manifest",
            python_optional_extras,
        ),
        (
            "installation.capability_dependencies",
            "python-source",
            "mechanical_repository",
            python_capability_dependencies,
        ),
        (
            "python.distribution",
            "pyproject-manifest",
            "mechanical_manifest",
            python_distribution_evidence,
        ),
        ("api.public_surface", "python-exports", "mechanical_repository", python_public_surface),
        (
            "repository.implementation_components",
            "python-implementation-components",
            "mechanical_repository",
            python_implementation_components,
        ),
        (
            "repository.examples",
            "repository-inventory",
            "mechanical_repository",
            lambda candidate_root: example_inventory(candidate_root, source_revision),
        ),
        (
            "repository.format_directions",
            "python-source-directions",
            "mechanical_repository",
            python_source_format_directions,
        ),
        (
            "repository.python_import_shadowing",
            "python-package-export-overrides",
            "mechanical_repository",
            python_import_shadowing,
        ),
        (
            "development.assets",
            "repository-inventory",
            "mechanical_repository",
            development_assets,
        ),
        (
            "development.commands",
            "repository-guidance",
            "mechanical_repository",
            repository_development_commands,
        ),
        (
            "repository.documentation_assets",
            "root-documents",
            "mechanical_repository",
            repository_documentation_assets,
        ),
        (
            "repository.security_guidance",
            "security-policy-and-source",
            "mechanical_repository",
            repository_security_guidance,
        ),
        (
            "repository.contribution_guidance",
            "repository-entry-points",
            "mechanical_repository",
            repository_contribution_guidance,
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
            "source-guidance",
            "mechanical_repository",
            source_guidance_limitations,
        ),
        (
            "repository.capability_details",
            "python-public-source-surfaces",
            "mechanical_repository",
            python_pdf_capability_details,
        ),
        (
            "repository.public_guidance",
            "python-pdf-source-guidance",
            "mechanical_repository",
            python_pdf_public_guidance,
        ),
        (
            "repository.verified_boundaries",
            "authoritative-source-and-tests",
            "mechanical_repository",
            python_pdf_verified_boundaries,
        ),
    )
    facts: list[FactRecordV2] = []
    python_fields = {
        "installation.optional_extras",
        "installation.capability_dependencies",
        "python.distribution",
        "api.public_surface",
        "repository.implementation_components",
        "repository.format_directions",
        "repository.python_import_shadowing",
        "repository.capability_details",
        "repository.public_guidance",
        "repository.verified_boundaries",
    }
    for field, qualifier, source_type, collector in collectors:
        if ecosystem is not None and ecosystem.casefold() != "python" and field in python_fields:
            continue
        result: _CollectorResult | None = collector(root)
        if result is None:
            continue
        value, locations = result
        affected_surfaces = {
            "repository.capability_details": ["readme.capabilities", "readme.examples"],
            "repository.implementation_components": ["readme.opening", "readme.api_reference"],
            "repository.format_directions": ["readme.capabilities"],
            "repository.python_import_shadowing": ["readme.api"],
            "repository.public_guidance": ["readme.opening", "readme.examples"],
            "repository.verified_boundaries": ["readme.limitations", "readme.security"],
        }.get(field)
        facts.append(
            _fact(
                field,
                qualifier,
                value,
                source_type=source_type,
                locations=locations,
                source_revision=source_revision,
                observed_at=observed_at,
                affected_surfaces=affected_surfaces,
            )
        )
    if ecosystem is None or ecosystem.casefold() == "python":
        golden_workflow = python_golden_workflow_fact(
            root,
            source_revision=source_revision,
            observed_at=observed_at,
        )
        if golden_workflow is not None:
            facts.append(golden_workflow)
    return facts
