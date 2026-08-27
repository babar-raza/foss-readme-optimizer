#!/usr/bin/env python3
"""One-shot: mark RDM-030 IMPLEMENTED after both collision mechanisms were repaired
and unit-tested on 2026-08-27 (empty-suffix family-fallback collision in
role_sentence(), and the case-only `ID`/`Id` collision disambiguated in
verified_template_api_reference.py). Live fleet re-verification against
aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET is recorded separately once run.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/update_rdm030_status_fixed.py`
Kept after use as the executable record of what was changed (repo layout
placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

EVIDENCE_ADDENDUM = (
    " RDM030-FIX-002 (2026-08-27): fixed both collision mechanisms. (1) "
    "role_sentence()'s empty-suffix fallback now resolves to the fixed word "
    '"base" instead of public_noun(family), so it can no longer coincide with '
    "a same-family type's explicit-prefix subject; unit-tested "
    "(test_family_fallback_no_longer_collides_with_an_explicit_prefix_sibling). "
    "Live-verified against aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET: this alone "
    "did not clear the repository's blocker -- a second, independent collision "
    "was still present. (2) Found via that live retry: `ID` and `Id` are two "
    "real, distinct .NET classes differing only by letter case; both fall "
    "through role_sentence()'s fully generic fallback and render text that "
    "already differs in case, but presentation_template.py's duplicate check "
    "casefolds before comparing, so they still collided there. Fixed at the "
    "rendering layer (verified_template_api_reference.py's new "
    "_disambiguate_duplicate_descriptions(), which appends each colliding "
    "row's own distinguishing member names, only for rows that actually "
    "collide); unit-tested "
    "(test_case_only_class_name_collision_gets_distinct_descriptions, "
    "test_non_colliding_descriptions_are_left_unmodified in "
    "tests/unit/test_verified_template_api_reference_disambiguation.py). "
    "Direct verification: re-rendering the real 660-row .NET API reference "
    "table now produces 660 unique descriptions (0 duplicates). Full writeup: "
    "plans/investigations/evidence/api-reference-description-name-collision-"
    "2026-08-26/api-reference-description-name-collision-2026-08-26.md."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("requirement_id") != "RDM-030":
            continue
        if "RDM030-FIX-002" in record.get("acceptance_evidence", ""):
            print("RDM-030 already updated; nothing to do")
            return
        record["status"] = "IMPLEMENTED"
        record["acceptance_evidence"] = record["acceptance_evidence"] + EVIDENCE_ADDENDUM
        lines[index] = json.dumps(record, ensure_ascii=False)
        updated += 1
    if updated != 1:
        raise SystemExit(f"expected exactly one RDM-030 row, found {updated}")
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("RDM-030 marked IMPLEMENTED")


if __name__ == "__main__":
    main()
