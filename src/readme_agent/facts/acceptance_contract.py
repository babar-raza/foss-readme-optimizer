"""Version the complete deterministic contract that accepts cached product truth."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.gating import SurfaceFactRequirementV1, evaluate_surface_facts
from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2

ProductTruthOutcome = Literal[
    "FACTS_READY",
    "BLOCKED_FACT_CONFLICT",
    "BLOCKED_MISSING_EVIDENCE",
]

README_TRUTH_FIELDS = (
    "product.audience",
    "product.problems_solved",
    "product.capabilities",
    "product.formats",
    "installation.verified_acquisition",
    "example.minimal",
    "product.license",
    "relationship.commercial_foss",
)
ACCEPTED_VERIFICATION_STATES = ("policy_approved", "verified")
BLOCKING_CONFLICT_STATUSES = ("unresolved",)
RECOLLECT_ON_COMPONENT_CHANGE = (
    "fact_schema",
    "fact_eligibility",
    "acquisition_truth",
    "drafting_and_example_selection",
    "evidence_polarity",
    "root_role_selection",
    "documentation_catalog",
)
VISITOR_RENDER_FIELDS = (
    "product.audience",
    "product.problems_solved",
    "product.capabilities",
    "product.formats",
)

_COMPONENT_FILES: dict[str, tuple[str, ...]] = {
    "documentation_catalog": (
        "catalog_documentation.py",
        "../../../data/aspose_org_links.json",
    ),
    "acquisition_truth": (
        "acquisition.py",
        "acquisition_pins.py",
        "acquisition_schema.py",
        "example_verification_schema.py",
        "compiled_consumer.py",
        "compiled_consumer_schema.py",
        "java_example_verifier.py",
        "dotnet_example_verifier.py",
        "dotnet_dependency_acquisition.py",
        "dotnet_dependency_schema.py",
        "dotnet_legacy_reference_fallback.py",
        "dotnet_lfs_acquisition.py",
        "dotnet_project_closure.py",
        "dotnet_source_generator_fallback.py",
        "cpp_example_verifier.py",
        "go_example_verifier.py",
        "python_example_verifier.py",
        "python_dependency_acquisition.py",
        "python_dependency_schema.py",
        "python_consumer.py",
        "python_consumer_schema.py",
        "typescript_example_verifier.py",
        "rust_example_verifier.py",
        "../ecosystems/foss_coordinate.py",
        "../ecosystems/registry_request.py",
        "../ecosystems/resolver.py",
    ),
    "classification_semantics": ("acceptance_contract.py",),
    "conflict_semantics": ("acceptance_contract.py", "resolution.py", "schema_v2.py"),
    "drafting_and_example_selection": (
        "aspose_org_dependency_snapshot.py",
        "aspose_org_format_adapter.py",
        "aspose_org_format_contract.py",
        "deterministic_truth_salvage.py",
        "format_direction.py",
        "repository_format_extraction.py",
        "example_quality.py",
        "interpretive_resolution.py",
        "problem_grounding.py",
        "python_repository_examples.py",
        "python_format_functionality.py",
        "python_family_format_functionality.py",
        "python_3d_format_functionality.py",
        "python_barcode_format_functionality.py",
        "python_email_format_functionality.py",
        "python_html_format_functionality.py",
        "dotnet_3d_format_functionality.py",
        "dotnet_email_format_functionality.py",
        "dotnet_repository_evidence_schema.py",
        "aspose_org_dotnet_adapter.py",
        "dotnet_repository_evidence.py",
        "dotnet_truth_selection.py",
        "repository_examples.py",
        "verified_repository_examples.py",
        "../capabilities/draft_product_truth.py",
    ),
    "fact_schema": ("schema_v2.py",),
    "fact_eligibility": ("gating.py",),
    "evidence_polarity": (
        "evidence_polarity.py",
        "policy_evidence.py",
        "interpretive_evidence.py",
    ),
    "root_role_selection": (
        "root_role_schema.py",
        "root_role_evidence.py",
        "root_roles.py",
        "manifest_facts.py",
        "migration.py",
        "provider.py",
        "repository_ingestion.py",
        "curated_readme_evidence.py",
        "curated_repository_guidance.py",
        "curated_constraint_evidence.py",
        "curated_python_api_ast.py",
        "curated_python_api_eligibility.py",
        "curated_python_api_projection.py",
        "curated_python_dependencies.py",
        "curated_python_development.py",
        "curated_python_evidence.py",
        "curated_python_example_validation.py",
        "curated_python_fixture_inventory.py",
        "curated_python_import_shadowing.py",
        "curated_python_implementation.py",
        "python_golden_workflow.py",
        "python_golden_workflow_schema.py",
        "curated_python_mcp.py",
        "curated_python_pdf_evidence.py",
        "curated_python_pdf_guidance.py",
        "curated_python_public_surface.py",
        "curated_python_readme.py",
        "curated_repository_assets.py",
    ),
    "visitor_render_eligibility": ("limitation_rendering.py", "render_views.py"),
}

_ECOSYSTEM_FILE_OWNERS = {
    "java_example_verifier.py": "java",
    "dotnet_example_verifier.py": "net",
    "dotnet_repository_evidence_schema.py": "net",
    "aspose_org_dotnet_adapter.py": "net",
    "dotnet_repository_evidence.py": "net",
    "dotnet_truth_selection.py": "net",
    "dotnet_dependency_acquisition.py": "net",
    "dotnet_dependency_schema.py": "net",
    "dotnet_legacy_reference_fallback.py": "net",
    "dotnet_lfs_acquisition.py": "net",
    "dotnet_project_closure.py": "net",
    "dotnet_source_generator_fallback.py": "net",
    "cpp_example_verifier.py": "cpp",
    "go_example_verifier.py": "go",
    "python_example_verifier.py": "python",
    "python_dependency_acquisition.py": "python",
    "python_dependency_schema.py": "python",
    "python_consumer.py": "python",
    "python_consumer_schema.py": "python",
    "python_repository_examples.py": "python",
    "python_format_functionality.py": "python",
    "python_family_format_functionality.py": "python",
    "typescript_example_verifier.py": "typescript",
    "rust_example_verifier.py": "rust",
    "curated_python_evidence.py": "python",
    "curated_python_api_ast.py": "python",
    "curated_python_api_eligibility.py": "python",
    "curated_python_api_projection.py": "python",
    "curated_python_dependencies.py": "python",
    "curated_python_development.py": "python",
    "curated_python_example_validation.py": "python",
    "curated_python_fixture_inventory.py": "python",
    "curated_python_import_shadowing.py": "python",
    "curated_python_implementation.py": "python",
    "python_golden_workflow.py": "python",
    "python_golden_workflow_schema.py": "python",
    "curated_python_mcp.py": "python",
    "curated_python_pdf_evidence.py": "python",
    "curated_python_pdf_guidance.py": "python",
    "curated_python_public_surface.py": "python",
    "curated_python_readme.py": "python",
}

_FAMILY_FILE_OWNERS = {
    "python_3d_format_functionality.py": ("python", "3d"),
    "python_barcode_format_functionality.py": ("python", "barcode"),
    "python_email_format_functionality.py": ("python", "email"),
    "python_html_format_functionality.py": ("python", "html"),
    "curated_python_pdf_evidence.py": ("python", "pdf"),
    "curated_python_pdf_guidance.py": ("python", "pdf"),
    "dotnet_3d_format_functionality.py": ("net", "3d"),
    "dotnet_email_format_functionality.py": ("net", "email"),
}


def _scoped_component_files(
    name: str,
    ecosystem: str | None,
    family: str | None = None,
) -> tuple[str, ...]:
    files = _COMPONENT_FILES[name]
    if ecosystem is None:
        if family is not None:
            raise ValueError("family-scoped fact contracts require an ecosystem")
        return files
    normalized_ecosystem = ecosystem.strip().casefold()
    normalized_family = family.strip().casefold() if family is not None else None
    family_context_required = any(
        owner_ecosystem == normalized_ecosystem
        for owner_ecosystem, _owner_family in _FAMILY_FILE_OWNERS.values()
    )
    if normalized_family is None and family_context_required:
        raise ValueError(
            f"family is required for the {normalized_ecosystem!r} fact acceptance contract"
        )
    return tuple(
        path
        for path in files
        if (
            ((owner := _ECOSYSTEM_FILE_OWNERS.get(path)) is None or owner == normalized_ecosystem)
            and (
                (family_owner := _FAMILY_FILE_OWNERS.get(path)) is None
                or family_owner == (normalized_ecosystem, normalized_family)
            )
        )
    )


class FactAcceptanceContractV1(BaseModel):
    """Hashable acceptance boundary for persisted facts and dependent lifecycle state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    required_fields: tuple[str, ...]
    accepted_verification_states: tuple[str, ...]
    blocking_conflict_statuses: tuple[str, ...]
    recollect_on_component_change: tuple[str, ...]
    visitor_render_fields: tuple[str, ...]
    component_hashes: dict[str, str]

    def canonical_hash(self) -> str:
        """Return the exact hash stored beside every accepted cached fact graph."""

        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _component_hash(root: Path, relative_paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for relative_path in relative_paths:
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        with (root / relative_path).open("r", encoding="utf-8", newline=None) as source:
            normalized_source = source.read()
        digest.update(normalized_source.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def current_fact_acceptance_contract(
    ecosystem: str | None = None,
    family: str | None = None,
) -> FactAcceptanceContractV1:
    """Build the contract from common, ecosystem, and exact-family implementation files."""

    root = Path(__file__).parent
    return FactAcceptanceContractV1(
        required_fields=README_TRUTH_FIELDS,
        accepted_verification_states=ACCEPTED_VERIFICATION_STATES,
        blocking_conflict_statuses=BLOCKING_CONFLICT_STATUSES,
        recollect_on_component_change=RECOLLECT_ON_COMPONENT_CHANGE,
        visitor_render_fields=VISITOR_RENDER_FIELDS,
        component_hashes={
            name: _component_hash(root, _scoped_component_files(name, ecosystem, family))
            for name in sorted(_COMPONENT_FILES)
        },
    )


def fact_contract_change_requires_recollection(
    stored_components: dict[str, str],
    current_contract: FactAcceptanceContractV1,
) -> bool:
    """Return whether a changed contract can alter the persisted selected fact graph."""

    if not stored_components:
        # Bundles predating component hashes are reclassified once under the current
        # contract. The caller remains responsible for binding the migrated contract.
        return False
    return any(
        stored_components.get(component) != current_contract.component_hashes.get(component)
        for component in current_contract.recollect_on_component_change
    )


def classify_product_truth(
    facts: ProductFactsV2,
    contract: FactAcceptanceContractV1 | None = None,
) -> ProductTruthOutcome:
    """Classify the current graph without trusting a persisted terminal label."""

    active_contract = contract or current_fact_acceptance_contract()
    try:
        selected = [facts.selected_fact(field) for field in active_contract.required_fields]
    except KeyError:
        return "BLOCKED_MISSING_EVIDENCE"
    if any(
        fact.verification_state == "conflicting"
        or any(
            conflict.status in active_contract.blocking_conflict_statuses
            for conflict in fact.conflicts
        )
        for fact in selected
    ):
        return "BLOCKED_FACT_CONFLICT"
    if any(
        fact.verification_state not in active_contract.accepted_verification_states
        for fact in selected
    ):
        return "BLOCKED_MISSING_EVIDENCE"
    eligibility = evaluate_surface_facts(
        facts,
        [
            SurfaceFactRequirementV1(
                surface_id="readme",
                required_fields=list(active_contract.required_fields),
            )
        ],
    )[0]
    if not eligibility.eligible:
        return "BLOCKED_MISSING_EVIDENCE"
    if any(
        (view := visitor_fact_render_view(facts, field)) is None or not view.phrases
        for field in active_contract.visitor_render_fields
    ):
        return "BLOCKED_MISSING_EVIDENCE"
    return "FACTS_READY"
