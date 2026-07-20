"""`ORC-001`: explicit task states, cycle rejection, and the `SUPERSEDED`
dedup rule that makes convergence decidable. No network, no LLM."""

import pytest

from readme_agent.errors import ConfigError
from readme_agent.supervisor.task import Task, TaskGraph


class TestReferentialIntegrity:
    def test_dangling_depends_on_rejected(self):
        graph = TaskGraph()
        with pytest.raises(ConfigError):
            graph.add_task(Task(depends_on=["nonexistent"]))

    def test_duplicate_task_id_rejected(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a"))
        with pytest.raises(ConfigError):
            graph.add_task(Task(task_id=t1.task_id, capability_id="b"))


class TestCycleRejection:
    def test_validate_acyclic_passes_on_a_dag(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a"))
        graph.add_task(Task(capability_id="b", depends_on=[t1.task_id]))
        graph.validate_acyclic()  # must not raise

    def test_validate_acyclic_catches_a_direct_cycle(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a"))
        t2 = graph.add_task(Task(capability_id="b", depends_on=[t1.task_id]))
        # Simulate a cycle by direct mutation -- add_task()'s own per-edge
        # check makes this structurally unreachable through the public API;
        # validate_acyclic() is the independent, whole-graph gate that must
        # still catch it (ORC-001: "before execution", not just at add-time).
        graph.tasks[t1.task_id] = graph.tasks[t1.task_id].model_copy(
            update={"depends_on": [t2.task_id]}
        )
        with pytest.raises(ConfigError):
            graph.validate_acyclic()

    def test_validate_acyclic_catches_a_transitive_cycle(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a"))
        t2 = graph.add_task(Task(capability_id="b", depends_on=[t1.task_id]))
        t3 = graph.add_task(Task(capability_id="c", depends_on=[t2.task_id]))
        graph.tasks[t1.task_id] = graph.tasks[t1.task_id].model_copy(
            update={"depends_on": [t3.task_id]}
        )
        with pytest.raises(ConfigError):
            graph.validate_acyclic()


class TestSupersededDedup:
    def test_repeat_proposal_after_passed_is_superseded_not_redispatched(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a", arguments={"org_repo": "x/y"}))
        graph.mark(t1.task_id, "PASSED", result={"ok": True})

        t2 = graph.add_task(Task(capability_id="a", arguments={"org_repo": "x/y"}))
        assert t2.state == "SUPERSEDED"
        assert t2.supersedes == t1.task_id
        assert t2.result == {"ok": True}

    def test_different_arguments_are_not_deduped(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a", arguments={"org_repo": "x/y"}))
        graph.mark(t1.task_id, "PASSED", result={"ok": True})

        t2 = graph.add_task(Task(capability_id="a", arguments={"org_repo": "other/repo"}))
        assert t2.state == "DISCOVERED"

    def test_dedup_only_applies_to_passed_not_failed(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a", arguments={"org_repo": "x/y"}))
        graph.mark(t1.task_id, "FAILED")

        t2 = graph.add_task(Task(capability_id="a", arguments={"org_repo": "x/y"}))
        assert t2.state == "DISCOVERED"  # not superseded -- the original never passed


class TestReadyTasks:
    def test_task_with_no_deps_is_ready(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a"))
        assert t1 in graph.ready_tasks()

    def test_task_waiting_on_an_unresolved_dep_is_not_ready(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a"))
        t2 = graph.add_task(Task(capability_id="b", depends_on=[t1.task_id]))
        assert t2 not in graph.ready_tasks()

    def test_repair_task_becomes_ready_once_its_failed_dependency_is_terminal(self):
        """The concrete regression this proves: a repair task's sole
        dependency is the FAILED task it repairs, which will never become
        PASSED. Requiring PASSED specifically (not just terminal) would
        strand every repair task forever -- found live via a smoke test
        before this was a regression test."""
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a"))
        graph.mark(t1.task_id, "FAILED")
        repair = graph.add_task(Task(capability_id="a", depends_on=[t1.task_id]))
        assert repair in graph.ready_tasks()


class TestConvergence:
    def test_empty_graph_is_converged(self):
        assert TaskGraph().is_converged()

    def test_all_terminal_is_converged(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a"))
        graph.mark(t1.task_id, "PASSED")
        assert graph.is_converged()

    def test_discovered_task_is_not_converged(self):
        graph = TaskGraph()
        graph.add_task(Task(capability_id="a"))
        assert not graph.is_converged()


class TestSnapshot:
    def test_snapshot_is_json_serializable(self):
        import json

        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a", arguments={"org_repo": "x/y"}))
        graph.mark(t1.task_id, "PASSED", result={"ok": True})
        json.dumps(graph.snapshot())  # must not raise
