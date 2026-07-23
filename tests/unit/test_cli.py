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

    def test_repo_and_mission_graph_are_mutually_exclusive(self):
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["supervise"])
        with pytest.raises(SystemExit):
            parser.parse_args(
                [
                    "supervise",
                    "--repo",
                    "org/repo",
                    "--mission-task-graph",
                    "mission.yaml",
                ]
            )

    def test_mission_graph_does_not_require_a_repository(self):
        args = _build_parser().parse_args(
            [
                "supervise",
                "--mission-task-graph",
                "plans/investigations/control/level8-autonomous-mission-task-graph.yaml",
                "--mission-action",
                "status",
            ]
        )
        assert args.repo is None
        assert args.mission_task_graph.endswith("level8-autonomous-mission-task-graph.yaml")

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
            loop_module,
            "supervise_repo",
            lambda repo, state_backend=None, allowed_permission_classes=None: fake_result,
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
            loop_module,
            "supervise_repo",
            lambda repo, state_backend=None, allowed_permission_classes=None: fake_result,
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
            loop_module,
            "supervise_repo",
            lambda repo, state_backend=None, allowed_permission_classes=None: fake_result,
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
            loop_module,
            "supervise_repo",
            lambda repo, state_backend=None, allowed_permission_classes=None: fake_result,
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


class TestEnableDynamicPlanningFlag:
    """Wave 12.2 (`ORC-003`/`AGT-008`): the confirmed real gap this phase
    closes -- `enable_specialist_skip`/`specialist_selection_client`/
    `repair_planner_client` had all defaulted `None`/`False` in every
    shipped CLI path since Wave 8.6, so the dynamic specialist-skip and
    repair-alternative-selection mechanisms, fully built and unit-tested,
    had zero effect in production. `--enable-dynamic-planning` is the new,
    explicit, never-a-default opt-in."""

    def test_defaults_to_false(self):
        args = _build_parser().parse_args(["supervise", "--repo", "org/repo"])
        assert args.enable_dynamic_planning is False

    def test_flag_sets_true(self):
        args = _build_parser().parse_args(
            ["supervise", "--repo", "org/repo", "--enable-dynamic-planning"]
        )
        assert args.enable_dynamic_planning is True

    def test_without_the_flag_no_dynamic_planning_kwargs_are_passed(self, monkeypatch):
        """Regression: every existing caller (this test file's own fakes
        included) that never sets `enable_dynamic_planning` gets the exact
        prior behavior -- no new kwargs reach `supervise_repo()` at all."""
        import readme_agent.supervisor.loop as loop_module

        _stub_preflight_ok(monkeypatch)
        captured: dict[str, object] = {}

        def _fake_supervise_repo(repo, *, state_backend=None, allowed_permission_classes=None):
            captured["kwargs_seen"] = "only the pre-existing ones"
            return argparse.Namespace(
                status="CONVERGED_NO_CHANGE", blocked_reason=None, decisions=[]
            )

        monkeypatch.setattr(loop_module, "supervise_repo", _fake_supervise_repo)

        args = argparse.Namespace(
            repo="org/repo", durable_state=False, domain=None, execution_profile=None
        )
        assert cmd_supervise(args) == 0
        assert captured["kwargs_seen"] == "only the pre-existing ones"

    def test_with_the_flag_real_clients_and_enable_specialist_skip_are_passed(self, monkeypatch):
        import readme_agent.env as env
        import readme_agent.supervisor.loop as loop_module
        from readme_agent.llm.planner_client import LivePlannerClient

        _stub_preflight_ok(monkeypatch)
        monkeypatch.setattr(env, "llm_base_url", lambda: "https://gateway.example")
        monkeypatch.setattr(env, "llm_api_key", lambda: "fake-key")
        captured: dict[str, object] = {}

        def _fake_supervise_repo(
            repo,
            *,
            state_backend=None,
            allowed_permission_classes=None,
            enable_specialist_skip=False,
            specialist_selection_client=None,
            repair_planner_client=None,
        ):
            captured["enable_specialist_skip"] = enable_specialist_skip
            captured["specialist_selection_client"] = specialist_selection_client
            captured["repair_planner_client"] = repair_planner_client
            return argparse.Namespace(
                status="CONVERGED_NO_CHANGE", blocked_reason=None, decisions=[]
            )

        monkeypatch.setattr(loop_module, "supervise_repo", _fake_supervise_repo)

        args = argparse.Namespace(
            repo="org/repo",
            durable_state=False,
            domain=None,
            execution_profile=None,
            enable_dynamic_planning=True,
        )
        assert cmd_supervise(args) == 0
        assert captured["enable_specialist_skip"] is True
        assert isinstance(captured["specialist_selection_client"], LivePlannerClient)
        assert isinstance(captured["repair_planner_client"], LivePlannerClient)
        # Distinct clients, each job-routed independently -- not the same
        # instance reused for both purposes.
        assert captured["specialist_selection_client"] is not captured["repair_planner_client"]


