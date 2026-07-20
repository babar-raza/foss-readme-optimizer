"""Central env-var precedence resolution — the only place these are read from."""

import os

DEFAULT_LLM_BASE_URL = "https://llm.professionalize.com/v1"
DEFAULT_LLM_MODEL = "qwen3-next"
DEFAULT_LLM_TIMEOUT_SECONDS = 90

# Per-job model routing (Decision 26(e), `LLM-016`): chosen from live-tested
# gateway behavior in plans/investigations/llm-gateway-characterization.md,
# not model-name folklore. A job not listed here falls back to
# DEFAULT_LLM_MODEL. gpt-oss is not routed to any freeform/structured job --
# it scored 1/10 on freeform-JSON validity there, though it tool-calls
# reliably (5/5), which is a different mechanism this table does not cover.
JOB_MODEL_ROUTING: dict[str, str] = {
    "relationship_explained": "qwen3-next",
    # Wave 5's planner: qwen3-next is the routing-recommended model for
    # instruction-critical/planning steps (L2/L3/L6,
    # runtime-framework-evaluation.md) and the model Wave 1's spike proved
    # the loop against (agentic-loop-proof.md) -- explicit here rather than
    # relying on it happening to match DEFAULT_LLM_MODEL.
    "supervisor_planning": "qwen3-next",
}


def gh_token() -> str | None:
    """GH_TOKEN (primary) > GITHUB_PAT (fallback). Read-only usage only."""
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_PAT") or None


def llm_base_url() -> str:
    """LLM_BASE_URL > GPT_OSS_ENDPOINT > the documented professionalize default."""
    value = (
        os.environ.get("LLM_BASE_URL") or os.environ.get("GPT_OSS_ENDPOINT") or DEFAULT_LLM_BASE_URL
    )
    return value.rstrip("/")


def llm_api_key() -> str | None:
    """LLM_API_KEY > PROFESSIONALIZE_API_KEY > GPT_OSS_API_KEY."""
    return (
        os.environ.get("LLM_API_KEY")
        or os.environ.get("PROFESSIONALIZE_API_KEY")
        or os.environ.get("GPT_OSS_API_KEY")
        or None
    )


def llm_model() -> str:
    return os.environ.get("LLM_MODEL") or DEFAULT_LLM_MODEL


def llm_model_for_job(job: str) -> str:
    """LLM_MODEL env override > per-job routing table > DEFAULT_LLM_MODEL."""
    return os.environ.get("LLM_MODEL") or JOB_MODEL_ROUTING.get(job, DEFAULT_LLM_MODEL)


def llm_timeout_seconds() -> float:
    raw = os.environ.get("LLM_TIMEOUT_SECONDS")
    return float(raw) if raw else DEFAULT_LLM_TIMEOUT_SECONDS


def secret_values() -> list[str]:
    """All live secret-like values currently set, for redaction — read once."""
    names = [
        "GH_TOKEN",
        "GITHUB_PAT",
        "LLM_API_KEY",
        "PROFESSIONALIZE_API_KEY",
        "GPT_OSS_API_KEY",
    ]
    return [v for name in names if (v := os.environ.get(name))]
