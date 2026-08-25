#!/usr/bin/env python3
"""One-shot: log two pre-existing unit-test failures found on clean `main`
while running the impact tier for the PF05 CMake development-commands repair.

Both were verified as pre-existing by stashing the session's own changes and
re-running the two tests against an otherwise clean tree -- they fail
identically with no local modifications, so they are not caused by that
repair. Per `GOV-014` they are logged as `BACKLOG` rather than fixed as
unrequested scope creep or silently narrated.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/log_preexisting_presentation_test_failures_backlog.py`
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
        "requirement_id": "VAL-019",
        "section": "12. Validation and quality gates",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "`tests/unit/test_repository_presentation_template.py::"
            "test_verified_template_omits_missing_compatibility_from_installation_binding` "
            "MUST pass: the installation template provenance SHOULD still expose a binding "
            "whose fact fields are exactly "
            "`{installation.coordinates, installation.verified_acquisition}` when "
            "`product.compatibility` is absent."
        ),
        "acceptance_evidence": (
            "Currently failing on clean `main` with `StopIteration` at "
            "tests/unit/test_repository_presentation_template.py:817 -- no provenance entry "
            "matches that exact fact-field pair. Verified pre-existing on 2026-08-25 by "
            "stashing all local changes and re-running the test against an otherwise clean "
            "tree; it fails identically, so it is unrelated to the PF05 CMake "
            "development-commands repair that surfaced it. Root cause not investigated."
        ),
        "traceability": "GOV-014; observed during L8-PF-05 impact-tier run, 2026-08-25",
    },
    {
        "requirement_id": "VAL-020",
        "section": "12. Validation and quality gates",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "`tests/unit/test_verified_source_assurance.py::"
            "test_api_disclosure_shell_is_structural_and_compatibility_is_correctable` "
            "MUST pass: an API-disclosure `<details>`/`<summary>` shell SHOULD assess as two "
            "`api_structure` claims, not one."
        ),
        "acceptance_evidence": (
            "Currently failing on clean `main`: "
            "`[risk.obligation_id for risk in risks]` yields a single `api_structure` entry "
            "where the test expects two, so either `assess_material_claims()` now merges the "
            "shell into one claim or the expectation is stale. Verified pre-existing on "
            "2026-08-25 by the same stash-and-rerun check as `VAL-019`. Root cause not "
            "investigated; note the claim-count semantics here are the same machinery the "
            "`development_commands` accountability path depends on."
        ),
        "traceability": "GOV-014; observed during L8-PF-05 impact-tier run, 2026-08-25",
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
