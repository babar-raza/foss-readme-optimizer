#!/usr/bin/env python3
"""One-shot: log the systemic dropped-source-claim resolution coverage gap
found while triaging the L8-PF-05/fleet-final2 portfolio pass on 2026-08-26.

Root-caused via targeted investigation across at least six repositories in
three ecosystems and written up in full at
plans/investigations/evidence/dropped-source-claim-resolution-coverage-gap-2026-08-26/
dropped-source-claim-resolution-coverage-gap-2026-08-26.md, but not fixed
there: both files the fix touches are document-contract-bound
(document_templates.py::DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS), so editing
either invalidates every repository's cached composition plan portfolio-wide
-- unsafe while the fleet-final2-20260826 portfolio pass is actively in
flight. Also a genuine design task (reliable cross-ecosystem detection of a
format/role boilerplate drop), not a mechanical patch.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/log_rdm029_dropped_claim_resolution_gap.py`
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
        "requirement_id": "RDM-029",
        "section": "10. README generation requirements",
        "status": "BACKLOG",
        "priority": "P1",
        "requirement": (
            "The compose/resolution-authoring stage MUST reliably author a "
            "`verified_omission`/`presentation_policy_correction` `SourceClaimResolutionV1` "
            "for every source claim it drops specifically because that claim describes a "
            "format/input/output role the accepted product facts do not authorize for this "
            "FOSS edition -- not only some of them -- so the deterministic claim-accountability "
            "gate does not block on an intentional, correct drop for lack of a recorded "
            "resolution."
        ),
        "acceptance_evidence": (
            "RDM029-DROPPED-CLAIM-RESOLUTION-001: fleet-final2-20260826 portfolio pass shows "
            "'claim accountability has N blocking claim(s): source:claim:...' blocking at "
            "least six repositories across three ecosystems (Python: aspose-page-foss, "
            "aspose-pdf-foss; .NET: aspose-pdf-foss, aspose-cells-foss, aspose-slides-foss, "
            "aspose-words-foss). 16 of 18 observed blocking IDs are source:claim:* (inherited "
            "vendor-README claims dropped from the candidate), almost always co-occurring with "
            "presentation.format_direction_contradiction findings on the same candidate, "
            "confirming the dropped claims are unsupported-format vendor boilerplate the "
            "planner correctly removed but never recorded a resolution for. No auto-repair: "
            "readme_presentation.py's in-run repair loop only fires for a downstream "
            "prose_quality flag, never for a presentation_plan/claim-accountability block, and "
            "escalation_alert confirms consecutive_failure_count as high as 30 for one "
            "repository with no self-healing across fleet passes. Full writeup: "
            "plans/investigations/evidence/"
            "dropped-source-claim-resolution-coverage-gap-2026-08-26/"
            "dropped-source-claim-resolution-coverage-gap-2026-08-26.md. Not fixed directly: "
            "both readme/claim_accountability_helpers.py and readme/document_validation.py "
            "match document_templates.py's DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS, so editing "
            "either invalidates every repository's cached composition plan portfolio-wide -- "
            "unsafe while this exact fleet pass is in flight -- and the fix needs a real design "
            "decision on how resolution-authoring reliably detects a format/role boilerplate "
            "drop across ecosystems, not a mechanical patch."
        ),
        "traceability": (
            "GOV-014; found during L8-PF-05/fleet-final2 portfolio pass triage, 2026-08-26"
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
