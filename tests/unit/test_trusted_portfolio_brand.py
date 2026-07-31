"""Versioned cross-repository brand controls for trusted README candidates."""

from __future__ import annotations

import hashlib
import re

import pytest

from readme_agent.errors import LLMError
from readme_agent.facts.trusted_readme_extraction import (
    bind_configured_standards,
    configured_standard_addition,
)
from readme_agent.facts.trusted_readme_schema import (
    InheritedReadmeFactV1,
    ReadmeSourceSpanV1,
    TrustedReadmeFactGraphV1,
)
from readme_agent.readme.presentation_contract import (
    PRESENTATION_CONTRACT_VERSION,
    PRESENTATION_HEADING_PREFIX_ALIASES,
    PRESENTATION_MERMAID_GRAMMAR,
    PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS,
    PRESENTATION_MERMAID_MAX_NODES,
)
from readme_agent.readme.trusted_portfolio_brand import (
    find_trusted_capability_list_representation,
    normalize_trusted_enterprise_product_links,
    normalize_trusted_portfolio_emojis,
    normalize_trusted_portfolio_header_assets,
    normalize_trusted_portfolio_headings,
    normalize_trusted_portfolio_mermaid,
    restore_trusted_at_a_glance,
    validate_trusted_portfolio_brand,
    validate_trusted_portfolio_cohort,
)

_CORE_ROW = (
    "![Platform: Python](https://img.shields.io/badge/Platform-Python-3776AB.svg) "
    "![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)"
)


def _graph(org_repo: str, enterprise_url: str) -> TrustedReadmeFactGraphV1:
    source = "# Source\n"
    encoded = source.encode()
    digest = hashlib.sha256(encoded).hexdigest()
    graph = TrustedReadmeFactGraphV1(
        org_repo=org_repo,
        source_revision="a" * 40,
        readme_path="README.md",
        readme_sha256=digest,
        source_byte_count=len(encoded),
        covered_material_byte_count=len(encoded),
        inherited_facts=(
            InheritedReadmeFactV1(
                fact_id="readme.inherited:" + "a" * 24,
                value=source,
                material_kind="heading",
                source_span=ReadmeSourceSpanV1(
                    source_path="README.md",
                    source_revision="a" * 40,
                    source_sha256=digest,
                    byte_start=0,
                    byte_end=len(encoded),
                    start_line=1,
                    end_line_exclusive=2,
                    content_sha256=digest,
                ),
            ),
        ),
    )
    config = b"brand-v1"
    return bind_configured_standards(
        graph,
        [
            configured_standard_addition(
                "readme.header",
                configuration_source="config/policies/test.yml",
                configuration_bytes=config,
                parameters={
                    "brand_contract_version": PRESENTATION_CONTRACT_VERSION,
                    "emoji_policy": "none",
                    "heading_style": "sentence_case_without_emoji",
                    "heading_prefix_aliases": PRESENTATION_HEADING_PREFIX_ALIASES,
                    "required_h2_prefix": [
                        "At a glance",
                        "Navigation",
                        "Key capabilities",
                        "Installation",
                        "Quick start",
                    ],
                },
            ),
            configured_standard_addition(
                "readme.badges",
                configuration_source="config/policies/test.yml",
                configuration_bytes=config,
                parameters={"required_core_row": _CORE_ROW},
            ),
            configured_standard_addition(
                "readme.at_a_glance_mermaid",
                configuration_source="config/policies/test.yml",
                configuration_bytes=config,
                parameters={
                    "visual_grammar": PRESENTATION_MERMAID_GRAMMAR,
                    "max_nodes": PRESENTATION_MERMAID_MAX_NODES,
                    "max_label_characters": PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS,
                },
            ),
            configured_standard_addition(
                "readme.contextual_links",
                configuration_source="data/aspose_com_links.json",
                configuration_bytes=config,
                parameters={
                    "required_aspose_com_occurrences": 1,
                    "required_enterprise_url": enterprise_url,
                    "enterprise_product_name": "Aspose.Note Enterprise Edition",
                },
            ),
        ],
    )


