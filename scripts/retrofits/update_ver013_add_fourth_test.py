#!/usr/bin/env python3
"""One-shot: add a fourth pre-existing test failure to VER-013, found while
regression-testing the presentation_lint_format_directions.py fix on
2026-08-27: test_public_candidate_quality_registry.py::
test_checks_source_hash_matches_recorded_version.

Confirmed pre-existing and unrelated via git-stash isolation (identical
failure with that change fully reverted) and via source inspection: the
hashed module set (_CHECK_SOURCE_MODULES in public_quality_registry.py)
does not include presentation_lint_format_directions.py at all -- a
completely disjoint check-registry tripwire. `git log` on the actually-hashed
modules shows their last touch predates this session entirely, so this
version-pinning drift is long-standing, not caused by any 2026-08-26/27 work.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/update_ver013_add_fourth_test.py`
Kept after use as the executable record of what was changed (repo layout
placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

NEW_REQUIREMENT = (
    "Four failing unit tests found during unrelated regression testing on "
    "2026-08-26/27 MUST be root-caused and either fixed or, if their expectations are "
    "themselves stale, updated: "
    "`test_verified_source_assurance.py::test_api_disclosure_shell_is_structural_and_"
    "compatibility_is_correctable`, "
    "`test_verified_source_opening.py::test_verified_pdf_opening_keeps_source_and_"
    "audience_provenance_exact`, "
    "`test_repository_presentation_template.py::test_verified_template_omits_missing_"
    "compatibility_from_installation_binding`, and "
    "`test_public_candidate_quality_registry.py::"
    "test_checks_source_hash_matches_recorded_version`."
)
NEW_EVIDENCE_ADDENDUM = (
    " VER013-STALE-TESTS-002 (2026-08-27): `test_checks_source_hash_matches_recorded_version` "
    "also found pre-existing via the same stash-isolation method, while regression-testing "
    "an unrelated presentation_lint_format_directions.py fix. This one is a version-pinning "
    "tripwire (`public_quality_registry.py::compute_checks_source_hash()`), not a logic bug: "
    "its hashed module set does not include the file that was actually being fixed, and the "
    "modules it does hash (public_quality_semantic_common.py and four siblings) were each "
    "last touched by commits predating this session entirely -- long-standing drift between "
    "PUBLIC_QUALITY_CHECKS_VERSION and its recorded source hash, not something introduced "
    "2026-08-26/27."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("requirement_id") != "VER-013":
            continue
        if "VER013-STALE-TESTS-002" in record.get("acceptance_evidence", ""):
            print("VER-013 already updated; nothing to do")
            return
        record["requirement"] = NEW_REQUIREMENT
        record["acceptance_evidence"] = record["acceptance_evidence"] + NEW_EVIDENCE_ADDENDUM
        lines[index] = json.dumps(record, ensure_ascii=False)
        updated += 1
    if updated != 1:
        raise SystemExit(f"expected exactly one VER-013 row, found {updated}")
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("VER-013 updated with the fourth pre-existing failure")


if __name__ == "__main__":
    main()
