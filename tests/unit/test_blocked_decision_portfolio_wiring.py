"""Portfolio wiring for the blocked-decision cache (2026-08-18 Gate A recovery).

Proves the loop-level contract end to end through `_cmd_supervise_registry`:

1. a live BLOCKED member persists a dependency-bound decision record;
2. the next pass with unchanged fingerprints reuses it -- the canonical
   supervisor is NOT invoked and zero provider calls occur;
3. any fingerprint change (or `--retry-blocked`) forces a live re-run;
4. a live non-blocked outcome clears the record.
"""

from __future__ import annotations

import argparse
from types import SimpleNamespace

import pytest


class _FakeBackend:
    def __init__(self, state=None):
        self._state = state

    def load(self, org_repo):
        return self._state

    def save(self, org_repo, state, expected_version):
        from readme_agent.state.backend import SaveResult

        current_version = self._state.state_version if self._state else None
        new_version = (current_version or 0) + 1
        self._state = state.model_copy(update={"state_version": new_version})
        return SaveResult(outcome="saved", new_version=new_version)


_SOURCE_REVISION = "a" * 40
_DEPS = {"source_revision": _SOURCE_REVISION, "control_plane_fingerprint": "c" * 64}


def _blocked_lifecycle_state():
    from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
    from readme_agent.state.schema import RunStateV2

    return RunStateV2(
        org_repo="org/repo",
        state_version=1,
        readme_poc_lifecycle=ReadmePocLifecycleStateV2(
            org_repo="org/repo",
            source_revision=_SOURCE_REVISION,
            status="FACTS_READY",
        ),
    )


@pytest.fixture()
def _portfolio(monkeypatch, tmp_path):
    """One stubbed single-entry portfolio; returns a namespace of knobs."""

    import readme_agent.gitsafety.clone as clone_module
    import readme_agent.paths as paths
    import readme_agent.registry.loader as loader_module
    import readme_agent.state.git_backend as git_backend_module
    import readme_agent.state.local_poc_backend as local_poc_backend_module
    import readme_agent.supervisor.local_poc_cache as cache_module
    import readme_agent.supervisor.registry_revision_preflight as preflight_module

    entry = argparse.Namespace(
        org_repo="org/repo",
        clone_url="https://example.invalid/org/repo.git",
        ecosystem="python",
        family="note",
        policy_profile=None,
    )
    backend = _FakeBackend(_blocked_lifecycle_state())
    monkeypatch.setattr(loader_module, "load_products", lambda path: (entry,))
    monkeypatch.setattr(git_backend_module, "default_state_backend", lambda: backend)
    monkeypatch.setattr(
        local_poc_backend_module, "default_local_poc_state_backend", lambda: backend
    )
    monkeypatch.setattr(clone_module, "remote_head_sha", lambda clone_url: _SOURCE_REVISION)
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        paths, "readme_poc_portfolio_summary_path", lambda: tmp_path / "summary.json"
    )
    monkeypatch.setattr(
        preflight_module,
        "prepare_registry_revision",
        lambda registry_path, state_backend, **kwargs: SimpleNamespace(
            revision=SimpleNamespace(
                revision_id="a" * 64,
                model_dump=lambda **kw: {"revision_id": "a" * 64},
            ),
            gate=SimpleNamespace(eligible=True, reasons=[]),
        ),
    )
    monkeypatch.setattr(
        cache_module,
        "evaluate_completed_local_poc_cache",
        lambda state, bundle_dir, **kwargs: SimpleNamespace(
            reusable=False, status=None, cache_key="d" * 64
        ),
    )
    # Fingerprint computation is deterministic-but-heavy; pin it so the test
    # controls exactly when "the dependencies changed".
    deps = dict(_DEPS)
    monkeypatch.setattr(
        cache_module,
        "current_blocked_decision_dependencies",
        lambda **kwargs: dict(deps),
    )
    import readme_agent.supervisor.convergence as convergence_module

    monkeypatch.setattr(
        convergence_module, "compute_control_plane_fingerprint", lambda policy_profile: "c" * 64
    )
    return SimpleNamespace(entry=entry, backend=backend, deps=deps, tmp_path=tmp_path)