def _candidate(product: str, url: str, *, input_label: str = "Source documents") -> str:
    return (
        f"# {product}\n\n"
        f"{_CORE_ROW}\n\n"
        f"{product} provides a focused Python API for document workflows.\n\n"
        "## At a glance\n\n"
        "```mermaid\n"
        "flowchart LR\n"
        "  subgraph Inputs\n"
        f'    I1["{input_label}"]\n'
        "  end\n"
        f'  PRODUCT["{product} API"]\n'
        "  subgraph Capabilities\n"
        '    C1["Parse document structure"]\n'
        '    C2["Extract product content"]\n'
        '    C3["Convert supported documents"]\n'
        "  end\n"
        "  subgraph Outputs\n"
        '    O1["Structured content"]\n'
        '    O2["Converted document output"]\n'
        "  end\n"
        "  I1 --> PRODUCT\n"
        "  PRODUCT --> C1\n"
        "  PRODUCT --> C2\n"
        "  PRODUCT --> C3\n"
        "  C1 --> O1\n"
        "  C2 --> O2\n"
        "```\n\n"
        "## Navigation\n\n"
        "- [Key capabilities](#key-capabilities)\n"
        "- [Installation](#installation)\n"
        "- [Quick start](#quick-start)\n\n"
        "## Key capabilities\n\n"
        "- Read inherited formats\n"
        "- Produce inherited outputs\n\n"
        "## Installation\n\n"
        "Install the package described by this repository.\n\n"
        "## Quick start\n\n"
        "Run the repository's inherited example.\n\n"
        "## Project scope and limitations\n\n"
        "This open-source implementation covers the scope documented here. For broader "
        f"commercial capabilities, evaluate the [Aspose.Note Enterprise Edition]({url}) when those "
        "additional requirements apply.\n\n"
        "## Development and contributing\n\n"
        "Use the repository development workflow.\n\n"
        "## License\n\nMIT.\n"
    )


def test_portfolio_brand_accepts_the_shared_professional_grammar() -> None:
    url = "https://products.aspose.com/note/"
    validate_trusted_portfolio_brand(
        _candidate("Aspose.Note FOSS for Python", url),
        _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", url),
    )


def test_header_asset_normalization_enforces_one_blank_line_before_core_badges() -> None:
    url = "https://products.aspose.com/note/"
    graph = _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", url)
    candidate = _candidate("Aspose.Note FOSS for Python", url).replace(
        "# Aspose.Note FOSS for Python\n\n",
        "# Aspose.Note FOSS for Python\n\n\n\n",
        1,
    )

    normalized = normalize_trusted_portfolio_header_assets(candidate, graph)

    assert normalized.startswith(f"# Aspose.Note FOSS for Python\n\n{_CORE_ROW}\n\n")


def test_header_asset_normalization_removes_control_leakage_and_duplicate_badges() -> None:
    url = "https://products.aspose.com/note/"
    graph = _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", url)
    pypi = "![PyPI](https://img.shields.io/pypi/v/aspose-note.svg)"
    candidate = _candidate("Aspose.Note FOSS for Python", url).replace(
        f"{_CORE_ROW}\n\n",
        f"{_CORE_ROW}\n\n{pypi}\n\nQuick links: [Examples](examples/)\n\n"
        "required_core_row\n"
        f"{pypi}\n\nQuick links: \U0001f4da [Examples](examples/)\n\n",
        1,
    )

    normalized = normalize_trusted_portfolio_header_assets(candidate, graph)

    assert "required_core_row" not in normalized
    assert normalized.count(pypi) == 1
    assert normalized.count("Quick links:") == 1
    assert "\n\n\n" not in normalized.split("## At a glance", maxsplit=1)[0]
    validate_trusted_portfolio_brand(normalized, graph)


