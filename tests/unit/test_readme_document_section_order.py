from readme_agent.readme.document_operations import apply_document_operations, build_operation
from readme_agent.readme.document_section_order import enforce_canonical_section_order
from readme_agent.readme.document_structure import parse_headings


def _h2_titles(markdown: str) -> list[str]:
    return [heading.title for heading in parse_headings(markdown) if heading.level == 2]


def test_moves_complete_sections_into_template_order_and_preserves_unknown_section():
    source = b"""# Aspose.Note FOSS for Python

## Navigation

- [Quick start](#quick-start)
- [Additional examples](#additional-examples)
- [Installation](#installation)
- [Custom internals](#custom-internals)
- [Scope and limitations](#scope-and-limitations)

## Quick start

quick-body

## Additional examples

additional-body

## Installation

installation-body

## Custom internals

custom-body

## Scope and limitations

scope-body
"""

    operations = enforce_canonical_section_order(source, [])
    candidate = apply_document_operations(source, operations).decode()

    assert _h2_titles(candidate) == [
        "Navigation",
        "Installation",
        "Quick start",
        "Additional examples",
        "Custom internals",
        "Scope and limitations",
    ]
    assert candidate.count("quick-body") == 1
    assert candidate.count("additional-body") == 1
    assert candidate.count("installation-body") == 1
    assert candidate.count("custom-body") == 1
    assert candidate.count("scope-body") == 1
    assert "- [Installation](#installation)\n- [Quick start](#quick-start)" in candidate
    assert operations[-1].operation == "move_exact"
    assert operations[-1].coordinate_space == "candidate_utf8"


def test_section_move_preserves_prior_source_operation_output():
    source = b"""# Product

## Quick start

unverified-example

## Installation

pip install product
"""
    start = source.index(b"unverified-example")
    correction = build_operation(
        operation_id="readme.example.verified",
        operation="replace",
        source=source,
        start=start,
        end=start + len(b"unverified-example"),
        replacement="verified-example",
        fact_ids=[],
        treatment="presentation_policy_correction",
        rationale="Use the separately verified example.",
    )

    operations = enforce_canonical_section_order(source, [correction])
    candidate = apply_document_operations(source, operations).decode()

    assert _h2_titles(candidate) == ["Installation", "Quick start"]
    assert "verified-example" in candidate
    assert "unverified-example" not in candidate
    assert correction in operations


def test_already_ordered_candidate_does_not_add_move_operation():
    source = b"""# Product

## Installation

install

## Quick start

example

## Additional examples

more
"""

    assert enforce_canonical_section_order(source, []) == []


def test_normalizes_public_spacing_but_preserves_fenced_code_spacing():
    source = b"""# Product


## Installation

```python
first = 1


second = 2
```


## Quick start

example
"""

    operations = enforce_canonical_section_order(source, [])
    candidate = apply_document_operations(source, operations).decode()

    assert "# Product\n\n## Installation" in candidate
    assert "```python\nfirst = 1\n\n\nsecond = 2\n```" in candidate
    assert "```\n\n## Quick start" in candidate
