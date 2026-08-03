"""Literal README fact-grounding controls."""

from unittest.mock import patch

from readme_agent.facts.resolution import resolve_product_facts
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2
from readme_agent.readme.fact_grounding import find_literal_fact_match, literal_fact_ids


def test_short_license_token_matches_only_as_a_complete_token():
    match = find_literal_fact_match(
        "[![License: MIT](https://img.shields.io/badge/License-MIT-blue)](LICENSE)",
        "MIT",
    )

    assert match is not None
    assert match.phrase == "MIT"


def test_short_fact_does_not_match_inside_an_unrelated_word():
    assert find_literal_fact_match("Commit changes after review.", "MIT") is None


def test_absent_large_fact_does_not_compile_a_regular_expression() -> None:
    large_fact = "repository evidence " * 10_000

    with patch(
        "readme_agent.readme.fact_grounding.re.search",
        side_effect=AssertionError("long literal facts must use bounded string search"),
    ):
        assert find_literal_fact_match("A concise README candidate.", large_fact) is None


def _structured_fact(field: str, value: object) -> FactRecordV2:
    return FactRecordV2(
        fact_id=f"{field}:test",
        field=field,
        value=value,
        source=FactSourceV2(
            source_type="mechanical_repository",
            location="repository://fixture",
            source_revision="abc123",
        ),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme.test"],
    )


def _facts(*records: FactRecordV2):
    return resolve_product_facts(
        "acme/widget",
        list(records),
        missing_source=FactSourceV2(
            source_type="mechanical_repository",
            location="repository://fixture",
            source_revision="abc123",
        ),
    )


def test_internal_example_metadata_cannot_approve_a_parity_claim() -> None:
    example = _structured_fact(
        "example.minimal",
        {
            "code": "from aspose.threed import Scene\n",
            "verified_public_symbols": ["aspose.threed.Scene"],
            "public_api_sha256": "a" * 64,
            "python_package": {
                "distribution_name": "aspose-3d-foss",
                "package_paths": ["aspose", "aspose/threed"],
            },
        },
    )
    facts = _facts(example)

    assert (
        literal_fact_ids(
            "Aspose.3D shares the same public API design as another product.",
            facts,
            [example.fact_id],
        )
        == []
    )


def test_typed_public_identifier_and_repository_path_remain_matchable() -> None:
    api = _structured_fact(
        "api.public_surface",
        {
            "modules": [
                {
                    "module": "aspose.note",
                    "exports": ["Document", "LoadOptions"],
                    "source_path": "src/aspose/note/__init__.py",
                    "source_sha256": "b" * 64,
                }
            ]
        },
    )
    examples = _structured_fact(
        "repository.examples",
        {
            "files": [
                {
                    "path": "examples/export_pdf.py",
                    "sha256": "c" * 64,
                    "execution_verified": False,
                }
            ]
        },
    )
    facts = _facts(api, examples)

    assert literal_fact_ids("Use `LoadOptions`.", facts, [api.fact_id]) == [api.fact_id]
    assert literal_fact_ids(
        "See [export_pdf.py](examples/export_pdf.py).",
        facts,
        [examples.fact_id],
    ) == [examples.fact_id]


def _maven_coordinates() -> FactRecordV2:
    return _structured_fact(
        "installation.coordinates",
        [
            {
                "ecosystem": "java",
                "group_id": "org.example",
                "artifact_id": "example-foss",
                "version": "1.0.0",
            }
        ],
    )


def test_complete_fenced_maven_dependency_grounds_exact_coordinates() -> None:
    coordinate = _maven_coordinates()
    facts = _facts(coordinate)
    block = """```xml
<dependency>
  <groupId>org.example</groupId>
  <artifactId>example-foss</artifactId>
  <version>1.0.0</version>
</dependency>
```"""

    assert literal_fact_ids(block, facts, [coordinate.fact_id]) == [coordinate.fact_id]


def test_exact_coordinate_version_replacement_remains_grounded() -> None:
    coordinate = _maven_coordinates()
    facts = _facts(coordinate)

    assert literal_fact_ids("1.0.0", facts, [coordinate.fact_id]) == [coordinate.fact_id]


