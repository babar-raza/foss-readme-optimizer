"""Offline tests for capabilities/dispatcher.py -- the permission-aware
dispatch gate (sprint Task 4.2). Registry lookups are monkeypatched for the
scenario-focused tests; one test dispatches against the real, unmodified
registry to prove the actual check_install_path manifest's permission class
is honored, not just a mocked one."""

from readme_agent.capabilities import dispatcher, registry
from readme_agent.capabilities.schema import CapabilityManifest


def _manifest(**overrides) -> CapabilityManifest:
    defaults = dict(
        capability_id="widget_capability",
        version="1",
        name="Widget capability",
        purpose="test fixture",
        category="test",
        owner="tests",
        execution_type="deterministic_tool",
        required_inputs={"org_repo": "string"},
        side_effect_class="read_only_local",
    )
    return CapabilityManifest(**{**defaults, **overrides})


def _tool_call(name: str, arguments: str) -> dict:
    return {"id": "call-1", "function": {"name": name, "arguments": arguments}}


class TestDispatchSuccess:
    def test_executes_and_returns_result(self, monkeypatch):
        manifest = _manifest()

        def fake_execute(org_repo):
            return {"org_repo": org_repo, "ok": True}

        monkeypatch.setattr(registry, "get", lambda cid: manifest)
        monkeypatch.setattr(registry, "get_executor", lambda cid: fake_execute)
        tool_call = _tool_call("widget_capability", '{"org_repo": "acme/widget"}')

        result = dispatcher.dispatch_tool_call(tool_call, allowed_permissions={"read_only_local"})

        assert result.outcome == "executed"
        assert result.result == {"org_repo": "acme/widget", "ok": True}
        assert result.gap is None
        assert result.error is None


class TestDispatchUnknownCapability:
    def test_creates_gap_record_not_a_silent_skip(self, monkeypatch):
        monkeypatch.setattr(registry, "get", lambda cid: None)
        tool_call = _tool_call("nonexistent_capability", '{"org_repo": "acme/widget"}')

        result = dispatcher.dispatch_tool_call(tool_call, allowed_permissions={"read_only_local"})

        assert result.outcome == "rejected_unknown_capability"
        assert result.gap is not None
        assert result.gap.requested_capability_id == "nonexistent_capability"
        assert result.gap.org_repo == "acme/widget"
        assert result.result is None


class TestDispatchPermissionDenied:
    def test_rejects_when_side_effect_class_not_allowed(self, monkeypatch):
        manifest = _manifest(side_effect_class="read_only_network")
        monkeypatch.setattr(registry, "get", lambda cid: manifest)
        tool_call = _tool_call("widget_capability", '{"org_repo": "acme/widget"}')

        result = dispatcher.dispatch_tool_call(tool_call, allowed_permissions={"read_only_local"})

        assert result.outcome == "rejected_permission_denied"
        assert result.result is None
        assert "read_only_network" in result.error

    def test_real_check_install_path_manifest_is_network_and_gets_denied(self):
        """Uses the real, unmodified registry -- proves the production
        check_install_path manifest actually declares read_only_network,
        not just a test double."""
        tool_call = _tool_call("check_install_path", '{"org_repo": "acme/widget"}')

        result = dispatcher.dispatch_tool_call(tool_call, allowed_permissions={"read_only_local"})

        assert result.outcome == "rejected_permission_denied"


