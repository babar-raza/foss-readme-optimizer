#!/usr/bin/env python3
"""One-shot: log the offline bounded-review retry test-fixture gap found while
fixing three unrelated Windows MAX_PATH bugs on 2026-08-26.

Root-caused with source-level verification (including a live message-shape
dump from the actual failing fixture call) and written up in full at
plans/investigations/evidence/windows-max-path-and-bounded-review-fixture-gaps-2026-08-26/
bounded-review-retry-fixture-gap-2026-08-26.md, but not fixed there: two
independent unknowns remain (why the first bounded-packet attempt fails
grounding in this specific test scenario, and how to reconstruct a schema-valid
response from only the compact retry payload), each large enough to be its own
follow-up task.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/log_ver012_bounded_review_retry_fixture_gap.py`
Kept after use as the executable record of what was appended (repo layout
placement rule 5).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

ROWS: list[dict] = [
    {
        "requirement_id": "VER-012",
        "section": "19. Autonomous runtime and capability requirements",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "The offline bounded-review test fixture "
            "(`tests/review_role_fixture_support.py::GroundedAcceptingRoleReviewClient`) "
            "MUST handle `review_role_execution.py::run_grounded_role()`'s deliberate "
            "compact-grounding-retry message shape (`context_mode='compact_grounding_retry'`, "
            "system message plus one `grounding_retry_context()` reconciliation turn, no "
            "catalog-bearing prompt) in addition to the first-attempt full-prompt shape it "
            "already handles, so tests whose first bounded-review attempt fails grounding "
            "validation do not crash the fixture instead of producing a second, corrected "
            "response."
        ),
        "acceptance_evidence": (
            "VER012-BOUNDED-RETRY-001: `tests/unit/test_supervisor_loop.py::TestBasicLoop::"
            "test_local_poc_records_snapshot_and_profile_before_later_stages` fails with "
            "'fixture reviewer could not find its typed review input' on its second "
            "supervise_repo() call, once bounded review actually executes (after three prior, "
            "independently verified fixes this session removed the Windows MAX_PATH/WinError "
            "145 masking and the missing build_live_role_review_clients fixture wiring ahead "
            "of it). A live dump of the exact `messages` list "
            "GroundedAcceptingRoleReviewClient.analyze() received on the failing call confirmed "
            "only two messages -- system plus a compact retry turn -- with no candidate catalog "
            "text anywhere, matching run_grounded_role()'s own deliberate "
            "`current_messages = [*system messages, retry_message]` reconstruction at "
            "review_role_execution.py:321-324. Full writeup: "
            "plans/investigations/evidence/"
            "windows-max-path-and-bounded-review-fixture-gaps-2026-08-26/"
            "bounded-review-retry-fixture-gap-2026-08-26.md. Not fixed directly: root-causing "
            "why the first bounded-packet attempt fails grounding in this scenario, and safely "
            "reconstructing a grounded response from only the compact retry payload, are each "
            "a genuinely separate investigation from the MAX_PATH fixes that surfaced this."
        ),
        "traceability": (
            "GOV-014; VER-011; found during Windows MAX_PATH investigation, 2026-08-26"
        ),
    },
]


def _synthetic_hash(marker: str) -> str:
    return hashlib.sha256(f"native-authored:{marker}".encode()).hexdigest()


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    existing = {json.loads(line)["requirement_id"] for line in lines}
    new_rows = [row for row in ROWS if row["requirement_id"] not in existing]
    if not new_rows:
        print("no new rows to append (already present)")
        return
    for row in new_rows:
        record = {
            **row,
            "schema_version": 1,
            "legacy_line": len(lines) + 1,
            "legacy_row_sha256": _synthetic_hash(row["requirement_id"]),
        }
        lines.append(json.dumps(record, ensure_ascii=False))
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"appended {len(new_rows)} requirement rows to {CATALOG_PATH}")


if __name__ == "__main__":
    main()
