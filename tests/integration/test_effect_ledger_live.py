"""Live proof of `capabilities/effect_ledger.py`'s two-phase apply against
the real `GitStateBackend` (real git push/fetch to this project's own
remote, never a target repo) -- what `test_effect_ledger.py`'s offline
`FakeStateBackend` suite can't cover: the actual git read/write mechanics
underneath the pending/applied record. Uses the same synthetic-effector
idiom as the offline suite (`EFF-002`'s own written acceptance criterion:
"for a test effector"), not a real registered capability -- none exists yet
(Wave 7's job).

CAUTION: run only with explicit confirmation -- real `git push` to whatever
`origin` remote the invoking working directory has configured. See
`tests/integration/test_state_git_backend_live.py`'s docstring for the
local push-credential prerequisite (`OPS-009`) this file shares.
"""

import uuid
from types import SimpleNamespace

import pytest

from readme_agent.capabilities import registry
from readme_agent.capabilities.effect_ledger import dispatch_gated_effect
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.gitsafety._git import run_git
from readme_agent.state.git_backend import (
    LOCK_REF_PREFIX,
    STATE_REF_PREFIX,
    GitStateBackend,
    _ref_key,
)


def _disposable_org_repo() -> str:
    return f"readme-agent-effect-ledger-live-test/{uuid.uuid4().hex[:12]}"


def _delete_refs(*org_repos: str) -> None:
    for org_repo in org_repos:
        key = _ref_key(org_repo)
        run_git(["push", "origin", f":{STATE_REF_PREFIX}/{key}"])
        run_git(["push", "origin", f":{LOCK_REF_PREFIX}/{key}"])


def _effector_manifest(**overrides) -> CapabilityManifest:
    defaults = dict(
        capability_id="mutate_thing",
        version="1",
        name="Mutate thing",
        purpose="live test effector",
        category="test",
        owner="tests",
        execution_type="gated_effector",
        side_effect_class="local_write",
        required_inputs={"org_repo": "string"},
        idempotency_inputs=["org_repo"],
        retry_policy="idempotent_only",
    )
    return CapabilityManifest(**{**defaults, **overrides})


def _register(monkeypatch, manifest: CapabilityManifest, execute):
    module = SimpleNamespace(MANIFEST=manifest, execute=execute)
    manifests, executors, reconciliation_checks, prechecks = registry._build((module,))
    monkeypatch.setattr(registry, "_MANIFESTS", manifests)
    monkeypatch.setattr(registry, "_EXECUTORS", executors)
    monkeypatch.setattr(registry, "_RECONCILIATION_CHECKS", reconciliation_checks)
    monkeypatch.setattr(registry, "_PRECHECKS", prechecks)


def _tool_call(capability_id: str, arguments: dict) -> dict:
    import json

    return {"function": {"name": capability_id, "arguments": json.dumps(arguments)}}


@pytest.mark.live
def test_pending_then_applied_against_the_real_backend(monkeypatch):
    counter = {"n": 0}

    def execute(org_repo):
        counter["n"] += 1
        return {"count": counter["n"]}

    _register(monkeypatch, _effector_manifest(), execute)
    org_repo = _disposable_org_repo()
    backend = GitStateBackend()
    try:
        result = dispatch_gated_effect(
            _tool_call("mutate_thing", {"org_repo": org_repo}), {"local_write"}, backend, org_repo
        )
        assert result.outcome == "dispatched"
        assert result.dispatch.outcome == "executed"
        assert counter["n"] == 1

        state = backend.load(org_repo)
        assert state is not None
        assert state.capability_outputs[0].status == "applied"

        second = dispatch_gated_effect(
            _tool_call("mutate_thing", {"org_repo": org_repo}), {"local_write"}, backend, org_repo
        )
        assert second.outcome == "already_applied"
        assert counter["n"] == 1  # not re-executed, against a real durable record
    finally:
        _delete_refs(org_repo)


@pytest.mark.live
def test_crash_between_pending_and_applied_survives_a_fresh_backend_instance(monkeypatch):
    """The actual `RUN-001`-shaped proof: a *second, independent*
    `GitStateBackend()` instance (simulating a fresh runner with no
    in-memory state) must see the same `pending` record and refuse to
    blindly re-execute -- not just the same Python object across two calls."""
    counter = {"n": 0}

    def crashing_execute(org_repo):
        counter["n"] += 1
        raise RuntimeError("simulated crash after the real side effect landed")

    _register(monkeypatch, _effector_manifest(), crashing_execute)
    org_repo = _disposable_org_repo()
    first_backend = GitStateBackend()
    try:
        first = dispatch_gated_effect(
            _tool_call("mutate_thing", {"org_repo": org_repo}),
            {"local_write"},
            first_backend,
            org_repo,
        )
        assert first.dispatch.outcome == "execution_error"
        assert counter["n"] == 1

        fresh_backend = GitStateBackend()  # a genuinely separate instance
        second = dispatch_gated_effect(
            _tool_call("mutate_thing", {"org_repo": org_repo}),
            {"local_write"},
            fresh_backend,
            org_repo,
        )
        assert second.outcome == "blocked_pending_reconciliation"
        assert counter["n"] == 1  # not re-executed
    finally:
        _delete_refs(org_repo)
