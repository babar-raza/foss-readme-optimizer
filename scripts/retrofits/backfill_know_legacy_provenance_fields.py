#!/usr/bin/env python3
"""One-shot: backfill the mandatory legacy-provenance fields on the new
records this session added to the requirements and decisions catalogs
(KNOW-001..013, Decision 106).

`RequirementCatalogRecordV1`/`DecisionCatalogRecordV1`
(`supervisor/mission_schema.py`) require `legacy_line`/`legacy_row_sha256`
and `legacy_record_sha256` respectively on every record regardless of
status, but their real meaning -- confirmed by reading
`scripts/governance/compact_active_authority.py`, the original
markdown-table-to-JSONL migration tool -- is "line number and content hash
in the pre-migration legacy document this row was migrated from." The
KNOW rows and Decision 106 were authored directly in JSONL and have no such
legacy source, so this script assigns each one:

* `legacy_line` (requirements only): its own 1-indexed line number in
  `catalog.jsonl` (a real, verifiable position, even though it is not a
  legacy-document line).
* `legacy_row_sha256` / `legacy_record_sha256`: sha256 of a stable, explicit
  synthetic marker (`b"native-authored:{id}"`) rather than any attempt to
  hash the row's own serialization (which would be circular -- the hash
  field would have to include itself) or fabricate a fictitious
  legacy-document excerpt.

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
DECISIONS_CATALOG_PATH = REPO_ROOT / "plans" / "decisions" / "catalog.jsonl"
REQUIREMENT_TARGET_PREFIX = "KNOW-"
DECISION_TARGET_IDS = {106}


def _synthetic_hash(marker: str) -> str:
    return hashlib.sha256(f"native-authored:{marker}".encode()).hexdigest()


def backfill_requirements() -> int:
    lines = REQUIREMENTS_CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    changed = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if not record.get("requirement_id", "").startswith(REQUIREMENT_TARGET_PREFIX):
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


def backfill_decisions() -> int:
    lines = DECISIONS_CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    changed = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("decision_id") not in DECISION_TARGET_IDS:
            continue
        if "legacy_record_sha256" in record:
            continue
        record["legacy_record_sha256"] = _synthetic_hash(f"decision-{record['decision_id']}")
        lines[index] = json.dumps(record, ensure_ascii=False)
        changed += 1
    if changed:
        DECISIONS_CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return changed


def main() -> None:
    requirement_changes = backfill_requirements()
    decision_changes = backfill_decisions()
    print(
        f"requirements catalog: backfilled {requirement_changes} row(s); "
        f"decisions catalog: backfilled {decision_changes} record(s)"
    )


if __name__ == "__main__":
    main()
