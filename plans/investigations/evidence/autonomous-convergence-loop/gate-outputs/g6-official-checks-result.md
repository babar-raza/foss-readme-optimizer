# G6 — official checks, clean tree (proof-eligible)

`.venv/Scripts/python scripts/governance/run_official_checks.py` at HEAD
`68b503342193417dc9f841ed8610d6992c7f6bd4`. Raw log: `g6-official-checks-clean-tree.log`.

**Tree state: TREE CLEAN** — the run's own start/end `git status --porcelain` were both empty and
identical, so unlike the earlier attempts in this sprint this one *is* evidence about a specific
commit.

| Check | Result |
|---|---|
| ruff check | OK |
| ruff format --check | OK |
| mypy src | OK |
| bounded full pytest (complete non-live inventory) | **FAILED (exit 1)** |
| validate_plan_structure.py | OK |
| check_verifiers_are_wired.py --check | OK |
| check_prompt_hygiene.py | OK |
| build_level8_requirement_taskcard_coverage.py --check | OK |
| traceability_matrix.py --check | **FAILED (exit 1)** |
| actionlint | OK |

Overall exit 1.

## The two failures, characterised

**pytest — 2 failed, 5505 passed, 1 skipped** (`runs/acl-verified-count-pytest.log`,
`tree_changed_during_run: false`). Both are the tracked VER-012 pair,
`test_local_poc_repairs_revalidates_and_rereviews_before_accepting` and
`test_local_poc_byte_identical_repair_reroutes_before_rereview`. Baseline at the start of this
sprint was 5 failed / 5498 passed. Exact resume condition is in `logs/2026-08-29.md`: they patch
`build_live_merged_review_client`, but production dispatches the separated role reviewer via
`run_separated_readme_review()`, so nothing rejects and no repair cycle runs. The correct seam is
`build_live_role_review_clients` with the already-written, never-wired `_fake_repair_role_clients`
— but rewiring alone is insufficient, because `_RejectThenAcceptBlindReviewClient`'s bare `next(...)`
calls still assume a review-packet prose shape the bounded reviewer no longer sends. That is the
VER-012 migration proper, and it was deliberately not half-done here.

**traceability_matrix.py — pre-existing, not caused by this sprint.** Three `IMPLEMENTED`
requirement rows cite neither a concrete pytest node nor a committed evidence artifact:
`LLM-023` (introduced by `3e4da1b88`, 2026-08-27), `CORE-041` (`67f66f6d9`, 2026-08-28),
`CORE-042` (`f1efd83a2`, 2026-08-28). All three predate this work and belong to other sessions'
commits. Because this is one of the official checks, it keeps `run_official_checks.py` red
independently of anything done here — worth stating plainly rather than letting "official checks
are red" read as this sprint's doing.

## What changed versus the sprint's first attempt

`validate_plan_structure.py` now passes; it had failed on a `logs/2026-08-29.md` entry-count
mismatch against the shard's own index table, fixed here. The two earlier official-checks attempts
in this sprint are not evidence about any commit: both recorded `TREE DIRTY` / `TREE MODIFIED
DURING RUN` because repair work was still landing while they executed.
