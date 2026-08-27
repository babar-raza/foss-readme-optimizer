#!/usr/bin/env python3
"""One-shot: append live-verification evidence to RDM-030 after re-running
the actual blocking repository with both fixes committed (2026-08-27).

`readme-agent portfolio-proof --mode fleet --retry-blocked --only
"aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET"` against commit e654a706e no
longer reproduces "API reference contains duplicated descriptions" -- the
repository now advances past presentation compilation into the
presentation_plan review stage, blocked there on a separate, unrelated set
of findings.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/update_rdm030_live_verified.py`
Kept after use as the executable record of what was changed (repo layout
placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

EVIDENCE_ADDENDUM = (
    " RDM030-LIVE-VERIFIED-003 (2026-08-27): readme-agent portfolio-proof "
    '--mode fleet --retry-blocked --only "aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET" '
    'against commit e654a706e (both fixes landed) no longer reproduces "API reference '
    'contains duplicated descriptions" anywhere in the blocking reasons. The repository '
    "now advances past presentation compilation entirely into the presentation_plan "
    "review stage, blocked there on a separate, unrelated set of findings (claim "
    "accountability, code_fence_spacing, format_direction_contradiction, "
    "claim_grounding_negative_fact) -- confirming the fix, not merely the unit tests."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("requirement_id") != "RDM-030":
            continue
        if "RDM030-LIVE-VERIFIED-003" in record.get("acceptance_evidence", ""):
            print("RDM-030 already updated; nothing to do")
            return
        record["acceptance_evidence"] = record["acceptance_evidence"] + EVIDENCE_ADDENDUM
        lines[index] = json.dumps(record, ensure_ascii=False)
        updated += 1
    if updated != 1:
        raise SystemExit(f"expected exactly one RDM-030 row, found {updated}")
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("RDM-030 updated with live-verification evidence")


if __name__ == "__main__":
    main()
