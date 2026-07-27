"""Rust package identity, syntax reachability, and public-API contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from readme_agent.ecosystems.rust_format_truth import extract_rust_format_evidence
from readme_agent.ecosystems.rust_package_layout import pinned_rust_git_dependency
from readme_agent.ecosystems.rust_public_api import inspect_rust_public_api


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _fixture(root: Path) -> None:
    _write(
        root / "Cargo.toml",
        """
[package]
name = "widget-core"
version = "1.2.3"
edition = "2021"
rust-version = "1.80"

[dependencies]
serde = "1"
""".strip(),
    )
    _write(
        root / "src/lib.rs",
        """
mod hidden;
mod impls;
pub mod exposed;
#[path = "odd.path.rs"]
mod mapped;

pub use exposed::*;
pub use hidden::{Gadget as Renamed, PublicUnion};
pub use mapped::Mapped;
pub(crate) use hidden::Restricted;

/// Root visitor type.
#[derive(Debug, Clone)]
pub struct Root {
    pub visible: i32,
    pub(crate) crate_only: i32,
    private: i32,
}

pub trait Readable: Send + Sync {
    fn read(&self) -> i32;
}

impl Root {
    pub fn new() -> Self {
        Self { visible: 1, crate_only: 2, private: 3 }
    }

    pub(crate) fn crate_new() -> Self { Self::new() }
    fn hidden_new() -> Self { Self::new() }
}

impl Readable for Root {
    fn read(&self) -> i32 { self.visible }
}

#[cfg(test)]
mod tests {
    #[test]
    fn root_roundtrip() {
        let value = super::Root::new();
        assert_eq!(value.visible, 1);
    }
}
""".strip(),
    )
    _write(
        root / "src/hidden.rs",
        """
#[derive(Debug, Clone)]
/// A curated public type inside a private module.
pub struct Gadget {
    pub value: usize,
    private: usize,
}

pub(crate) struct Restricted;
pub(super) struct ParentOnly;
pub(in crate) struct CratePathOnly;

pub union PublicUnion {
    pub whole: u32,
    pub byte: u8,
}
""".strip(),
    )
    _write(
        root / "src/impls.rs",
        """
use crate::Root;

impl Root {
    pub fn cross_file(&self) -> i32 { self.visible }
}
""".strip(),
    )
    _write(
        root / "src/exposed.rs",
        """
pub enum Mode {
    Fast,
    Safe(u8),
}

pub type Identifier = String;
pub const DEFAULT_LIMIT: usize = 10;
pub static ENABLED: bool = true;
pub fn helper() -> Mode { Mode::Fast }

pub enum SaveFormat {
    Xlsx,
    Unknown,
}

pub enum LoadFormat {
    Xlsx,
    Csv,
}

pub struct Converter;

impl Converter {
    pub fn save_to_html(&self) {}
    pub fn load_csv(&self) {}
    pub fn to_vec(&self) {}
    pub fn from_bits(&self) {}
}
""".strip(),
    )
    _write(
        root / "src/odd.path.rs",
        """
pub struct Mapped;

