"""Typed provenance for compiler-verified consumers outside Python, TypeScript, and Rust."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.facts.isolated_execution_schema import IsolatedExecutionResultV1

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CompiledConsumerProofV1(BaseModel):
    """Bind one exact consumer to the source paths and isolated compiler that accepted it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str
    ecosystem: Literal["java", "dotnet", "cpp", "go"]
    source_paths: list[str] = Field(min_length=1)
    selected_symbols: list[str] = Field(min_length=1)
    source_sha256: str
    example_sha256: str
    isolated_execution: IsolatedExecutionResultV1
    accepted: bool

    @model_validator(mode="after")
    def accepted_proof_requires_exact_isolated_success(self) -> CompiledConsumerProofV1:
        if not _SHA256_RE.fullmatch(self.source_sha256):
            raise ValueError("compiled consumer source_sha256 must be lowercase SHA-256")
        if not _SHA256_RE.fullmatch(self.example_sha256):
            raise ValueError("compiled consumer example_sha256 must be lowercase SHA-256")
        if self.source_paths != sorted(set(self.source_paths)):
            raise ValueError("compiled consumer source paths must be sorted and unique")
        if self.selected_symbols != sorted(set(self.selected_symbols)):
            raise ValueError("compiled consumer symbols must be sorted and unique")
        if self.accepted and (
            not self.isolated_execution.truth_eligible
            or self.isolated_execution.return_code != 0
            or self.isolated_execution.org_repo != self.org_repo
            or self.isolated_execution.source_revision != self.source_revision
        ):
            raise ValueError("accepted compiled consumer lacks exact isolated success")
        return self