def _args(**overrides):
    base = dict(
        registry="data/products.json",
        execution_profile="local_poc",
        domain=None,
        resume_trigger_key=None,
        no_registry_heal=True,
        portfolio_time_budget_seconds=300.0,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def _run_live_blocked_pass(monkeypatch, reason="claim accountability has 2 blocking claim(s)"):
    import readme_agent.commands_supervision as supervision_module
    from readme_agent.supervisor.models import SuperviseResult
    from readme_agent.supervisor.task import TaskGraph

    calls: list[str] = []

    def _fake_member_run(member_args):
        calls.append(member_args.repo)
        member_args._terminal_supervise_result = SuperviseResult(
            status="BLOCKED",
            org_repo="org/repo",
            task_graph=TaskGraph(),
            blocked_reason=reason,
            blocked_category="agent_fixable",
        )
        return 1

    monkeypatch.setattr(supervision_module, "cmd_supervise", _fake_member_run)
    exit_code = supervision_module._cmd_supervise_registry(_args())
    return exit_code, calls


def _decision_path(tmp_path):
    return tmp_path / "runs" / "readme-poc" / "org__repo" / "blocked-decision.json"


class TestBlockedDecisionPortfolioWiring:
    def test_live_blocked_outcome_persists_a_dependency_bound_record(self, monkeypatch, _portfolio):
        from readme_agent.supervisor.blocked_decision_cache import load_blocked_decision

        exit_code, calls = _run_live_blocked_pass(monkeypatch)
        assert exit_code == 1
        assert calls == ["org/repo"]
        record = load_blocked_decision(_decision_path(_portfolio.tmp_path))
        assert record is not None
        assert record.blocked_reason == "claim accountability has 2 blocking claim(s)"
        assert record.blocked_category == "agent_fixable"
        assert record.status == "FACTS_READY"
        assert record.dependencies == _DEPS
        assert record.consecutive_count == 1

    def test_unchanged_fingerprints_skip_the_supervisor_with_zero_provider_calls(
        self, monkeypatch, _portfolio, capsys
    ):
        import readme_agent.commands_supervision as supervision_module

        _run_live_blocked_pass(monkeypatch)
        capsys.readouterr()

        monkeypatch.setattr(
            supervision_module,
            "cmd_supervise",
            lambda member_args: (_ for _ in ()).throw(
                AssertionError("blocked-decision reuse must not re-execute the member")
            ),
        )
        exit_code = supervision_module._cmd_supervise_registry(_args())
        assert exit_code == 1  # still blocked -- honestly reported, cheaply
        output = capsys.readouterr().out
        assert "BLOCKED (cached, not re-executed" in output
        assert "claim accountability has 2 blocking claim(s)" in output
        summary = (_portfolio.tmp_path / "summary.json").read_text(encoding="utf-8")
        assert '"llm_call_count": 0' in summary
        assert '"llm_cache_reuse_count": 1' in summary
        assert '"blocked_reason": "claim accountability has 2 blocking claim(s)"' in summary

    def test_a_changed_fingerprint_forces_a_live_re_run_and_recounts(self, monkeypatch, _portfolio):
        from readme_agent.supervisor.blocked_decision_cache import load_blocked_decision

        _run_live_blocked_pass(monkeypatch)
        _portfolio.deps["control_plane_fingerprint"] = "e" * 64

        exit_code, calls = _run_live_blocked_pass(monkeypatch)
        assert exit_code == 1
        assert calls == ["org/repo"]  # live run happened
        record = load_blocked_decision(_decision_path(_portfolio.tmp_path))
        assert record is not None
        assert record.consecutive_count == 2  # same reason reproduced live
        assert record.dependencies["control_plane_fingerprint"] == "e" * 64

    def test_retry_blocked_flag_bypasses_the_cache_without_deleting_it(
        self, monkeypatch, _portfolio
    ):
        import readme_agent.commands_supervision as supervision_module
        from readme_agent.supervisor.blocked_decision_cache import load_blocked_decision
        from readme_agent.supervisor.models import SuperviseResult
        from readme_agent.supervisor.task import TaskGraph

        _run_live_blocked_pass(monkeypatch)

        calls: list[str] = []

        def _fake_member_run(member_args):
            calls.append(member_args.repo)
            member_args._terminal_supervise_result = SuperviseResult(
                status="BLOCKED",
                org_repo="org/repo",
                task_graph=TaskGraph(),
                blocked_reason="claim accountability has 2 blocking claim(s)",
                blocked_category="agent_fixable",
            )
            return 1

        monkeypatch.setattr(supervision_module, "cmd_supervise", _fake_member_run)
        supervision_module._cmd_supervise_registry(_args(retry_blocked=True))
        assert calls == ["org/repo"]
        record = load_blocked_decision(_decision_path(_portfolio.tmp_path))
        assert record is not None
        assert record.consecutive_count == 2

    def test_a_live_non_blocked_outcome_clears_the_record(self, monkeypatch, _portfolio):
        import readme_agent.commands_supervision as supervision_module
        from readme_agent.supervisor.blocked_decision_cache import load_blocked_decision
        from readme_agent.supervisor.models import SuperviseResult
        from readme_agent.supervisor.task import TaskGraph

        _run_live_blocked_pass(monkeypatch)

        # The repaired member now converges; force a live run via --retry-blocked.
        def _fake_member_run(member_args):
            member_args._terminal_supervise_result = SuperviseResult(
                status="CONVERGED_NO_CHANGE",
                org_repo="org/repo",
                task_graph=TaskGraph(),
            )
            return 0

        monkeypatch.setattr(supervision_module, "cmd_supervise", _fake_member_run)
        exit_code = supervision_module._cmd_supervise_registry(_args(retry_blocked=True))
        assert exit_code == 0
        assert load_blocked_decision(_decision_path(_portfolio.tmp_path)) is None
