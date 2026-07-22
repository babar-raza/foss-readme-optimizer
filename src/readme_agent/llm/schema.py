"""Strict response contract. The LLM is asked for the relationship-explanation
paragraph only -- everything else (links, license line, resources section) is
already known from policy config and rendered deterministically.
"""

from pydantic import BaseModel, Field


class LLMClaims(BaseModel):
    license_name: str | None = None
    commercial_link_url: str | None = None


class LLMBlockResponse(BaseModel):
    relationship_paragraph: str
    talking_points_covered: list[str] = Field(default_factory=list)
    claims: LLMClaims = Field(default_factory=LLMClaims)


class Usage(BaseModel):
    """AGT-008/Wave 8.5: the gateway's own reported token accounting, when
    present -- both fields are optional since not every response includes
    `usage` (confirmed: this project's own prior evidence never read it).
    Consumers must never assume either field is populated."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LLMResponseMeta(BaseModel):
    """Best-effort drift-observability signal. Empirically confirmed (live
    probe, 2026-07-17): the gateway echoes back the requested `model` string
    verbatim -- there is no separate model-version/checkpoint identifier.
    `id` and `created` are the best available per-request signals."""

    request_id: str | None = None
    created: int | None = None
    model: str | None = None
    usage: Usage | None = None
