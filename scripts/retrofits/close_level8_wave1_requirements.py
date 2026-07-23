"""Reconcile Level-8 Wave 1 requirement rows with verified delivered behavior."""

from __future__ import annotations

import hashlib
from pathlib import Path

REQUIREMENTS = Path("plans/requirements.md")
EXPECTED_SHA256S = {
    "9c86ab2868f63c4f21621d8c8c82234b53fcf07a10d4dd704b2573af8834b364",
    "10db2969408ad7dbc5085d8bacdbc9c47d00ec2a6a130863002c3048f8b00755",
}
EVIDENCE = "`plans/investigations/evidence/level8-wave1-heterogeneous-fail-closed-2026-07-23/`"
REQUIREMENT_TEXT = {
    "OPS-010": (
        "Non-live tests MUST NOT inherit live credentials, access the network, hang after "
        "cancellation, or leave git/Python descendant processes running."
    )
}

UPDATES: dict[str, tuple[str, str]] = {
    "OPS-010": (
        "IMPLEMENTED",
        "Wave 1 closes both mechanisms rather than inferring safety from clean reruns: "
        "`tests/conftest.py` strips every live GitHub/LLM credential from non-live tests, and "
        "`gitsafety/process.py::run_bounded()` launches git non-interactively in an isolated "
        "process group and terminates its exact descendant tree on timeout. "
        "`tests/unit/test_bounded_process.py` creates a real parent plus Python descendant, "
        "times it out, and proves both disappear; the complete non-live suite passes with no "
        "workspace git/Python descendant left behind. Evidence: "
        f"{EVIDENCE}.",
    ),
    "CAP-002": (
        "IMPLEMENTED",
        "The registry is eagerly constructed when the canonical runner imports it; "
        "`list_all()`/`filter_by()` provide enumeration and permission filtering. "
        "`capabilities/compatibility.py` defines one data-driven ecosystem vocabulary, rejects "
        "unknown compatibility declarations at registry construction, and "
        "`registry.filter_compatible()` filters against typed `RepositoryProfile` data. "
        "Dispatcher permission enforcement checks the complete `required_permissions` set, not "
        "only the highest side-effect class. Covered by `tests/unit/test_capabilities.py` and "
        "`tests/unit/test_capability_dispatcher.py`.",
    ),
    "CAP-008": (
        "IMPLEMENTED",
        "`capabilities/contracts.py` materializes a concrete Pydantic input and output model for "
        "every registered capability. Generated input models forbid undeclared arguments; the "
        "dispatcher validates arguments before execution and validates every executor result "
        "before returning `executed`. Custom models such as `OrgRepoOnlyInputV1` retain stronger "
        "field semantics. Registry construction rejects unsupported contract types and missing "
        "output contracts. Tests prove all registered manifests have both models, malformed "
        "`org_repo` and wiring-only arguments fail before execution, and invalid output types "
        "fail closed.",
    ),
    "ORC-005": (
        "IMPLEMENTED",
        "`orchestrator.run_repo()` no longer commits. The local commit primitive moved to "
        "`effects/local_readme_commit.py` and is imported only by the registered "
        "`commit_readme_write` capability; remote branch/PR primitives are used only by "
        "`open_presentation_pr`. Legacy `generate`/`run`/`run-registry` commands route through "
        "`supervise_repo()` with read-only permissions. "
        "`canonical-mutation-path-audit.json` proves those symbol and command call paths, while "
        "`tests/unit/test_commands_compatibility.py` proves non-zero blocked exits. Evidence: "
        f"{EVIDENCE}.",
    ),
    "VER-001": (
        "IMPLEMENTED",
        "The independent `verify_readme_candidate` capability re-derives candidate truth and "
        "mints the run-bound verdict token required by both registered mutation capabilities. "
        "Invalid and valid real-candidate paths were live-proven previously by "
        "`scripts/retrofits/prove_verify_gate_live.py`; nonce replay and missing-verdict tests "
        "remain green. Wave 1 removes the only bypass: `orchestrator.run_repo()` cannot commit, "
        "all legacy commands are supervised read-only façades, and the static canonical-mutation "
        f"audit in {EVIDENCE} finds no alternate commit/push/PR path.",
    ),
    "VER-009": (
        "IMPLEMENTED",
        "`supervisor/convergence.py::final_status()` consumes the complete specialist map before "
        "task-graph convergence, and `supervisor/planner_loop.py` preserves a known specialist "
        "failure ahead of generic repair exhaustion. Unit tests cover direct errors, raised "
        "specialist exceptions, and max-turn precedence. Live .NET, corrected C++, and Go runs "
        "return `BLOCKED`; Rust returns explicit unsupported/exit 1; the actual earlier .NET, "
        "Python, C++, and Go false-success statuses replay through the current classifier with "
        f"4/4 exact `BLOCKED` results. Evidence: {EVIDENCE}.",
    ),
    "L8-002": (
        "IMPLEMENTED",
        "`supervise_repo()` is the only production repository runtime. `generate`, `run`, and "
        "`run-registry` are compatibility façades that call it with read-only permission classes "
        "and use the canonical terminal exit classifier. `orchestrator.run_repo()` is "
        "non-mutating; local and remote mutation primitives are reachable only through their "
        "registered verifier/authorization/effect-ledger capabilities. Negative command tests "
        f"and the checksum-addressed static call-path audit are in {EVIDENCE}.",
    ),
}


def _replace_row(line: str, requirement_id: str, status: str, acceptance: str) -> str:
    parts = line.split(" | ", 4)
    if len(parts) != 5 or parts[0] != f"| {requirement_id}":
        raise RuntimeError(f"cannot parse requirement row {requirement_id}")
    _old_acceptance, trace = parts[4].rsplit(" | ", 1)
    requirement = REQUIREMENT_TEXT.get(requirement_id, parts[3])
    return " | ".join((parts[0], parts[1], status, requirement, acceptance, trace))


def main() -> None:
    raw = REQUIREMENTS.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest not in EXPECTED_SHA256S:
        raise SystemExit(
            "refusing requirements reconciliation: expected one of "
            f"{sorted(EXPECTED_SHA256S)}, observed {digest}"
        )

    lines = raw.decode("utf-8").splitlines(keepends=True)
    seen: set[str] = set()
    for index, original in enumerate(lines):
        line = original.rstrip("\r\n")
        ending = original[len(line) :]
        for requirement_id, (status, acceptance) in UPDATES.items():
            if line.startswith(f"| {requirement_id} |"):
                lines[index] = (
                    _replace_row(
                        line,
                        requirement_id,
                        status,
                        acceptance,
                    )
                    + ending
                )
                seen.add(requirement_id)
                break
    missing = set(UPDATES) - seen
    if missing:
        raise SystemExit(f"missing requirement rows: {sorted(missing)}")
    REQUIREMENTS.write_text("".join(lines), encoding="utf-8", newline="")


if __name__ == "__main__":
    main()
