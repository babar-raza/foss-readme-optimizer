"""Rust platform manifest parser: Cargo.toml. Real TOML, so this uses stdlib
`tomllib` unconditionally (GOVERNANCE.md rule 8), matching `ecosystems/python.py`'s
own pyproject.toml precedent -- Cargo.toml has no legacy-manifest fallback the
way Python has setup.py, so this is a single parse, not a two-path one.

Unlike pyproject.toml's PEP 621 `license` (a string or a `{text|file}` table),
Cargo.toml's `package.license` is always a plain SPDX-expression string -- a
crate declares a license file instead via the separate `license-file` key,
never a `license = {file = "..."}` table. `license` is read as a plain string
only; a crate using `license-file` instead simply has no `license` in `info`,
which is correct, not a gap.
"""

import tomllib
from pathlib import Path


def parse_cargo_toml(cargo_toml_path: Path) -> dict[str, str]:
    info: dict[str, str] = {}
    data = tomllib.loads(cargo_toml_path.read_text(encoding="utf-8", errors="replace"))
    package = data.get("package", {})
    if package.get("name"):
        info["name"] = package["name"]
    if package.get("version"):
        info["version"] = package["version"]
    if package.get("license"):
        info["license"] = package["license"]
    if package.get("edition"):
        info["edition"] = package["edition"]
    if package.get("rust-version"):
        info["rust_version"] = package["rust-version"]

    lib = data.get("lib", {})
    if lib.get("name"):
        info["lib_name"] = lib["name"]

    return info


def parse(repo_root: Path) -> dict[str, str]:
    cargo_toml_path = repo_root / "Cargo.toml"
    if not cargo_toml_path.exists():
        return {}
    return parse_cargo_toml(cargo_toml_path)
