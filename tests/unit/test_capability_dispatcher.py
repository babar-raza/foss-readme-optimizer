"""Offline tests for capabilities/dispatcher.py -- the permission-aware
dispatch gate (sprint Task 4.2). Registry lookups are monkeypatched for the
scenario-focused tests; one test dispatches against the real, unmodified
registry to prove the actual check_install_path manifest's permission class
is honored, not just a mocked one."""

from readme_agent.capabilities import dispatcher, registry
from readme_agent.capabilities.schema import CapabilityManifest, OrgRepoOnlyInputV1
from readme_agent.state.schema import ModelRouteStatusV1


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

    def test_real_audit_github_generated_surfaces_manifest_is_domain_scoped_and_gets_denied(self):
        """Wave 7b: the second real domain-scoped capability, and the second
        real domain -- CAP-006's cross-domain-denial path proven against
        genuinely two different domains, not just one repeated capability."""
        tool_call = _tool_call("audit_github_generated_surfaces", '{"org_repo": "acme/widget"}')

        result = dispatcher.dispatch_tool_call(
            tool_call,
            allowed_permissions={"read_only_local", "read_only_network"},
            caller_domain="readme_reconciliation",
        )

        assert result.outcome == "rejected_domain_denied"

    def test_each_real_domain_scoped_capability_only_admits_its_own_domain(self):
        """The other half of the same proof: `readme_reconciliation`'s own
        capability must equally reject a caller claiming to be the *other*
        real domain -- neither domain's capabilities are reachable by the
        other's caller_domain."""
        tool_call = _tool_call("classify_upstream_change", '{"org_repo": "acme/widget"}')

        result = dispatcher.dispatch_tool_call(
            tool_call,
            allowed_permissions={"read_only_local", "read_only_network"},
            caller_domain="github_generated_surface_audit",
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


class TestDispatchInputModelValidation:
    """Wave 11.4 (`CAP-008`): a capability declaring `input_model` gets
    real structural validation -- not just presence -- before the executor
    ever runs. A capability without `input_model` (every one that predates
    this field) is completely unaffected (proven throughout this file's
    other test classes, none of which set it)."""

    def test_malformed_org_repo_is_rejected_before_execute_runs(self, monkeypatch):
        manifest = _manifest(input_model=OrgRepoOnlyInputV1)

        def fail_if_called(org_repo):
            raise AssertionError("execute() must not run for a failed input_model validation")

        monkeypatch.setattr(registry, "get", lambda cid: manifest)
        monkeypatch.setattr(registry, "get_executor", lambda cid: fail_if_called)
        tool_call = _tool_call("widget_capability", '{"org_repo": "not-a-valid-repo-ref"}')

        result = dispatcher.dispatch_tool_call(tool_call, allowed_permissions={"read_only_local"})

        assert result.outcome == "rejected_invalid_arguments"
        assert "org_repo" in result.error

    def test_valid_org_repo_still_executes(self, monkeypatch):
        manifest = _manifest(input_model=OrgRepoOnlyInputV1)

        def fake_execute(org_repo):
            return {"org_repo": org_repo}

        monkeypatch.setattr(registry, "get", lambda cid: manifest)
        monkeypatch.setattr(registry, "get_executor", lambda cid: fake_execute)
        tool_call = _tool_call("widget_capability", '{"org_repo": "acme/widget"}')

        result = dispatcher.dispatch_tool_call(tool_call, allowed_permissions={"read_only_local"})

        assert result.outcome == "executed"
        assert result.result == {"org_repo": "acme/widget"}

    def test_no_input_model_skips_structural_validation_entirely(self, monkeypatch):
        """Backward compatibility: a manifest with `input_model=None` (the
        default) never invokes Pydantic validation at all -- an
        org_repo-shaped-oddly value that the old presence-only check would
        have allowed through still executes, exactly as before."""
        manifest = _manifest()  # input_model defaults to None
        assert manifest.input_model is None

        def fake_execute(org_repo):
            return {"org_repo": org_repo}

        monkeypatch.setattr(registry, "get", lambda cid: manifest)
        monkeypatch.setattr(registry, "get_executor", lambda cid: fake_execute)
        tool_call = _tool_call("widget_capability", '{"org_repo": "not-a-valid-repo-ref"}')

        result = dispatcher.dispatch_tool_call(tool_call, allowed_permissions={"read_only_local"})

        assert result.outcome == "executed"


class _FakeModelRouteBackend:
    def __init__(self, status: ModelRouteStatusV1 | None):
        self._status = status

    def load_model_route_status(self, job: str) -> ModelRouteStatusV1 | None:
        return self._status


class TestDispatchModelRouteGate:
    """Wave 13.4 (`LLM-020`): a capability declaring `model_route` whose
    route a human has durably disabled must not dispatch -- generalizes the
    hardcoded `supervisor_planning`-only check `supervisor/loop.py` already
    had to every capability that declares one. A no-op unless BOTH
    `model_route` is declared AND a live `state_backend` is supplied --
    every existing caller/test above (none of which pass `state_backend`)
    is completely unaffected."""

    def test_disabled_route_blocks_before_execute_runs(self, monkeypatch):
        manifest = _manifest(model_route="some_job")

        def fail_if_called(org_repo):
            raise AssertionError("execute() must not run when the route is disabled")

        monkeypatch.setattr(registry, "get", lambda cid: manifest)
        monkeypatch.setattr(registry, "get_executor", lambda cid: fail_if_called)
        tool_call = _tool_call("widget_capability", '{"org_repo": "acme/widget"}')
        backend = _FakeModelRouteBackend(
            ModelRouteStatusV1(job="some_job", status="disabled", reason="golden-set failure")
        )

        result = dispatcher.dispatch_tool_call(
            tool_call, allowed_permissions={"read_only_local"}, state_backend=backend
        )

        assert result.outcome == "rejected_model_route_disabled"
        assert "some_job" in result.error
        assert "golden-set failure" in result.error

    def test_enabled_route_proceeds_normally(self, monkeypatch):
        manifest = _manifest(model_route="some_job")

        def fake_execute(org_repo):
            return {"org_repo": org_repo}

        monkeypatch.setattr(registry, "get", lambda cid: manifest)
        monkeypatch.setattr(registry, "get_executor", lambda cid: fake_execute)
        tool_call = _tool_call("widget_capability", '{"org_repo": "acme/widget"}')
        backend = _FakeModelRouteBackend(ModelRouteStatusV1(job="some_job", status="enabled"))

        result = dispatcher.dispatch_tool_call(
            tool_call, allowed_permissions={"read_only_local"}, state_backend=backend
        )

        assert result.outcome == "executed"

    def test_no_recorded_status_at_all_proceeds_normally(self, monkeypatch):
        """`load_model_route_status()` returning `None` means "enabled"
        (the permissive default, per its own docstring) -- never itself a
        block."""
        manifest = _manifest(model_route="some_job")

        def fake_execute(org_repo):
            return {"org_repo": org_repo}

        monkeypatch.setattr(registry, "get", lambda cid: manifest)
        monkeypatch.setattr(registry, "get_executor", lambda cid: fake_execute)
        tool_call = _tool_call("widget_capability", '{"org_repo": "acme/widget"}')
        backend = _FakeModelRouteBackend(None)

        result = dispatcher.dispatch_tool_call(
            tool_call, allowed_permissions={"read_only_local"}, state_backend=backend
        )

        assert result.outcome == "executed"

    def test_no_state_backend_supplied_is_a_no_op_even_for_a_routed_capability(self, monkeypatch):
        """Regression guard: every existing caller in this file (none of
        which pass `state_backend`) is completely unaffected, even for a
        capability that DOES declare `model_route`."""
        manifest = _manifest(model_route="some_job")

        def fake_execute(org_repo):
            return {"org_repo": org_repo}

        monkeypatch.setattr(registry, "get", lambda cid: manifest)
        monkeypatch.setattr(registry, "get_executor", lambda cid: fake_execute)
        tool_call = _tool_call("widget_capability", '{"org_repo": "acme/widget"}')

        result = dispatcher.dispatch_tool_call(tool_call, allowed_permissions={"read_only_local"})

        assert result.outcome == "executed"

    def test_capability_with_no_model_route_is_unaffected_even_with_a_disabled_backend(
        self, monkeypatch
    ):
        manifest = _manifest()  # model_route defaults to None
        assert manifest.model_route is None

        def fake_execute(org_repo):
            return {"org_repo": org_repo}

        monkeypatch.setattr(registry, "get", lambda cid: manifest)
        monkeypatch.setattr(registry, "get_executor", lambda cid: fake_execute)
        tool_call = _tool_call("widget_capability", '{"org_repo": "acme/widget"}')
        backend = _FakeModelRouteBackend(
            ModelRouteStatusV1(job="unrelated_job", status="disabled", reason="n/a")
        )

        result = dispatcher.dispatch_tool_call(
            tool_call, allowed_permissions={"read_only_local"}, state_backend=backend
        )

        assert result.outcome == "executed"

    def test_the_real_verify_prose_quality_capability_declares_its_model_route(self):
        manifest = registry.get("verify_prose_quality")
        assert manifest.model_route == "prose_quality_check"

    def test_the_real_compare_against_presentation_standard_capability_declares_its_model_route(
        self,
    ):
        manifest = registry.get("compare_against_presentation_standard")
        assert manifest.model_route == "presentation_standard_compliance"

    def test_the_real_review_visual_asset_accuracy_capability_declares_its_model_route(self):
        manifest = registry.get("review_visual_asset_accuracy")
        assert manifest.model_route == "visual_asset_accuracy"


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
