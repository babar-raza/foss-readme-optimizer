"""`AGT-004`: stop only on defined convergence, missing-permission, or
genuine-blocker conditions -- never an arbitrary global iteration limit."""

from readme_agent.capabilities.schema import CapabilityGap
from readme_agent.supervisor.convergence import check_repair_exhausted, final_status, is_fresh
from readme_agent.supervisor.task import Task, TaskGraph


class TestIsFresh:
    def test_matching_revisions_is_fresh(self):
        assert is_fresh("abc123", "abc123")

    def test_different_revisions_is_not_fresh(self):
        assert not is_fresh("abc123", "def456")

    def test_none_recorded_is_not_fresh(self):
        assert not is_fresh(None, "abc123")

    def test_none_current_is_not_fresh(self):
        assert not is_fresh("abc123", None)


class TestCheckRepairExhausted:
    def test_under_max_turns_returns_none(self):
        assert check_repair_exhausted(turns_taken=1, max_turns=8) is None

    def test_at_max_turns_is_blocked_as_a_bug_detector_not_a_normal_stop(self):
        outcome = check_repair_exhausted(turns_taken=8, max_turns=8)
        assert outcome is not None
        assert outcome.status == "BLOCKED"
        assert outcome.blocked_reason == "repair_exhausted"


class TestFinalStatus:
    def test_no_blocked_tasks_converges_no_change(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a"))
        graph.mark(t1.task_id, "PASSED")
        outcome = final_status(graph, applied_any_effect=False)
        assert outcome.status == "CONVERGED_NO_CHANGE"

    def test_applied_effect_converges_applied(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a"))
        graph.mark(t1.task_id, "PASSED")
        outcome = final_status(graph, applied_any_effect=True)
        assert outcome.status == "CONVERGED_APPLIED"

    def test_blocked_task_with_no_other_passed_work_is_blocked(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a"))
        graph.mark(t1.task_id, "BLOCKED", blocked_reason="rejected_permission_denied")
        outcome = final_status(graph, applied_any_effect=False)
        assert outcome.status == "BLOCKED"
        assert outcome.blocked_reason == "rejected_permission_denied"

    def test_blocked_gap_alongside_independent_passed_work_is_partial_with_gap(self):
        """GAP-001's 'continue independent supported work' + GAP-002's exact
        literal status string, proven together."""
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a"))
        graph.mark(t1.task_id, "PASSED")
        t2 = graph.add_task(Task(capability_id="unknown"))
        graph.mark(
            t2.task_id,
            "BLOCKED",
            gap=CapabilityGap(requested_need="x", reason="no match"),
        )
        outcome = final_status(graph, applied_any_effect=False)
        assert outcome.status == "PARTIAL_WITH_CAPABILITY_GAP"

    def test_blocked_gap_with_no_independent_passed_work_is_plain_blocked(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="unknown"))
        graph.mark(
            t1.task_id,
            "BLOCKED",
            gap=CapabilityGap(requested_need="x", reason="no match"),
        )
        outcome = final_status(graph, applied_any_effect=False)
        assert outcome.status == "BLOCKED"
