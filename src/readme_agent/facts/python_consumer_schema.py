"""Typed installed-consumer proof for Python README symbols and examples."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from readme_agent.ecosystems.python_api_schema import (
    ConsumerExampleV1,
    PythonPackageLayoutV1,
)
from readme_agent.facts.isolated_execution_schema import IsolatedExecutionResultV1


class PythonConsumerProofV1(BaseModel):
    """Installed-package proof for a source revision and exact consumer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str
    package: PythonPackageLayoutV1
    example: ConsumerExampleV1
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
