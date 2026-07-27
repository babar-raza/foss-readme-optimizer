"""Typed external-consumer proof for a source-pinned Rust crate."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from readme_agent.ecosystems.rust_api_schema import (
    RustConsumerExampleV1,
    RustPackageLayoutV1,
    RustPublicApiSurfaceV1,
)
from readme_agent.facts.isolated_execution_schema import IsolatedExecutionResultV1
from readme_agent.facts.rust_dependency_schema import RustDependencyAcquisitionV1


class RustConsumerProofV1(BaseModel):
    """Locked offline Cargo check of an exact external consumer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str
    package: RustPackageLayoutV1
    surface: RustPublicApiSurfaceV1
    example: RustConsumerExampleV1
    acquisition: RustDependencyAcquisitionV1
    verified_symbols: list[str]
    missing_symbols: list[str]
    diagnostics: list[str]
    isolated_execution: IsolatedExecutionResultV1
    accepted: bool

    @model_validator(mode="after")
    def accepted_requires_locked_public_consumer(self) -> RustConsumerProofV1:
        if self.accepted and (
            set(self.verified_symbols) != set(self.example.required_symbols)
            or self.missing_symbols
            or self.diagnostics
            or not self.isolated_execution.truth_eligible
            or self.isolated_execution.return_code != 0
            or self.isolated_execution.policy.network_mode != "none"
            or not self.acquisition.cleanup_complete
        ):
            raise ValueError("accepted Rust proof requires locked offline public-consumer success")
        return self
