"""Wraps `orchestrator.prepare_readme_candidate()` -- the read-only half of
the Wave 7 `EFF-001` fix (decision #26 addendum). Computes what the README
*should* look like (skip decision, conditional LLM call, render) without
writing anything. `commit_readme_write` (the paired `gated_effector`,
registered only once its domain exists -- Wave 7g) performs the one real
write from this capability's `final_text`/`facts_hash` output. Unscoped, like
every other read-only capability -- matches `inspect_repository`'s own
classification despite also cloning a baseline repo (this project's existing
convention: `read_only_local` covers "reads network sources but never
mutates tracked/durable state," `read_only_network` is reserved for live
external verification lookups like `check_install_path`'s Maven resolution).

No live `state_backend` object here (this capability must stay stateless,
decision #26(b)) -- but it DOES accept the same durable-skip signal as plain
values (`prior_facts_hash`/`prior_content_fingerprint`/`prior_status`), a
fix added by independent production-reliability review (2026-07-20). The
first draft of this module assumed `readme_presentation`'s own classify-
first step would make this unnecessary -- that assumption was checked
against the actual code and found wrong: unlike every other Wave 7
specialist, `readme_presentation` has no classify node before render (its
graph is `render -> commit -> record`, not `classify -> record`), so
nothing upstream of this capability ever short-circuited a fresh-work-clone
render. On an ephemeral CI runner (the normal case, `RUN-001`) that meant a
real LLM call on every single run with any upstream commit at all, not just
one touching tracked content -- `orchestrator.py`'s own CLI path has had the
matching fix since decision #38; this capability now can too, when its
caller (`specialists/readme_presentation.py`) supplies its own domain's
prior accepted state as plain arguments.

`llm_mode`/`fixture_response_path`/`prior_facts_hash`/
`prior_content_fingerprint`/`prior_status` are accepted but deliberately NOT
declared in `required_inputs`/`optional_inputs` -- they must never appear in
the tool schema offered to a planner (an LLM has no business choosing
fixture mode or asserting its own prior-acceptance facts); they exist only
for deterministic test/wiring callers, exactly as `orchestrator.
generate_repo()` already has `llm_mode`/`fixture_response_path`."""

from pathlib import Path

from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.orchestrator import prepare_readme_candidate

CAPABILITY_ID = "render_readme_candidate"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Render README candidate",
    purpose="Read-only: compute the skip-vs-render decision, run the one existing LLM job "
    "if relationship_explained is a real gap, and render the resulting README candidate -- "
    "no filesystem write. Pairs with the gated_effector commit_readme_write, which performs "
    "the actual write from this capability's facts_hash/final_text output.",
    category="readme_presentation",
    owner="readme_agent.orchestrator",
    execution_type="deterministic_tool",
    required_inputs={"org_repo": "string"},
    optional_inputs={"force_regenerate": "boolean"},
    produced_outputs={
        "facts_hash": "string",
        "fresh_fingerprint": "string",
        "skip_regeneration": "boolean",
        "needs_write": "boolean",
        "final_text": "string",
        "status": "string",
        "llm_called": "boolean",
        "llm_calls": "array",
    },
    preconditions=["org_repo must be listed in data/products.json with a non-disabled mode"],
    required_permissions=["read_only_local"],
    side_effect_class="read_only_local",
    tools_used=["orchestrator.prepare_readme_candidate"],
    failure_modes=["NotAllowlistedError if org_repo is not permitted with an enabled mode"],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py"],
)


def execute(
    org_repo: str,
    force_regenerate: bool = False,
    llm_mode: str = "live",
    fixture_response_path: str | None = None,
    prior_facts_hash: str | None = None,
    prior_content_fingerprint: str | None = None,
    prior_status: str | None = None,
) -> dict:
    candidate = prepare_readme_candidate(
        org_repo,
        force_regenerate=force_regenerate,
        llm_mode=llm_mode,
        fixture_response_path=Path(fixture_response_path) if fixture_response_path else None,
        prior_facts_hash=prior_facts_hash,
        prior_content_fingerprint=prior_content_fingerprint,
        prior_status=prior_status,
    )
    return {
        "facts_hash": candidate.facts_hash,
        "fresh_fingerprint": candidate.fresh_fingerprint,
        "skip_regeneration": candidate.skip_regeneration,
        "needs_write": candidate.final_text != candidate.original_text,
        "final_text": candidate.final_text,
        "status": candidate.status,
        "llm_called": candidate.llm_called,
        "llm_calls": candidate.llm_calls,
    }
