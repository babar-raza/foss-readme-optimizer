"""Additive prose-quality check (Wave 8.6, `VER-006` reversal) -- layered
on top of the existing deterministic `verify_readme_candidate` gate, never
a replacement of it. Domain-scoped identically to that capability
(`allowed_domains=[INDEPENDENT_VERIFICATION]`); dispatched only after the
deterministic gate has already accepted a candidate (`specialists/readme_
presentation.py::_verify_node` short-circuits before reaching this on a
deterministic reject -- zero extra cost there, protecting `VER-003`'s "no
unnecessary work").

`client` is accepted but deliberately NOT declared in `required_inputs`/
`optional_inputs` -- never offered in the tool schema, exists only for
deterministic test/wiring callers, exactly as `render_readme_candidate.py`'s
own `llm_mode`/`fixture_response_path` convention already establishes.
"""

from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.env import llm_api_key, llm_base_url, llm_model_for_job
from readme_agent.llm.verifier_client import ForcedToolClient, LiveForcedToolClient
from readme_agent.verification.prose_quality import check_prose_quality

CAPABILITY_ID = "verify_prose_quality"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Verify prose quality",
    purpose="Read-only, additive check layered on top of the deterministic "
    "verify_readme_candidate gate: asks one narrow, forced-tool-call question about whether "
    "the one LLM-authored span reads as generic/repetitive/mechanically-inserted prose "
    "(RDM-020). Never trusted at face value -- the model's claim is corroborated against the "
    "actual reviewed text before it can affect anything; an uncorroborated claim is discarded.",
    category="independent_verification",
    owner="readme_agent.verification.prose_quality",
    execution_type="agentic_analysis",
    required_inputs={"org_repo": "string", "final_text": "string"},
    produced_outputs={
        "flagged": "boolean",
        "corroborated": "boolean",
        "quoted_span": "string",
        "reason": "string",
    },
    preconditions=[
        "final_text is the candidate the deterministic verify_readme_candidate gate has "
        "already accepted this turn -- this capability never re-checks facts/links/licensing"
    ],
    required_permissions=["read_only_network"],
    side_effect_class="read_only_network",
    allowed_domains=[INDEPENDENT_VERIFICATION],
    model_route="prose_quality_check",
    tools_used=["llm.verifier_client.LiveForcedToolClient"],
    failure_modes=[
        "LLMError propagates as a normal execution_error on any gateway failure -- never "
        "silently treated as accept or reject"
    ],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py", "tests/unit/test_verification_prose_quality.py"],
    requirement_ids=["RDM-020"],
)


def execute(
    org_repo: str,  # unused directly -- kept for dispatcher/schema consistency with every
    # other capability, which always receives its target repo
    final_text: str,
    *,
    client: ForcedToolClient | None = None,
) -> dict:
    resolved_client = client or LiveForcedToolClient(
        llm_base_url(), llm_api_key(), llm_model_for_job("prose_quality_check")
    )
    return check_prose_quality(final_text, resolved_client)
