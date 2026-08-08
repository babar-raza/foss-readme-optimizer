"""Template loading, hashing, and fact-to-section prose synthesis.

Owns the fill-and-match README templates (loading + a stable hash of every
template input) and deterministic verified installation/example prose.
Extracted verbatim from the former single-file ``document_renderer``
(`GOVERNANCE.md` "no monoliths").
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from readme_agent.facts.acquisition_schema import AcquisitionDecisionV1
from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.acquisition_contracts import matching_coordinate_row

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_ROOT = _PROJECT_ROOT / "templates" / "readme"
DOCUMENT_TEMPLATE_NAMES = (
    "repository-presentation-v1.json",
    "additional-examples-details.md",
    "contextual-enterprise-relationship.md",
    "contextual-example-link.md",
    "contextual-foss-product.md",
    "contextual-product-relationship.md",
    "agentic-overview-and-navigation.md",
    "product-overview-and-navigation.md",
    "verified-limitations.md",
    "verified-repository-constraints.md",
    "verified-minimal-example.md",
    "verified-maven-acquisition.md",
    "verified-python-pypi-acquisition.md",
    "verified-dotnet-nuget-acquisition.md",
    "verified-cpp-nuget-acquisition.md",
    "verified-go-acquisition.md",
    "verified-source-acquisition.md",
)
DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS = (
    "src/readme_agent/readme/document_renderer.py",
    "src/readme_agent/readme/document_acquisition.py",
    "src/readme_agent/readme/acquisition_contracts.py",
    "src/readme_agent/readme/document_opening.py",
    "src/readme_agent/readme/document_legal.py",
    "src/readme_agent/readme/document_links.py",
    "src/readme_agent/readme/document_structure.py",
    "src/readme_agent/readme/document_validation.py",
    "src/readme_agent/readme/example_assurance_validation.py",
    "src/readme_agent/readme/presentation_lint.py",
    "src/readme_agent/readme/presentation_lint_semantics.py",
    "src/readme_agent/readme/presentation_lint_structure.py",
    "src/readme_agent/readme/presentation_lint_text.py",
    "src/readme_agent/presentation/runtime_repairs.py",
    "src/readme_agent/presentation/template_adapters.py",
    "src/readme_agent/presentation/template_compiler.py",
    "src/readme_agent/presentation/template_schema.py",
    "src/readme_agent/presentation/verified_preservation_sections.py",
    "src/readme_agent/presentation/verified_preservation_segments.py",
    "src/readme_agent/presentation/verified_source_preservation.py",
    "src/readme_agent/presentation/verified_source_assurance_projection.py",
    "src/readme_agent/presentation/verified_source_placements.py",
    "src/readme_agent/presentation/verified_template_draft.py",
    "src/readme_agent/presentation/verified_template_provenance.py",
    "src/readme_agent/presentation/verified_template_runtime.py",
    "src/readme_agent/presentation/verified_template_sections.py",
    "src/readme_agent/readme/document_templates.py",
    "src/readme_agent/readme/header_visual.py",
    "src/readme_agent/readme/header_badges.py",
    "src/readme_agent/readme/fact_grounding.py",
    "src/readme_agent/readme/claim_accountability.py",
    "src/readme_agent/readme/claim_accountability_candidate_policy.py",
    "src/readme_agent/readme/claim_accountability_helpers.py",
    "src/readme_agent/readme/claim_accountability_models.py",
    "src/readme_agent/readme/claim_replacement_validation.py",
    "src/readme_agent/readme/claim_accountability_validation.py",
    "src/readme_agent/readme/claim_map.py",
    "src/readme_agent/readme/assessment.py",
    "src/readme_agent/readme/assessment_claims.py",
    "src/readme_agent/readme/source_claim_risk.py",
    "src/readme_agent/readme/limitation_validation.py",
    "src/readme_agent/readme/document_plan.py",
    "src/readme_agent/readme/document_plan_finalizer.py",
    "src/readme_agent/readme/composition_lineage.py",
    "src/readme_agent/readme/composition_lineage_models.py",
    "src/readme_agent/readme/composition_operation_origins.py",
    "src/readme_agent/readme/composition_lineage_validation.py",
    "src/readme_agent/validation/presentation_template.py",
    "src/readme_agent/registry/loader.py",
    "src/readme_agent/registry/models.py",
)
DOCUMENT_CONTRACT_IMPLEMENTATION_GLOBS = (
    "src/readme_agent/links/*.py",
    "src/readme_agent/presentation/verified_*.py",
    "src/readme_agent/readme/claim_*.py",
    "src/readme_agent/readme/source_claim_*.py",
)
DOCUMENT_CONTRACT_CATALOG_PATHS = (
    "data/aspose_com_links.json",
    "data/aspose_org_links.json",
)
_ACCEPTED_FACT_STATES = {"verified", "policy_approved"}


def load_template(name: str) -> str:
    return (TEMPLATE_ROOT / name).read_text(encoding="utf-8")


def document_template_hash() -> str:
    """Hash every fill-and-match input used by the document renderer."""

    digest = hashlib.sha256()
    for name in DOCUMENT_TEMPLATE_NAMES:
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update((TEMPLATE_ROOT / name).read_bytes())
        digest.update(b"\0")
    contract_paths = set(DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS)
    contract_paths.update(DOCUMENT_CONTRACT_CATALOG_PATHS)
    for pattern in DOCUMENT_CONTRACT_IMPLEMENTATION_GLOBS:
        matches = [path for path in _PROJECT_ROOT.glob(pattern) if path.is_file()]
        if not matches:
            raise FileNotFoundError(f"document contract input pattern has no matches: {pattern}")
        contract_paths.update(path.relative_to(_PROJECT_ROOT).as_posix() for path in matches)
    for relative in sorted(contract_paths):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update((_PROJECT_ROOT / relative).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def fact(facts: ProductFactsV2, field: str):
    return facts.selected_fact(field)


def accepted_fact(facts: ProductFactsV2, field: str):
    """Return only a selected, conflict-free fact eligible for authored prose."""

    selected = fact(facts, field)
    if selected.verification_state not in _ACCEPTED_FACT_STATES or selected.has_unresolved_conflict:
        return None
    return selected


def sentence_list(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item).rstrip(".") + "." for item in value)
    return str(value)


def text_value(value: object) -> str:
    if isinstance(value, list):
        return sentence_list(value)
    return str(value)


def visitor_text(facts: ProductFactsV2, field: str) -> str | None:
    """Render the same visitor-facing phrases used by grounding and validation."""

    view = visitor_fact_render_view(facts, field)
    return sentence_list(view.phrases) if view is not None and view.phrases else None


def mapping_value(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        return value[0]
    return {}


def first_mapping(value: object) -> dict:
    if isinstance(value, list):
        return next((item for item in value if isinstance(item, dict)), {})
    return mapping_value(value)


def installation_text(
    facts: ProductFactsV2,
    org_repo: str,
    source_revision: str,
) -> str | None:
    """Render only a mechanically verified, ecosystem-correct acquisition path."""

    acquisition = accepted_fact(facts, "installation.verified_acquisition")
    coordinates = accepted_fact(facts, "installation.coordinates")
    identity = accepted_fact(facts, "product.identity")
    if acquisition is None or coordinates is None or identity is None:
        return None

    acquisition_value = mapping_value(acquisition.value)
    coordinate = mapping_value(acquisition_value.get("coordinate"))
    identity_value = mapping_value(identity.value)
    ecosystem = str(identity_value.get("ecosystem") or identity_value.get("platform") or "")
    method = str(acquisition_value.get("method") or "")

    matching_row = matching_coordinate_row(coordinates.value, coordinate)
    version = str(matching_row.get("version") or "").strip()

    if method == "maven_central":
        group_id = str(coordinate.get("group_id") or "").strip()
        artifact_id = str(coordinate.get("artifact_id") or "").strip()
        if not group_id or not artifact_id or not version:
            return None
        return (
            load_template("verified-maven-acquisition.md")
            .format(
                group_id=group_id,
                artifact_id=artifact_id,
                version=version,
                source_revision=source_revision,
            )
            .strip()
        )
    if method == "pypi" and ecosystem == "python":
        package_name = str(coordinate.get("name") or "").strip()
        if not package_name:
            return None
        compatibility = visitor_text(facts, "product.compatibility") or ""
        return (
            load_template("verified-python-pypi-acquisition.md")
            .format(package_name=package_name, compatibility=compatibility)
            .strip()
        )
    if method == "source_build" and ecosystem == "python":
        try:
            decision = AcquisitionDecisionV1.model_validate(acquisition_value)
        except ValueError:
            return None
        receipt = decision.source_build_receipt
        registry_receipt = decision.registry_receipt
        repository_identity = str(identity_value.get("repository") or "").strip()
        manifest_names = identity_value.get("manifest_names")
        manifest_names = manifest_names if isinstance(manifest_names, list) else []
        package_name = next(
            (
                str(name).strip()
                for name in manifest_names
                if str(name).strip()
                and matching_coordinate_row(coordinates.value, {"name": str(name).strip()})
            ),
            "",
        )
        source_pin = f"source_revision={source_revision}"
        if (
            decision.outcome != "SOURCE_BUILD_VERIFIED"
            or decision.org_repo != org_repo
            or decision.source_revision != source_revision
            or decision.ecosystem != "python"
            or receipt is None
            or registry_receipt is None
            or registry_receipt.found
            or registry_receipt.resolver_ecosystem != "python"
            or registry_receipt.coordinate != coordinate
            or repository_identity != org_repo
            or not package_name
            or source_pin not in receipt.dependency_pins
            or not any(
                pin.startswith("python_package_source_sha256=") for pin in receipt.dependency_pins
            )
        ):
            return None
        repository_name = org_repo.split("/", 1)[1]
        return (
            "Install the package directly from its source repository:\n\n"
            "```bash\n"
            f"git clone https://github.com/{org_repo}.git\n"
            f"cd {repository_name}\n"
            f"git checkout --detach {source_revision}\n"
            "python -m pip install .\n"
            "```\n\n"
            f"Use source installation for the `{package_name}` distribution."
        )
    if method == "nuget" and ecosystem in {"net", "dotnet", "cpp"}:
        package_name = str(coordinate.get("name") or "").strip()
        if not package_name:
            return None
        template = (
            "verified-cpp-nuget-acquisition.md"
            if ecosystem == "cpp"
            else "verified-dotnet-nuget-acquisition.md"
        )
        version_argument = (
            f" -Version {version}"
            if ecosystem == "cpp" and version
            else f" --version {version}"
            if version
            else ""
        )
        return (
            load_template(template)
            .format(
                package_name=package_name,
                version_argument=version_argument,
                source_revision=source_revision,
            )
            .strip()
        )
    if method == "go_proxy" and ecosystem == "go":
        module_name = str(coordinate.get("name") or "").strip()
        if not module_name:
            return None
        return (
            load_template("verified-go-acquisition.md")
            .format(module_name=module_name, source_revision=source_revision)
            .strip()
        )
    if method == "source_build" and ecosystem == "java":
        compatibility = accepted_fact(facts, "product.compatibility")
        compatibility_value = mapping_value(compatibility.value) if compatibility else {}
        minimum_runtime = str(compatibility_value.get("minimum_runtime") or "").strip()
        if not minimum_runtime:
            return None
        return (
            load_template("verified-source-acquisition.md")
            .format(
                org_repo=org_repo,
                repository_name=org_repo.split("/", 1)[1],
                source_revision=source_revision,
                minimum_runtime=minimum_runtime,
            )
            .strip()
        )
    return None


def example_text(facts: ProductFactsV2, source_revision: str) -> str:
    example = accepted_fact(facts, "example.minimal")
    if example is None:
        return ""
    value = example.value if isinstance(example.value, dict) else {}
    prerequisites = ""
    return (
        load_template("verified-minimal-example.md")
        .format(
            language=value.get("language", "text"),
            code=str(value.get("code", "")).rstrip(),
            source_revision=source_revision,
            prerequisites=prerequisites,
        )
        .strip()
    )


def limitations_text(facts: ProductFactsV2) -> str:
    """Render every selected verified limitation without editorial invention."""

    limitations = accepted_fact(facts, "product.limitations")
    if limitations is None or not limitations.value:
        return ""
    values = limitations.value if isinstance(limitations.value, list) else [limitations.value]
    items = "\n".join(f"- {str(value).strip()}" for value in values if str(value).strip())
    if not items:
        return ""
    return load_template("verified-limitations.md").format(items=items).strip()


def missing_limitation_constraints_text(facts: ProductFactsV2, existing_text: str) -> str:
    """Render a separate exact-fact section when existing limitations are incomplete."""

    limitations = accepted_fact(facts, "product.limitations")
    if limitations is None or not limitations.value:
        return ""
    values = limitations.value if isinstance(limitations.value, list) else [limitations.value]
    missing = [
        str(value).strip()
        for value in values
        if str(value).strip() and str(value).strip() not in existing_text
    ]
    items = "\n".join(f"- {value}" for value in missing)
    if not items:
        return ""
    return load_template("verified-repository-constraints.md").format(items=items).strip()