class TestExecutionProfileFlag:
    """Wave 9.4 (execution profiles): `--execution-profile` is the explicit, typed replacement
    for "which flags happened to be passed." A `github_*` profile must reject `--domain` before
    anything else runs (no registry heal, no preflight, no clone) -- a usage error, not a runtime
    one."""

    def test_execution_profile_defaults_to_none(self):
        args = _build_parser().parse_args(["supervise", "--repo", "org/repo"])
        assert args.execution_profile is None

    def test_execution_profile_flag_sets_value(self):
        args = _build_parser().parse_args(
            ["supervise", "--repo", "org/repo", "--execution-profile", "github_observe"]
        )
        assert args.execution_profile == "github_observe"

    def test_invalid_execution_profile_choice_rejected_by_argparse(self):
        with pytest.raises(SystemExit):
            _build_parser().parse_args(
                ["supervise", "--repo", "org/repo", "--execution-profile", "not_a_real_profile"]
            )

    @pytest.mark.parametrize("profile_name", ["github_observe", "github_proposal", "github_apply"])
    def test_domain_rejected_under_every_github_profile_before_heal_or_preflight_run(
        self, monkeypatch, profile_name
    ):
        import readme_agent.preflight.runner as preflight_module
        import readme_agent.registry.self_heal as self_heal_module

        def _fail_if_called(*args, **kwargs):
            raise AssertionError("must not run once --domain is rejected under a github_ profile")

        monkeypatch.setattr(self_heal_module, "heal_registry_drift", _fail_if_called)
        monkeypatch.setattr(preflight_module, "run_preflight_for_repo", _fail_if_called)

        args = argparse.Namespace(
            repo="org/repo",
            durable_state=False,
            domain="readme_reconciliation",
            execution_profile=profile_name,
        )
        assert cmd_supervise(args) == 2

    @pytest.mark.parametrize("profile_name", ["local_inspect", "local_dry_run"])
    def test_domain_still_permitted_under_local_profiles(self, monkeypatch, profile_name):
        import readme_agent.specialists.registry as specialists_registry_module

        _stub_preflight_ok(monkeypatch)
        monkeypatch.setattr(
            specialists_registry_module, "all_domains", lambda: ["readme_reconciliation"]
        )
        monkeypatch.setattr(
            specialists_registry_module,
            "run_domain",
            lambda domain, repo, backend: argparse.Namespace(
                accepted_status="NO_CHANGE", details={}
            ),
        )

        args = argparse.Namespace(
            repo="org/repo",
            durable_state=False,
            domain="readme_reconciliation",
            execution_profile=profile_name,
        )
        assert cmd_supervise(args) == 0

    def test_github_profile_forces_a_durable_state_backend_without_the_flag(self, monkeypatch):
        import readme_agent.env as env
        import readme_agent.state.git_backend as git_backend_module
        import readme_agent.supervisor.loop as loop_module

        _stub_preflight_ok(monkeypatch)
        sentinel_backend = object()
        monkeypatch.setattr(git_backend_module, "default_state_backend", lambda: sentinel_backend)
        # Isolate from the REAL CI environment this test suite may itself be
        # running inside (`GITHUB_RUN_ID`/`GITHUB_EVENT_NAME` are ambient on
        # any real Actions runner, including under `act`) -- found live via
        # a real `act` proof run, Wave 13.6: without this, a `push`-triggered
        # workflow's own `GITHUB_EVENT_NAME` leaks in and `TriggerRecordV1`
        # rejects `event_type="push"` (not one of its four valid values),
        # crashing a test that has nothing to do with trigger identity.
        # `None` skips that whole branch entirely, matching real local-CLI
        # use (`env.github_run_id()`'s own docstring: "None outside Actions").
        monkeypatch.setattr(env, "github_run_id", lambda: None)

        captured: dict[str, object] = {}

        def _fake_supervise_repo(repo, *, state_backend=None, allowed_permission_classes=None):
            captured["state_backend"] = state_backend
            captured["allowed_permission_classes"] = allowed_permission_classes
            return argparse.Namespace(
                status="CONVERGED_NO_CHANGE", blocked_reason=None, decisions=[]
            )

        monkeypatch.setattr(loop_module, "supervise_repo", _fake_supervise_repo)

        args = argparse.Namespace(
            repo="org/repo",
            durable_state=False,  # deliberately NOT passed -- the profile alone must force it
            domain=None,
            execution_profile="github_observe",
        )
        assert cmd_supervise(args) == 0
        assert captured["state_backend"] is sentinel_backend
        assert captured["allowed_permission_classes"] == {"read_only_local", "read_only_network"}

    def test_duplicate_github_run_id_short_circuits_without_calling_supervise_repo(
        self, monkeypatch
    ):
        """Wave 9.5 (`RUN-006`): a re-dispatch of the SAME GitHub Actions run (identical
        `GITHUB_RUN_ID`) must not re-execute the full run."""
        import readme_agent.env as env
        import readme_agent.state.git_backend as git_backend_module
        import readme_agent.supervisor.loop as loop_module

        _stub_preflight_ok(monkeypatch)

        class _MiniFakeBackend:
            """Just enough of the `StateBackend` Protocol for trigger recording."""

            def __init__(self):
                self._state = None

            def load(self, org_repo):
                return self._state

            def save(self, org_repo, state, expected_version):
                from readme_agent.state.backend import SaveResult

                current_version = self._state.state_version if self._state else None
                if expected_version != current_version:
                    return SaveResult(outcome="stale", new_version=current_version)
                new_version = (current_version or 0) + 1
                self._state = state.model_copy(update={"state_version": new_version})
                return SaveResult(outcome="saved", new_version=new_version)

            def acquire_lock(self, org_repo):
                from readme_agent.state.backend import Lock

                return Lock(org_repo=org_repo, holder_id="fake", leased_until="9999-01-01T00:00:00")

            def release_lock(self, lock):
                pass

        backend = _MiniFakeBackend()
        monkeypatch.setattr(git_backend_module, "default_state_backend", lambda: backend)
        monkeypatch.setattr(env, "github_run_id", lambda: "run-42")
        monkeypatch.setattr(env, "github_event_name", lambda: "workflow_dispatch")

        call_count = {"n": 0}

        def _fake_supervise_repo(repo, *, state_backend=None, allowed_permission_classes=None):
            call_count["n"] += 1
            return argparse.Namespace(
                status="CONVERGED_NO_CHANGE", blocked_reason=None, decisions=[]
            )

        monkeypatch.setattr(loop_module, "supervise_repo", _fake_supervise_repo)

        args = argparse.Namespace(
            repo="org/repo", durable_state=False, domain=None, execution_profile="github_observe"
        )
        assert cmd_supervise(args) == 0
        assert cmd_supervise(args) == 0  # same GITHUB_RUN_ID -- must be deduplicated
        assert call_count["n"] == 1


