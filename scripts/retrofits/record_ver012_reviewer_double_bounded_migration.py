#!/usr/bin/env python
"""Record the VER-012 reviewer-double migration to the bounded review contract.

VER-012 stays `PARTIAL` on purpose. Its requirement text is specifically about
`GroundedAcceptingRoleReviewClient` handling `run_grounded_role()`'s
`context_mode='compact_grounding_retry'` message shape, and that gap is still open --
`review_role_fixture_support.py` still *avoids* the retry (by picking
`markdown_integrity`, the one criterion every `_CRITERIA_BY_ROOT` entry admits) rather
than handling it.

What this records is the separate defect that the two failing tests actually had, which
the sprint had been tracking under the same VER-012 label: they patched the *merged*
reviewer while routing sent every document-plan-bearing candidate to the bounded/
separated reviewer, so the `project` fixture's always-accepting role clients stayed in
charge and the repair loop was never exercised at all.

Kept after use as the executable record of the edit -- see plans/GOVERNANCE.md,
"Repository layout", placement rule 5.

Run: .venv/Scripts/python scripts/retrofits/record_ver012_reviewer_double_bounded_migration.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

MARKER = "VER012-REVIEWER-DOUBLE-BOUNDED-MIGRATION-001"

EVIDENCE = (
    " " + MARKER + " (2026-08-29, autonomous execution): the two long-tracked failures "
    "`test_supervisor_loop.py::TestBasicLoop::"
    "test_local_poc_repairs_revalidates_and_rereviews_before_accepting` and "
    "`::test_local_poc_byte_identical_repair_reroutes_before_rereview` were not a "
    "compact-grounding-retry gap at all. Both patched "
    "`separated_readme_review.build_live_merged_review_client`, but "
    "`run_merged_readme_review` routes to the bounded/separated reviewer for every "
    "candidate carrying a document plan (6591c6cc2, 'route by rubric evidence, not "
    "candidate size') -- which is every candidate the `project` fixture builds. The "
    "override therefore hit a reviewer that never ran, the fixture's own "
    "always-accepting `_fake_accepting_role_clients` stayed in charge, the candidate was "
    "accepted on the first round, and the repair loop under test was never entered "
    "(`statuses.count('AGENT_REVIEWING') == 1`, not 2). A previous cycle tried rewiring "
    "to `build_live_role_review_clients` alone and correctly reverted it: that moves the "
    "failure to `independent_review_exception:StopIteration`, because "
    "`_RejectThenAcceptBlindReviewClient` was written for the merged reviewer, which sees "
    "the whole candidate in one call. Bounded review sends one packet per section, so "
    "'reject on call 1' meant 'reject whichever section is packed first', and the "
    "double's `next(... startswith('```mermaid'))` raised as soon as that section held no "
    "diagram. Migrated the double to the bounded contract: it now selects the packet that "
    "actually contains the mermaid anchor rather than a call ordinal, and rejects exactly "
    "once. That target is load-bearing, not cosmetic -- "
    "`readme_repair_validation.py::build_repair_receipt` only marks a finding "
    "`addressed_pending_rereview` when the finding's own section text changes, a bound "
    "operation changes, and its quoted span stops occurring, and "
    "`_RepairAwareCompositionForcedToolClient` is the thing that makes all three true by "
    "re-planning that diagram; `rereview_authorized` further requires *every* finding to "
    "be addressed. `product_specificity` remains in-scope under "
    "`bounded_review_visitor_scope.py` (`_COMMON_CRITERIA`, hence "
    "`_CRITERIA_BY_ROOT['at-a-glance']`), so no grounding retry is forced. Assertions "
    "updated to the bounded contract: finding ids are packet-namespaced "
    "(`pkt.visitor.<ordinal>.<section-path>.<hash>.<finding-id>`), and the per-round call "
    "literals were replaced with the relationships they stood for (one rejection; "
    "after-rereview count strictly greater than before; the accepted rerun leaves both "
    "counters untouched) because a fixed number there encodes today's section packing, "
    "not the contract. Proved non-vacuous by restoring the pre-fix wiring in place: both "
    "tests fail, and both pass with the migration. Requirement stays PARTIAL -- the "
    "`compact_grounding_retry` shape named in the requirement text is still avoided "
    "rather than handled."
)


def main() -> int:
    lines = CATALOG.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    found = False
    for line in lines:
        if not line.strip():
            updated.append(line)
            continue
        record = json.loads(line)
        if record.get("requirement_id") != "VER-012":
            updated.append(line)
            continue
        found = True
        evidence = record.get("acceptance_evidence", "")
        if MARKER in evidence:
            print("VER-012: already recorded, left unchanged")
            updated.append(line)
            continue
        record["acceptance_evidence"] = evidence.rstrip() + EVIDENCE
        updated.append(json.dumps(record, ensure_ascii=False))
        print("VER-012: evidence appended (status left PARTIAL)")

    if not found:
        print("error: VER-012 not found in the catalog")
        return 1

    # newline="" keeps the catalog LF-only; the pinned catalog/coverage hashes are
    # computed over these bytes, and a text-mode write would CRLF-ify every record.
    with CATALOG.open("w", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(updated) + "\n")
    print(f"wrote {CATALOG.relative_to(REPO_ROOT).as_posix()} ({len(updated)} records)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
