"""Live proof of `supervisor.loop.supervise_repo()` -- the production-code
equivalent of Wave 1's spike (`plans/investigations/tools/prove_agentic_loop.py`),
proving the promotion into `src/readme_agent/supervisor/` didn't lose the
live-proven loop mechanics, and goes materially further: real multi-round
planning against the real 4-capability registry, real durable convergence
on a second call via the real `GitStateBackend` (not a fake). Real network,
real LLM gateway calls, real git push to this project's own remote (never a
target repo) -- read-only against the target repository throughout
(`--mode dry_run` semantics; `supervise_repo()` never registers a mutating
capability in Wave 5, see decision #26's addendum).

Leaves real, correct durable state behind for `pdf/java` after this test --
not cleaned up, matching Wave 4's own precedent (this is genuine accepted
production state for a real enabled pilot, not disposable test data).

CAUTION: run only with explicit confirmation. See
`tests/integration/test_state_git_backend_live.py`'s docstring for the local
push-credential prerequisite (`OPS-009`) this file shares -- without it,
`GitStateBackend`'s `git push` calls block silently and indefinitely with no
error, confirmed again on 2026-07-19 when this exact file hit it.
"""

import pytest

from readme_agent.llm.planner_client import LivePlannerClient
from readme_agent.state.git_backend import GitStateBackend
from readme_agent.supervisor.loop import supervise_repo

ORG_REPO = "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java"  # allow-listed, mode: dry_run pilot


@pytest.mark.live
def test_live_multi_round_supervise_converges_without_hitting_the_turn_bound():
    from readme_agent import env

    planner = LivePlannerClient(
        env.llm_base_url(), env.llm_api_key(), env.llm_model_for_job("supervisor_planning")
    )

    result = supervise_repo(ORG_REPO, planner_client=planner, write_evidence_bundle=True)

    # AGT-004: must reach a real stop condition, not the repair_exhausted
    # bug-detector bound -- that would mean the live planner got stuck.
    assert result.status != "BLOCKED" or result.blocked_reason != "repair_exhausted"
    assert len(result.task_graph.tasks) >= 1  # at least the deterministic bootstrap
    assert any(t.capability_id == "inspect_repository" for t in result.task_graph.tasks.values())
    # AGT-003: every decision recorded, not just hidden model reasoning.
    assert len(result.decisions) >= 2  # bootstrap + at least the final stop


@pytest.mark.live
def test_live_second_call_converges_durably_with_zero_planning_calls():
    """VER-003 against the real backend: a second `supervise_repo()` call
    for the same, unchanged upstream repo must recognize the accepted
    record from the first live run and never even construct a live planner
    call."""
    backend = GitStateBackend()

    first = supervise_repo(
        ORG_REPO,
        planner_client=LivePlannerClient(*_planner_args()),
        state_backend=backend,
        write_evidence_bundle=True,
    )
    assert first.status != "BLOCKED" or first.blocked_reason != "repair_exhausted"

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
    assert second.task_graph.tasks == {}


def _planner_args() -> tuple[str, str | None, str]:
    from readme_agent import env

    return env.llm_base_url(), env.llm_api_key(), env.llm_model_for_job("supervisor_planning")
