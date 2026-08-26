#!/usr/bin/env python3
"""One-shot: log three pre-existing, unrelated test failures found while
regression-testing the RDM-029 fix on 2026-08-26.

Confirmed pre-existing (not caused by that fix) via a direct git-stash
isolation: the identical three failures reproduce with the RDM-029 change
fully reverted. Not root-caused here -- discovered as a side effect of an
unrelated regression sweep, and each looks like a genuinely separate defect
(a claim-risk-counting mismatch vs. two structured-fact-coordinates/binding
mismatches), not one shared cause, so a full investigation is its own task.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/log_ver013_three_preexisting_test_failures.py`
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
        "requirement_id": "VER-013",
        "section": "19. Autonomous runtime and capability requirements",
        "status": "BACKLOG",
        "priority": "P3",
        "requirement": (
            "Three failing unit tests found during unrelated regression testing on "
            "2026-08-26 MUST be root-caused and either fixed or, if their expectations are "
            "themselves stale, updated: "
            "`test_verified_source_assurance.py::test_api_disclosure_shell_is_structural_and_"
            "compatibility_is_correctable`, "
            "`test_verified_source_opening.py::test_verified_pdf_opening_keeps_source_and_"
            "audience_provenance_exact`, and "
            "`test_repository_presentation_template.py::test_verified_template_omits_missing_"
            "compatibility_from_installation_binding`."
        ),
        "acceptance_evidence": (
            "VER013-STALE-TESTS-001: found while regression-testing the RDM-029 fix "
            "(presentation/verified_source_policy.py's new format-direction edit generator). "
            "Confirmed pre-existing and unrelated via git-stash isolation: reverting the "
            "RDM-029 change entirely reproduces the identical three failures, so this is not "
            "a regression from that work. `test_api_disclosure_shell_...` fails a claim-risk "
            "count assertion (`['api_structure'] == ['api_structure', 'api_structure']`, "
            "one fewer risk detected than expected). The other two both fail with a "
            "`structured_fact_coordinates_exact` / binding-lookup `StopIteration` in "
            "provenance matching, but on different fixtures (a real aspose-pdf-foss evidence "
            "bundle vs. a synthetic installation-binding case), so this is plausibly two or "
            "three separate defects, not one shared root cause -- not established here. "
            "Neither test file has been touched since 2026-08-24 "
            "(`df8b56e3b55185c53bd1b85da6274889e77d2c0d`), so production code they depend on "
            "has plausibly moved past their fixtures' expectations since."
        ),
        "traceability": ("GOV-014; found during RDM-029 fix regression testing, 2026-08-26"),
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
