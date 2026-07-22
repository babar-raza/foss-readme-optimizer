import argparse

import pytest

from readme_agent.cli import _build_parser, main
from readme_agent.commands import cmd_supervise


@pytest.fixture(autouse=True)
def _stub_registry_heal(monkeypatch):
    """CORE-034 (decision #47): `cmd_supervise` self-heals the registry before
    anything else -- stubbed module-wide so every CLI unit test stays
    network-free. The stub records its calls (appended to the returned list)
    so TestSuperviseRegistryHealHook can assert count/ordering/arguments."""
    import readme_agent.registry.self_heal as self_heal_module

    calls: list[tuple] = []

    def _fake_heal(**kwargs):
        calls.append(("heal", kwargs))
        return self_heal_module.RegistryHealResult(status="SKIPPED_DISABLED", detail="stubbed")

    monkeypatch.setattr(self_heal_module, "heal_registry_drift", _fake_heal)
    return calls


def _stub_preflight_ok(monkeypatch) -> None:
    """Wave 8.5 (`ORC-006`/D2): `cmd_supervise` now checks
    `run_preflight_for_repo()` before anything else -- stubbed to a
    passing result so these unit tests stay network-free, matching this
    project's own `@pytest.mark.live` convention."""
    import readme_agent.preflight.runner as preflight_runner_module

    monkeypatch.setattr(
        preflight_runner_module,
        "run_preflight_for_repo",
        lambda org_repo: argparse.Namespace(ok=True),
    )


def test_version_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "0.1.0" in capsys.readouterr().out


def test_missing_command_exits_nonzero():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code != 0


class TestInspectCheckInstallFlag:
    """Phase 21d: --check-install is opt-in on the inspect verb, defaulting to
    False -- matching validate's established --check-links pattern."""

    def test_defaults_to_false(self):
        args = _build_parser().parse_args(["inspect", "--repo", "org/repo"])
        assert args.check_install is False

    def test_flag_sets_true(self):
        args = _build_parser().parse_args(["inspect", "--repo", "org/repo", "--check-install"])
        assert args.check_install is True


class TestSuperviseCommand:
    """Wave 5: `supervise` is a new, additive verb -- `--durable-state`
    mirrors `run`'s opt-in convention, defaulting to False."""

    def test_repo_required(self):
        with pytest.raises(SystemExit):
            _build_parser().parse_args(["supervise"])

    def test_durable_state_defaults_to_false(self):
        args = _build_parser().parse_args(["supervise", "--repo", "org/repo"])
        assert args.durable_state is False

    def test_durable_state_flag_sets_true(self):
        args = _build_parser().parse_args(["supervise", "--repo", "org/repo", "--durable-state"])
        assert args.durable_state is True

    @pytest.mark.parametrize(
        ("status", "expected_exit_code"),
        [
            ("CONVERGED_NO_CHANGE", 0),
            ("CONVERGED_APPLIED", 0),
            # Wave 6 (decision #39): the registry-driven specialist tier's
            # own converged outcome -- must exit 0 like the other converged
            # statuses, not be treated as a failure.
            ("CONVERGED_NO_TRACKED_CHANGE", 0),
            ("PARTIAL_WITH_CAPABILITY_GAP", 1),
            ("BLOCKED", 1),
        ],
    )
    def test_exit_code_matches_status(self, monkeypatch, status, expected_exit_code):
        import readme_agent.supervisor.loop as loop_module

        _stub_preflight_ok(monkeypatch)
        fake_result = argparse.Namespace(
            status=status, blocked_reason=None, decisions=[], org_repo="org/repo"
        )
        monkeypatch.setattr(
            loop_module, "supervise_repo", lambda repo, state_backend=None: fake_result
        )

        args = argparse.Namespace(repo="org/repo", durable_state=False)
        assert cmd_supervise(args) == expected_exit_code