def test_altered_or_registry_only_maven_text_cannot_ground_coordinates() -> None:
    coordinate = _maven_coordinates()
    facts = _facts(coordinate)
    exact = """```xml
<dependency>
  <groupId>org.example</groupId>
  <artifactId>example-foss</artifactId>
  <version>1.0.0</version>
</dependency>
```"""
    altered = [
        exact.replace("org.example", "org.attacker"),
        exact.replace("example-foss", "other-artifact"),
        exact.replace("1.0.0", "9.9.9"),
        "The coordinate was verified against Maven Central.",
        "org.example:example-foss:1.0.0",
    ]

    for claim in altered:
        assert literal_fact_ids(claim, facts, [coordinate.fact_id]) == []


def test_curated_structured_fields_expose_only_visitor_meaningful_values() -> None:
    records = [
        _structured_fact(
            "installation.capability_dependencies",
            {
                "entries": [
                    {
                        "distribution": "Pillow",
                        "purpose": "optional image capability",
                        "install_command": "python -m pip install Pillow",
                        "source_sha256": "1" * 64,
                    }
                ]
            },
        ),
        _structured_fact(
            "python.distribution",
            {
                "manifest_path": "pyproject.toml",
                "requires_python": ">=3.11",
                "runtime_dependencies": ["cryptography>=42"],
                "development_status": "Alpha",
                "typed_marker": {"path": "src/aspose_pdf/py.typed", "sha256": "2" * 64},
            },
        ),
        _structured_fact(
            "development.commands",
            {
                "entries": [
                    {
                        "command": "scripts/build.sh",
                        "embedded_commands": ["python -m build"],
                        "sources": [{"path": "scripts/build.sh", "sha256": "3" * 64}],
                    },
                    {"command": "scripts/check.sh"},
                ]
            },
        ),
        _structured_fact(
            "repository.documentation_assets",
            {"entries": [{"path": "supported-features.md", "sha256": "4" * 64}]},
        ),
        _structured_fact(
            "repository.contribution_guidance",
            {
                "path": "CONTRIBUTING.md",
                "validation_scripts": [{"path": "scripts/check.sh", "sha256": "5" * 64}],
            },
        ),
        _structured_fact(
            "repository.security_guidance",
            {
                "policy": {
                    "path": "SECURITY.md",
                    "private_reporting_url": (
                        "https://github.com/acme/widget/security/advisories/new"
                    ),
                    "sha256": "6" * 64,
                },
                "resource_limits": {
                    "class": "PdfLoadLimits",
                    "fields": ["max_input_bytes"],
                },
            },
        ),
    ]
    facts = _facts(*records)

    expected_claims = {
        records[0].fact_id: "- optional capability: python -m pip install Pillow",
        records[1].fact_id: "Alpha; cryptography>=42; src/aspose_pdf/py.typed",
        records[2].fact_id: "Run `scripts/build.sh` and `scripts/check.sh`.",
        records[3].fact_id: "See [supported features](supported-features.md).",
        records[4].fact_id: "Run [scripts/check.sh](scripts/check.sh) before contributing.",
        records[5].fact_id: (
            "See SECURITY.md or report privately at "
            "https://github.com/acme/widget/security/advisories/new; PdfLoadLimits defines "
            "1 source-defined limits."
        ),
    }
    for fact_id, claim in expected_claims.items():
        assert literal_fact_ids(claim, facts, [fact_id]) == [fact_id]

    for record in records:
        assert literal_fact_ids("Internal digest " + "1" * 64, facts, [record.fact_id]) == []


def test_unknown_or_altered_structured_values_remain_ungrounded() -> None:
    known = _structured_fact(
        "development.commands",
        {"entries": [{"command": "scripts/check.sh"}]},
    )
    unknown = _structured_fact(
        "repository.unknown_structure",
        {"command": "scripts/check.sh", "path": "CONTRIBUTING.md"},
    )
    facts = _facts(known, unknown)

    assert literal_fact_ids("Run `scripts/check.sh`.", facts, [known.fact_id]) == [known.fact_id]
    assert literal_fact_ids("Run `scripts/check.ps1`.", facts, [known.fact_id]) == []
    assert literal_fact_ids("Run `scripts/check.sh`.", facts, [unknown.fact_id]) == []
    assert literal_fact_ids("See CONTRIBUTING.md.", facts, [unknown.fact_id]) == []
