"""Central env-var precedence resolution — the only place these are read from."""

import os

DEFAULT_LLM_BASE_URL = "https://llm.professionalize.com/v1"
DEFAULT_LLM_MODEL = "qwen3-next"
DEFAULT_LLM_TIMEOUT_SECONDS = 90
# Wave 8.6 (item I, `LLM-017`): the one embedding model this gateway hosts,
# characterized live (plans/investigations/llm-gateway-characterization.md
# L4) -- 4096-dim, showed real separation between a known same-template
# README pair (cosine 0.788) and unrelated pairs (0.45-0.55). Batch-only,
# deliberately never routed through JOB_MODEL_ROUTING/llm_model_for_job()
# (that table is for the per-run supervisor/generation jobs only).
DEFAULT_EMBEDDING_MODEL = "qwen3-embedding-8b"

# Per-job model routing (Decision 26(e), `LLM-016`): chosen from live-tested
# gateway behavior in plans/investigations/llm-gateway-characterization.md,
# not model-name folklore. A job not listed here falls back to
# DEFAULT_LLM_MODEL. gpt-oss is not routed to any freeform/structured job --
# its freeform-JSON validity is poor and inconsistent across reruns (LLM-018:
# a 0.4-0.8 swing across two single-session N=10 runs, not a stable "1/10"
# rate as originally reported), though it tool-calls reliably (5/5), which is
# a different mechanism this table does not cover.
JOB_MODEL_ROUTING: dict[str, str] = {
    "relationship_explained": "qwen3-next",
    # Wave 5's planner: qwen3-next is the routing-recommended model for
    # instruction-critical/planning steps (L2/L3/L6,
    # runtime-framework-evaluation.md) and the model Wave 1's spike proved
    # the loop against (agentic-loop-proof.md) -- explicit here rather than
    # relying on it happening to match DEFAULT_LLM_MODEL.
    "supervisor_planning": "qwen3-next",
    # Wave 8.6 (`ORC-003` reversal): the specialist-skip decision is a single,
    # narrow, forced-tool-call choice among an already-deterministically-
    # vetted menu -- same reliability profile as supervisor_planning, same
    # routing choice.
    "specialist_selection": "qwen3-next",
    # Wave 8.6 (`VER-006` reversal): both a single narrow forced-tool-call
    # judgment (prose quality) and a single narrow forced-tool-call choice
    # among an already-dispatcher-validated capability menu (repair
    # alternative selection) -- same reliability profile, same routing
    # choice as the two entries above.
    "prose_quality_check": "qwen3-next",
    "repair_capability_selection": "qwen3-next",
    # Wave 8.6 (comparison capability): a freeform structured-JSON analysis
    # call -- qwen3-next's 5/5 structured-output reliability (L3) is the
    # routing evidence here, same as relationship_explained's own choice.
    "presentation_standard_compliance": "qwen3-next",
    # Wave 8.6 (item H, vision integration): the only vision-capable model
    # this gateway hosts and has any structured-output evidence for --
    # flagged PARTIAL until a real image-bearing call is confirmed live
    # (see prompts/verification/visual_asset_accuracy.yaml's own notes).
    "visual_asset_accuracy": "Qwen2.5-VL-7B",
}


def gh_token() -> str | None:
    """GH_TOKEN (primary) > GITHUB_PAT (fallback). Used read-only by every
    caller except `capabilities/open_presentation_pr.py` (TC-08, the one
    `remote_write` capability this project registers) -- whether a write
    actually succeeds is a server-side permission check on the token itself
    (confirmed live, decision #46: `push=true`/`admin=true` on the 3
    confirmed pilots), never a client-side restriction this function could
    enforce by returning a different value for different callers."""
    if os.environ.get("README_AGENT_PRODUCTION_AUTH") == "github_app":
        # Production profiles receive the installation token through a
        # dedicated variable. Ambient GH_TOKEN/GITHUB_PAT values are ignored
        # so a missing App token fails closed instead of silently widening
        # authority through a PAT fallback.
        return os.environ.get("README_AGENT_GITHUB_APP_TOKEN") or None
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_PAT") or None


