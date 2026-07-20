"""`EFF-002`/`EFF-003`: the two-phase effect ledger, proven against a
synthetic effector with a real, observable side-effect counter -- the same
`SimpleNamespace(MANIFEST=..., execute=...)` idiom
`TestRegistryEff001RegistrationGate` already established, matching
`EFF-002`'s own written acceptance criterion ("for a test effector").
`GitStateBackend`'s live counterpart is proven separately,
`@pytest.mark.live` (`tests/integration/test_effect_ledger_live.py`)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from readme_agent.capabilities import registry
from readme_agent.capabilities.effect_ledger import (
    dispatch_gated_effect,
    idempotency_key,
    retry_is_safe,
)
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.schema import RunStateV1

ORG_REPO = "acme/widget"


class _Counter:
    def __init__(self):
        self.applied = 0


class FakeStateBackend:
    def __init__(self):
        self._states: dict[str, RunStateV1] = {}
        self._locks: dict[str, tuple[str, datetime]] = {}

    def load(self, org_repo):
        return self._states.get(org_repo)

    def save(self, org_repo, state, expected_version):
        current = self._states.get(org_repo)
        cv = current.state_version if current else None
        if expected_version != cv:
            return SaveResult(outcome="stale", new_version=cv)
        nv = (cv or 0) + 1
        self._states[org_repo] = state.model_copy(update={"state_version": nv})
        return SaveResult(outcome="saved", new_version=nv)

    def acquire_lock(self, org_repo):
        existing = self._locks.get(org_repo)
        if existing is not None and existing[1] > datetime.now(UTC):
            return None
        leased_until = datetime.now(UTC) + timedelta(seconds=900)
        self._locks[org_repo] = ("holder", leased_until)
        return Lock(org_repo=org_repo, holder_id="holder", leased_until=leased_until.isoformat())

    def release_lock(self, lock):
        self._locks.pop(lock.org_repo, None)


def _effector_manifest(**overrides) -> CapabilityManifest:
    defaults = dict(
        capability_id="mutate_thing",
        version="1",
        name="Mutate thing",
        purpose="test effector",
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
    manifests, executors = registry._build((module,))
    monkeypatch.setattr(registry, "_MANIFESTS", manifests)
    monkeypatch.setattr(registry, "_EXECUTORS", executors)


def _tool_call(capability_id: str, arguments: dict) -> dict:
    import json

    return {"function": {"name": capability_id, "arguments": json.dumps(arguments)}}


class TestIdempotencyKey:
    def test_same_inputs_same_key(self):
        k1 = idempotency_key("cap", {"org_repo": "a/b", "extra": 1}, ["org_repo"])
        k2 = idempotency_key("cap", {"org_repo": "a/b", "extra": 2}, ["org_repo"])
        assert k1 == k2  # "extra" is not in idempotency_inputs -- excluded from the key

    def test_different_selected_inputs_different_key(self):
        k1 = idempotency_key("cap", {"org_repo": "a/b"}, ["org_repo"])
        k2 = idempotency_key("cap", {"org_repo": "a/c"}, ["org_repo"])
        assert k1 != k2


class TestRetryIsSafe:
    def test_read_only_always_safe(self):
        m = _effector_manifest(
            side_effect_class="read_only_local", idempotency_inputs=[], retry_policy=None
        )
        assert retry_is_safe(m)

    def test_mutating_without_idempotent_only_is_unsafe(self):
        m = _effector_manifest(retry_policy=None, idempotency_inputs=["org_repo"])
        # Bypass the registration gate directly to test the function in isolation.
        assert retry_is_safe(m) is False

    def test_mutating_with_idempotent_only_is_safe(self):
        m = _effector_manifest(retry_policy="idempotent_only")
        assert retry_is_safe(m)


class TestDispatchGatedEffectHappyPath:
    def test_pending_then_applied(self, monkeypatch):
        counter = _Counter()

        def execute(org_repo):
            counter.applied += 1
            return {"applied": True, "count": counter.applied}

        _register(monkeypatch, _effector_manifest(), execute)
        backend = FakeStateBackend()

        result = dispatch_gated_effect(
            _tool_call("mutate_thing", {"org_repo": ORG_REPO}),
            {"local_write"},
            backend,
            ORG_REPO,
        )
        assert result.outcome == "dispatched"
        assert result.dispatch.outcome == "executed"
        assert counter.applied == 1

        state = backend.load(ORG_REPO)
        assert len(state.capability_outputs) == 1
        assert state.capability_outputs[0].status == "applied"

    def test_second_dispatch_with_same_key_is_already_applied_no_reexecution(self, monkeypatch):
        counter = _Counter()

        def execute(org_repo):
            counter.applied += 1
            return {"count": counter.applied}

        _register(monkeypatch, _effector_manifest(), execute)
        backend = FakeStateBackend()
        tool_call = _tool_call("mutate_thing", {"org_repo": ORG_REPO})

        dispatch_gated_effect(tool_call, {"local_write"}, backend, ORG_REPO)
        second = dispatch_gated_effect(tool_call, {"local_write"}, backend, ORG_REPO)

        assert second.outcome == "already_applied"
        assert counter.applied == 1  # NOT re-executed -- this is the actual EFF-002 guarantee


class TestDispatchGatedEffectCrashRecovery:
    def test_deterministic_interruption_between_pending_and_applied_is_not_reexecuted(
        self, monkeypatch
    ):
        """The actual EFF-002 proof: a crash *after* the executor's side
        effect but *before* the ledger can flip the record to `applied`
        must not be silently re-applied on the next attempt. Interruption is
        deterministically triggered (the effector raises after incrementing
        its own counter), not a wall-clock race."""
        counter = _Counter()

        def crashing_execute(org_repo):
            counter.applied += 1
            raise RuntimeError("simulated crash after the real side effect landed")

        _register(monkeypatch, _effector_manifest(), crashing_execute)
        backend = FakeStateBackend()
        tool_call = _tool_call("mutate_thing", {"org_repo": ORG_REPO})

        first = dispatch_gated_effect(tool_call, {"local_write"}, backend, ORG_REPO)
        assert first.outcome == "dispatched"
        assert first.dispatch.outcome == "execution_error"
        assert counter.applied == 1

        state = backend.load(ORG_REPO)
        assert state.capability_outputs[0].status == "pending"  # never flipped to applied

        second = dispatch_gated_effect(tool_call, {"local_write"}, backend, ORG_REPO)
        assert second.outcome == "blocked_pending_reconciliation"
        assert counter.applied == 1  # NOT re-executed -- refused to guess


class TestDispatchGatedEffectRetryInertness:
    def test_a_failed_attempt_always_blocks_the_next_one_regardless_of_retry_policy(
        self, monkeypatch
    ):
        """The ledger's own `pending`-after-failure check fires for *any*
        subsequent attempt with the same key, regardless of `retry_policy`
        -- "did the effect land" is genuinely unknown here, a strictly
        stronger reason to refuse than `retry_policy` alone. `EFF-003`'s own
        enforcement point is one layer up: `supervisor/repair.py`'s
        `retry_is_safe()` gate decides whether to even *propose* dispatching
        this capability+arguments again in the first place (see
        `test_repair.py`) -- this test proves the ledger backstops that
        decision defensively even if something else tried to bypass it."""

        def failing_execute(org_repo):
            raise RuntimeError("boom")

        _register(
            monkeypatch,
            _effector_manifest(retry_policy="manual_reconciliation_required"),
            failing_execute,
        )
        backend = FakeStateBackend()
        tool_call = _tool_call("mutate_thing", {"org_repo": ORG_REPO})

        first = dispatch_gated_effect(tool_call, {"local_write"}, backend, ORG_REPO)
        assert first.dispatch.outcome == "execution_error"

        second = dispatch_gated_effect(tool_call, {"local_write"}, backend, ORG_REPO)
        assert second.outcome == "blocked_pending_reconciliation"


class TestDispatchGatedEffectPassthrough:
    def test_read_only_capability_bypasses_the_ledger_entirely(self):
        """A non-mutating capability_id is never gated -- plain dispatch,
        the ledger has nothing to add (matches every existing registered
        capability today)."""
        backend = FakeStateBackend()
        result = dispatch_gated_effect(
            _tool_call("inspect_repository", {"org_repo": "not-a-real-repo/x"}),
            {"read_only_local"},
            backend,
            "not-a-real-repo/x",
        )
        assert result.outcome == "dispatched"
        # Nothing written to the ledger for a read-only capability.
        assert backend.load("not-a-real-repo/x") is None
