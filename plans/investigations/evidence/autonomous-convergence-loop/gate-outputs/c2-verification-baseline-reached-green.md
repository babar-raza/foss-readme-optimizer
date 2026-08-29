# Cycle 2 — the canonical suite reached green, and what still fails

## The number

`scripts/governance/run_full_pytest.py` on a clean tree at HEAD `af09e2ca8`:

```
outcome_counts: {"deselected": 0, "errors": 0, "failed": 0, "passed": 5507,
                 "skipped": 1, "xfailed": 0, "xpassed": 0}
dirty_tree: false
tree_changed_during_run: false
exit_code: 0            <- pytest's own exit code
```

Sprint baseline was 5 failed / 5498 passed. This is the first fully green run of the sprint.

Two repairs got it there, both in cycle 2:

- **traceability** — `LLM-023`, `CORE-041`, `CORE-042` gained the pytest node citations they lacked
  (commit `99a1ad007`). Every cited node was collected and run green *before* being cited.
- **VER-012** — the reviewer double was migrated to the bounded contract (commit `af09e2ca8`); see
  the separate artifact.

## What still fails, and why it is not a test failure

`run_official_checks.py` exits 1. Nine of ten checks are `OK`. The tenth is:

```
--- bounded full pytest (complete non-live inventory): FAILED (exit 1)
```

…while the very same run reports `failed: 0` and `exit_code: 0`. The sole cause is:

```
leaked_process_ids: [4432, 57664]
error: full pytest left descendant process IDs [4432, 57664]
```

`run_full_pytest.py::_repository_process_ids` (line 104) matches **any** process named
`python`/`pytest` whose command line contains the repository root, and `_matching_process_ids`
diffs that global set before and after the run. There is **no parent or descendant check
anywhere**. Any other python process touching this repository during the run — a second agent, a
second terminal, an IDE test runner — is therefore counted as a leaked descendant.

## Why that is a false positive here, measured rather than assumed

| Run | Concurrent python processes on this repo | `leaked_process_ids` |
|---|---|---|
| baseline (during ad-hoc diagnostics) | 2 | `[14404, 49368]` — 2 |
| official checks (during the independent-verification lane) | 2 | `[4432, 57664]` — 2 |

Sampled directly during the second run:

```
60000|...\.venv\Scripts\python.exe -m pytest tests/unit/test_supervisor_loop.py::TestBasicLoop::test_...
49896|...\.venv\Scripts\python.exe -m pytest tests/unit/test_supervisor_loop.py::TestBasicLoop::test_...
```

Those are the independent-verification lane's own targeted runs — exactly two, matching exactly two
reported "leaks". The count tracks concurrency, not anything the suite did.

## Disposition

Carded as `ACL-PYTEST-LEAK-GUARD-CONCURRENCY` (P0, blocker). Deliberately **not** fixed in this
cycle by deleting or relaxing the guard: real subprocess leaks are what it exists to catch, and
narrowing it correctly needs descendant tracking plus two controls (it must still fail on a
synthetic real leak, and pass with an unrelated concurrent process). That is engineering with a
falsifiable acceptance test, not a one-line edit at the end of a long session.

## Also recorded: a second false red from the same family

The cycle's first baseline run reported 8 failures, 6 of them in
`tests/unit/test_mission_execution_guard.py`. Those are not regressions either. That file reads the
real `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` at fixture time, and
`scripts/governance/build_level8_requirement_taskcard_coverage.py` rewrites exactly that file — it
ran while the suite was in flight. The runner flagged it honestly (`dirty_tree: true`,
`tree_changed_during_run: true`); those flags are disqualifying and the counts underneath them
should not be read. All 7 pass in isolation.

**The rule this earns:** never run the canonical suite concurrently with governance regeneration or
with any other python process against this repository, and treat `dirty_tree` /
`tree_changed_during_run` / an unexplained `leaked_process_ids` as "re-run", not as a result.
