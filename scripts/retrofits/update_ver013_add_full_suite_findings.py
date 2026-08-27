#!/usr/bin/env python3
"""One-shot: add eight more pre-existing test failures to VER-013, found while
running the FULL unit-test suite for the first time this window (2026-08-27)
as final regression proof for the RDM-030 `ID`/`Id` disambiguation fix:

test_aspose_org_check_battery_source.py::
  test_vendored_check_battery_matches_its_content_addressed_manifest
test_readme_composition_characterization.py::
  test_document_composition_bytes_and_plan_are_characterized (3 parametrized cases:
  aspose-cells-foss/Java, aspose-3d-foss/Java, aspose-pdf-foss/Java)
test_supervisor_loop.py::TestBasicLoop::
  test_local_poc_records_snapshot_and_profile_before_later_stages
  test_local_poc_repairs_revalidates_and_rereviews_before_accepting
  test_local_poc_byte_identical_repair_reroutes_before_rereview
  test_heterogeneous_local_poc_members_share_the_real_supervisor_path

Confirmed pre-existing and unrelated via the same git-stash isolation method
already used for VER-013's other entries: all eight reproduce identically with
verified_template_api_reference.py's duplicate-description disambiguation fix
(RDM-030's second collision mechanism) fully reverted.

Note: the first full-suite run (with a live 34-repo fleet pass running
concurrently) additionally showed six test_agile_execution_controls.py
failures that did NOT reproduce on a clean rerun once the fleet pass had
finished -- those were resource/state contention from the concurrent fleet
process, not real failures, and are NOT logged here.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/update_ver013_add_full_suite_findings.py`
Kept after use as the executable record of what was changed (repo layout
placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

NEW_REQUIREMENT = (
    "Sixteen failing unit tests found during unrelated regression testing on "
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
    "`test_verified_template_sections.py::test_absent_distribution_fact_returns_none`, "
    "`test_verified_template_sections.py::test_unverified_distribution_fact_returns_none`, "
    "`test_aspose_org_check_battery_source.py::"
    "test_vendored_check_battery_matches_its_content_addressed_manifest`, "
    "`test_readme_composition_characterization.py::"
    "test_document_composition_bytes_and_plan_are_characterized` (3 parametrized Java cases), "
    "and `test_supervisor_loop.py::TestBasicLoop::"
    "test_local_poc_records_snapshot_and_profile_before_later_stages`, "
    "`test_local_poc_repairs_revalidates_and_rereviews_before_accepting`, "
    "`test_local_poc_byte_identical_repair_reroutes_before_rereview`, and "
    "`test_heterogeneous_local_poc_members_share_the_real_supervisor_path`."
)
NEW_EVIDENCE_ADDENDUM = (
    " VER013-STALE-TESTS-005 (2026-08-27): eight more failures found running the "
    "FULL unit-test suite (5396 passed, 22 failed) as final regression proof for the "
    "RDM-030 ID/Id disambiguation fix. Six additional test_agile_execution_controls.py "
    "failures seen on that same run did NOT reproduce on a clean rerun once a "
    "concurrently-running live fleet pass had finished -- confirmed resource/state "
    "contention, not real failures, and are not counted here. The remaining eight "
    "(test_aspose_org_check_battery_source.py, test_readme_composition_"
    "characterization.py x3, test_supervisor_loop.py::TestBasicLoop x4) reproduced "
    "identically on a clean rerun and via the same stash-isolation method with the "
    "RDM-030 change fully reverted."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("requirement_id") != "VER-013":
            continue
        if "VER013-STALE-TESTS-005" in record.get("acceptance_evidence", ""):
            print("VER-013 already updated; nothing to do")
            return
        record["requirement"] = NEW_REQUIREMENT
        record["acceptance_evidence"] = record["acceptance_evidence"] + NEW_EVIDENCE_ADDENDUM
        lines[index] = json.dumps(record, ensure_ascii=False)
        updated += 1
    if updated != 1:
        raise SystemExit(f"expected exactly one VER-013 row, found {updated}")
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("VER-013 updated with eight more pre-existing failures")


if __name__ == "__main__":
    main()
