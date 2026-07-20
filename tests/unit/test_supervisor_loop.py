"""`supervise_repo()` end to end against the real capability registry and
dispatcher, a synthetic local git repo (no network), and a fixture planner
-- a materially harder proof than Wave 1's N=1 spike: multi-round, real
replanning after a real failure, real durable convergence on a second call.
Mirrors `test_orchestrator.py`'s synthetic-local-repo fixture pattern."""

import json

import pytest

from readme_agent.capabilities import registry
from readme_agent.gitsafety._git import run_git
from readme_agent.llm.planner_client import FixturePlannerClient, PlannerTurn
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.state.backend import SaveResult
from readme_agent.state.schema import RunStateV1
from readme_agent.supervisor.loop import supervise_repo

ORG_REPO = "example-foss/Example-FOSS-for-Java"


def _tool_call(call_id: str, capability_id: str, arguments: dict | None = None) -> dict:
    return {
        "id": call_id,
        "function": {"name": capability_id, "arguments": json.dumps(arguments or {})},
    }


def _init_source_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    run_git(["init", "-b", "main"], cwd=path)
    run_git(["config", "user.email", "test@example.com"], cwd=path)
    run_git(["config", "user.name", "Test"], cwd=path)
    (path / "README.md").write_text("# Example FOSS for Java\n", encoding="utf-8")
    (path / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    run_git(["add", "."], cwd=path)
    run_git(["commit", "-m", "initial"], cwd=path)
    return path


def _setup_project_root(tmp_path, source_clone_url: str):
    (tmp_path / "data").mkdir()
    products = [
        {
            "family": "thing",
            "platform": "java",
            "repo_name": "Example-FOSS-for-Java",
            "repo_url": "https://github.com/example-foss/Example-FOSS-for-Java",
            "clone_url": source_clone_url,
            "active": True,
            "discovered_via": "manual",
            "mode": "dry_run",
            "ecosystem": "java",
            "policy_profile": "test-profile",
        }
    ]
    (tmp_path / "data" / "products.json").write_text(json.dumps(products), encoding="utf-8")


class FakeStateBackend:
    def __init__(self):
        self._states: dict[str, RunStateV1] = {}
        self._locks: dict[str, object] = {}

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
        if org_repo in self._locks:
            return None
        lock = object()
        self._locks[org_repo] = lock
        return type("Lock", (), {"org_repo": org_repo})()

    def release_lock(self, lock):
        self._locks.pop(lock.org_repo, None)


@pytest.fixture
def project(tmp_path, monkeypatch):
    source = _init_source_repo(tmp_path / "source")
    _setup_project_root(tmp_path, str(source))
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestBasicLoop:
    def test_bootstrap_then_planner_capability_then_stop_converges(self, project):
        turns = [
            PlannerTurn(
                tool_call=_tool_call("c1", "detect_readme_gaps", {"org_repo": ORG_REPO}),
                meta=LLMResponseMeta(),
            ),
            PlannerTurn(content="done", meta=LLMResponseMeta()),
        ]
        result = supervise_repo(
            ORG_REPO, planner_client=FixturePlannerClient(turns), write_evidence_bundle=False
        )

        assert result.status == "CONVERGED_NO_CHANGE"
        capability_ids = [t.capability_id for t in result.task_graph.tasks.values()]
        assert "inspect_repository" in capability_ids  # the deterministic bootstrap
        assert "detect_readme_gaps" in capability_ids  # the planner's own choice
        assert all(t.state == "PASSED" for t in result.task_graph.tasks.values())

    def test_planner_never_consulted_when_it_would_only_repeat_itself(self, project):
        """SUPERSEDED dedup: asking for the same capability+arguments twice
        short-circuits instead of re-dispatching."""
        turns = [
            PlannerTurn(
                tool_call=_tool_call("c1", "inspect_repository", {"org_repo": ORG_REPO}),
                meta=LLMResponseMeta(),
            ),
            PlannerTurn(content="done", meta=LLMResponseMeta()),
        ]
        result = supervise_repo(
            ORG_REPO, planner_client=FixturePlannerClient(turns), write_evidence_bundle=False
        )
        superseded = [t for t in result.task_graph.tasks.values() if t.state == "SUPERSEDED"]
        assert len(superseded) == 1
        assert superseded[0].capability_id == "inspect_repository"


class TestCapabilityGap:
    def test_unknown_capability_gap_alongside_independent_passed_branch(self, project):
        """GAP-001's 'continue independent supported work' + GAP-002's exact
        literal status string, proven together against the real dispatcher."""
        turns = [
            PlannerTurn(
                tool_call=_tool_call("c1", "totally_unknown_capability", {"org_repo": ORG_REPO}),
                meta=LLMResponseMeta(),
            ),
            PlannerTurn(
                tool_call=_tool_call("c2", "detect_readme_gaps", {"org_repo": ORG_REPO}),
                meta=LLMResponseMeta(),
            ),
            PlannerTurn(content="done", meta=LLMResponseMeta()),
        ]
        result = supervise_repo(
            ORG_REPO, planner_client=FixturePlannerClient(turns), write_evidence_bundle=False
        )

        assert result.status == "PARTIAL_WITH_CAPABILITY_GAP"
        gap_tasks = [t for t in result.task_graph.tasks.values() if t.gap is not None]
        assert len(gap_tasks) == 1
        assert gap_tasks[0].state == "BLOCKED"
        passed = [t for t in result.task_graph.tasks.values() if t.state == "PASSED"]
        assert any(t.capability_id == "detect_readme_gaps" for t in passed)


class TestRepair:
    def test_execution_error_triggers_an_automatic_repair_that_recovers(self, project, monkeypatch):
        """ORC-002/VER-002: a repairable failure creates a repair task and
        the run still converges, without discarding the unrelated
        bootstrap's already-PASSED result."""
        real_executor = registry.get_executor("detect_readme_gaps")
        calls = {"n": 0}

        def flaky(org_repo):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("simulated transient failure")
            return real_executor(org_repo)

        monkeypatch.setitem(registry._EXECUTORS, "detect_readme_gaps", flaky)

        turns = [
            PlannerTurn(
                tool_call=_tool_call("c1", "detect_readme_gaps", {"org_repo": ORG_REPO}),
                meta=LLMResponseMeta(),
            ),
            PlannerTurn(content="done", meta=LLMResponseMeta()),
        ]
        result = supervise_repo(
            ORG_REPO, planner_client=FixturePlannerClient(turns), write_evidence_bundle=False
        )

        assert calls["n"] == 2  # the original attempt + exactly one auto-repair
        assert result.status == "CONVERGED_NO_CHANGE"
        assert any(t.state == "FAILED" for t in result.task_graph.tasks.values())
        assert any(
            t.state == "PASSED" and t.capability_id == "detect_readme_gaps"
            for t in result.task_graph.tasks.values()
        )
        repair_decisions = [d for d in result.decisions if d.kind == "repair"]
        assert len(repair_decisions) == 1


class TestDurableConvergence:
    def test_second_call_with_unchanged_upstream_converges_with_zero_planning_calls(self, project):
        """VER-003, proven against the real freshness check: a
        FixturePlannerClient seeded with zero turns would raise if `.plan()`
        were ever called -- the assertion is structural, not just
        behavioral. `write_evidence_bundle=True` here (unlike the other
        tests in this file) -- matches `orchestrator.py`'s own established
        contract that `write_evidence_bundle=False` means "no side effects
        at all," including no durable write-back (`validate_repo()`'s
        precedent), so the freshness check has nothing to read back from
        without it."""
        backend = FakeStateBackend()
        first = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert first.status == "CONVERGED_NO_CHANGE"

        class _RaisingPlanner:
            def plan(self, messages, tools):
                raise AssertionError("planner must not be consulted on an unchanged rerun")

        second = supervise_repo(
            ORG_REPO,
            planner_client=_RaisingPlanner(),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert second.status == "CONVERGED_NO_CHANGE"
        assert second.task_graph.tasks == {}  # no tasks even attempted


class TestSpecialistDrivenConvergence:
    """Wave 6 (decision #39): a second, registry-driven convergence tier
    ahead of the existing coarse commit-SHA check. The coarse check alone
    would force a full replan on ANY upstream commit, even one that touches
    nothing this tool tracks (README/LICENSE/community files)."""

    def test_upstream_commit_changes_but_tracked_content_unchanged_converges_without_planning(
        self, project
    ):
        backend = FakeStateBackend()
        first = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert first.status == "CONVERGED_NO_CHANGE"

        # An upstream commit that touches nothing the fingerprint tracks.
        source = project / "source"
        (source / "CHANGELOG.md").write_text("Unrelated changelog entry.\n", encoding="utf-8")
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "chore: unrelated"], cwd=source)

        class _RaisingPlanner:
            def plan(self, messages, tools):
                raise AssertionError("planner must not be consulted when nothing tracked changed")

        second = supervise_repo(
            ORG_REPO,
            planner_client=_RaisingPlanner(),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert second.status == "CONVERGED_NO_TRACKED_CHANGE"
        assert second.task_graph.tasks == {}  # no tasks even attempted

    def test_tracked_content_change_falls_through_to_full_planner_loop(self, project):
        backend = FakeStateBackend()
        first = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert first.status == "CONVERGED_NO_CHANGE"

        source = project / "source"
        (source / "README.md").write_text(
            "# Example FOSS for Java\n\nA new paragraph a maintainer added.\n", encoding="utf-8"
        )
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "docs: update"], cwd=source)

        second = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert second.status == "CONVERGED_NO_CHANGE"
        # The bootstrap/planner loop actually ran this time, not short-circuited.
        assert "inspect_repository" in [t.capability_id for t in second.task_graph.tasks.values()]


