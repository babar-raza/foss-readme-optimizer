"""Add a companion `local_poc_backend` monkeypatch next to every existing
`git_backend_module.default_state_backend` monkeypatch inside a
`local_poc`-profile test in tests/unit/test_cli.py.

Run once after commands_supervision.py's `_state_backend_for_profile` split
(2026-08-18): `local_poc`-profile invocations now construct their state
backend via `local_poc_backend.default_local_poc_state_backend()`, not
`git_backend.default_state_backend()`, so tests that only stubbed the latter
now fall through to the real, isolated-but-still-real git backend -- correct
in production, but far too slow for a unit test (real `git init --bare` +
`git fetch`/`push` subprocesses against a OneDrive-synced path, well past
`run_git`'s 120s default timeout in this environment). Mirrors each existing
stub so both code paths return the same fake regardless of which one a given
test exercises.
"""

from __future__ import annotations

import re
from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "tests" / "unit" / "test_cli.py"

_LOCAL_POC_TEST_NAMES = {
    "test_bounded_verified_canary_uses_full_local_poc_contract",
    "test_local_poc_member_forces_dynamic_planning_and_cli_lifecycle",
    "test_local_poc_intake_block_stops_before_llm_preflight_and_supervisor",
    "test_intake_stage_limit_writes_complete_zero_call_terminal_evidence",
    "test_not_applicable_intake_is_a_truthful_zero_call_terminal",
    "test_access_block_is_external_and_retryable_without_later_execution",
    "test_facts_stage_runs_heterogeneous_registry_without_promoting_persisted_labels",
    "test_registry_uses_the_canonical_supervisor_for_every_mode_and_isolates_failures",
    "test_frozen_registry_fanout_isolates_failures_and_writes_summary",
    "test_portfolio_recovers_member_completed_before_aggregation_exception",
    "test_registry_pass_automatically_resumes_retryable_member_work",
    "test_registry_pass_does_not_steal_unexpired_active_member",
    "test_registry_pass_checkpoints_a_bounded_execution_slice",
    "test_bounded_registry_pass_skips_current_fact_bundle_and_advances",
    "test_complete_cache_uses_live_revision_and_records_inspectable_key",
    "test_recovered_terminal_member_still_honors_slice_budget",
    "test_local_poc_member_resumes_a_retryable_cli_trigger",
}

_DEF_RE = re.compile(r"^    def (test_\w+)")
_IMPORT_RE = re.compile(r"^(\s*)import readme_agent\.state\.git_backend as git_backend_module\s*$")
_PATCH_RE = re.compile(
    r'^(\s*)monkeypatch\.setattr\(git_backend_module, "default_state_backend", (.+)\)\s*$'
)


def main() -> None:
    lines = TARGET.read_text(encoding="utf-8").split("\n")
    out: list[str] = []
    current_test: str | None = None
    added_import = False
    added_count = 0

    for line in lines:
        def_match = _DEF_RE.match(line)
        if def_match:
            current_test = def_match.group(1)
            added_import = False
        in_target_test = current_test in _LOCAL_POC_TEST_NAMES

        import_match = _IMPORT_RE.match(line)
        if in_target_test and import_match and not added_import:
            indent = import_match.group(1)
            out.append(line)
            out.append(
                f"{indent}import readme_agent.state.local_poc_backend as local_poc_backend_module"
            )
            added_import = True
            continue

        patch_match = _PATCH_RE.match(line)
        if in_target_test and patch_match:
            indent, rhs = patch_match.group(1), patch_match.group(2)
            out.append(line)
            out.append(
                f"{indent}monkeypatch.setattr("
                f'local_poc_backend_module, "default_local_poc_state_backend", {rhs})'
            )
            added_count += 1
            continue

        out.append(line)

    TARGET.write_text("\n".join(out), encoding="utf-8")
    print(f"added {added_count} companion patches")


if __name__ == "__main__":
    main()