def github_run_id() -> str | None:
    """`GITHUB_RUN_ID` -- GitHub Actions' own per-workflow-run identity, automatically set on every
    real Actions runner, stable across a re-run of the *same* run (unlike `github.run_attempt`,
    which changes). `None` outside Actions (local CLI use) -- Wave 9.5's trigger-dedup mechanism
    (`state/trigger.py`) falls back to a manual/schedule identity in that case."""
    return os.environ.get("GITHUB_RUN_ID") or None


def github_event_name() -> str | None:
    """`GITHUB_EVENT_NAME` -- one of `workflow_dispatch`/`schedule`/`repository_dispatch`/... on a
    real Actions runner, `None` for local CLI use."""
    return os.environ.get("GITHUB_EVENT_NAME") or None


def github_run_attempt() -> int:
    value = os.environ.get("GITHUB_RUN_ATTEMPT")
    try:
        return max(int(value or "1"), 1)
    except ValueError:
        return 1


def github_sha() -> str | None:
    return os.environ.get("GITHUB_SHA") or None


def trigger_provider_event_id() -> str | None:
    return os.environ.get("README_AGENT_TRIGGER_ID") or None


def trigger_delivery_id() -> str | None:
    return os.environ.get("README_AGENT_DELIVERY_ID") or None


def trigger_schedule_window() -> str | None:
    return os.environ.get("README_AGENT_SCHEDULE_WINDOW") or None


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
    """Per-job routing table (`JOB_MODEL_ROUTING`) > `DEFAULT_LLM_MODEL`.

    Wave 13.4 (`LLM-020`): `LLM_MODEL` no longer overrides a routed job by
    default -- a stale/forgotten `LLM_MODEL` env var (local debugging
    leftover, or a value carried over from an unrelated CI job) would
    otherwise silently substitute a different model for a job whose route
    was carefully evidence-selected (see `JOB_MODEL_ROUTING`'s own
    docstring), including a job a golden-set run just disabled for cause --
    exactly the "silent model substitution" `state/schema.py::
    ModelRouteStatusV1`'s own docstring says a disabled route must never
    permit. Requires an explicit, separate opt-in --
    `READMEAGENT_DEBUG_MODEL_OVERRIDE=1` alongside `LLM_MODEL` -- for local
    debugging only; never set together in a real workflow run."""
    if os.environ.get("READMEAGENT_DEBUG_MODEL_OVERRIDE") == "1":
        override = os.environ.get("LLM_MODEL")
        if override:
            return override
    return JOB_MODEL_ROUTING.get(job, DEFAULT_LLM_MODEL)


def llm_timeout_seconds() -> float:
    raw = os.environ.get("LLM_TIMEOUT_SECONDS")
    return float(raw) if raw else DEFAULT_LLM_TIMEOUT_SECONDS


# SCL-004: cold `clone_baseline()` calls for the identical real repo measured
# 158s-1004s across separate attempts (GitHub server-side shallow-pack
# variance, not payload) -- 600s is evidence-informed headroom over the
# previous hardcoded 300s, not a guarantee it covers the full observed tail.
# Env-tunable for large real repos (e.g. Aspose.Words-FOSS-for-.NET, ~15.5k
# files) an operator knows will need more, mirroring llm_timeout_seconds().
DEFAULT_GIT_CLONE_TIMEOUT_SECONDS = 600


def git_clone_timeout_seconds() -> float:
    raw = os.environ.get("GIT_CLONE_TIMEOUT_SECONDS")
    return float(raw) if raw else DEFAULT_GIT_CLONE_TIMEOUT_SECONDS


def llm_embedding_model() -> str:
    return os.environ.get("LLM_EMBEDDING_MODEL") or DEFAULT_EMBEDDING_MODEL


def secret_values() -> list[str]:
    """All live secret-like values currently set, for redaction — read once."""
    names = [
        "GH_TOKEN",
        "GITHUB_PAT",
        "README_AGENT_GITHUB_APP_TOKEN",
        "LLM_API_KEY",
        "PROFESSIONALIZE_API_KEY",
        "GPT_OSS_API_KEY",
    ]
    return [v for name in names if (v := os.environ.get(name))]
