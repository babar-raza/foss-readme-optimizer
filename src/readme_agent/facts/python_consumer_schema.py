"""Typed installed-consumer proof for Python README symbols and examples."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.ecosystems.python_api_schema import (
    ConsumerExampleV1,
    PythonPackageLayoutV1,
)
from readme_agent.facts.isolated_execution_schema import IsolatedExecutionResultV1


class PythonFixtureBindingV1(BaseModel):
    """One repository-owned input fixture staged under the README's visitor-facing name."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_path: str
    target_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class PythonConsumerProofV1(BaseModel):
    """Installed-package proof for a source revision and exact consumer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str
    package: PythonPackageLayoutV1
    example: ConsumerExampleV1
    fixture_bindings: list[PythonFixtureBindingV1] = Field(default_factory=list)
    verified_symbols: list[str]
    isolated_execution: IsolatedExecutionResultV1
    accepted: bool

    @model_validator(mode="after")
    def accepted_requires_complete_isolated_proof(self) -> PythonConsumerProofV1:
        if self.accepted and (
            set(self.verified_symbols) != set(self.example.required_symbols)
            or not self.isolated_execution.truth_eligible
            or self.isolated_execution.return_code != 0
        ):
            raise ValueError("accepted Python proof requires every symbol and isolated success")
        return self
