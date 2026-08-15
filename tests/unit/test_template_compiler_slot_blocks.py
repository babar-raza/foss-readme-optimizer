"""T5 (disposition-ledger real fix): `compiled_slot_blocks` returns each
included slot's exact compiled block text, matching what
`compile_repository_presentation` actually joins into the candidate, without
altering that function's own behavior."""

from __future__ import annotations

from readme_agent.presentation.template_compiler import (
    compile_repository_presentation,
    compiled_slot_blocks,
)
from readme_agent.presentation.template_schema import (
    BoundTemplateContentV1,
    PresentationTemplateInputV1,
)


def _fact(markdown: str, *ids: str) -> BoundTemplateContentV1:
    return BoundTemplateContentV1(
        markdown=markdown, source_kind="repository_fact", fact_ids=list(ids)
    )


def _configured(markdown: str, standard: str) -> BoundTemplateContentV1:
    return BoundTemplateContentV1(
        markdown=markdown, source_kind="configured_standard", standard_ids=[standard]
    )


def _minimal_input() -> PresentationTemplateInputV1:
    return PresentationTemplateInputV1(
        org_repo="acme-foss/Acme-FOSS-for-Python",
        source_revision="rev",
        source_line_count=80,
        title=_fact("Acme FOSS for Python", "identity:acme"),
        badges=_fact(
            "[![PyPI](https://img.shields.io/pypi/v/acme.svg)](https://pypi.org/project/acme/)",
            "acquisition:acme",
        ),
        summary=_fact("Acme FOSS for Python reads and writes Acme documents.", "identity:acme"),
        sections={
            "at_a_glance": _fact(
                "- Reads Acme documents\n- Writes Acme documents", "capabilities:acme"
            ),
            "key_capabilities": _fact("- **Read** - Read Acme documents.", "capabilities:acme"),
            "installation": _fact("```bash\npython -m pip install acme\n```", "acquisition:acme"),
            "quick_start": _fact("```python\nimport acme\n```", "example:acme"),
            "scope_and_limitations": _fact(
                "Support is limited to verified formats.", "limitations:acme"
            ),
            "license": _configured(
                "This project uses the [MIT License](LICENSE).", "license-benefits-v1"
            ),
        },
    )


def test_compiled_slot_blocks_matches_compile_repository_presentation_output():
    template_input = _minimal_input()

    candidate = compile_repository_presentation(template_input)
    blocks = compiled_slot_blocks(template_input)

    assert set(blocks) == {
        "At a Glance",
        "Key Capabilities",
        "Installation",
        "Quick Start",
        "Scope and Limitations",
        "License",
    }
    for heading, block_text in blocks.items():
        assert block_text.startswith(f"## {heading}\n\n")
        assert block_text in candidate


def test_compiled_slot_blocks_omits_slots_the_input_never_included():
    template_input = _minimal_input()

    blocks = compiled_slot_blocks(template_input)

    assert "Documentation and Resources" not in blocks
    assert "API Reference" not in blocks


def test_compiled_slot_blocks_does_not_alter_compile_repository_presentation():
    """Calling compiled_slot_blocks alongside the real compiler must never
    change compile_repository_presentation's own output -- same input,
    same candidate bytes, called in either order."""

    template_input = _minimal_input()

    candidate_before = compile_repository_presentation(template_input)
    compiled_slot_blocks(template_input)
    candidate_after = compile_repository_presentation(template_input)

    assert candidate_before == candidate_after
