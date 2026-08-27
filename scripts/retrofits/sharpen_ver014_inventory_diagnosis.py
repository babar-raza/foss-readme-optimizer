#!/usr/bin/env python3
"""One-shot: sharpen VER-014's evidence with the exact mismatch mechanism found via live
debug instrumentation (temporarily added to loop.py/local_poc_cache.py, fully reverted
before this script ran -- confirmed via `git status --short` showing a clean tree).

Found while continuing the autonomous mission-execution phase on 2026-08-27/28, right
after landing VER-012's fix (commit 2f8f8b09d) and confirming VER-014's existence via a
fresh clean full-suite baseline (4 failed, 5458 passed, 1 skipped -- the 3 VER-014 tests
plus RDM-034, zero new regressions).

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/sharpen_ver014_inventory_diagnosis.py`
Kept after use as the executable record of what was appended (repo layout placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

ADDENDUM = (
    " VER014-INVENTORY-MISMATCH-002 (2026-08-27, autonomous execution phase): traced "
    "`test_local_poc_records_snapshot_and_profile_before_later_stages`'s exact failure "
    "mechanism via temporary debug prints in `loop.py` (reverted before commit, confirmed "
    "clean via `git status --short`). The pre-clone no-op reuse gate "
    "(`loop.py`'s Wave 8.5 block) IS reached and IS condition-satisfied on the second "
    "`supervise_repo()` call (`prior_full_state.readme_poc_lifecycle.status == "
    "'AGENT_APPROVED'` holds), but `promote_approved_local_poc_noop()` returns "
    "`promoted=False` with `decision.mismatch_reasons == ['artifact_inventory_invalid']` -- "
    "the single reason `_evaluate_local_poc_cache()`'s (`local_poc_cache.py`) inventory "
    "check appends when `_inventory_valid(bundle_dir, expected)` returns False. Instrumented "
    "`_inventory_valid()` directly: zero extra files, zero digest mismatches -- every "
    "discrepancy is `missing_from_actual`, all 18 of them under "
    "`review/bounded-packet-cache/*.json`. These filenames are recorded verbatim in "
    "`bundle_dir/sha256sums.txt` (so they existed on disk at some earlier point during the "
    "first `supervise_repo()` call, when `refresh_sha256sums(bundle_dir)` last ran) but do "
    "not exist on disk by the time the second call's inventory check runs. Not yet "
    "determined: the exact call site that removes them, or whether that removal is itself "
    "correct-but-unaccounted-for (a plausible working hypothesis, not confirmed: "
    "`local_poc_review_cache_preservation.py`'s own docstring already documents packet-cache "
    "contents as 'only an execution optimization and never acceptance' -- if some later step "
    "legitimately prunes them post-approval without re-running `refresh_sha256sums()`, "
    "`_inventory_valid()`'s blanket `bundle_dir.rglob('*')` comparison would be checking a "
    "directory that was never meant to gate durable acceptance in the first place, which "
    "would make the fix an exclusion in `_inventory_valid()`/`_load_inventory()` rather than "
    "a change to whatever prunes the files). Tracing the exact removal call site is the next "
    "concrete step, not attempted further this session -- `_inventory_valid()` gates whether "
    "`NO_OP_PROVEN` can ever fire, so a wrong fix here has real correctness blast radius and "
    "deserves direct confirmation before landing, not a guess. The `test_local_poc_repairs_"
    "revalidates_and_rereviews_before_accepting` (`AGENT_REVIEWING` count 1 vs 2) and "
    "`test_local_poc_byte_identical_repair_reroutes_before_rereview` "
    "(`CONVERGED_PROPOSAL_READY` vs `BLOCKED`) failures were not re-instrumented this pass; "
    "given all three concern the same no-op/repair-cycle convergence layer, this inventory "
    "finding is a plausible but unconfirmed shared cause for those two as well."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated_lines: list[str] = []
    found = False
    for line in lines:
        record = json.loads(line)
        if record["requirement_id"] == "VER-014":
            found = True
            if "VER014-INVENTORY-MISMATCH-002" not in record["acceptance_evidence"]:
                record["acceptance_evidence"] = record["acceptance_evidence"].rstrip() + ADDENDUM
        updated_lines.append(json.dumps(record, ensure_ascii=False))
    if not found:
        raise SystemExit("VER-014 not found in catalog -- run the row-creation script first")

    CATALOG_PATH.write_text("\n".join(updated_lines) + "\n", encoding="utf-8", newline="\n")
    print("updated VER-014 with the sharpened inventory-mismatch diagnosis")


if __name__ == "__main__":
    main()