impl Mapped {
    pub fn create() -> Self { Self }
}
""".strip(),
    )
    _write(
        root / "examples/basic.rs",
        "fn main() { let _root = widget_core::Root::new(); }\n",
    )
    _write(root / "tests/public.rs", "#[test]\nfn public_api() {}\n")


def _by_name(surface):
    return {symbol.qualified_name: symbol for symbol in surface.symbols}


def test_package_identity_and_revision_addressed_source_hash(tmp_path):
    _fixture(tmp_path)

    first = inspect_rust_public_api(
        tmp_path,
        org_repo="fixture/widget-core",
        source_revision="a" * 40,
    )
    second = inspect_rust_public_api(
        tmp_path,
        org_repo="fixture/widget-core",
        source_revision="a" * 40,
    )

    assert first.package.package_name == "widget-core"
    assert first.package.crate_name == "widget_core"
    assert first.package.lib_path == "src/lib.rs"
    assert first.package.edition == "2021"
    assert first.package.rust_version == "1.80"
    assert first.package.dependency_names == ["serde"]
    assert first.package.example_paths == ["examples/basic.rs"]
    assert first.package.test_paths == ["tests/public.rs"]
    assert first.package.acquisition == "pinned_source"
    assert {(snippet.kind, snippet.function_name) for snippet in first.snippets} == {
        ("example_main", "main"),
        ("test_function", "root_roundtrip"),
        ("test_function", "public_api"),
    }
    assert first.canonical_hash() == second.canonical_hash()
    assert first.parser.startswith("tree-sitter@0.25.2+tree-sitter-rust@")
    assert pinned_rust_git_dependency(
        first.package,
        org_repo="fixture/widget-core",
        source_revision="a" * 40,
    ) == (f'widget-core = {{ git = "https://github.com/fixture/widget-core", rev = "{"a" * 40}" }}')


def test_public_api_resolves_modules_reexports_members_traits_and_docs(tmp_path):
    _fixture(tmp_path)

    surface = inspect_rust_public_api(
        tmp_path,
        org_repo="fixture/widget-core",
        source_revision="b" * 40,
    )
    symbols = _by_name(surface)

    assert {module.module_path for module in surface.modules} == {
        "widget_core",
        "widget_core::exposed",
        "widget_core::hidden",
        "widget_core::impls",
        "widget_core::mapped",
        "widget_core::tests",
    }
    mapped = next(module for module in surface.modules if module.module_path.endswith("::mapped"))
    assert mapped.source_path == "src/odd.path.rs"
    assert mapped.path_attribute == "odd.path.rs"
    assert mapped.public_from_parent is False

    root = symbols["widget_core::Root"]
    assert root.derives == ["Clone", "Debug"]
    assert root.rustdoc == "Root visitor type."
    assert root.implemented_traits == ["Readable"]
    assert "widget_core::Root.visible" in symbols
    assert "widget_core::Root.new" in symbols
    assert "widget_core::Root.read" in symbols
    assert "widget_core::Root.cross_file" in symbols
    assert "widget_core::Root.crate_only" not in symbols
    assert "widget_core::Root.crate_new" not in symbols
    assert "widget_core::Root.hidden_new" not in symbols

    readable = symbols["widget_core::Readable"]
    assert readable.supertraits == ["Send", "Sync"]
    assert "widget_core::Readable.read" in symbols

    renamed = symbols["widget_core::Renamed"]
    assert renamed.visibility_evidence == "public_reexport"
    assert renamed.derives == ["Clone", "Debug"]
    assert renamed.rustdoc == "A curated public type inside a private module."
    assert "widget_core::Renamed.value" in symbols
    assert "widget_core::hidden::Gadget" not in symbols
    assert not any("Restricted" in name for name in symbols)
    assert not any("ParentOnly" in name for name in symbols)
    assert not any("CratePathOnly" in name for name in symbols)

    assert "widget_core::PublicUnion" in symbols
    assert "widget_core::PublicUnion.whole" in symbols
    assert "widget_core::Mapped" in symbols
    assert "widget_core::Mapped.create" in symbols

    for name in (
        "widget_core::Mode",
        "widget_core::Mode.Fast",
        "widget_core::Mode.Safe",
        "widget_core::Identifier",
        "widget_core::DEFAULT_LIMIT",
        "widget_core::ENABLED",
        "widget_core::helper",
        "widget_core::exposed::Mode",
    ):
        assert name in symbols


def test_formats_require_directional_enum_or_explicit_io_method(tmp_path):
    _fixture(tmp_path)
    surface = inspect_rust_public_api(
        tmp_path,
        org_repo="fixture/widget-core",
        source_revision="f" * 40,
    )

    records = extract_rust_format_evidence(surface)
    values = {(item.format, item.direction, item.evidence_kind) for item in records}

    assert ("xlsx", "export", "format_enum_variant") in values
    assert ("xlsx", "import", "format_enum_variant") in values
    assert ("csv", "import", "format_enum_variant") in values
    assert ("html", "export", "explicit_io_method") in values
    assert ("csv", "import", "explicit_io_method") in values
    assert not any(item.format in {"vec", "bits", "unknown"} for item in records)


def test_multi_package_root_requires_one_deterministic_cargo_package(tmp_path):
    _write(tmp_path / "first/Cargo.toml", '[package]\nname="first"\nversion="1.0.0"\n')
    _write(tmp_path / "first/src/lib.rs", "pub struct First;\n")
    _write(tmp_path / "second/Cargo.toml", '[package]\nname="second"\nversion="1.0.0"\n')
    _write(tmp_path / "second/src/lib.rs", "pub struct Second;\n")

    with pytest.raises(ValueError, match="one deterministic package"):
        inspect_rust_public_api(
            tmp_path,
            org_repo="fixture/multi-root",
            source_revision="c" * 40,
        )
