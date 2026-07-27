"""Build canonical authoritative-registry request URLs from exact coordinates."""

from __future__ import annotations

_MAVEN_METADATA_URL_TEMPLATE = (
    "https://repo1.maven.org/maven2/{group_path}/{artifact}/maven-metadata.xml"
)
_PYPI_URL_TEMPLATE = "https://pypi.org/pypi/{name}/json"
_NPM_URL_TEMPLATE = "https://registry.npmjs.org/{name}"
_NUGET_URL_TEMPLATE = "https://api.nuget.org/v3-flatcontainer/{name}/index.json"
_GO_PROXY_URL_TEMPLATE = "https://proxy.golang.org/{module}/@v/list"
_CRATES_IO_URL_TEMPLATE = "https://crates.io/api/v1/crates/{name}"
_CONAN_CENTER_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/conan-io/conan-center-index/master/recipes/{name}/config.yml"
)
_VCPKG_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/microsoft/vcpkg/master/ports/{name}/vcpkg.json"
)


def escape_go_module_path(module: str) -> str:
    """Apply the Go module proxy's uppercase path escaping."""

    return "".join(
        f"!{character.lower()}" if character.isupper() else character for character in module
    )


def registry_request_url(ecosystem: str, coordinate: dict[str, str]) -> str | None:
    """Return the exact existence-check URL or ``None`` for incomplete/unknown coordinates."""

    if ecosystem == "java":
        group_id = coordinate.get("group_id")
        artifact_id = coordinate.get("artifact_id")
        if not group_id or not artifact_id:
            return None
        return _MAVEN_METADATA_URL_TEMPLATE.format(
            group_path=group_id.replace(".", "/"),
            artifact=artifact_id,
        )

    name = coordinate.get("name") or (
        coordinate.get("library_target") if ecosystem in {"cpp_conan", "cpp_vcpkg"} else None
    )
    if not name:
        return None
    if ecosystem == "python":
        return _PYPI_URL_TEMPLATE.format(name=name)
    if ecosystem == "typescript":
        return _NPM_URL_TEMPLATE.format(name=name)
    if ecosystem == "net":
        return _NUGET_URL_TEMPLATE.format(name=name.lower())
    if ecosystem == "go":
        return _GO_PROXY_URL_TEMPLATE.format(module=escape_go_module_path(name))
    if ecosystem == "rust":
        return _CRATES_IO_URL_TEMPLATE.format(name=name)
    if ecosystem == "cpp_conan":
        return _CONAN_CENTER_URL_TEMPLATE.format(name=name.lower())
    if ecosystem == "cpp_vcpkg":
        return _VCPKG_URL_TEMPLATE.format(name=name.lower())
    return None
