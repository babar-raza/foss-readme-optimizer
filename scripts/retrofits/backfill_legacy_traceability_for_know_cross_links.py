"""One-shot: freeze pre-edit `traceability` text as `legacy_traceability` for the
11 legacy requirement rows whose `traceability` field gained a Decision 106 /
KNOW-* cross-reference in the 2026-08-19 documentation-reconciliation pass, so
`scripts/governance/validate_compact_authority.py`'s lossless-migration proof
(which reconstructs each legacy row from its `legacy_*` fields, falling back to
the live field only when no `legacy_*` override exists) still recovers the
original pre-migration source text for these rows, matching the existing
convention (e.g. `RDM-018`/`L8-020`/`L8-041` already carry `legacy_traceability`
from an earlier edit).

Edits each target line as a single in-place text substitution (`str.replace`,
count=1) rather than reserializing the whole record: this file mixes
`\\uXXXX`-escaped and raw non-ASCII bytes across rows accumulated over many
separate edits, so any whole-record `json.dumps` reformats bytes on lines this
pass never intended to touch. Preserves the file's exact original line endings
(opened with `newline=""`).

Run once from the repository root:
`python scripts/retrofits/backfill_legacy_traceability_for_know_cross_links.py`
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

# Rows whose live `traceability` this pass edited but which had no pre-existing
# `legacy_traceability` field at HEAD (RDM-018/L8-020/L8-041 already had one
# from an earlier edit and are intentionally excluded).
TARGET_IDS = {
    "FACT-001",
    "FACT-002",
    "FACT-003",
    "FACT-005",
    "FACT-006",
    "LLM-005",
    "VAL-001",
    "VAL-007",
    "NFR-002",
    "L8-018",
    "L8-042",
}


def _head_traceability_by_id() -> dict[str, str]:
    head_text = subprocess.run(
        ["git", "show", f"HEAD:{CATALOG_PATH.relative_to(REPO_ROOT).as_posix()}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    result = {}
    for line in head_text.splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        result[record["requirement_id"]] = record["traceability"]
    return result


def main() -> int:
    head_traceability = _head_traceability_by_id()
    raw = CATALOG_PATH.read_text(encoding="utf-8", newline="")
    lines = raw.split("\n")
    patched = set()
    for i, line in enumerate(lines):
        stripped = line.rstrip("\r")
        if not stripped.strip():
            continue
        record = json.loads(stripped)
        rid = record.get("requirement_id")
        if rid not in TARGET_IDS:
            continue
        if "legacy_traceability" in record:
            raise SystemExit(f"{rid} already has legacy_traceability -- remove from TARGET_IDS")
        if rid not in head_traceability:
            raise SystemExit(f"{rid} not found in HEAD catalog -- cannot backfill")
        marker = '"priority":'
        if stripped.count(marker) != 1:
            raise SystemExit(f"{rid}: expected exactly one {marker!r} in its line")
        insertion = json.dumps(head_traceability[rid], ensure_ascii=True)
        new_stripped = stripped.replace(marker, f'"legacy_traceability":{insertion},{marker}', 1)
        # Round-trip-verify the edited line is still valid JSON with the intended value.
        check = json.loads(new_stripped)
        if check["legacy_traceability"] != head_traceability[rid]:
            raise SystemExit(f"{rid}: round-trip verification failed")
        line_ending = "\r" if line.endswith("\r") else ""
        lines[i] = new_stripped + line_ending
        patched.add(rid)

    missing = TARGET_IDS - patched
    if missing:
        raise SystemExit(f"target IDs not found/patched in catalog: {sorted(missing)}")
    CATALOG_PATH.write_text("\n".join(lines), encoding="utf-8", newline="")
    print(f"backfilled legacy_traceability on {len(patched)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
