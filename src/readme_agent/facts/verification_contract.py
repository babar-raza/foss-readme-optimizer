"""Build ecosystem-scoped hashes for isolated product verification."""

from __future__ import annotations

import hashlib
from pathlib import Path

_COMMON_FILES = (
    "local_verification.py",
    "example_execution.py",
    "isolated_execution.py",
    "isolated_execution_inputs.py",
    "isolated_execution_schema.py",
    "example_quality.py",
    "repository_examples.py",
    "verified_repository_examples.py",
    "example_verification_schema.py",
    "aspose_org_dependency_snapshot.py",
    "aspose_org_format_adapter.py",
    "aspose_org_format_contract.py",
    "deterministic_truth_salvage.py",
    "format_direction.py",
)

_COMPILED_COMMON_FILES = (
    "compiled_consumer.py",
    "compiled_consumer_schema.py",
)

_ECOSYSTEM_FILES: dict[str, tuple[str, ...]] = {
    "python": (
        "python_consumer.py",
        "python_consumer_fixtures.py",
        "python_consumer_schema.py",
        "python_dependency_acquisition.py",
        "python_dependency_schema.py",
        "python_example_normalization.py",
        "python_example_verifier.py",
        "python_family_format_functionality.py",
        "python_3d_format_functionality.py",
        "python_barcode_format_functionality.py",
        "python_email_format_functionality.py",
        "python_html_format_functionality.py",
        "python_repository_examples.py",
        "../ecosystems/python_api_schema.py",
        "../ecosystems/python_package_layout.py",
        "../ecosystems/python_public_api.py",
        "../ecosystems/python_symbol_members.py",
    ),
    "typescript": (
        "typescript_consumer.py",
        "typescript_consumer_driver.js",
        "typescript_consumer_schema.py",
        "typescript_example_normalization.py",
        "typescript_example_verifier.py",
        "typescript_toolchain.py",
        "../ecosystems/typescript_api_schema.py",
        "../ecosystems/typescript_package_layout.py",
    ),
    "rust": (
        "rust_consumer.py",
        "rust_consumer_schema.py",
        "rust_dependency_acquisition.py",
        "rust_dependency_schema.py",
        "rust_example_normalization.py",
        "rust_example_verifier.py",
        "example_verifiers/rust.py",
        "../ecosystems/rust_api_schema.py",
        "../ecosystems/rust_format_truth.py",
        "../ecosystems/rust_package_layout.py",
        "../ecosystems/rust_public_api.py",
        "../ecosystems/rust_snippets.py",
        "../ecosystems/rust_symbol_extraction.py",
        "../ecosystems/rust_syntax.py",
        "../ecosystems/rust_use_resolution.py",
    ),
    "java": _COMPILED_COMMON_FILES + ("java_example_verifier.py",),
    "net": _COMPILED_COMMON_FILES + ("dotnet_example_verifier.py",),
    "cpp": _COMPILED_COMMON_FILES
    + (
        "cpp_example_verifier.py",
        "example_verifiers/cpp.py",
    ),
    "go": _COMPILED_COMMON_FILES + ("go_example_verifier.py",),
}

_ALIASES = {
    "c++": "cpp",
    "csharp": "net",
    "dotnet": "net",
    ".net": "net",
    "py": "python",
    "ts": "typescript",
}


def normalize_verification_ecosystem(ecosystem: str | None) -> str | None:
    """Normalize registry and example-language labels to contract keys."""

    if ecosystem is None:
        return None
    normalized = ecosystem.strip().lower()
    return _ALIASES.get(normalized, normalized)


def verification_contract_files(ecosystem: str | None = None) -> tuple[str, ...]:
    """Return the exact implementation files relevant to one ecosystem."""

    normalized = normalize_verification_ecosystem(ecosystem)
    if normalized is None:
        platform_files = tuple(
            path for key in sorted(_ECOSYSTEM_FILES) for path in _ECOSYSTEM_FILES[key]
        )
    else:
        platform_files = _ECOSYSTEM_FILES.get(normalized, ())
    return tuple(dict.fromkeys((*_COMMON_FILES, *platform_files)))


def verification_contract_hash(root: Path, ecosystem: str | None = None) -> str:
    """Hash the common verifier seam plus only the selected ecosystem adapter."""

    digest = hashlib.sha256()
    for relative_path in verification_contract_files(ecosystem):
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update((root / relative_path).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
