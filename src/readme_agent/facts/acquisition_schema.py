"""Typed registry-or-source acquisition decisions for product truth."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.ecosystems.registry_request import registry_request_url

AcquisitionOutcome = Literal[
    "REGISTRY_VERIFIED",
    "SOURCE_BUILD_VERIFIED",
    "NOT_PUBLISHED",
    "BLOCKED_NETWORK",
    "BLOCKED_LOCAL_VERIFICATION",
    "BLOCKED_TOOLCHAIN",
    "BUILD_FAILED",
    "ISOLATION_REQUIRED",
    "CAPABILITY_GAP",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RegistryReceiptV1(_StrictModel):
    """One exact authoritative-registry response, including negative 404 truth."""

    schema_version: Literal[1] = 1
    resolver_ecosystem: str = Field(min_length=1)
    registry_label: str = Field(min_length=1)
    coordinate: dict[str, str] = Field(min_length=1)
    request_url: str = Field(min_length=1)
    status_code: int = Field(ge=100, le=599)
    response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retrieved_at: datetime
    found: bool
    detail: str = Field(min_length=1)

    @model_validator(mode="after")
    def status_matches_found(self) -> RegistryReceiptV1:
        if self.found != (200 <= self.status_code < 300):
            raise ValueError("registry receipt found flag must match its HTTP status")
        expected_url = registry_request_url(self.resolver_ecosystem, self.coordinate)
        if expected_url is None or self.request_url != expected_url:
            raise ValueError("registry receipt URL must match its exact coordinate")
        return self


class SourceBuildReceiptV1(_StrictModel):
    """Revision- and executor-bound proof for an unpublished source package."""

    schema_version: Literal[1] = 1
    org_repo: str = Field(pattern=r"^[^/]+/[^/]+$")
    source_revision: str = Field(min_length=1)
    argv: list[str] = Field(min_length=1)
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    immutable_image: str = Field(min_length=1)
    network_mode: Literal["none"] = "none"
    dependency_pins: list[str] = Field(min_length=2)
    cleanup_complete: Literal[True] = True
    return_code: Literal[0] = 0
    truth_eligible: Literal[True] = True


class AcquisitionDecisionV1(_StrictModel):
    """The single selected acquisition path for one immutable repository revision."""

    schema_version: Literal[1] = 1
    org_repo: str = Field(pattern=r"^[^/]+/[^/]+$")
    source_revision: str = Field(min_length=1)
    ecosystem: str = Field(min_length=1)
    method: str = Field(min_length=1)
    outcome: AcquisitionOutcome
    detail: str = Field(min_length=1)
    coordinate: dict[str, str] | None = None
    registry_receipt: RegistryReceiptV1 | None = None
    source_build_receipt: SourceBuildReceiptV1 | None = None
    truth_eligible: bool

    @model_validator(mode="after")
    def selected_path_has_complete_proof(self) -> AcquisitionDecisionV1:
        if self.outcome == "REGISTRY_VERIFIED":
            if (
                not self.truth_eligible
                or self.registry_receipt is None
                or not self.registry_receipt.found
                or self.coordinate != self.registry_receipt.coordinate
                or self.source_build_receipt is not None
            ):
                raise ValueError("registry-verified acquisition requires one matching 2xx receipt")
        elif self.outcome == "SOURCE_BUILD_VERIFIED":
            registry_disproves_publication = (
                self.registry_receipt is not None and not self.registry_receipt.found
            )
            registry_not_applicable = self.registry_receipt is None and self.coordinate is None
            if (
                not self.truth_eligible
                or self.source_build_receipt is None
                or self.source_build_receipt.org_repo != self.org_repo
                or self.source_build_receipt.source_revision != self.source_revision
                or not (registry_disproves_publication or registry_not_applicable)
            ):
                raise ValueError(
                    "source-build acquisition requires isolated proof and no published coordinate"
                )
        elif self.truth_eligible or self.source_build_receipt is not None:
            raise ValueError("blocked acquisition cannot retain truth-eligible source-build proof")
        return self