class TestSuperviseRegistryHealHook:
    """CORE-034 (decision #47): registry drift self-heals once per
    `cmd_supervise` invocation, before preflight and before any allow-list
    gate -- and a heal failure never changes the command's outcome."""

    def test_no_registry_heal_defaults_to_false(self):
        args = _build_parser().parse_args(["supervise", "--repo", "org/repo"])
        assert args.no_registry_heal is False

    def test_no_registry_heal_flag_sets_true(self):
        args = _build_parser().parse_args(["supervise", "--repo", "org/repo", "--no-registry-heal"])
        assert args.no_registry_heal is True

    def test_heal_runs_exactly_once_and_before_preflight(self, monkeypatch, _stub_registry_heal):
        import readme_agent.preflight.runner as preflight_runner_module
        import readme_agent.supervisor.loop as loop_module

        calls = _stub_registry_heal

        def _fake_preflight(org_repo):
            calls.append(("preflight", org_repo))
            return argparse.Namespace(ok=True)

        monkeypatch.setattr(preflight_runner_module, "run_preflight_for_repo", _fake_preflight)
        fake_result = argparse.Namespace(
            status="CONVERGED_NO_CHANGE", blocked_reason=None, decisions=[]
        )
        monkeypatch.setattr(
            loop_module, "supervise_repo", lambda repo, state_backend=None: fake_result
        )

        args = argparse.Namespace(repo="org/repo", durable_state=False)
        assert cmd_supervise(args) == 0
        assert [kind for kind, _ in calls] == ["heal", "preflight"]

    def test_no_registry_heal_flag_disables_the_heal(self, monkeypatch, _stub_registry_heal):
        import readme_agent.supervisor.loop as loop_module

        _stub_preflight_ok(monkeypatch)
        fake_result = argparse.Namespace(
            status="CONVERGED_NO_CHANGE", blocked_reason=None, decisions=[]
        )
        monkeypatch.setattr(
            loop_module, "supervise_repo", lambda repo, state_backend=None: fake_result
        )

        args = argparse.Namespace(repo="org/repo", durable_state=False, no_registry_heal=True)
        assert cmd_supervise(args) == 0
        assert _stub_registry_heal == [("heal", {"enabled": False})]

    def test_heal_error_does_not_change_the_exit_code(self, monkeypatch):
        import readme_agent.registry.self_heal as self_heal_module
        import readme_agent.supervisor.loop as loop_module

        _stub_preflight_ok(monkeypatch)
        monkeypatch.setattr(
            self_heal_module,
            "heal_registry_drift",
            lambda **kwargs: self_heal_module.RegistryHealResult(
                status="SKIPPED_ERROR", detail="github exploded"
            ),
        )
        fake_result = argparse.Namespace(
            status="CONVERGED_NO_CHANGE", blocked_reason=None, decisions=[]
        )
        monkeypatch.setattr(
            loop_module, "supervise_repo", lambda repo, state_backend=None: fake_result
        )

        args = argparse.Namespace(repo="org/repo", durable_state=False)
        assert cmd_supervise(args) == 0


