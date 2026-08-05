"""Normalize selected product-manifest runtime compatibility."""

_RUNTIME_REQUIREMENT_FIELDS: dict[str, tuple[str, str]] = {
    "cpp": ("cmake_min_version", "CMake"),
    "go": ("runtime_min_version", "Go"),
    "java": ("runtime_min_version", "Java"),
    "net": ("min_framework", ".NET"),
    "python": ("requires_python", "Python"),
    "rust": ("rust_version", "Rust"),
    "typescript": ("engines_node", "Node.js"),
}


def manifest_compatibility_rows(
    ecosystem: str,
    parsed: dict[str, str],
    manifest_path: str,
) -> list[dict]:
    """Return source-bound compatibility rows for one selected product root."""

    if ecosystem == "python" and manifest_path.replace("\\", "/").endswith("/setup.py"):
        return []
    if ecosystem == "python" and manifest_path == "setup.py":
        return []

    requirement_key, runtime_label = _RUNTIME_REQUIREMENT_FIELDS.get(
        ecosystem,
        ("runtime_min_version", ecosystem),
    )
    runtime = parsed.get(requirement_key)
    supported_runtime_versions = (
        [
            version.strip()
            for version in parsed.get("python_classifier_versions", "").split(",")
            if version.strip()
        ]
        if ecosystem == "python"
        else []
    )
    compatibility_kind = "minimum_runtime"
    if not runtime and ecosystem == "typescript":
        runtime = parsed.get("typescript_target")
        runtime_label = "ECMAScript"
        compatibility_kind = "compiler_target"
    if not runtime and not supported_runtime_versions:
        return []
    return [
        {
            key: value
            for key, value in {
                "ecosystem": ecosystem,
                "runtime_label": runtime_label,
                "minimum_runtime": runtime,
                "supported_runtime_versions": supported_runtime_versions or None,
                "compatibility_kind": compatibility_kind,
                "manifest_path": manifest_path,
                "root_role": "product",
            }.items()
            if value is not None
        }
    ]
