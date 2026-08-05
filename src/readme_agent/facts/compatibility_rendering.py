"""Render source-bound runtime compatibility as visitor-facing prose."""

import re

_ECOSYSTEM_LABELS = {
    "cpp": "C++",
    "dotnet": ".NET",
    "go": "Go",
    "java": "Java",
    "net": ".NET",
    "python": "Python",
    "rust": "Rust",
    "typescript": "TypeScript",
}
_RUNTIME_LABELS = {
    ".net": ".NET",
    "cmake": "CMake",
    "ecmascript": "ECMAScript",
    "go": "Go",
    "java": "Java",
    "node": "Node.js",
    "node.js": "Node.js",
    "python": "Python",
    "rust": "Rust",
}


def ecosystem_display_label(ecosystem: str) -> str:
    """Return the governed visitor-facing spelling for an ecosystem identifier."""

    normalized = ecosystem.strip().casefold()
    return _ECOSYSTEM_LABELS.get(normalized, normalized.replace("-", " ").title())


def ecosystem_label_items() -> tuple[tuple[str, str], ...]:
    """Return stable ecosystem tokens and their governed display labels."""

    return tuple(_ECOSYSTEM_LABELS.items())


def _natural_join(values: list[str]) -> str:
    if len(values) < 2:
        return "".join(values)
    if len(values) == 2:
        return " and ".join(values)
    return ", ".join(values[:-1]) + f", and {values[-1]}"


def _normalized_runtime(label: str, runtime: str) -> str:
    value = runtime.strip()
    value = re.sub(rf"^{re.escape(label)}\s*", "", value, flags=re.IGNORECASE)
    value = value.removesuffix("+").strip()
    if label == ".NET":
        folded = value.casefold()
        if folded.startswith("netcoreapp"):
            value = "Core " + value[len("netcoreapp") :]
        elif folded.startswith("netstandard"):
            value = "Standard " + value[len("netstandard") :]
        elif folded.startswith("net"):
            value = value[3:]
    if value.startswith(">=") and not re.search(r"[,<|^~*]", value[2:]):
        value = value[2:].strip()
    return value


def compatibility_phrases(value: object) -> list[str]:
    """Render one non-redundant compatibility statement per manifest row."""

    rows = value if isinstance(value, list) else [value]
    phrases: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ecosystem = str(row.get("ecosystem") or row.get("platform") or "").strip().lower()
        runtime = str(row.get("minimum_runtime") or "").strip()
        runtime_label = str(row.get("runtime_label") or "").strip().lower()
        compatibility_kind = str(row.get("compatibility_kind") or "minimum_runtime")
        label = _RUNTIME_LABELS.get(runtime_label) or _ECOSYSTEM_LABELS.get(ecosystem)
        raw_supported_versions = row.get("supported_runtime_versions", [])
        supported_versions = (
            [str(version).strip() for version in raw_supported_versions if str(version).strip()]
            if isinstance(raw_supported_versions, list)
            else []
        )
        if label and supported_versions:
            supported = _natural_join([f"{label} {version}" for version in supported_versions])
            if runtime:
                phrases.append(
                    f"Requires {label} {runtime} and is explicitly classified for {supported}."
                )
            else:
                phrases.append(f"Explicitly classified for {supported}.")
            continue
        if label and runtime:
            normalized_runtime = _normalized_runtime(label, runtime)
            if normalized_runtime:
                if compatibility_kind == "compiler_target":
                    phrases.append(f"Targets {label} {normalized_runtime}.")
                    continue
                has_upper_bound = bool(re.search(r"[,<|^~*]", runtime.removeprefix(">=")))
                suffix = "." if has_upper_bound else " or later."
                phrases.append(f"Requires {label} {normalized_runtime}{suffix}")
    return phrases
