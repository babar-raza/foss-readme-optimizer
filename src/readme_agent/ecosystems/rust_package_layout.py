"""Resolve Cargo package/lib identity and immutable source inputs."""

from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path
from typing import Any

from readme_agent.ecosystems.rust_api_schema import RustPackageLayoutV1

_FULL_GIT_REVISION = re.compile(r"^[0-9a-f]{40,64}$")


def _cargo_manifest(repository_root: Path) -> Path:
    direct = repository_root / "Cargo.toml"
    if direct.is_file():
        return direct
    manifests = sorted(
        path for path in repository_root.glob("*/Cargo.toml") if "target" not in path.parts
    )
    if len(manifests) != 1:
        raise ValueError(
            "Rust repository must have one deterministic package Cargo.toml; "
            f"found {len(manifests)}"
        )
    return manifests[0]


def _string_table(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def inspect_rust_package_layout(repository_root: Path) -> RustPackageLayoutV1:
    """Return Cargo package and library identity without executing repository code."""

    manifest_path = _cargo_manifest(repository_root)
    package_root = manifest_path.parent
    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8", errors="strict"))
    package = _string_table(manifest.get("package"))
    package_name = package.get("name")
    if not isinstance(package_name, str) or not package_name:
        raise ValueError("Cargo package has no package.name")
    library = _string_table(manifest.get("lib"))
    crate_name = library.get("name") or package_name.replace("-", "_")
    if not isinstance(crate_name, str) or not crate_name:
        raise ValueError("Cargo package has no deterministic library crate name")
    lib_path = library.get("path") or "src/lib.rs"
    if not isinstance(lib_path, str) or not (package_root / lib_path).is_file():
        raise ValueError(f"Cargo library source does not exist: {lib_path!r}")
    dependencies = _string_table(manifest.get("dependencies"))
    digest = hashlib.sha256()
    source_files = sorted(package_root.rglob("*.rs"))
    for path in [manifest_path, *source_files]:
        relative = path.relative_to(repository_root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    manifest_relative = manifest_path.relative_to(repository_root).as_posix()
    package_relative = package_root.relative_to(repository_root).as_posix()
    return RustPackageLayoutV1(
        manifest_path=manifest_relative,
        package_root=package_relative or ".",
        package_name=package_name,
        crate_name=crate_name,
        version=str(package["version"]) if package.get("version") else None,
        edition=str(package.get("edition") or "2015"),
        rust_version=str(package["rust-version"]) if package.get("rust-version") else None,
        lib_path=(package_root / lib_path).relative_to(repository_root).as_posix(),
        dependency_names=sorted(str(name) for name in dependencies),
        example_paths=sorted(
            path.relative_to(repository_root).as_posix()
            for path in package_root.glob("examples/*.rs")
        ),
        test_paths=sorted(
            path.relative_to(repository_root).as_posix() for path in package_root.glob("tests/*.rs")
        ),
        acquisition="pinned_source",
        manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        source_sha256=digest.hexdigest(),
    )


def pinned_rust_git_dependency(
    package: RustPackageLayoutV1,
    *,
    org_repo: str,
    source_revision: str,
) -> str:
    """Return a source-pinned Cargo dependency without assuming crates.io publication."""

    if not _FULL_GIT_REVISION.fullmatch(source_revision):
        raise ValueError("Rust source dependency requires a full immutable Git revision")
    if org_repo.count("/") != 1:
        raise ValueError("Rust source dependency requires an org/repository identity")
    return (
        f'{package.package_name} = {{ git = "https://github.com/{org_repo}", '
        f'rev = "{source_revision}" }}'
    )