def test_heading_style_normalization_removes_only_decorative_heading_emoji() -> None:
    url = "https://products.aspose.com/note/"
    graph = _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", url)
    candidate = (
        _candidate("Aspose.Note FOSS for Python", url)
        .replace(
            "# Aspose.Note",
            "# 🗒️ Aspose.Note",
        )
        .replace("## Quick start", "## 🚀 Quick start")
    )

    normalized = normalize_trusted_portfolio_headings(candidate, graph)

    assert normalized.startswith("# Aspose.Note")
    assert "## Quick start" in normalized
    assert "🗒️" not in normalized
    assert "🚀" not in normalized


def test_heading_style_normalization_applies_sentence_case_without_damaging_terms() -> None:
    url = "https://products.aspose.com/note/"
    graph = _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", url)
    candidate = (
        _candidate("Aspose.Note FOSS for Python", url)
        .replace("## Development and contributing", "## Example Results")
        .replace("## License", "## Build and Test (Developers)")
    )

    normalized = normalize_trusted_portfolio_headings(candidate, graph)

    assert "## Example results" in normalized
    assert "## Build and test (developers)" in normalized
    assert "# Aspose.Note FOSS for Python" in normalized


def test_heading_style_maps_product_why_heading_to_key_capabilities() -> None:
    url = "https://products.aspose.com/note/"
    graph = _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", url)

    normalized = normalize_trusted_portfolio_headings(
        "## Why Aspose.Note for Python\n",
        graph,
    )

    assert normalized == "## Key capabilities\n"


def test_capability_list_representation_accepts_equivalent_wording_without_duplicates() -> None:
    source = (
        "- Convert PS/EPS to PDF in Python\n"
        "- Integrate conversion workflows through MCP server tools\n"
    )
    candidate = (
        "## Key capabilities\n\n"
        "- PS/EPS to PDF conversion\n"
        "- MCP server integration for conversion workflows\n"
    )

    represented = find_trusted_capability_list_representation(source, candidate)

    assert represented == (
        "- PS/EPS to PDF conversion\n- MCP server integration for conversion workflows"
    )


def test_candidate_wide_emoji_normalization_removes_all_visible_emoji() -> None:
    url = "https://products.aspose.com/note/"
    graph = _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", url)
    candidate = (
        _candidate("Aspose.Note FOSS for Python", url)
        .replace("provides a focused", "provides a focused ✅")
        .replace("[Key capabilities]", "[📚 Key capabilities]")
        .replace("- Read inherited formats", "- ✨ Read inherited formats")
        .replace('C1["Parse document structure"]', 'C1["🔎 Parse document structure"]')
    )

    normalized = normalize_trusted_portfolio_emojis(candidate, graph)

    assert all(symbol not in normalized for symbol in ("✅", "📚", "✨", "🔎"))
    validate_trusted_portfolio_brand(normalized, graph)


def test_mermaid_normalization_preserves_selected_labels_and_repairs_model_ids() -> None:
    url = "https://products.aspose.com/note/"
    graph = _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", url)
    candidate = (
        _candidate("Aspose.Note FOSS for Python", url)
        .replace(
            'I1["Source documents"]',
            "I1[Source documents]",
        )
        .replace(
            'PRODUCT["Aspose.Note FOSS for Python API"]',
            "Aspose.Note-FOSS[Aspose.Note FOSS for Python API]",
        )
        .replace("I1 --> PRODUCT", "I1 --> Aspose-FiSS")
        .replace("PRODUCT --> C1", "Aspose-FiSS --> C1")
    )

    normalized = normalize_trusted_portfolio_mermaid(candidate, graph)

    assert 'I1["Source documents"]' in normalized
    assert 'PRODUCT["Aspose.Note FOSS for Python API"]' in normalized
    assert "I1 --> PRODUCT" in normalized
    assert "PRODUCT --> C1" in normalized
    assert "C1 --> O1" in normalized
    validate_trusted_portfolio_brand(normalized, graph)


