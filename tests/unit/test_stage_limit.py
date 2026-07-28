"""Tests for typed local README proof stage ceilings."""

from readme_agent.supervisor.models import SuperviseResult
from readme_agent.supervisor.stage_limit import evaluate_stage_boundary
from readme_agent.supervisor.status import terminal_exit_code
from readme_agent.supervisor.task import TaskGraph


def test_facts_boundary_accepts_facts_and_later_stages():
    assert evaluate_stage_boundary("FACTS_READY", "FACTS_READY").reached is True
    assert evaluate_stage_boundary("FACTS_READY", "NO_OP_PROVEN").reached is True


def test_facts_boundary_rejects_incomplete_or_blocked_truth():
    assert evaluate_stage_boundary("FACTS_READY", "PROFILED").reached is False
    assert evaluate_stage_boundary("FACTS_READY", "BLOCKED_MISSING_EVIDENCE").reached is False
    assert evaluate_stage_boundary("FACTS_READY", "BLOCKED_FACT_CONFLICT").reached is False


def test_candidate_and_deterministic_boundaries_are_strictly_ordered():
    assert evaluate_stage_boundary("CANDIDATE_GENERATED", "FACTS_READY").reached is False
    assert evaluate_stage_boundary("CANDIDATE_GENERATED", "CANDIDATE_GENERATED").reached is True
    assert evaluate_stage_boundary("CANDIDATE_GENERATED", "DETERMINISTIC_VALIDATED").reached is True
    assert (
        evaluate_stage_boundary("DETERMINISTIC_VALIDATED", "CANDIDATE_GENERATED").reached is False
    )
    assert (
        evaluate_stage_boundary("DETERMINISTIC_VALIDATED", "DETERMINISTIC_VALIDATED").reached
        is True
    )
    assert (
        evaluate_stage_boundary(
            "DETERMINISTIC_VALIDATED",
            "DETERMINISTIC_VALIDATION_FAILED",
        ).reached
        is False
    )


def test_stage_complete_is_a_truthful_successful_process_terminal():
    result = SuperviseResult(
        status="STAGE_COMPLETE",
        org_repo="org/repo",
        task_graph=TaskGraph(),
    )

    assert terminal_exit_code(result) == 0