class TestAuthorizationValidateCommand:
    """Wave 13.2 (`AUTH-001`-`006`): diagnostic, read-only -- never itself
    grants authority."""

    def test_parses_required_repo_flag(self):
        args = _build_parser().parse_args(["authorization-validate", "--repo", "acme/widget"])
        assert args.repo == "acme/widget"

    def test_missing_repo_flag_exits_nonzero(self):
        with pytest.raises(SystemExit):
            _build_parser().parse_args(["authorization-validate"])

    def test_no_record_reports_honestly_and_exits_zero(self, tmp_path, monkeypatch, capsys):
        from readme_agent import commands
        from readme_agent.authorization import registry as auth_registry

        monkeypatch.setattr(auth_registry, "AUTHORIZATION_DIR", tmp_path)
        args = argparse.Namespace(repo="acme/widget")

        exit_code = commands.cmd_authorization_validate(args)

        assert exit_code == 0
        assert "no authorization record filed" in capsys.readouterr().out

    def test_real_record_reports_covered_effect_classes(self, tmp_path, monkeypatch, capsys):
        import yaml

        from readme_agent import commands
        from readme_agent.authorization import registry as auth_registry

        monkeypatch.setattr(auth_registry, "AUTHORIZATION_DIR", tmp_path)
        (tmp_path / "acme__widget.yml").write_text(
            yaml.safe_dump(
                {
                    "repository": "acme/widget",
                    "effect_classes": ["PR_BRANCH_PUSH"],
                    "branch_pattern": "*",
                    "approving_identity": "a@example.com",
                    "rollback": "n/a",
                }
            ),
            encoding="utf-8",
        )
        args = argparse.Namespace(repo="acme/widget")

        exit_code = commands.cmd_authorization_validate(args)

        output = capsys.readouterr().out
        assert exit_code == 0
        assert "PR_BRANCH_PUSH: AUTHORIZED" in output
        assert "REPOSITORY_SETTINGS_WRITE: not authorized" in output

    def test_malformed_record_exits_nonzero(self, tmp_path, monkeypatch, capsys):
        from readme_agent import commands
        from readme_agent.authorization import registry as auth_registry

        monkeypatch.setattr(auth_registry, "AUTHORIZATION_DIR", tmp_path)
        (tmp_path / "acme__widget.yml").write_text("{not: valid: yaml:", encoding="utf-8")
        args = argparse.Namespace(repo="acme/widget")

        assert commands.cmd_authorization_validate(args) == 2


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


