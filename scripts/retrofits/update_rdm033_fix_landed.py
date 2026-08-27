#!/usr/bin/env python3
"""One-shot: update RDM-033 after landing a fix (commit 95b162a7e) that
retries section-cluster authoring on LLMTruncatedResponseError, reusing the
existing same-cluster correction loop's repair-hint machinery. Unit-tested
and regression-clean, but not yet confirmed live against a genuine
truncation recurrence (the error is itself nondeterministic, so a single
targeted retry run did not happen to reproduce it). Status stays PARTIAL,
not IMPLEMENTED, until a live fleet pass shows the retry actually recovering
a real truncation.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/update_rdm033_fix_landed.py`
Kept after use as the executable record of what was changed (repo layout
placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

EVIDENCE_ADDENDUM = (
    " RDM033-FIX-LANDED-002 (2026-08-27): fixed in commit 95b162a7e -- extended "
    "specialists/section_cluster_authoring.py's existing same-cluster correction retry loop "
    "(previously only caught ValidationError/SectionAuthoringAcceptanceError) to also catch "
    "LLMTruncatedResponseError, reusing its established repair-hint rebuild with a "
    '"write more concisely" instruction. Cannot regress normal operation: no client/token-'
    "budget change, and the worst case (retry also truncates) degrades to the prior "
    "fail-closed behavior after the same bounded attempt count. Unit-tested "
    "(test_truncated_response_triggers_a_concise_retry_then_succeeds, "
    "test_truncated_response_exhausts_retries_and_fails_closed in "
    "tests/unit/test_section_cluster_authoring.py); broader regression sweep clean (415 "
    "passed, only the 2 already-documented VER-013 pre-existing failures). Live-verified for "
    "safety only (aspose-words-foss/Python retry ran clean) -- that specific run did not "
    "happen to reproduce a real truncation, so live confirmation of the retry actually "
    "recovering one is still pending a natural recurrence. Status kept PARTIAL, not "
    "IMPLEMENTED, until that's observed."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("requirement_id") != "RDM-033":
            continue
        if "RDM033-FIX-LANDED-002" in record.get("acceptance_evidence", ""):
            print("RDM-033 already updated; nothing to do")
            return
        record["status"] = "PARTIAL"
        record["acceptance_evidence"] = record["acceptance_evidence"] + EVIDENCE_ADDENDUM
        lines[index] = json.dumps(record, ensure_ascii=False)
        updated += 1
    if updated != 1:
        raise SystemExit(f"expected exactly one RDM-033 row, found {updated}")
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("RDM-033 updated with fix-landed evidence, status PARTIAL")


if __name__ == "__main__":
    main()
