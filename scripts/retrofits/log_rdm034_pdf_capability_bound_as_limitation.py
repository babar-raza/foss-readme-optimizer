#!/usr/bin/env python3
"""One-shot: log RDM-034 -- a verbatim product.capabilities list item gets bound to
product.limitations instead during claim-accountability disposition, found while
autonomously fixing VER-013's remaining CI failures on 2026-08-27.

Also appends VER-013 evidence for the same-session api_disclosure_shell test fix (a
correct, already-landed fix, unrelated to RDM-034 -- both investigated during the same
pass over tests/unit/test_verified_source_assurance.py and
tests/unit/test_verified_source_opening.py).

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/log_rdm034_pdf_capability_bound_as_limitation.py`
Kept after use as the executable record of what was appended (repo layout placement rule 5).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

NEW_ROWS: list[dict] = [
    {
        "requirement_id": "RDM-034",
        "section": "10. README generation requirements",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "Claim-accountability disposition MUST NOT bind a source claim to "
            "`product.limitations` when its text is a verbatim, byte-identical match to a "
            "`product.capabilities` list item -- an exact-text match against the more "
            "specific, positively-framed fact SHOULD take priority over a looser/semantic "
            "match to a paraphrased, negatively-framed one."
        ),
        "acceptance_evidence": (
            "RDM034-CAPABILITY-BOUND-AS-LIMITATION-001 (2026-08-27, autonomous execution "
            "phase): found while fixing VER-013's remaining CI failures. "
            "test_verified_pdf_opening_keeps_source_and_audience_provenance_exact "
            "(tests/unit/test_verified_source_opening.py) fails "
            "validate_claim_accountability_map()'s structured_fact_coordinates_exact check "
            "for real aspose-pdf-foss evidence. Instrumented the validator directly "
            "(temporary debug print at claim_accountability_validation.py's coordinate-"
            "mismatch branch, reverted before commit) to find the exact record: source "
            "claim `- Perform heuristic PDF/A and PDF/UA checks and conversions` "
            "(claim_id source:claim:1351:2f02923bb13c9406). Confirmed directly against the "
            "real fixture (tests/fixtures data, promoted evidence for "
            "aspose-pdf-foss/Aspose-PDF-FOSS-for-Python) that this exact string is a "
            "verbatim item in the accepted product.capabilities fact list, while "
            "product.limitations only has a paraphrased, distinct item ('PDF/A and PDF/UA "
            "checks are heuristic signals, not certification-grade conformance.'). The "
            "accountability record's accepted_fact_ids is "
            "['product.limitations:repository-extension'] with accepted_fact_coordinates "
            "== [] -- the disposition step bound this claim to the limitations paraphrase "
            "instead of (or in addition to) the exact capabilities match, while the "
            "validator's independent structured_fact_coordinates() re-derivation correctly "
            "finds the exact capabilities-item coordinate the disposition step missed. Not "
            "fixed: the actual binding/disposition logic (verified_preservation_"
            "composition.py and its claim-to-fact matching pipeline) was not traced far "
            "enough to identify the exact site choosing 'limitations' over 'capabilities' "
            "for this claim, and a wrong fix risks destabilizing claim-accountability "
            "across the whole portfolio (the same class of risk RDM-029's own investigation "
            "repeatedly flagged for this contract-bound area). Scoped as its own follow-up, "
            "not attempted further this session."
        ),
        "traceability": "GOV-014; found 2026-08-27 fixing VER-013's remaining CI failures",
    },
]

VER013_ADDENDUM = (
    " VER013-FIX-007 (2026-08-27, autonomous execution phase): fixed "
    "test_api_disclosure_shell_is_structural_and_compatibility_is_correctable. A heading "
    "(`## API reference`) never gets its own material claim -- confirmed separately on a "
    "plain heading+body source, so this is not specific to <details> shells. The test's "
    "source now yields exactly one claim (the whole non-empty <details>/<summary> shell) "
    "instead of two; the real assertion (every claim from this shell classifies as "
    "structural, non-entailment-required api_structure) holds regardless of how many "
    "claims the shell is split into, so the count expectation was simply updated. "
    "test_verified_source_assurance.py (19/19) passes; ruff/ruff-format clean. Investigated "
    "test_verified_pdf_opening_keeps_source_and_audience_provenance_exact in the same pass "
    "-- root-caused precisely but not fixed, logged separately as RDM-034 (a real, distinct "
    "defect, not test drift). VER-013 final tally: 11 of the original 16 tracked failures "
    "now fixed with evidence (api_disclosure_shell(1) + composition_characterization(3) + "
    "installation_binding(1) + checks_source_hash(1) + spreadsheet_io(1) + "
    "diagram_derives(1) + absent_distribution(1) + unverified_distribution(1) + "
    "check_battery_manifest(1) = 11). 5 remain: verified_pdf_opening (now precisely "
    "diagnosed as RDM-034, not merely open) and the 4 VER-012 supervisor_loop cases (VER-012's "
    "own separate, already-diagnosed fixture-shape gap)."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    existing_ids = {json.loads(line)["requirement_id"] for line in lines if line.strip()}

    updated_lines: list[str] = []
    for line in lines:
        record = json.loads(line)
        if record["requirement_id"] == "VER-013":
            record["acceptance_evidence"] = record["acceptance_evidence"].rstrip() + VER013_ADDENDUM
        updated_lines.append(json.dumps(record, ensure_ascii=False))

    new_rows = [row for row in NEW_ROWS if row["requirement_id"] not in existing_ids]
    for row in new_rows:
        record = {
            **row,
            "schema_version": 1,
            "legacy_line": len(updated_lines) + 1,
            "legacy_row_sha256": hashlib.sha256(
                f"native-authored:{row['requirement_id']}".encode()
            ).hexdigest(),
        }
        updated_lines.append(json.dumps(record, ensure_ascii=False))

    CATALOG_PATH.write_text("\n".join(updated_lines) + "\n", encoding="utf-8", newline="\n")
    print(f"updated VER-013, appended {len(new_rows)} new row(s)")


if __name__ == "__main__":
    main()