def test_mermaid_normalization_accepts_inline_node_declarations_from_model() -> None:
    url = "https://products.aspose.com/note/"
    graph = _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", url)
    inline = """flowchart LR
  I1[OneNote .one file] --> PRODUCT
  I2[Binary stream] --> PRODUCT
  PRODUCT[Aspose.Note Python API] --> C1[Parse OneStore]
  PRODUCT --> C2[Traverse document nodes]
  PRODUCT --> C3[Extract embedded content]
  C1 --> O1[Document object model]
  C2 --> O2[Pages and outlines]
  C2 --> O3[Text images and attachments]"""
    candidate = re.sub(
        r"(?ms)(```mermaid\r?\n).*?(\r?\n```)",
        rf"\1{inline}\2",
        _candidate("Aspose.Note FOSS for Python", url),
        count=1,
    )

    normalized = normalize_trusted_portfolio_mermaid(candidate, graph)

    assert "subgraph Inputs" in normalized
    assert "subgraph Capabilities" in normalized
    assert "subgraph Outputs" in normalized
    assert 'I1["OneNote .one file"]' in normalized
    assert 'C3["Extract embedded content"]' in normalized
    assert "C2 --> O3" in normalized
    assert "C3 --> O3" not in normalized
    validate_trusted_portfolio_brand(normalized, graph)


def test_mermaid_normalization_recovers_unlabelled_canonical_product_node() -> None:
    url = "https://products.aspose.com/note/"
    graph = _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", url)
    inline = """flowchart LR
  I1[OneNote file] --> PRODUCT
  PRODUCT --> C1[Parse document structure]
  PRODUCT --> C2[Traverse document nodes]
  C1 --> O1[Document object model]
  C2 --> O2[Pages and outlines]
  classDef product fill:#3776AB
  class PRODUCT product"""
    candidate = re.sub(
        r"(?ms)(```mermaid\r?\n).*?(\r?\n```)",
        rf"\1{inline}\2",
        _candidate("Aspose.Note FOSS for Python", url),
        count=1,
    )

    normalized = normalize_trusted_portfolio_mermaid(candidate, graph)

    assert 'PRODUCT["Aspose.Note FOSS for Python"]' in normalized
    assert "classDef" not in normalized
    validate_trusted_portfolio_brand(normalized, graph)


def test_repair_restores_the_validated_at_a_glance_shell() -> None:
    url = "https://products.aspose.com/note/"
    graph = _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", url)
    accepted = _candidate("Aspose.Note FOSS for Python", url)
    key_capabilities = accepted.index("## Key capabilities")
    repaired_without_visual = accepted[key_capabilities:]

    restored = restore_trusted_at_a_glance(repaired_without_visual, accepted, graph)

    assert restored.startswith("# Aspose.Note FOSS for Python\n\n" + _CORE_ROW)
    assert restored.count("## At a glance") == 1
    assert restored.count("```mermaid") == 1
    assert (
        restored.index("## At a glance")
        < restored.index("## Navigation")
        < restored.index("## Key capabilities")
    )
    validate_trusted_portfolio_brand(restored, graph)


def test_enterprise_link_normalization_keeps_only_the_configured_product_target() -> None:
    url = "https://products.aspose.com/note/"
    graph = _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", url)
    candidate = (
        _candidate("Aspose.Note FOSS for Python", url)
        .replace(
            "Use Aspose.Note FOSS",
            f"See [Aspose.Note Enterprise Edition]({url}). Use Aspose.Note FOSS",
        )
        .replace(
            "## Project scope and limitations",
            "See [another product](https://products.aspose.com/note/net/).\n\n"
            "## Project scope and limitations",
        )
    )

    normalized = normalize_trusted_enterprise_product_links(candidate, graph)

    assert normalized.count("https://products.aspose.com/") == 1
    assert f"[Aspose.Note Enterprise Edition]({url})" in normalized
    assert "another product" in normalized
    assert normalized.index(url) > normalized.index("## Project scope and limitations")
    validate_trusted_portfolio_brand(normalized, graph)


