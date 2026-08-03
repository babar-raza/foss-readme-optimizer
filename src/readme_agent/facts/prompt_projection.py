"""Project verified facts into bounded LLM-facing values without losing evidence hashes."""

from __future__ import annotations

from typing import Any

_EXAMPLE_PROMPT_KEYS = (
    "language",
    "class_name",
    "code",
    "verification_outcome",
    "verification_detail",
    "verified_public_symbols",
    "input_fixture_bindings",
    "python_package",
    "typescript_package",
    "rust_package",
    "rust_formats",
    "rust_source_dependency",
)
_ACQUISITION_PROMPT_KEYS = (
    "schema_version",
    "org_repo",
    "source_revision",
    "ecosystem",
    "method",
    "outcome",
    "detail",
    "coordinate",
    "truth_eligible",
)


def prompt_fact_value(field: str, value: Any) -> Any:
    """Return the exact fact subset useful to an author or factual reviewer.

    Native execution transcripts and registry/source-build receipts remain in the
    checksum-bound ProductFactsV2 artifact. They are deterministic-verifier inputs,
    not prose-authoring or review context.
    """

    if not isinstance(value, dict):
        return value
    keys: tuple[str, ...] | None = None
    if field == "example.minimal":
        keys = _EXAMPLE_PROMPT_KEYS
    elif field == "installation.verified_acquisition":
        keys = _ACQUISITION_PROMPT_KEYS
    if keys is None:
        return value
    return {key: value[key] for key in keys if key in value}
