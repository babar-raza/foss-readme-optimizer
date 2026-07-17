"""Live LLM connectivity check: GET {base}/models, resolve+validate the selected model.

LLM_MODEL explicit but not in the live list -> hard failure, never silently
substitute. LLM_MODEL unset -> default model, but only if it's actually live;
otherwise fail closed rather than guessing.
"""

import os
from dataclasses import dataclass, field

import requests

from readme_agent.env import DEFAULT_LLM_MODEL

# Model ids known (from the live gateway) to be non-text-chat -- excluded from
# the candidate list by keyword, not an exhaustive enum, since new models can
# appear over time.
_NON_CHAT_KEYWORDS = ("embedding", "-vl", "vl-", "diffusion", "vision")


@dataclass
class LlmCheckResult:
    ok: bool
    available_models: list[str] = field(default_factory=list)
    candidate_models: list[str] = field(default_factory=list)
    selected_model: str | None = None
    selection_reason: str | None = None
    error: str | None = None


def is_text_chat_candidate(model_id: str) -> bool:
    lowered = model_id.lower()
    return not any(kw in lowered for kw in _NON_CHAT_KEYWORDS)


def check_models(base_url: str, api_key: str | None, timeout: float = 15) -> LlmCheckResult:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        resp = requests.get(f"{base_url}/models", headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        return LlmCheckResult(ok=False, error=f"network error: {exc}")
    if resp.status_code != 200:
        return LlmCheckResult(ok=False, error=f"HTTP {resp.status_code} from GET {base_url}/models")

    try:
        data = resp.json()
    except ValueError as exc:
        return LlmCheckResult(ok=False, error=f"non-JSON response from /models: {exc}")

    available = [m.get("id") for m in data.get("data", []) if m.get("id")]
    candidates = [m for m in available if is_text_chat_candidate(m)]

    explicit_model = os.environ.get("LLM_MODEL")
    if explicit_model:
        if explicit_model not in available:
            return LlmCheckResult(
                ok=False,
                available_models=available,
                candidate_models=candidates,
                error=f"LLM_MODEL={explicit_model!r} is not in the live model list",
            )
        return LlmCheckResult(
            ok=True,
            available_models=available,
            candidate_models=candidates,
            selected_model=explicit_model,
            selection_reason="explicitly set via LLM_MODEL",
        )

    if DEFAULT_LLM_MODEL in available:
        return LlmCheckResult(
            ok=True,
            available_models=available,
            candidate_models=candidates,
            selected_model=DEFAULT_LLM_MODEL,
            selection_reason=f"default model {DEFAULT_LLM_MODEL!r}, confirmed live",
        )

    return LlmCheckResult(
        ok=False,
        available_models=available,
        candidate_models=candidates,
        error=(
            f"default model {DEFAULT_LLM_MODEL!r} is not in the live model list and "
            "LLM_MODEL is not set -- refusing to guess"
        ),
    )