def test_portfolio_brand_rejects_a_non_descriptive_enterprise_link_label() -> None:
    url = "https://products.aspose.com/note/"
    graph = _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", url)

    with pytest.raises(LLMError, match="descriptive product label"):
        validate_trusted_portfolio_brand(
            _candidate("Aspose.Note FOSS for Python", url).replace(
                "[Aspose.Note Enterprise Edition]",
                "[Enterprise Edition]",
            ),
            graph,
        )


def test_enterprise_link_normalization_materializes_missing_scope_context() -> None:
    url = "https://products.aspose.com/note/"
    graph = _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", url)
    candidate = _candidate("Aspose.Note FOSS for Python", url).replace(
        f"[Aspose.Note Enterprise Edition]({url})",
        "Enterprise Edition",
    )

    normalized = normalize_trusted_enterprise_product_links(candidate, graph)

    assert normalized.count(url) == 1
    assert normalized.index(url) > normalized.index("## Project scope and limitations")
    assert "outside this repository's documented scope" in normalized
    validate_trusted_portfolio_brand(normalized, graph)


def test_enterprise_link_normalization_moves_an_out_of_scope_link() -> None:
    url = "https://products.aspose.com/note/"
    graph = _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", url)
    candidate = _candidate("Aspose.Note FOSS for Python", url).replace(
        "## Project scope and limitations",
        "## Commercial relationship",
    )

    normalized = normalize_trusted_enterprise_product_links(candidate, graph)

    assert normalized.count(url) == 1
    assert "## Project scope and limitations" in normalized
    assert normalized.index(url) > normalized.index("## Project scope and limitations")
    validate_trusted_portfolio_brand(normalized, graph)


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (
            lambda text: text.replace("# Aspose.Note", "# 🗒️ Aspose.Note"),
            "emojis anywhere",
        ),
        (lambda text: text.replace(_CORE_ROW, "", 1), "core badge row"),
        (
            lambda text: text.replace("## At a glance", "## Overview", 1),
            "common At a glance",
        ),
        (
            lambda text: text.replace("  subgraph Inputs\n", ""),
            "Inputs, Capabilities, and Outputs zones",
        ),
        (
            lambda text: text.replace("  I1 --> PRODUCT\n", "  I1 --> O1\n"),
            "Inputs to Product to Capabilities to Outputs",
        ),
        (
            lambda text: text.replace(
                "when those additional requirements apply.",
                "when those additional requirements apply. "
                "See https://products.aspose.com/note/ too.",
            ),
            "exactly one products.aspose.com",
        ),
        (
            lambda text: text.replace("Enterprise Edition", "commercial product"),
            "descriptive product label",
        ),
    ],
)
def test_portfolio_brand_rejects_recurring_review_defects(mutation, error) -> None:
    url = "https://products.aspose.com/note/"
    with pytest.raises(LLMError, match=error):
        validate_trusted_portfolio_brand(
            mutation(_candidate("Aspose.Note FOSS for Python", url)),
            _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", url),
        )


def test_cohort_rejects_a_reused_generic_diagram() -> None:
    note_url = "https://products.aspose.com/note/"
    page_url = "https://products.aspose.com/page/"
    shared = _candidate("Aspose.Note FOSS for Python", note_url)
    page = _candidate("Aspose.Page FOSS for Python", page_url).replace(
        'PRODUCT["Aspose.Page FOSS for Python API"]',
        'PRODUCT["Aspose.Note FOSS for Python API"]',
    )
    with pytest.raises(LLMError, match="reused a generic At a glance diagram"):
        validate_trusted_portfolio_cohort(
            {
                "note": (
                    shared,
                    _graph("aspose-note-foss/Aspose.Note-FOSS-for-Python", note_url),
                ),
                "page": (
                    page,
                    _graph("aspose-page-foss/Aspose.Page-FOSS-for-Python", page_url),
                ),
            }
        )
