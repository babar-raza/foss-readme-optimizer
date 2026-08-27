#!/usr/bin/env python3
"""One-shot: record RDM-032's fix (commit f8ba9ab5d) live-verification result.

The fix landed safely (namespace-scoping now actually matches via
section_text, capped at 24 classes/functions, projection_complete_for_namespace
reported truthfully) and 88 focused/regression tests pass. A live retry
against the repository that originally demonstrated the symptom
(aspose-3d-foss/Aspose.3D-FOSS-for-.NET) still fails with the identical
error. Direct inspection of the persisted bounded-review-plan.json shows
why: that repository's oversized unit-0048 is section `api-method-index`
(char_start=32680, char_end=156297 -- 123,617 raw characters alone,
already over the 120,000 budget before any facts payload), not a
per-namespace class table. That is RDM-028's already-known, already-
backlogged finding (a monolithic API Method Index table, deliberately not
mechanically patched pending a curation-cutoff design decision) -- a
distinct root cause RDM-032 was never designed to fix. Confirmed RDM-032's
own target pattern (per-namespace tables, e.g.
`api-reference/asposehtmldom-namespace-aspose_htmldom` at 133,095 required
budget) is real and present elsewhere in the portfolio, so the fix has
genuine value; it simply doesn't single-handedly clear this specific demo
repository.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/update_rdm032_live_verification_cross_references_rdm028.py`
Kept after use as the executable record of what was changed (repo layout
placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

EVIDENCE_ADDENDUM = (
    " RDM032-LIVE-VERIFICATION-006 (2026-08-27): fix committed (f8ba9ab5d), 88 focused/"
    "regression tests pass. Live retry against aspose-3d-foss/Aspose.3D-FOSS-for-.NET "
    "(the repository that originally demonstrated this symptom) still fails identically. "
    "Root cause: that repository's failing unit (unpacketizable-oversized-factual-unit-0048-"
    "table) is section `api-method-index`, whose own raw rendered text is 123,617 characters "
    "-- already over the 120,000 budget before any facts payload -- confirmed via direct "
    "inspection of the persisted bounded-review-plan.json (required_min_budget=127189). This "
    "is RDM-028's already-known, already-backlogged monolithic-index-table finding, not a "
    "per-namespace scoping defect; RDM-032's fix was never designed to address it and "
    "correctly does not. RDM-032's own target pattern is confirmed real and present "
    "elsewhere in the portfolio (e.g. aspose-html-foss/Aspose.HTML-FOSS-for-Python's "
    "`api-reference/asposehtmldom-namespace-aspose_htmldom`, required_min_budget=133095), so "
    "the fix has genuine, verified value even though it does not clear this specific demo "
    "repository. Status: IMPLEMENTED (for its own defect); this repository's actual blocker "
    "is RDM-028, tracked separately."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("requirement_id") != "RDM-032":
            continue
        if "RDM032-LIVE-VERIFICATION-006" in record.get("acceptance_evidence", ""):
            print("RDM-032 already updated; nothing to do")
            return
        record["acceptance_evidence"] = record["acceptance_evidence"] + EVIDENCE_ADDENDUM
        if record.get("status") != "IMPLEMENTED":
            record["status"] = "IMPLEMENTED"
        lines[index] = json.dumps(record, ensure_ascii=False)
        updated += 1
    if updated != 1:
        raise SystemExit(f"expected exactly one RDM-032 row, found {updated}")
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("RDM-032 updated with live-verification result and RDM-028 cross-reference")


if __name__ == "__main__":
    main()
