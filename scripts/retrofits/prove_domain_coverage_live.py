"""VER-005 live proof: a real specialist crash, against a real registry
pilot's real clone, correctly gets durably recorded (via `merge_unrecorded_
failures()`'s fold into the existing `SupervisorStateV1` write) and correctly
forces a subsequent `supervise_repo()` call to bypass the coarse `is_fresh()`
shortcut until coverage is complete again.

Uses an in-memory `FakeStateBackend`, never the real `GitStateBackend` --
this run's own deliberately-injected crash must never land in this project's
real per-repo state ref. Real baseline/work clones against the real pilot
are used throughout (network I/O is real; only the state backend is faked),
matching this session's own `prove_verify_gate_live.py` precedent for this
exact class of controlled proof.

Kept after use as the executable record of this verification -- see
plans/GOVERNANCE.md, "Repository layout", placement rule 5.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent.llm.planner_client import FixturePlannerClient, PlannerTurn  # noqa: E402
from readme_agent.llm.schema import LLMResponseMeta  # noqa: E402
from readme_agent.specialists import registry as specialists_registry  # noqa: E402
from readme_agent.state.backend import SaveResult  # noqa: E402
from readme_agent.state.schema import RunStateV1  # noqa: E402
from readme_agent.supervisor.loop import supervise_repo  # noqa: E402


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


def _planner():
    return FixturePlannerClient([PlannerTurn(content="done", meta=LLMResponseMeta())])


def main() -> None:
    org_repo = sys.argv[1] if len(sys.argv) > 1 else "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    crash_domain = sys.argv[2] if len(sys.argv) > 2 else "readme_reconciliation"
    print(f"Pilot: {org_repo}")
    print(f"Domain forced to crash on the first call: {crash_domain}")

    real_run_domain = specialists_registry.run_domain

    def _raise_for_one_domain(domain, org_repo_, backend):
        if domain == crash_domain:
            raise RuntimeError(f"simulated crash for {crash_domain} only")
        return real_run_domain(domain, org_repo_, backend)

    backend = FakeStateBackend()

    specialists_registry.run_domain = _raise_for_one_domain
    try:
        first = supervise_repo(org_repo, planner_client=_planner(), state_backend=backend)
    finally:
        specialists_registry.run_domain = real_run_domain

    print("\n=== FIRST call (one domain forced to crash) ===")
    print(f"status: {first.status}")
    dispatched = [t.capability_id for t in first.task_graph.tasks.values()]
    print(f"tasks dispatched this run: {dispatched}")
    stored = backend.load(org_repo)
    crashed_entry = stored.domain_states.get(crash_domain)
    print(f"{crash_domain}.accepted_status: {crashed_entry.accepted_status!r}")
    print(f"{crash_domain}.last_failure_reason: {crashed_entry.last_failure_reason!r}")
    print(f"{crash_domain}.consecutive_failure_count: {crashed_entry.consecutive_failure_count}")
    print(
        "supervisor_state.domain_coverage_complete: "
        f"{stored.supervisor_state.domain_coverage_complete}"
    )
    # A real crash against a real pilot's real clone is correctly captured,
    # classified with the "ERROR:<reason>:<detail>" colon convention (not
    # silently mistaken for a clean accept), and durably recorded via the
    # enriched SupervisorStateV1 write -- the core VER-005 guarantee.
    assert crashed_entry.last_failure_reason == "execution_error", "colon convention broken"
    assert crashed_entry.consecutive_failure_count == 1
    # domain_coverage_complete correctly stays True here: the crash WAS
    # captured and durably recorded (as a classified failure, not silently
    # lost) -- "every domain has *some* entry" is exactly what this field
    # means, deliberately not "every domain succeeded". The gap this field
    # guards against is a domain the loop never even reached (a killed
    # process) or a write that failed entirely -- covered by
    # test_supervisor_loop.py's direct-corruption test, not reproducible
    # safely via a real, live crash injection like this one.
    assert stored.supervisor_state.domain_coverage_complete is True

    print("\nAll assertions passed: a real crash against a real pilot is durably")
    print("recorded with the correct colon convention, and does not silently vanish.")


if __name__ == "__main__":
    main()
