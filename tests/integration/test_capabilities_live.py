"""Live proof that the real capability registry + dispatcher work end to end
against the real llm.professionalize.com gateway and a real allow-listed
pilot repository -- the production-code equivalent of Wave 1's spike
(plans/investigations/tools/prove_agentic_loop.py), proving the promotion
from spike to src/readme_agent/capabilities/ didn't lose the live-proven
behavior. Real network, real secrets, read-only throughout."""

import pytest
import requests

from readme_agent import env
from readme_agent.capabilities import dispatcher, registry

MODEL = "qwen3-next"  # routing-recommended model, see llm-gateway-characterization.md L2/L3/L6
ORG_REPO = "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java"  # allow-listed, mode: dry_run pilot


def _plan_one_tool_call(model: str, instruction: str, tool_schema: dict) -> dict:
    """Minimal live planning call -- test-only transport glue, not a new
    production client (that's Wave 5's supervisor territory). Offers exactly
    one tool so the live model's choice is deterministic to check."""
    base = env.llm_base_url().rstrip("/")
    headers = {"Authorization": f"Bearer {env.llm_api_key()}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": instruction}],
        "tools": [tool_schema],
        "tool_choice": "auto",
        "temperature": 0.0,
        "max_tokens": 200,
    }
    resp = requests.post(f"{base}/chat/completions", headers=headers, json=payload, timeout=90)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]


def _dispatch_live(capability_id: str, instruction: str, allowed_permissions: set[str]):
    tool_schema = registry.get(capability_id).to_tool_schema()
    message = _plan_one_tool_call(MODEL, instruction, tool_schema)
    tool_calls = message.get("tool_calls") or []
    assert tool_calls, f"model did not return a tool call for {capability_id!r}: {message}"
    return dispatcher.dispatch_tool_call(tool_calls[0], allowed_permissions=allowed_permissions)


@pytest.mark.live
def test_live_tool_call_dispatches_through_the_real_registry():
    result = _dispatch_live(
        "inspect_repository",
        f"Inspect the repository {ORG_REPO} using the available tool.",
        allowed_permissions={"read_only_local", "read_only_network"},
    )

    assert result.outcome == "executed"
    assert result.error is None
    assert result.result["org_repo"] == ORG_REPO
    assert result.result["has_readme"] is True


@pytest.mark.live
def test_live_detect_readme_gaps_dispatches_through_the_real_registry():
    result = _dispatch_live(
        "detect_readme_gaps",
        f"Check the README of {ORG_REPO} for presentation gaps using the available tool.",
        allowed_permissions={"read_only_local", "read_only_network"},
    )

    assert result.outcome == "executed"
    assert result.error is None
    assert isinstance(result.result["total_gaps"], int)


@pytest.mark.live
def test_live_check_install_path_dispatches_through_the_real_registry():
    result = _dispatch_live(
        "check_install_path",
        f"Check whether {ORG_REPO} resolves against its package registry using the tool.",
        allowed_permissions={"read_only_local", "read_only_network"},
    )

    assert result.outcome == "executed"
    assert result.error is None
    assert "install_path_resolved" in result.result


@pytest.mark.live
def test_live_profile_repository_dispatches_through_the_real_registry():
    """Wave 3: proves the real profile_repository capability -- not a
    synthetic fixture -- against a real repository through the real
    dispatcher. Targets the same enabled Java pilot as the other live tests
    (decision #4's hard allow-list applies unconditionally; the newly-ported
    Python/Go/.NET/TypeScript/C++ parsers stay proven-by-synthetic-fixture
    only, since no non-Java registry entry is enabled -- an honest, stated
    limitation, not a silently skipped check)."""
    result = _dispatch_live(
        "profile_repository",
        f"Profile the repository {ORG_REPO} using the available tool.",
        allowed_permissions={"read_only_local", "read_only_network"},
    )

    assert result.outcome == "executed"
    assert result.error is None
    assert result.result["org_repo"] == ORG_REPO
    ecosystems = {d["ecosystem"] for d in result.result["detected_ecosystems"]}
    assert "java" in ecosystems
