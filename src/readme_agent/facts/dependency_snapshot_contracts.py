"""Typed dependency-snapshot contracts shared by ecosystem collectors."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

DependencyRole = Literal["runtime", "build", "dev"]


class DependencyEntryV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    ecosystem: str
    version_constraint: str | None
    category: str
    dev_only: bool
    role: DependencyRole


class DependencySnapshotV1(BaseModel):
    """Structured dependency evidence with explicit applicability and parse failures."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ecosystem: str
    applicable: bool
    not_applicable_reason: str | None = None
    source_manifest_path: str | None = None
    parse_errors: tuple[str, ...] = ()
    required: tuple[DependencyEntryV1, ...] = ()
    optional: tuple[DependencyEntryV1, ...] = ()
    native_system: tuple[DependencyEntryV1, ...] = ()
    proprietary_runtime: tuple[DependencyEntryV1, ...] = ()
    development: tuple[DependencyEntryV1, ...] = ()


__all__ = ["DependencyEntryV1", "DependencyRole", "DependencySnapshotV1"]
