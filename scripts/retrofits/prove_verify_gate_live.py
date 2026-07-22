"""Wave 8e live proof: direct before/after comparison of the `VER-001` verify
gate (decision #42) against a real registry pilot, not a synthetic fixture
repo.

Both prior test-level proofs
(`tests/unit/test_specialists.py::test_a_genuinely_invalid_render_is_rejected_and_never_committed`)
and the 2026-07-21 consolidated live-proof pass used either a synthetic
fixture repo or a pilot that was already compliant (`needs_write=False`),
so `verify_readme_candidate` was never actually dispatched against a real,
genuinely-invalid candidate for a real registry pilot. This script closes
that gap using `render_readme_candidate`'s own already-declared
`force_regenerate` input plus `llm_mode="fixture"` (both legitimate,
pre-existing capability inputs -- not a hack) to force a real render against
a real pilot's real policy, with a deliberately non-compliant LLM response
(a real prohibited-terms violation, checked by the real validation
registry) standing in for a real bad model output. This is the same
"real, unmocked invalid render" methodology the existing unit test already
established, just run against the actual registry instead of a fixture repo.

Runs the SAME real, imported (never reimplemented) `_verify_node`/
`_commit_node`/`_record_node` from `specialists/readme_presentation.py`
twice, against the identical forced-invalid render:
  - "BEFORE" graph: render -> commit -> record (skips verify -- this is
    exactly Wave 7g's original 3-node graph, the pre-Wave-8b shape).
  - "AFTER" graph: render -> verify -> commit -> record (the current,
    shipped Wave 8b graph).

Uses an in-memory FakeStateBackend, never the real GitStateBackend -- this
run's own forced/artificial result must never land in this project's real
per-repo state ref. `commit_readme_write`'s own local git commit (if ever
reached) lands only in the pilot's own disposable local work clone, never
pushed (push-neutering is untouched, structural, and unaffected by this
script).

Kept after use as the executable record of this verification -- see
plans/GOVERNANCE.md, "Repository layout", placement rule 5.
"""

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from langgraph.graph import END, START, StateGraph  # noqa: E402

from readme_agent.capabilities.dispatcher import dispatch_tool_call  # noqa: E402
from readme_agent.capabilities.domains import README_PRESENTATION  # noqa: E402
from readme_agent.specialists.readme_presentation import (  # noqa: E402
    _commit_node,
    _record_node,
    _verify_node,
)
from readme_agent.state.backend import SaveResult  # noqa: E402
from readme_agent.state.domain_state import merge_details  # noqa: E402
from readme_agent.state.schema import DomainStateV1, RunStateV1  # noqa: E402

_READ_ONLY_PERMISSIONS = {"read_only_local", "read_only_network"}

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "invalid_relationship_paragraph.json"


class FakeStateBackend:
    """In-memory only -- never touches this project's real remote state ref."""

    def __init__(self):
        self._states: dict[str, RunStateV1] = {}

    def load(self, org_repo):
        return self._states.get(org_repo)

    def save(self, org_repo, state, expected_version):
        current = self._states.get(org_repo)
        current_version = current.state_version if current else None
        if expected_version != current_version:
            return SaveResult(outcome="stale", new_version=current_version)
        new_version = (current_version or 0) + 1
        self._states[org_repo] = state.model_copy(update={"state_version": new_version})
        return SaveResult(outcome="saved", new_version=new_version)

    def acquire_lock(self, org_repo):
        return object()

    def release_lock(self, lock):
        pass


_ACTIVE_FIXTURE_PATH = FIXTURE_PATH


def _render_node_forced(state: DomainStateV1, config) -> dict:
    """Same shape as the real `_render_node`, plus the three inputs that
    force a genuine, real, deliberately-invalid render: `force_regenerate`
    (a declared, real `render_readme_candidate` input, never wired through
    by the specialist today since nothing upstream needs it -- Wave 8a's
    control-plane fingerprint check covers the "control plane changed"
    case), `llm_mode="fixture"` + `fixture_response_path` (accepted but
    deliberately not planner-exposed, exactly as documented in
    `capabilities/render_readme_candidate.py`'s own module docstring)."""
    org_repo = config["configurable"]["org_repo"]
    arguments = {
        "org_repo": org_repo,
        "force_regenerate": True,
        "llm_mode": "fixture",
        "fixture_response_path": str(_ACTIVE_FIXTURE_PATH),
    }
    tool_call = {
        "function": {"name": "render_readme_candidate", "arguments": json.dumps(arguments)}
    }
    dispatch = dispatch_tool_call(
        tool_call, _READ_ONLY_PERMISSIONS, caller_domain=README_PRESENTATION
    )
    if dispatch.outcome != "executed":
        return {"accepted_status": f"ERROR:{dispatch.outcome}:{dispatch.error}"}
    assert dispatch.result is not None
    return {"details": merge_details(state, render_result=dispatch.result)}


