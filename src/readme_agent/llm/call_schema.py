"""Typed redacted contracts for LLM call accounting."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CallDisposition = Literal["provider_call", "fixture", "cache_reuse"]
CallOutcome = Literal[
    "success",
    "http_error",
    "timeout",
    "connection_error",
    "cancelled",
    "response_invalid",
    "fixture",
    "cache_reuse",
]


class LlmCallRecordV1(BaseModel):
    """One provider attempt or explicitly non-provider fixture/cache event."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    call_id: str
    logical_call_id: str
    org_repo: str
    source_revision: str
    run_id: str
    campaign_id: str
    stage: str
    job: str
    prompt_id: str
    prompt_sha256: str | None = None
    provider: str
    model: str
    attempt: int = Field(ge=0)
    disposition: CallDisposition
    started_at: str
    finished_at: str
    latency_ms: int = Field(ge=0)
    outcome: CallOutcome
    http_status: int | None = None
    request_sha256: str
    response_sha256: str | None = None
    provider_request_id: str | None = None
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    cost: float | None = Field(default=None, ge=0)
    cost_currency: str | None = None
    cost_unavailable_reason: str | None = "pricing_not_configured"
    pricing_source: str | None = "unconfigured"
    pricing_version: str | None = "unconfigured"
    error_class: str | None = None

    @model_validator(mode="after")
    def _require_versioned_cost_disposition(self) -> LlmCallRecordV1:
        if self.disposition != "provider_call":
            return self
        if not self.pricing_source or not self.pricing_version:
            raise ValueError("provider-call pricing source and version are required")
        if self.cost is None and not self.cost_unavailable_reason:
            raise ValueError("provider-call null cost requires an unavailable reason")
        if self.cost is not None and not self.cost_currency:
            raise ValueError("provider-call cost requires a currency")
        return self


class LlmAccountingSummaryV1(BaseModel):
    """Reconciled unique-call totals suitable for run and README manifests."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["EXACT", "UNKNOWN_LEGACY"]
    provider_call_count: int | None = Field(default=None, ge=0)
    fixture_call_count: int | None = Field(default=None, ge=0)
    cache_reuse_count: int | None = Field(default=None, ge=0)
    call_ids: list[str] = Field(default_factory=list)
    calls_by_job: dict[str, int] = Field(default_factory=dict)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    ledger_path: str | None = None
    ledger_sha256: str | None = None
