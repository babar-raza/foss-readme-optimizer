"""Typed Python package-layout, public-API, and consumer-proof contracts."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PythonSymbolKind = Literal[
    "module",
    "class",
    "function",
    "method",
    "property",
    "enum",
    "enum_member",
    "typed_field",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PythonPackageLayoutV1(_StrictModel):
    """Distributed Python package roots and the preferred consumer import."""

    schema_version: Literal[1] = 1
    manifest_path: str
    distribution_name: str
    version: str | None = None
    requires_python: str | None = None
    source_root: str
    package_paths: list[str] = Field(min_length=1)
    canonical_import: str
    namespace_packages: list[str] = Field(default_factory=list)
    source_sha256: str


class PublicSymbolV1(_StrictModel):
    """One statically visible Python symbol with exact import provenance."""

    schema_version: Literal[1] = 1
    qualified_name: str
    import_module: str
    name: str
    kind: PythonSymbolKind
    source_path: str
    source_line: int = Field(ge=1)
    decorators: list[str] = Field(default_factory=list)
    annotation: str | None = None
    writable: bool | None = None
    reexported_from: str | None = None
    public_by: Literal["name", "__all__", "reexport"]
    import_verified: bool = False


class PublicApiSurfaceV1(_StrictModel):
    """Static source surface; import verification is additive and explicit."""

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str
    package: PythonPackageLayoutV1
    symbols: list[PublicSymbolV1]
    unresolved_reexports: list[str] = Field(default_factory=list)
    source_sha256: str

    def canonical_hash(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ConsumerExampleV1(_StrictModel):
    """Exact Python example and public symbols that it must import and use."""

    schema_version: Literal[1] = 1
    code: str = Field(min_length=1)
    required_symbols: list[str] = Field(min_length=1)
