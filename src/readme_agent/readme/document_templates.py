"""Template loading, hashing, and fact-to-section prose synthesis.

Owns the fill-and-match README templates (loading + a stable hash of every
template input) and the deterministic rendering of the overview/navigation,
verified installation, and verified example sections from ``ProductFactsV2``.
Extracted verbatim from the former single-file ``document_renderer``
(`GOVERNANCE.md` "no monoliths").
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_structure import Heading, github_anchor

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_ROOT = _PROJECT_ROOT / "templates" / "readme"
DOCUMENT_TEMPLATE_NAMES = (
    "product-overview-and-navigation.md",
    "verified-minimal-example.md",
    "verified-maven-acquisition.md",
    "verified-dotnet-nuget-acquisition.md",
    "verified-cpp-nuget-acquisition.md",
    "verified-go-acquisition.md",
    "verified-source-acquisition.md",
)
_ACCEPTED_FACT_STATES = {"verified", "policy_approved"}
_OMIT_LINE = "__README_AGENT_OMIT_LINE__"


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
    coordinate_rows = coordinates.value if isinstance(coordinates.value, list) else []
    identity_value = mapping_value(identity.value)
    ecosystem = str(identity_value.get("ecosystem") or identity_value.get("platform") or "")
    method = str(acquisition_value.get("method") or "")

    matching_row = next(
        (
            row
            for row in coordinate_rows
            if isinstance(row, dict)
            and (
                row.get("name") == coordinate.get("name")
                or (
                    row.get("group_id") == coordinate.get("group_id")
                    and row.get("artifact_id") == coordinate.get("artifact_id")
                )
            )
        ),
        next((row for row in coordinate_rows if isinstance(row, dict)), {}),
    )
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
    if method == "nuget" and ecosystem in {"net", "dotnet", "cpp"}:
        package_name = str(coordinate.get("name") or "").strip()
        if not package_name:
            return None
        template = (
            "verified-cpp-nuget-acquisition.md"
            if ecosystem == "cpp"
            else "verified-dotnet-nuget-acquisition.md"
        )
        version_argument = f" --version {version}" if version else ""
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
    return (
        load_template("verified-minimal-example.md")
        .format(
            language=value.get("language", "text"),
            code=str(value.get("code", "")).rstrip(),
            source_revision=source_revision,
        )
        .strip()
    )


def overview_text(facts: ProductFactsV2, headings: list[Heading]) -> str:
    audience = accepted_fact(facts, "product.audience")
    problem = accepted_fact(facts, "product.problems_solved")
    capabilities = accepted_fact(facts, "product.capabilities")
    formats = accepted_fact(facts, "product.formats")
    compatibility = accepted_fact(facts, "product.compatibility")
    limitations = accepted_fact(facts, "product.limitations")
    compatibility_value = mapping_value(compatibility.value) if compatibility else {}
    navigation = "\n".join(
        f"- [{heading.title}](#{github_anchor(heading.title)})"
        for heading in headings
        if heading.level == 2
        and heading.title.strip().lower() not in {"at a glance", "in this readme"}
    )
    rendered = (
        load_template("product-overview-and-navigation.md")
        .format(
            audience=text_value(audience.value) if audience is not None else _OMIT_LINE,
            problem=text_value(problem.value) if problem is not None else _OMIT_LINE,
            capabilities=(
                sentence_list(capabilities.value) if capabilities is not None else _OMIT_LINE
            ),
            formats=sentence_list(formats.value) if formats is not None else _OMIT_LINE,
            minimum_runtime=(
                compatibility_value["minimum_runtime"]
                if compatibility_value.get("minimum_runtime")
                else _OMIT_LINE
            ),
            limitations=(
                text_value(limitations.value)
                if limitations is not None and limitations.value
                else _OMIT_LINE
            ),
            navigation=navigation or "- Continue with the repository guidance below.",
        )
        .strip()
    )
    return "\n".join(line for line in rendered.splitlines() if _OMIT_LINE not in line).strip()