class TestLockContention:
    def test_lock_already_held_is_blocked_not_silently_ignored(self, project):
        backend = FakeStateBackend()
        held_lock = backend.acquire_lock(ORG_REPO)
        assert held_lock is not None

        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient([]),
            state_backend=backend,
            write_evidence_bundle=False,
        )
        assert result.status == "BLOCKED"
        assert result.blocked_reason == "lock_held"


class TestMaxTurns:
    def test_a_planner_that_never_stops_is_blocked_as_repair_exhausted_not_silently_capped(
        self, project
    ):
        """AGT-004: the bound fires as a labeled BLOCKED reason, not a
        silent stop -- and it takes real, distinct proposals to reach it
        (SUPERSEDED dedup would otherwise short-circuit a naive repeat)."""
        capability_ids = [
            "inspect_repository",
            "detect_readme_gaps",
            "check_install_path",
            "profile_repository",
        ]
        turns = [
            PlannerTurn(
                tool_call=_tool_call(
                    f"c{i}",
                    capability_ids[i % len(capability_ids)] + "_never_matches",
                    {"org_repo": ORG_REPO},
                ),
                meta=LLMResponseMeta(),
            )
            for i in range(20)
        ]
        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(turns),
            write_evidence_bundle=False,
            max_turns=3,
        )
        assert result.status == "BLOCKED"
        assert result.blocked_reason == "repair_exhausted"
