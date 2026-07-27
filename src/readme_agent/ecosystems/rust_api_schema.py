"""Typed Rust package, syntax, public-API, and consumer-proof contracts."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RustSymbolKind = Literal[
    "struct",
    "union",
    "enum",
    "trait",
    "function",
    "type_alias",
    "constant",
    "static",
    "method",
    "field",
    "variant",
]
RustVisibilityEvidence = Literal["bare_pub", "public_reexport", "public_parent"]
RustFormatDirection = Literal["import", "export"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RustPackageLayoutV1(_StrictModel):
    """Cargo package/lib identity and source-consumer acquisition contract."""

    schema_version: Literal[1] = 1
    manifest_path: str
    package_root: str
    package_name: str
    crate_name: str
    version: str | None = None
    edition: str
    rust_version: str | None = None
    lib_path: str
    dependency_names: list[str]
    example_paths: list[str]
    test_paths: list[str]
    acquisition: Literal["pinned_source"]
    manifest_sha256: str
    source_sha256: str


class RustPublicSymbolV1(_StrictModel):
    """One syntax-resolved public Rust export or member."""

    schema_version: Literal[1] = 1
    qualified_name: str
    import_path: str
    name: str
    kind: RustSymbolKind
    visibility_evidence: RustVisibilityEvidence
    declaration_path: str
    source_line: int = Field(ge=1)
    parent_name: str | None = None
    type_text: str | None = None
    rustdoc: str | None = None
    derives: list[str] = Field(default_factory=list)
    supertraits: list[str] = Field(default_factory=list)
    implemented_traits: list[str] = Field(default_factory=list)
    syntax_resolved: Literal[True] = True


class RustModuleV1(_StrictModel):
    """One crate module reached through Rust module declarations."""

    schema_version: Literal[1] = 1
    module_path: str
    source_path: str
    public_from_parent: bool
    path_attribute: str | None = None


class RustSnippetV1(_StrictModel):
    """One syntax-valid repository-authored Rust example or test function."""

    schema_version: Literal[1] = 1
    kind: Literal["example_main", "test_function"]
    function_name: str
    source_path: str
    source_line: int = Field(ge=1)
    code: str
    syntax_resolved: Literal[True] = True


class RustPublicApiSurfaceV1(_StrictModel):
    """Reachability-aware public API for one immutable Rust crate."""

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str
    package: RustPackageLayoutV1
    modules: list[RustModuleV1]
    symbols: list[RustPublicSymbolV1]
    snippets: list[RustSnippetV1]
    parser: str
    source_sha256: str

    def canonical_hash(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RustConsumerExampleV1(_StrictModel):
    """Exact Cargo example target and public symbols it must exercise."""

    schema_version: Literal[1] = 1
    code: str = Field(min_length=1)
    required_symbols: list[str] = Field(min_length=1)


class RustFormatEvidenceV1(_StrictModel):
    """One directionally justified Rust format capability."""

    schema_version: Literal[1] = 1
    format: str = Field(min_length=1)
    direction: RustFormatDirection
    evidence_kind: Literal["format_enum_variant", "explicit_io_method"]
    qualified_symbol: str
    declaration_path: str
    source_line: int = Field(ge=1)
