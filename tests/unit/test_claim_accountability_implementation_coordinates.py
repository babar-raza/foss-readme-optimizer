from __future__ import annotations

from readme_agent.readme.claim_accountability_implementation_coordinates import (
    implementation_component_coordinates,
)


def _value() -> dict[str, object]:
    return {
        "capability_groups": [
            {
                "label": "Read and write DOCX documents using Python standard-library components",
                "format": "DOCX",
                "roles": ["read", "write"],
                "component_indexes": [0, 1],
                "stdlib_imports": ["xml.etree", "zipfile"],
                "runtime_imports": [],
                "source_summary": "DOCX reader uses only the standard library; DOCX writer.",
            },
            {
                "label": "Read Word 97-2003 DOC binary documents with olefile",
                "format": "DOC",
                "roles": ["read"],
                "component_indexes": [2],
                "stdlib_imports": [],
                "runtime_imports": ["olefile"],
                "source_summary": "Core reader for Word 97-2003 DOC binary files.",
            },
        ]
    }


def test_matches_source_and_public_rows_to_the_same_component_coordinate() -> None:
    source = (
        "- **DOCX Read/Write**: Pure Python reader using only the standard library "
        "(`zipfile`, `xml.etree`)"
    )
    public = "- **Read and write DOCX documents using Python standard-library components**"

    source_coordinates = implementation_component_coordinates(source, "implementation", _value())
    public_coordinates = implementation_component_coordinates(public, "implementation", _value())

    assert source_coordinates == public_coordinates
    assert len(source_coordinates) == 1


def test_known_public_api_name_is_not_misclassified_as_a_dependency() -> None:
    public = (
        "- **Read and write DOCX documents using Python standard-library components** - "
        "Process this format through the pure-Python reader and writer. "
        "Available through the public `Document` API."
    )

    coordinates = implementation_component_coordinates(
        public,
        "implementation",
        _value(),
        known_non_dependency_names={"Document"},
    )

    assert len(coordinates) == 1


def test_distinguishes_doc_from_docx_and_requires_declared_dependency() -> None:
    doc = "- **DOC Support**: Word 97-2003 binary format reader via `olefile`"

    assert len(implementation_component_coordinates(doc, "implementation", _value())) == 1
    assert not implementation_component_coordinates(
        "- **DOC Support**: Word 97-2003 binary format reader via `unknownlib`",
        "implementation",
        _value(),
    )


def test_standard_library_claim_fails_when_component_has_runtime_dependency() -> None:
    value = _value()
    group = value["capability_groups"][0]
    assert isinstance(group, dict)
    group["runtime_imports"] = ["thirdparty"]

    assert not implementation_component_coordinates(
        "Read DOCX with only the standard library",
        "implementation",
        value,
    )


def test_component_evidence_does_not_verify_an_unexecuted_code_fence() -> None:
    assert not implementation_component_coordinates(
        '```python\ndoc.save("output.docx")\n```',
        "implementation",
        _value(),
    )
