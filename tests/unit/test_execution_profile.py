"""Tests for `supervisor/execution_profile.py` (Wave 9.4, 2026-07-22 convergence-sprint plan)."""

from readme_agent.supervisor.execution_profile import (
    ExecutionProfileV1,
    get_profile,
    is_github_profile,
)


class TestProfileRegistry:
    def test_all_five_named_profiles_resolve(self):
        for name in (
            "local_inspect",
            "local_dry_run",
            "github_observe",
            "github_proposal",
            "github_apply",
        ):
            profile = get_profile(name)  # type: ignore[arg-type]
            assert isinstance(profile, ExecutionProfileV1)
            assert profile.name == name

    def test_is_github_profile(self):
        assert is_github_profile("github_observe") is True
        assert is_github_profile("github_proposal") is True
        assert is_github_profile("github_apply") is True
        assert is_github_profile("local_inspect") is False
        assert is_github_profile("local_dry_run") is False


class TestProfileInvariants:
    """The properties `commands.py::cmd_supervise()` actually depends on."""

    def test_only_local_profiles_allow_domain_bypass(self):
        assert get_profile("local_inspect").allows_domain_bypass is True
        assert get_profile("local_dry_run").allows_domain_bypass is True
        assert get_profile("github_observe").allows_domain_bypass is False
        assert get_profile("github_proposal").allows_domain_bypass is False
        assert get_profile("github_apply").allows_domain_bypass is False

    def test_all_github_profiles_fail_closed_and_require_durable_state(self):
        for name in ("github_observe", "github_proposal", "github_apply"):
            profile = get_profile(name)  # type: ignore[arg-type]
            assert profile.requires_durable_state is True
            assert profile.fail_closed_on_state_failure is True

    def test_local_profiles_never_fail_closed(self):
        assert get_profile("local_inspect").fail_closed_on_state_failure is False
        assert get_profile("local_dry_run").fail_closed_on_state_failure is False

    def test_observe_profiles_never_allow_write_permission_classes(self):
        for name in ("local_inspect", "github_observe"):
            allowed = get_profile(name).allowed_permission_classes  # type: ignore[arg-type]
            assert "local_write" not in allowed
            assert "remote_write" not in allowed

    def test_proposal_and_apply_profiles_allow_remote_write(self):
        for name in ("github_proposal", "github_apply"):
            allowed = get_profile(name).allowed_permission_classes  # type: ignore[arg-type]
            assert "remote_write" in allowed

    def test_local_dry_run_allows_local_write_not_remote_write(self):
        allowed = get_profile("local_dry_run").allowed_permission_classes
        assert "local_write" in allowed
        assert "remote_write" not in allowed

    def test_only_github_apply_restricts_to_workflow_dispatch_only(self):
        assert get_profile("github_apply").allowed_triggers == ["workflow_dispatch"]
        assert "schedule" in get_profile("github_proposal").allowed_triggers
        assert "schedule" in get_profile("github_observe").allowed_triggers