class TestSuperviseSingleDomainFlag:
    """Wave 7: `--domain` bypasses the full specialist-tier sweep and planner
    loop entirely, calling `specialists/registry.py::run_domain()` directly
    for exactly one domain -- the CLI-facing version of "trigger only the
    README agent" that's usable today, independent of Wave 10's MCP work."""

    def test_domain_defaults_to_none(self):
        args = _build_parser().parse_args(["supervise", "--repo", "org/repo"])
        assert args.domain is None

    def test_domain_flag_sets_value(self):
        args = _build_parser().parse_args(
            ["supervise", "--repo", "org/repo", "--domain", "readme_reconciliation"]
        )
        assert args.domain == "readme_reconciliation"

    def test_known_domain_calls_run_domain_not_the_full_sweep(self, monkeypatch):
        import readme_agent.specialists.registry as specialists_registry_module
        import readme_agent.supervisor.loop as loop_module

        _stub_preflight_ok(monkeypatch)
        calls: dict[str, object] = {}

        def _fake_run_domain(domain, repo, backend):
            calls["domain"] = domain
            calls["repo"] = repo
            return argparse.Namespace(accepted_status="NO_CHANGE", details={})

        def _raising_supervise_repo(repo, state_backend=None):
            raise AssertionError("the full specialist-tier sweep must not run")

        monkeypatch.setattr(specialists_registry_module, "run_domain", _fake_run_domain)
        monkeypatch.setattr(
            specialists_registry_module, "all_domains", lambda: ["readme_reconciliation"]
        )
        monkeypatch.setattr(loop_module, "supervise_repo", _raising_supervise_repo)

        args = argparse.Namespace(
            repo="org/repo", durable_state=False, domain="readme_reconciliation"
        )
        assert cmd_supervise(args) == 0
        assert calls == {"domain": "readme_reconciliation", "repo": "org/repo"}

    def test_unknown_domain_exits_2(self, monkeypatch):
        import readme_agent.specialists.registry as specialists_registry_module

        _stub_preflight_ok(monkeypatch)
        monkeypatch.setattr(
            specialists_registry_module, "all_domains", lambda: ["readme_reconciliation"]
        )

        args = argparse.Namespace(repo="org/repo", durable_state=False, domain="not_a_real_domain")
        assert cmd_supervise(args) == 2

    def test_error_status_exits_1(self, monkeypatch):
        import readme_agent.specialists.registry as specialists_registry_module

        _stub_preflight_ok(monkeypatch)
        monkeypatch.setattr(
            specialists_registry_module, "all_domains", lambda: ["readme_reconciliation"]
        )
        monkeypatch.setattr(
            specialists_registry_module,
            "run_domain",
            lambda domain, repo, backend: argparse.Namespace(
                accepted_status="ERROR", details={"error": "boom"}
            ),
        )

        args = argparse.Namespace(
            repo="org/repo", durable_state=False, domain="readme_reconciliation"
        )
        assert cmd_supervise(args) == 1


class TestModelRouteEnableCommand:
    """Wave 8.6 (`OPS-011` extension): the only way a disabled route ever
    becomes enabled again -- always explicit, always human-authored."""

    def test_parses_required_flags(self):
        args = _build_parser().parse_args(
            ["model-route-enable", "--job", "supervisor_planning", "--reason", "fixed the bug"]
        )
        assert args.job == "supervisor_planning"
        assert args.reason == "fixed the bug"

    def test_missing_job_flag_exits_nonzero(self):
        with pytest.raises(SystemExit):
            _build_parser().parse_args(["model-route-enable", "--reason", "x"])

    def test_saves_an_enabled_status_with_the_given_reason(self, monkeypatch):
        from readme_agent.commands import cmd_model_route_enable

        saved = {}

        class _FakeBackend:
            def save_model_route_status(self, status):
                saved["status"] = status

        import readme_agent.state.git_backend as git_backend_module

        monkeypatch.setattr(git_backend_module, "default_state_backend", lambda: _FakeBackend())

        args = argparse.Namespace(job="supervisor_planning", reason="fixed the bug")
        exit_code = cmd_model_route_enable(args)

        assert exit_code == 0
        assert saved["status"].job == "supervisor_planning"
        assert saved["status"].status == "enabled"
        assert saved["status"].reason == "fixed the bug"


class TestScaffoldPolicyCommand:
    """ONB-004: CLI parser wiring only -- behavior is covered end-to-end in
    tests/unit/test_scaffold_policy.py."""

    def test_parses_required_repo_flag(self):
        args = _build_parser().parse_args(["scaffold-policy", "--repo", "org/repo"])
        assert args.repo == "org/repo"
        assert args.force is False

    def test_missing_repo_flag_exits_nonzero(self):
        with pytest.raises(SystemExit):
            _build_parser().parse_args(["scaffold-policy"])

    def test_force_flag_sets_true(self):
        args = _build_parser().parse_args(["scaffold-policy", "--repo", "org/repo", "--force"])
        assert args.force is True
