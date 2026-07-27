"""Typed outcome shared by local ecosystem example verifiers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.ecosystems.python_api_schema import PythonPackageLayoutV1
from readme_agent.facts.example_execution import ExampleExecutionResultV1
from readme_agent.facts.isolated_execution_schema import IsolatedExecutionResultV1


class LocalProductVerificationV1(BaseModel):
    """Bounded build and exact-example result for one immutable snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str
    ecosystem: str
    outcome: Literal[
        "SOURCE_BUILD_VERIFIED",
        "BLOCKED_TOOLCHAIN",
        "BUILD_FAILED",
        "ISOLATION_REQUIRED",
    ]
    detail: str
    build: ExampleExecutionResultV1
    example_compile: ExampleExecutionResultV1 | None = None
    isolated_execution: IsolatedExecutionResultV1 | None = None
    truth_eligible: bool = False
    verified_public_symbols: list[str] = Field(default_factory=list)
    public_api_sha256: str | None = None
    python_package: PythonPackageLayoutV1 | None = None

    @model_validator(mode="after")
    def verified_truth_requires_isolated_execution(self) -> LocalProductVerificationV1:
        if self.truth_eligible and (
            self.outcome != "SOURCE_BUILD_VERIFIED"
            or self.isolated_execution is None
            or not self.isolated_execution.truth_eligible
            or self.isolated_execution.return_code != 0
        ):
            raise ValueError(
                "truth-eligible product verification requires a successful isolated execution"
            )
        if self.verified_public_symbols and (
            not self.truth_eligible or self.public_api_sha256 is None or self.python_package is None
        ):
            raise ValueError(
                "verified public symbols require truth eligibility, API hash, and package layout"
            )
        return self
