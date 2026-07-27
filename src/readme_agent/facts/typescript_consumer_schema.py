"""Typed isolated TypeScript package-consumer proof."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.ecosystems.typescript_api_schema import (
    TypeScriptConsumerExampleV1,
    TypeScriptPackageLayoutV1,
    TypeScriptPublicApiSurfaceV1,
)
from readme_agent.facts.isolated_execution_schema import IsolatedExecutionResultV1
from readme_agent.facts.typescript_toolchain import TypeScriptToolchainLockV1


class TypeScriptConsumerProofV1(BaseModel):
    """Compiler proof against one immutable built package artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str
    package: TypeScriptPackageLayoutV1
    example: TypeScriptConsumerExampleV1
    toolchain: TypeScriptToolchainLockV1
    surface: TypeScriptPublicApiSurfaceV1 | None = None
    built_artifact_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    verified_symbols: list[str]
    missing_symbols: list[str]
    diagnostics: list[str]
    isolated_execution: IsolatedExecutionResultV1
    accepted: bool

    @model_validator(mode="after")
    def accepted_requires_complete_compiler_proof(self) -> TypeScriptConsumerProofV1:
        if self.accepted and (
            self.surface is None
            or self.built_artifact_sha256 is None
            or set(self.verified_symbols) != set(self.example.required_symbols)
            or self.missing_symbols
            or self.diagnostics
            or not self.isolated_execution.truth_eligible
            or self.isolated_execution.return_code != 0
        ):
            raise ValueError(
                "accepted TypeScript proof requires a complete isolated compiler result"
            )
        return self
