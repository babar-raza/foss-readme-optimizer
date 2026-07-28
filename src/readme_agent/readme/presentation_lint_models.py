"""Typed exact-span findings for deterministic README presentation lint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PresentationLintSpanV1(_StrictModel):
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def _ordered(self) -> PresentationLintSpanV1:
        if self.end <= self.start:
            raise ValueError("presentation lint span must be non-empty and ordered")
        return self


class PresentationLintFindingV1(_StrictModel):
    finding_id: str = Field(pattern=r"^presentation\.[a-z0-9_]+\.[0-9a-f]{12}$")
    rule_id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    severity: Literal["critical", "warning"]
    message: str = Field(min_length=1)
    spans: list[PresentationLintSpanV1] = Field(min_length=1)


class PresentationLintResultV1(_StrictModel):
    schema_version: Literal[1] = 1
    valid: bool
    rules_run: list[str] = Field(min_length=1)
    findings: list[PresentationLintFindingV1] = Field(default_factory=list)

    @model_validator(mode="after")
    def _verdict_matches_findings(self) -> PresentationLintResultV1:
        expected = not any(finding.severity == "critical" for finding in self.findings)
        if self.valid != expected:
            raise ValueError("presentation lint verdict disagrees with critical findings")
        if self.rules_run != sorted(set(self.rules_run)):
            raise ValueError("presentation lint rules_run must be sorted and unique")
        return self