class TestDispatchDomainDenied:
    """CAP-006/Decision #33 -- the dispatcher-side domain check is the
    actual enforcement boundary for specialist isolation, independent of
    whatever tools a framework (LangGraph, Wave 6+) happens to offer."""

    def test_rejects_when_caller_domain_not_a_member(self, monkeypatch):
        manifest = _manifest(allowed_domains=["readme"])
        monkeypatch.setattr(registry, "get", lambda cid: manifest)
        tool_call = _tool_call("widget_capability", '{"org_repo": "acme/widget"}')

        result = dispatcher.dispatch_tool_call(
            tool_call, allowed_permissions={"read_only_local"}, caller_domain="metadata"
        )

        assert result.outcome == "rejected_domain_denied"
        assert result.result is None
        assert "metadata" in result.error

    def test_allows_when_caller_domain_is_a_member(self, monkeypatch):
        manifest = _manifest(allowed_domains=["readme", "metadata"])

        def fake_execute(org_repo):
            return {"org_repo": org_repo}

        monkeypatch.setattr(registry, "get", lambda cid: manifest)
        monkeypatch.setattr(registry, "get_executor", lambda cid: fake_execute)
        tool_call = _tool_call("widget_capability", '{"org_repo": "acme/widget"}')

        result = dispatcher.dispatch_tool_call(
            tool_call, allowed_permissions={"read_only_local"}, caller_domain="readme"
        )

        assert result.outcome == "executed"

    def test_unscoped_capability_allowed_regardless_of_caller_domain(self, monkeypatch):
        manifest = _manifest()  # allowed_domains defaults to []

        def fake_execute(org_repo):
            return {"org_repo": org_repo}

        monkeypatch.setattr(registry, "get", lambda cid: manifest)
        monkeypatch.setattr(registry, "get_executor", lambda cid: fake_execute)
        tool_call = _tool_call("widget_capability", '{"org_repo": "acme/widget"}')

        result = dispatcher.dispatch_tool_call(
            tool_call, allowed_permissions={"read_only_local"}, caller_domain="anything"
        )

        assert result.outcome == "executed"

    def test_real_classify_upstream_change_manifest_is_domain_scoped_and_gets_denied(self):
        """Uses the real, unmodified registry (Wave 6, decision #39) -- the
        first real domain-denied proof against a real manifest, not just a
        synthetic one."""
        tool_call = _tool_call("classify_upstream_change", '{"org_repo": "acme/widget"}')

        result = dispatcher.dispatch_tool_call(
            tool_call,
            allowed_permissions={"read_only_local", "read_only_network"},
            caller_domain="some_other_domain",
        )

        assert result.outcome == "rejected_domain_denied"

    def test_existing_call_sites_without_caller_domain_are_unaffected(self, monkeypatch):
        """Regression: every existing caller (this test file,
        test_capabilities_live.py) never passes caller_domain -- the
        default must not change behavior for an unscoped capability."""
        manifest = _manifest()

        def fake_execute(org_repo):
            return {"org_repo": org_repo}

        monkeypatch.setattr(registry, "get", lambda cid: manifest)
        monkeypatch.setattr(registry, "get_executor", lambda cid: fake_execute)
        tool_call = _tool_call("widget_capability", '{"org_repo": "acme/widget"}')

        result = dispatcher.dispatch_tool_call(tool_call, allowed_permissions={"read_only_local"})

        assert result.outcome == "executed"


class TestDispatchInvalidArguments:
    def test_malformed_json_rejected_before_any_lookup(self, monkeypatch):
        def fail_if_called(cid):
            raise AssertionError("registry.get must not be called for malformed arguments")

        monkeypatch.setattr(registry, "get", fail_if_called)
        tool_call = _tool_call("widget_capability", "{not valid json")

        result = dispatcher.dispatch_tool_call(tool_call, allowed_permissions={"read_only_local"})

        assert result.outcome == "rejected_invalid_arguments"

    def test_missing_required_argument_rejected(self, monkeypatch):
        manifest = _manifest(required_inputs={"org_repo": "string"})
        monkeypatch.setattr(registry, "get", lambda cid: manifest)
        tool_call = _tool_call("widget_capability", "{}")

        result = dispatcher.dispatch_tool_call(tool_call, allowed_permissions={"read_only_local"})

        assert result.outcome == "rejected_invalid_arguments"
        assert "org_repo" in result.error


class TestDispatchExecutionError:
    def test_wrapped_function_failure_becomes_a_typed_outcome_not_a_crash(self, monkeypatch):
        manifest = _manifest()
        monkeypatch.setattr(registry, "get", lambda cid: manifest)

        def boom(org_repo):
            raise RuntimeError("network exploded")

        monkeypatch.setattr(registry, "get_executor", lambda cid: boom)
        tool_call = _tool_call("widget_capability", '{"org_repo": "acme/widget"}')

        result = dispatcher.dispatch_tool_call(tool_call, allowed_permissions={"read_only_local"})

        assert result.outcome == "execution_error"
        assert "network exploded" in result.error
