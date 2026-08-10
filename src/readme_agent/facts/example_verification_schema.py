"""Typed outcome shared by local ecosystem example verifiers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.ecosystems.python_api_schema import PythonPackageLayoutV1
from readme_agent.ecosystems.rust_api_schema import (
    RustFormatEvidenceV1,
    RustPackageLayoutV1,
)
from readme_agent.ecosystems.typescript_api_schema import TypeScriptPackageLayoutV1
from readme_agent.facts.compiled_consumer_schema import CompiledConsumerProofV1
from readme_agent.facts.example_execution import ExampleExecutionResultV1
from readme_agent.facts.isolated_execution_schema import IsolatedExecutionResultV1
from readme_agent.facts.python_consumer_schema import PythonFixtureBindingV1


class LocalProductVerificationV1(BaseModel):
    """Bounded build and exact-example result for one immutable snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str
    ecosystem: str
    outcome: Literal[
        "SOURCE_BUILD_VERIFIED",
        "SOURCE_TREE_VERIFIED",
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
    input_fixture_bindings: list[PythonFixtureBindingV1] = Field(default_factory=list)
    public_api_sha256: str | None = None
    python_package: PythonPackageLayoutV1 | None = None
    typescript_package: TypeScriptPackageLayoutV1 | None = None
    rust_package: RustPackageLayoutV1 | None = None
    rust_formats: list[RustFormatEvidenceV1] = Field(default_factory=list)
    rust_source_dependency: str | None = None
    acquisition_dependency_pins: list[str] = Field(default_factory=list)
    python_execution_mode: Literal["installed_package", "source_tree"] | None = None
    python_source_install_failure: Literal["invalid_build_backend"] | None = None
    compiled_consumer: CompiledConsumerProofV1 | None = None

    def fact_projection(self) -> dict[str, object]:
        """Return the reproducible public-surface fields safe for ProductFactsV2."""

        return {
            "verified_public_symbols": self.verified_public_symbols,
            "input_fixture_bindings": [
                binding.model_dump(mode="json") for binding in self.input_fixture_bindings
            ],
            "public_api_sha256": self.public_api_sha256,
            "python_package": (
                self.python_package.model_dump(mode="json") if self.python_package else None
            ),
            "typescript_package": (
                self.typescript_package.model_dump(mode="json") if self.typescript_package else None
            ),
            "rust_package": (
                self.rust_package.model_dump(mode="json") if self.rust_package else None
            ),
            "rust_formats": [record.model_dump(mode="json") for record in self.rust_formats],
            "rust_source_dependency": self.rust_source_dependency,
            "acquisition_dependency_pins": self.acquisition_dependency_pins,
            "python_execution_mode": self.python_execution_mode,
            "python_source_install_failure": self.python_source_install_failure,
            "compiled_consumer": (
                self.compiled_consumer.model_dump(mode="json")
                if self.compiled_consumer is not None
                else None
            ),
        }

    @model_validator(mode="after")
    def verified_truth_requires_isolated_execution(self) -> LocalProductVerificationV1:
        if self.truth_eligible and (
            self.outcome not in {"SOURCE_BUILD_VERIFIED", "SOURCE_TREE_VERIFIED"}
            or self.isolated_execution is None
            or not self.isolated_execution.truth_eligible
            or self.isolated_execution.return_code != 0
        ):
            raise ValueError(
                "truth-eligible product verification requires a successful isolated execution"
            )
        if self.outcome == "SOURCE_TREE_VERIFIED" and (
            self.python_execution_mode != "source_tree"
            or self.python_source_install_failure is None
        ):
            raise ValueError("source-tree verification requires its typed install failure")
        if self.verified_public_symbols and (
            not self.truth_eligible
            or self.public_api_sha256 is None
            or (
                self.python_package is None
                and self.typescript_package is None
                and self.rust_package is None
                and self.compiled_consumer is None
            )
        ):
            raise ValueError(
                "verified public symbols require truth eligibility, API hash, and package layout"
            )
        return self
