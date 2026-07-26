"""Typed package-root role inventory and stable path/hash behavior."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.profile.schema import PackageRoot, RepositoryProfile

PackageRootRole = Literal[
    "product",
    "test",
    "sample",
    "converter",
    "generator",
    "benchmark",
    "build_tool",
    "unknown",
]
RootSelectionState = Literal["selected", "ambiguous", "missing"]


def portable_repository_path(value: str) -> str:
    """Normalize repository paths independently of the operator OS."""

    return value.replace("\\", "/").strip("/")


def filesystem_repository_path(value: str) -> Path:
    """Convert either Git or Windows separators into a local relative Path."""

    return Path(*portable_repository_path(value).split("/"))


class PackageRootRoleV1(BaseModel):
    """One source-revision-bound role decision for a detected package root."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    ecosystem: str
    manifest_path: str
    role: PackageRootRole
    confidence: float = Field(ge=0.0, le=1.0)
    parsed_identity: dict[str, str] = Field(default_factory=dict)
    referenced_manifest_paths: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(min_length=1)


class PackageRootRoleInventoryV1(BaseModel):
    """Complete role inventory plus the sole visitor-fact product-root binding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str | None
    selection_state: RootSelectionState
    selected_product_manifest_path: str | None
    selection_rationale: list[str] = Field(min_length=1)
    roots: list[PackageRootRoleV1]

    def canonical_hash(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def selected_package_root(self, profile: RepositoryProfile) -> PackageRoot | None:
        selected = self.selected_product_manifest_path
        if selected is None:
            return None
        by_manifest = {
            portable_repository_path(package_root.manifest_path): package_root
            for package_root in profile.package_roots
        }
        return by_manifest.get(selected)
