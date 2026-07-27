"""Typed TypeScript package, export, public-API, and consumer-proof contracts."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TypeScriptSymbolKind = Literal[
    "class",
    "interface",
    "type_alias",
    "enum",
    "function",
    "variable",
    "method",
    "property",
    "enum_member",
]
TypeScriptDeclaredBy = Literal["exports", "types", "main", "module", "legacy_index"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TypeScriptEntryPointV1(_StrictModel):
    """One declared or legacy package import mapped to its consumer files."""

    schema_version: Literal[1] = 1
    import_specifier: str
    subpath: str
    declaration_path: str | None = None
    runtime_path: str | None = None
    source_entry_path: str | None = None
    declared_by: TypeScriptDeclaredBy
    conditions: list[str] = Field(default_factory=list)
    declaration_preferred: bool = False


class TypeScriptPackageLayoutV1(_StrictModel):
    """Package metadata and deterministic consumer entry-point candidates."""

    schema_version: Literal[1] = 1
    manifest_path: str
    package_name: str
    version: str | None = None
    build_config_path: str | None = None
    source_root: str
    output_root: str
    entry_points: list[TypeScriptEntryPointV1] = Field(default_factory=list)
    canonical_import: str | None = None
    exports_restrict_subpaths: bool
    unsupported_export_patterns: list[str] = Field(default_factory=list)
    source_sha256: str


class TypeScriptPublicSymbolV1(_StrictModel):
    """One compiler-resolved export or public member."""

    schema_version: Literal[1] = 1
    qualified_name: str
    export_name: str
    member_name: str | None = None
    kind: TypeScriptSymbolKind
    declaration_path: str
    source_line: int = Field(ge=1)
    type_text: str | None = None
    readonly: bool = False
    compiler_resolved: bool = True


class TypeScriptPublicApiSurfaceV1(_StrictModel):
    """Compiler-derived exports for one exact built package import."""

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str
    package: TypeScriptPackageLayoutV1
    resolved_import: str
    resolved_declaration_path: str
    symbols: list[TypeScriptPublicSymbolV1]
    compiler_version: str
    source_sha256: str

    def canonical_hash(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TypeScriptConsumerExampleV1(_StrictModel):
    """Exact TypeScript example and compiler-resolved symbols it must use."""

    schema_version: Literal[1] = 1
    code: str = Field(min_length=1)
    import_specifier: str
    required_symbols: list[str] = Field(min_length=1)
