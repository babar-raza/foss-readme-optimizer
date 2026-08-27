#!/usr/bin/env python3
"""One-shot: record why a naive top-N cap on RDM-028's API Method Index is unsafe.

Investigated implementing RDM-028 directly this session (it looked tractable:
a clear design direction already existed in its own requirement text, and it
is confirmed the sole blocker for aspose-3d-foss/Aspose.3D-FOSS-for-.NET).
Traced the interaction with `facts/protected_content.py` before writing any
code and found a real landmine: `fingerprint_protected_content()` captures
every inline-code span (`` `...` ``) in the vendor's ORIGINAL README as its
own `technical_terminology` fragment, hashed individually via exact
normalized-text SHA-256. `document_validation.py`'s protected-content check
(`validate_protected_content()`) requires every such fragment to survive
somewhere in the candidate, with no partial-credit tolerance -- one missing
fragment is one `unauthorized protected-content loss`, a hard validation
failure distinct from (and, per this module's own docstring, the very
requirement) the oversized-unit failure RDM-028 targets.

A naive "sort rows, keep the first N" cap on `api_method_index_markdown()`
could silently drop exactly the rows this table exists to satisfy that gate
for, converting the current, clearly-diagnosed oversized-unit failure into a
protected-content-loss failure that would be much harder to trace back to
this change (it fires in a different validator, keyed by content hash, with
no obvious link to "which row got cut"). This does not invalidate RDM-028's
diagnosis or proposed direction -- it sharpens the "genuine curation-cutoff
decision" framing already in the requirement: any real fix must first
determine, per row, whether that row's identifier text is the sole surviving
match for a real protected-content fragment (in which case it cannot be cut
without another survival path) versus genuinely optional extra coverage --
not a uniform top-N slice. Not attempted further this session; still
correctly BACKLOG/P2, not implemented.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/update_rdm028_protected_content_interaction_risk.py`
Kept after use as the executable record of what was changed (repo layout
placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

EVIDENCE_ADDENDUM = (
    " RDM028-PROTECTED-CONTENT-INTERACTION-RISK-002 (2026-08-27): investigated implementing "
    "this directly (a clear design direction already existed and it is confirmed the sole "
    "blocker for aspose-3d-foss/Aspose.3D-FOSS-for-.NET), but traced the interaction with "
    "facts/protected_content.py before writing code and found a real landmine: "
    "fingerprint_protected_content() captures every inline-code span in the vendor's ORIGINAL "
    "README as its own technical_terminology fragment, hashed individually; "
    "document_validation.py's protected-content check requires every such fragment to survive "
    "somewhere in the candidate, with zero partial-credit tolerance -- exactly the requirement "
    "verified_template_api_method_index.py's own docstring says this table exists to satisfy. "
    "A naive 'sort rows, keep the first N' cap could silently drop exactly the rows this table "
    "exists to protect, converting today's clearly-diagnosed oversized-unit failure into a "
    "protected-content-loss failure in a different validator with no obvious link back to "
    "'which row got cut' -- much harder to trace than the current failure. Does not invalidate "
    "RDM-028's diagnosis; sharpens it: any real fix must first partition rows into "
    "'sole surviving match for a real protected-content fragment' (cannot be cut without "
    "another survival path) versus genuinely optional extra coverage -- not a uniform top-N "
    "slice. Not attempted further; correctly stays BACKLOG/P2."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("requirement_id") != "RDM-028":
            continue
        if "RDM028-PROTECTED-CONTENT-INTERACTION-RISK-002" in record.get("acceptance_evidence", ""):
            print("RDM-028 already updated; nothing to do")
            return
        record["acceptance_evidence"] = record["acceptance_evidence"] + EVIDENCE_ADDENDUM
        lines[index] = json.dumps(record, ensure_ascii=False)
        updated += 1
    if updated != 1:
        raise SystemExit(f"expected exactly one RDM-028 row, found {updated}")
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("RDM-028 updated with protected-content interaction risk")


if __name__ == "__main__":
    main()