class TestGoldenSetRunCommand:
    """Wave 13.5 (`OPS-011`/`OPS-012`): live golden-set run + auto-disable
    follow-up -- both the planner client and the state backend are faked
    here (the harness's own real scoring logic against a real corpus is
    proven separately in `test_golden_set.py`; this only proves the CLI
    command's own wiring and exit-code contract)."""

    def test_parses_required_job_flag(self):
        args = _build_parser().parse_args(["golden-set-run", "--job", "supervisor_planning"])
        assert args.job == "supervisor_planning"

    def test_missing_job_flag_exits_nonzero(self):
        with pytest.raises(SystemExit):
            _build_parser().parse_args(["golden-set-run"])

    def _patch_backend(self, monkeypatch, existing=None):
        import readme_agent.state.git_backend as git_backend_module
        from readme_agent.state.schema import ModelRouteStatusV1

        class _FakeBackend:
            def __init__(self):
                self.saved: ModelRouteStatusV1 | None = None
                self._existing = existing

            def load_model_route_status(self, job):
                return self._existing

            def save_model_route_status(self, status):
                self.saved = status

        backend = _FakeBackend()
        monkeypatch.setattr(git_backend_module, "default_state_backend", lambda: backend)
        return backend

    def _patch_planner(self, monkeypatch, tool_calls):
        import readme_agent.llm.planner_client as planner_client_module
        from readme_agent.llm.schema import LLMResponseMeta

        calls = iter(tool_calls)

        class _FakeLivePlannerClient:
            def __init__(self, base_url, api_key, model):
                self.model = model

            def plan(self, messages, tools):
                return planner_client_module.PlannerTurn(
                    tool_call=next(calls), meta=LLMResponseMeta()
                )

        monkeypatch.setattr(planner_client_module, "LivePlannerClient", _FakeLivePlannerClient)

    def test_a_healthy_run_exits_zero_and_does_not_touch_the_route(self, monkeypatch):
        from readme_agent.commands import cmd_golden_set_run
        from readme_agent.golden_set.scenarios import SCENARIOS, STOP

        # Construct the "correct" answer for every real scenario in the
        # shipped corpus, deterministically driving pass_rate to 1.0 --
        # never a hand-waved guess at what a live model would do.
        tool_calls = []
        for scenario in SCENARIOS:
            if scenario.expected_capability_id is not None:
                if scenario.expected_capability_id == STOP:
                    tool_calls.append(None)
                else:
                    tool_calls.append(
                        {
                            "id": "call-1",
                            "function": {
                                "name": scenario.expected_capability_id,
                                "arguments": "{}",
                            },
                        }
                    )
            else:
                # forbidden_capability_id set -- any capability OTHER than
                # the forbidden one passes; "stop" (None) always qualifies.
                tool_calls.append(None)
        self._patch_planner(monkeypatch, tool_calls)
        backend = self._patch_backend(monkeypatch)

        exit_code = cmd_golden_set_run(argparse.Namespace(job="supervisor_planning"))

        assert exit_code == 0
        assert backend.saved is None  # a perfect run must never touch the route

    def test_a_failing_run_below_the_floor_auto_disables_and_exits_nonzero(self, monkeypatch):
        from readme_agent.commands import cmd_golden_set_run
        from readme_agent.golden_set.scenarios import SCENARIOS

        # A capability name that matches no scenario's expectation and is
        # never the forbidden one either -- every scenario is scored against
        # this same wrong-on-purpose answer, driving pass_rate to 0.0,
        # unambiguously below auto_disable.PASS_RATE_FLOOR.
        tool_calls = [
            {"id": "call-1", "function": {"name": "__never_expected__", "arguments": "{}"}}
        ] * len(SCENARIOS)
        self._patch_planner(monkeypatch, tool_calls)
        backend = self._patch_backend(monkeypatch)

        exit_code = cmd_golden_set_run(argparse.Namespace(job="supervisor_planning"))

        assert exit_code == 1
        assert backend.saved is not None
        assert backend.saved.status == "disabled"
        assert backend.saved.job == "supervisor_planning"

    def test_an_already_disabled_route_is_not_touched_again(self, monkeypatch):
        from readme_agent.commands import cmd_golden_set_run
        from readme_agent.golden_set.scenarios import SCENARIOS
        from readme_agent.state.schema import ModelRouteStatusV1

        tool_calls = [
            {"id": "call-1", "function": {"name": "__never_expected__", "arguments": "{}"}}
        ] * len(SCENARIOS)
        self._patch_planner(monkeypatch, tool_calls)
        existing = ModelRouteStatusV1(
            job="supervisor_planning", status="disabled", reason="already disabled by a human"
        )
        backend = self._patch_backend(monkeypatch, existing=existing)

        exit_code = cmd_golden_set_run(argparse.Namespace(job="supervisor_planning"))

        assert exit_code == 0  # nothing NEW was disabled this run
        assert backend.saved is None  # the human's own record was never overwritten


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