def _build_before_graph():
    """Wave 7g's original shape: render -> commit -> record. No verify node
    -- reproduces the pre-Wave-8b defect exactly, using the REAL, current
    `_commit_node`/`_record_node` (imported, not reimplemented)."""
    graph = StateGraph(DomainStateV1)
    graph.add_node("render", _render_node_forced)
    graph.add_node("commit", _commit_node)
    graph.add_node("record", _record_node)
    graph.add_edge(START, "render")
    graph.add_edge("render", "commit")
    graph.add_edge("commit", "record")
    graph.add_edge("record", END)
    return graph.compile()


def _build_after_graph():
    """The current, shipped Wave 8b shape: render -> verify -> commit ->
    record. All four nodes are the REAL module functions."""
    graph = StateGraph(DomainStateV1)
    graph.add_node("render", _render_node_forced)
    graph.add_node("verify", _verify_node)
    graph.add_node("commit", _commit_node)
    graph.add_node("record", _record_node)
    graph.add_edge(START, "render")
    graph.add_edge("render", "verify")
    graph.add_edge("verify", "commit")
    graph.add_edge("commit", "record")
    graph.add_edge("record", END)
    return graph.compile()


def _run(label: str, graph, org_repo: str, work_path: Path) -> DomainStateV1:
    backend = FakeStateBackend()
    result = graph.invoke(
        DomainStateV1(domain=README_PRESENTATION),
        config={"configurable": {"org_repo": org_repo, "backend": backend}},
    )
    final_state = DomainStateV1(**result)

    readme_text = None
    readme_path = work_path / "README.md"
    if readme_path.exists():
        readme_text = readme_path.read_text(encoding="utf-8")

    print(f"\n=== {label} ===")
    print(f"accepted_status:        {final_state.accepted_status!r}")
    print(f"accepted_facts_hash:    {final_state.accepted_facts_hash!r}")
    print(f"details.render_status:  {final_state.details.get('render_status')!r}")
    print(f"details.written:        {final_state.details.get('written')!r}")
    print(f"details.committed:      {final_state.details.get('committed')!r}")
    print(f"details.verification:   {final_state.details.get('verification')!r}")
    print(f"README.md exists on disk in the work clone: {readme_text is not None}")
    if readme_text is not None:
        print(f"README.md length: {len(readme_text)} chars")
    return final_state


def main() -> None:
    global _ACTIVE_FIXTURE_PATH
    mode = sys.argv[1] if len(sys.argv) > 1 else "reject"  # "reject" or "accept"
    org_repo = sys.argv[2] if len(sys.argv) > 2 else "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    if len(sys.argv) > 3:
        _ACTIVE_FIXTURE_PATH = Path(sys.argv[3]).resolve()
    elif mode == "accept":
        _ACTIVE_FIXTURE_PATH = FIXTURE_PATH.parent / "valid_relationship_paragraph.json"
    print(f"Mode: {mode}")
    print(f"Pilot: {org_repo}")
    print(f"Fixture: {_ACTIVE_FIXTURE_PATH}")

    from readme_agent import paths
    from readme_agent.orchestrator import require_permitted

    entry = require_permitted(org_repo)
    work_path = paths.work_dir(entry.org, entry.repo_name)

    if mode == "accept":
        # Only the AFTER graph is meaningful here -- a genuinely compliant
        # forced regeneration has nothing to reject, so BEFORE and AFTER
        # would behave identically. The interesting proof for this mode is
        # that the real verify gate ACCEPTS a genuinely new, valid candidate
        # and the real commit_readme_write capability then actually fires
        # (a real local git commit, never pushed, mode == "full").
        if work_path.exists():
            shutil.rmtree(work_path, ignore_errors=True)
        after_state = _run("AFTER (accept path)", _build_after_graph(), org_repo, work_path)
        print("\n=== Verdict ===")
        print(
            f"accepted_status ERROR-prefixed (should be False): "
            f"{(after_state.accepted_status or '').startswith('ERROR:')}"
        )
        return

    before_state = _run(
        "BEFORE (render -> commit -> record, no verify)", _build_before_graph(), org_repo, work_path
    )

    # Reset the work clone so the AFTER run starts from the same real,
    # untouched baseline as BEFORE did -- otherwise BEFORE's own (bad) write
    # would contaminate AFTER's starting point.
    if work_path.exists():
        shutil.rmtree(work_path, ignore_errors=True)

    after_state = _run(
        "AFTER (render -> verify -> commit -> record)", _build_after_graph(), org_repo, work_path
    )

    before_rejected = (before_state.accepted_status or "").startswith("ERROR:")
    after_rejected = (after_state.accepted_status or "").startswith("ERROR:")
    print("\n=== Verdict ===")
    print(f"BEFORE accepted_status was ERROR-prefixed: {before_rejected}")
    print(f"AFTER  accepted_status was ERROR-prefixed: {after_rejected}")


if __name__ == "__main__":
    main()
