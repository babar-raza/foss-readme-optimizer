#!/usr/bin/env python3
"""One-shot: add two more pre-existing test failures to VER-013, found while
regression-testing the RDM-030 `ID`/`Id` case-collision disambiguation fix on
2026-08-27:
test_verified_template_sections.py::test_absent_distribution_fact_returns_none
and
test_verified_template_sections.py::test_unverified_distribution_fact_returns_none.

Confirmed pre-existing and unrelated via the same git-stash isolation method
already used for VER-013's other entries: both reproduce identically with the
new change (verified_template_api_reference.py's duplicate-description
disambiguation) fully reverted -- that change never touches
verified_template_sections.py or dependency_markdown().

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/update_ver013_add_dependency_markdown_tests.py`
Kept after use as the executable record of what was changed (repo layout
placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

NEW_REQUIREMENT = (
    "Eight failing unit tests found during unrelated regression testing on "
    "2026-08-26/27 MUST be root-caused and either fixed or, if their expectations are "
    "themselves stale, updated: "
    "`test_verified_source_assurance.py::test_api_disclosure_shell_is_structural_and_"
    "compatibility_is_correctable`, "
    "`test_verified_source_opening.py::test_verified_pdf_opening_keeps_source_and_"
    "audience_provenance_exact`, "
    "`test_repository_presentation_template.py::test_verified_template_omits_missing_"
    "compatibility_from_installation_binding`, "
    "`test_public_candidate_quality_registry.py::"
    "test_checks_source_hash_matches_recorded_version`, "
    "`test_verified_template_api_descriptions.py::"
    "test_spreadsheet_io_and_encryption_functions_have_concrete_descriptions`, "
    "`test_verified_template_structural_lineage.py::"
    "test_diagram_derives_every_explicit_import_export_output_without_dangling_text`, "
    "`test_verified_template_sections.py::test_absent_distribution_fact_returns_none`, and "
    "`test_verified_template_sections.py::test_unverified_distribution_fact_returns_none`."
)
NEW_EVIDENCE_ADDENDUM = (
    " VER013-STALE-TESTS-004 (2026-08-27): the two dependency_markdown/"
    "test_verified_template_sections.py tests also found pre-existing via the same "
    "stash-isolation method, while regression-testing an unrelated "
    "verified_template_api_reference.py duplicate-description disambiguation fix "
    "(RDM-030's second collision mechanism, `ID` vs `Id`). Both reproduce identically "
    "with that change fully reverted."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("requirement_id") != "VER-013":
            continue
        if "VER013-STALE-TESTS-004" in record.get("acceptance_evidence", ""):
            print("VER-013 already updated; nothing to do")
            return
        record["requirement"] = NEW_REQUIREMENT
        record["acceptance_evidence"] = record["acceptance_evidence"] + NEW_EVIDENCE_ADDENDUM
        lines[index] = json.dumps(record, ensure_ascii=False)
        updated += 1
    if updated != 1:
        raise SystemExit(f"expected exactly one VER-013 row, found {updated}")
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("VER-013 updated with two more pre-existing failures")


if __name__ == "__main__":
    main()
