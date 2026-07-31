"""Executable-code provenance controls for trusted README transformation."""

from __future__ import annotations

import pytest

from readme_agent.errors import LLMError
from readme_agent.readme.trusted_code_provenance import (
    validate_trusted_code_block_provenance,
)


def test_comment_removed_inherited_code_remains_provenanced() -> None:
    source = "```python\n# Explain the call.\nresult = convert(source)\n```\n"
    candidate = "```python\n\nresult = convert(source)\n```\n"

    validate_trusted_code_block_provenance(source, candidate)


def test_configured_mermaid_is_excluded_from_executable_provenance() -> None:
    source = "# Widget\n"
    candidate = "```mermaid\nflowchart LR\n  INPUT --> PRODUCT\n```\n"

    validate_trusted_code_block_provenance(source, candidate)


def test_new_executable_code_fails_closed() -> None:
    source = "```python\nresult = convert(source)\n```\n"
    candidate = (
        source
        + "\n```python\n"
        + "from widget import Converter\n"
        + "Converter().convert('input.widget')\n"
        + "```\n"
    )

    with pytest.raises(LLMError, match="without inherited README provenance"):
        validate_trusted_code_block_provenance(source, candidate)


def test_duplicate_inherited_code_fails_closed() -> None:
    source = "```bash\npip install widget\n```\n"
    candidate = source + "\n" + source

    with pytest.raises(LLMError, match="without inherited README provenance"):
        validate_trusted_code_block_provenance(source, candidate)
