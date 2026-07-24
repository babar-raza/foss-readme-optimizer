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
    "verified-source-acquisition.md",
)


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
) -> str:
    compatibility = fact(facts, "product.compatibility")
    value = mapping_value(compatibility.value)
    return (
        load_template("verified-source-acquisition.md")
        .format(
            org_repo=org_repo,
            repository_name=org_repo.split("/", 1)[1],
            source_revision=source_revision,
            minimum_runtime=value.get("minimum_runtime", "unknown"),
        )
        .strip()
    )


def example_text(facts: ProductFactsV2, source_revision: str) -> str:
    example = fact(facts, "example.minimal")
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
    compatibility = fact(facts, "product.compatibility")
    compatibility_value = mapping_value(compatibility.value)
    navigation = "\n".join(
        f"- [{heading.title}](#{github_anchor(heading.title)})"
        for heading in headings
        if heading.level == 2
        and heading.title.strip().lower() not in {"at a glance", "in this readme"}
    )
    return (
        load_template("product-overview-and-navigation.md")
        .format(
            audience=text_value(fact(facts, "product.audience").value),
            problem=text_value(fact(facts, "product.problems_solved").value),
            capabilities=sentence_list(fact(facts, "product.capabilities").value),
            formats=sentence_list(fact(facts, "product.formats").value),
            minimum_runtime=compatibility_value.get("minimum_runtime", "unknown"),
            limitations=text_value(fact(facts, "product.limitations").value),
            navigation=navigation or "- Continue with the repository guidance below.",
        )
        .strip()
    )
