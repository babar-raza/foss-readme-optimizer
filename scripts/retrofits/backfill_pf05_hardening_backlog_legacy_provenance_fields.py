#!/usr/bin/env python3
"""One-shot: backfill the mandatory legacy-provenance fields on the new
records this session added to the requirements catalog (CORE-035..038,
EVID-006 -- see `log_pf05_mission_controller_hardening_backlog.py`).

`RequirementCatalogRecordV1` (`supervisor/mission_schema.py`) requires
`legacy_line`/`legacy_row_sha256` on every record regardless of status; per
the same convention established by
`scripts/retrofits/backfill_know_legacy_provenance_fields.py` for the
KNOW-001..013 rows, these records were authored directly in JSONL and have
no legacy-document source, so each one gets:

* `legacy_line`: its own 1-indexed line number in `catalog.jsonl`.
* `legacy_row_sha256`: sha256 of a stable, explicit synthetic marker
  (`b"native-authored:{id}"`), matching the KNOW-row backfill exactly.

Idempotent: a record that already carries these fields is left untouched.
Kept after use as the executable record of what was backfilled and why
(repo layout placement rule 5).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS_CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"
TARGET_IDS = {"CORE-035", "CORE-036", "CORE-037", "CORE-038", "EVID-006"}


def _synthetic_hash(marker: str) -> str:
    return hashlib.sha256(f"native-authored:{marker}".encode()).hexdigest()


def backfill_requirements() -> int:
    lines = REQUIREMENTS_CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    changed = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("requirement_id") not in TARGET_IDS:
            continue
        if "legacy_line" in record and "legacy_row_sha256" in record:
            continue
        record["legacy_line"] = index + 1
        record["legacy_row_sha256"] = _synthetic_hash(record["requirement_id"])
        lines[index] = json.dumps(record, ensure_ascii=False)
        changed += 1
    if changed:
        REQUIREMENTS_CATALOG_PATH.write_text(
            "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
        )
    return changed


def main() -> None:
    changed = backfill_requirements()
    print(f"requirements catalog: backfilled {changed} row(s)")


if __name__ == "__main__":
    main()
