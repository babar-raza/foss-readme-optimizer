#!/usr/bin/env python3
"""One-shot: mark RDM-029 PARTIAL now that its fix has landed and been
live-verified (commit 16faa1358), reflecting that it measurably reduces --
but does not alone fully resolve -- the claim-accountability blocker for any
given repository (independent, separate content-generation issues remain).

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/update_rdm029_status_partial.py`
Kept after use as the executable record of what was changed (repo layout
placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("requirement_id") != "RDM-029":
            continue
        if record.get("status") == "PARTIAL":
            print("RDM-029 is already PARTIAL; nothing to do")
            return
        record["status"] = "PARTIAL"
        lines[index] = json.dumps(record, ensure_ascii=False)
        updated += 1
    if updated != 1:
        raise SystemExit(f"expected exactly one RDM-029 row, found {updated}")
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("RDM-029 status updated to PARTIAL")


if __name__ == "__main__":
    main()
