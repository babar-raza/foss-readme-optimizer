"""Wave 8.6 (item H): the first real acceptance mechanism for `LLM-010`
("generated visual concepts MUST not depict unsupported... factual accuracy
review") -- checks a prepared/existing visual asset against real product
facts via a vision-capable structured-analysis call.

**Flagged, not assumed**: the gateway's "5/5 structured JSON" evidence for
`Qwen2.5-VL-7B` (`plans/investigations/tools/probe_llm_gateway.py`) is
TEXT-ONLY -- no image was ever actually sent in any live probe run to date.
There is zero existing evidence this gateway accepts a real multimodal
image payload. This capability's status must stay `PARTIAL` until a live
image-bearing call is actually run and confirmed (`GOVERNANCE.md` rule 10).

Reuses the existing `VISUAL_PREPARATION` domain (checks the same artifact
`prepare_visual_asset.py` already owns) -- advisory only, never gates
`commit_readme_write`, which stays exclusively `VER-001`'s territory."""

from readme_agent import paths
from readme_agent.capabilities import _visual_asset_ops
from readme_agent.capabilities.domains import VISUAL_PREPARATION
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.env import llm_api_key, llm_base_url, llm_model_for_job
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.llm.analysis_client import LiveAnalysisClient
from readme_agent.llm.analysis_prompts import build_visual_asset_accuracy_messages
from readme_agent.registry.loader import require_listed

CAPABILITY_ID = "review_visual_asset_accuracy"

_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Review visual asset accuracy",
    purpose="Read-only, advisory: checks a prepared or existing visual asset (banner/logo) "
    "against real product facts via a vision-capable structured-analysis call, flagging any "
    "depicted content (formats, workflows, integrations) the product does not actually "
    "support (LLM-010). Never gates commit_readme_write -- that stays VER-001's exclusive "
    "territory. STATUS: unproven against a real multimodal payload -- see module docstring.",
    category="visual_preparation",
    owner="readme_agent.capabilities.review_visual_asset_accuracy",
    execution_type="agentic_analysis",
    required_inputs={"org_repo": "string"},
    optional_inputs={"family": "string", "platform": "string"},
    produced_outputs={
        "asset_source": "string",
        "depicts_unsupported_content": "boolean",
        "concerns": "array",
        "verdict": "string",
        "rationale": "string",
    },
    preconditions=[
        "org_repo must be listed in data/products.json",
        "advisory only -- never blocks any write path",
        "UNPROVEN: no live evidence yet confirms the gateway accepts a real image payload for "
        "this model -- status stays PARTIAL until a live image-bearing call is confirmed",
    ],
    required_permissions=["read_only_network"],
    side_effect_class="read_only_network",
    allowed_domains=[VISUAL_PREPARATION],
    model_route="visual_asset_accuracy",
    tools_used=["llm.analysis_client.LiveAnalysisClient", "PIL.Image"],
    failure_modes=[
        "LLMError propagates as execution_error on any gateway failure",
        "SVG assets are never reviewed (not rasterizable by Pillow) -- returns a note, not an "
        "error",
    ],
    rollback_behavior="not applicable -- read-only, advisory-only",
    tests=["tests/unit/test_capabilities.py"],
    requirement_ids=["LLM-010"],
)


def execute(
    org_repo: str,
    family: str | None = None,
    platform: str | None = None,
    *,
    client=None,
) -> dict:
    entry = require_listed(org_repo)
    baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
    clone_baseline(entry, baseline_path)

    existing_path = _visual_asset_ops.find_existing_asset(baseline_path)
    if existing_path is not None:
        asset_source = "existing"
        image_bytes = existing_path.read_bytes()
        extension = existing_path.suffix.lower()
    else:
        asset_source = "generated_candidate"
        label = f"{family or entry.family} FOSS for {platform or entry.platform}"
        image_bytes = _visual_asset_ops.generate_candidate_banner(label)
        extension = ".png"

    if extension == ".svg":
        return {
            "asset_source": asset_source,
            "depicts_unsupported_content": False,
            "concerns": [],
            "verdict": "not_reviewed",
            "rationale": "SVG assets are not rasterizable by Pillow -- not reviewed this pass",
        }

    media_type = _MEDIA_TYPES.get(extension, "image/png")
    product_facts_excerpt = (
        f"family={family or entry.family}, platform={platform or entry.platform}, "
        f"ecosystem={entry.ecosystem}"
    )

    resolved_client = client or LiveAnalysisClient(
        llm_base_url(), llm_api_key(), llm_model_for_job("visual_asset_accuracy")
    )
    messages = build_visual_asset_accuracy_messages(
        org_repo, product_facts_excerpt, image_bytes, media_type
    )
    result = resolved_client.analyze(messages)

    return {
        "asset_source": asset_source,
        "depicts_unsupported_content": bool(result.parsed.get("depicts_unsupported_content")),
        "concerns": result.parsed.get("concerns", []),
        "verdict": result.parsed.get("verdict", "flag"),
        "rationale": result.parsed.get("rationale", ""),
    }
