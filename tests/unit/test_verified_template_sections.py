"""Tests for verified_template_sections.py's dependency_markdown()."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.presentation.verified_template_sections import (
    dependency_markdown,
    development_dependency_markdown,
)

_SOURCE = FactSourceV2(
    source_type="mechanical_repository",
    location="repository://org/repo",
    source_revision="a" * 40,
)

_RENDERABLE_VALUES = {
    "product.audience": ["Developers using Python"],
    "product.problems_solved": ["Process widget files"],
    "product.capabilities": ["Create and inspect widgets"],
    "product.formats": ["WGT"],
}


def _facts(
    distribution_value: object | None, *, verification_state: str = "verified"
) -> ProductFactsV2:
    records = [
        FactRecordV2(
            fact_id=descriptive_fact_id(field, "dependency-markdown-fixture"),
            field=field,
            value=_RENDERABLE_VALUES.get(field, {"field": field}),
            source=_SOURCE,
            verification_state="verified",
            authoritative_owner="repository-source",
            confidence=1.0,
            affected_surfaces=["readme"],
        )
        for field in REQUIRED_PRODUCT_FIELDS
    ]
    if distribution_value is not None:
        records.append(
            FactRecordV2(
                fact_id="python.distribution:dependency-markdown-test",
                field="python.distribution",
                value=distribution_value,
                source=_SOURCE,
                verification_state=verification_state,
                authoritative_owner="repository-source",
                confidence=1.0,
                affected_surfaces=["readme.dependencies"],
            )
        )
    return ProductFactsV2(
        org_repo="org/repo",
        facts=records,
        selected_fact_ids={fact.field: fact.fact_id for fact in records},
    )


def test_verified_empty_runtime_dependencies_renders_the_standard_sentence():
    facts = _facts({"manifest_path": "pyproject.toml", "runtime_dependencies": []})

    assert dependency_markdown(facts) == "No required third-party package dependencies."


def test_absent_distribution_fact_falls_back_to_installation_pointer():
    """2026-08-25 (`0eb2eb53f`, "reconcile shared acceptance contracts"): when
    `python.distribution` can't supply a dependency list, `dependency_markdown()`
    now falls back to pointing at Installation instead of omitting the section
    entirely -- verified `installation.coordinates` (present in every `_facts()`
    fixture in this file, via `REQUIRED_PRODUCT_FIELDS`) is enough to trigger it.
    True absence of anything to say is covered separately by
    `test_absent_everything_still_returns_none` below."""

    facts = _facts(None)

    assert dependency_markdown(facts) == (
        "Use the repository package coordinate and package-manager command shown in "
        "[Installation](#installation)."
    )


def test_unverified_distribution_fact_falls_back_to_installation_pointer():
    """Same fallback as above -- an unverified (not just absent) distribution fact
    is equally insufficient to report dependencies, so the same pointer applies."""

    facts = _facts(
        {"manifest_path": "pyproject.toml", "runtime_dependencies": []},
        verification_state="unverified",
    )

    assert dependency_markdown(facts) == (
        "Use the repository package coordinate and package-manager command shown in "
        "[Installation](#installation)."
    )


def test_absent_everything_still_returns_none():
    """The genuinely-nothing-to-report path: no distribution fact AND no accepted
    `installation.coordinates` either. Every other `_facts()`-based test in this
    file has `installation.coordinates` unconditionally accepted (it's in
    `REQUIRED_PRODUCT_FIELDS`), so this is the one case that actually exercises
    `dependency_markdown()`'s `if coordinate is not None` branch being False --
    otherwise untested after the 2026-08-25 fallback landed. Downgrading (not
    removing) `installation.coordinates`'s verification_state keeps its
    `selected_fact_ids` entry intact -- `visitor_fact_render_view()`'s own
    compatibility lookup indexes it directly and isn't tolerant of true absence,
    a separate, narrower coupling than what this test is checking."""

    facts = _facts(None)
    downgraded = facts.model_copy(
        update={
            "facts": [
                (
                    fact.model_copy(update={"verification_state": "unverified"})
                    if fact.field == "installation.coordinates"
                    else fact
                )
                for fact in facts.facts
            ]
        }
    )

    assert dependency_markdown(downgraded) is None


def test_verified_non_empty_runtime_dependencies_is_unchanged():
    facts = _facts(
        {
            "manifest_path": "pyproject.toml",
            "runtime_dependencies": ["cryptography>=42", "asn1crypto>=1.5"],
        }
    )

    assert dependency_markdown(facts) == (
        "Required runtime dependencies declared in `pyproject.toml`: "
        "`cryptography>=42`, `asn1crypto>=1.5`."
    )


def test_verified_non_empty_development_dependencies_renders_the_list():
    facts = _facts(
        {
            "manifest_path": "pyproject.toml",
            "runtime_dependencies": ["Pillow>=10.1.0"],
            "development_dependencies": ["pytest>=8.0", "ruff>=0.15.7"],
        }
    )

    assert development_dependency_markdown(facts) == (
        "Development dependencies declared in `pyproject.toml`: `pytest>=8.0`, `ruff>=0.15.7`."
    )


def test_verified_empty_development_dependencies_renders_the_standard_sentence():
    facts = _facts(
        {
            "manifest_path": "pyproject.toml",
            "runtime_dependencies": [],
            "development_dependencies": [],
        }
    )

    assert development_dependency_markdown(facts) == (
        "No development dependencies declared in `pyproject.toml`."
    )


def test_absent_development_dependencies_key_returns_none():
    # No dev/test/lint/ci group declared at all in either PEP 621
    # optional-dependencies or PEP 735 dependency-groups tables -- absence is
    # NOT evidence of zero development dependencies (unlike required runtime
    # deps), so this stays unrendered rather than claiming verified-empty.
    facts = _facts({"manifest_path": "pyproject.toml", "runtime_dependencies": []})

    assert development_dependency_markdown(facts) is None


def test_development_dependencies_absent_distribution_fact_returns_none():
    facts = _facts(None)

    assert development_dependency_markdown(facts) is None


def test_development_dependencies_unverified_distribution_fact_returns_none():
    facts = _facts(
        {
            "manifest_path": "pyproject.toml",
            "runtime_dependencies": [],
            "development_dependencies": ["pytest>=8.0"],
        },
        verification_state="unverified",
    )

    assert development_dependency_markdown(facts) is None
