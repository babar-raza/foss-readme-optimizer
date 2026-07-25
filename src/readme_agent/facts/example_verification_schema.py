"""Typed outcome shared by local ecosystem example verifiers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.example_execution import ExampleExecutionResultV1


class LocalProductVerificationV1(BaseModel):
    """Bounded build and exact-example result for one immutable snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str
    ecosystem: str
    outcome: Literal["SOURCE_BUILD_VERIFIED", "BLOCKED_TOOLCHAIN", "BUILD_FAILED"]
    detail: str
    build: ExampleExecutionResultV1
    example_compile: ExampleExecutionResultV1 | None = None
