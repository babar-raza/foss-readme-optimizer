import argparse

import pytest

from readme_agent.cli import _build_parser, main
from readme_agent.commands import cmd_supervise


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

        fake_result = argparse.Namespace(
            status=status, blocked_reason=None, decisions=[], org_repo="org/repo"
        )
        monkeypatch.setattr(
            loop_module, "supervise_repo", lambda repo, state_backend=None: fake_result
        )

        args = argparse.Namespace(repo="org/repo", durable_state=False)
        assert cmd_supervise(args) == expected_exit_code
