#!/usr/bin/env python3
"""One-shot: append precise scope-gap evidence to RDM-029 (still PARTIAL) found
while investigating why "claim accountability" blockers recurred across three
ecosystems (TypeScript/3D, Rust/Cells, .NET/PDF) even after commit 16faa1358's
fix, via a live re-check on aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET on
2026-08-27. Two precise, evidenced scope gaps found:
(1) fenced code examples are categorically excluded from every edit path in
verified_source_policy.py, so a fenced example demonstrating an unauthorized
format direction never gets a resolution authored for it (8/10 previewed
blocking claims for this repo); (2) non-format-direction claim drops (plain
dependency prose) are untouched by the existing fix at all (2/10). Full
writeup: plans/investigations/evidence/dropped-source-claim-resolution-
coverage-gap-2026-08-26/dropped-source-claim-resolution-coverage-gap-
2026-08-26.md. Not implemented here: both gaps need new resolution-authoring
functions (a genuinely sized design task, matching this requirement's
existing PARTIAL status), not a mechanical patch.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/update_rdm029_precise_scope_gaps.py`
Kept after use as the executable record of what was changed (repo layout
placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

EVIDENCE_ADDENDUM = (
    " RDM029-PRECISE-SCOPE-GAPS-002 (2026-08-27): live re-check on "
    "aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET (still 13 blocking claims after commit "
    "16faa1358) found two precise, evidenced scope gaps, not a new mechanism. (1) Fenced "
    "code is categorically excluded from every edit path in "
    "verified_source_policy.py::_visitor_visible() -- correctly, to protect code examples "
    "from silent rewrites -- but this means a fenced example demonstrating an unauthorized "
    'format direction (e.g. a csharp block calling Document.Open("input.pdf") when PDF '
    "input is not accepted-fact-authorized) never gets any accountability path at all: not "
    "an edit (correctly) but also not a verified_omission resolution. 8 of 10 previewed "
    "blocking claims for this repo are exactly this. (2) 2 of 10 are plain "
    "dependency-prose drops with no connection to format direction, confirming the gap is "
    "broader than the one sub-case already fixed. Both need new, narrow "
    "resolution-authoring functions alongside the existing ones in "
    "presentation/verified_source_claim_omissions.py, not a gate change -- sized design "
    "work, keeping this requirement PARTIAL rather than closing it."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("requirement_id") != "RDM-029":
            continue
        if "RDM029-PRECISE-SCOPE-GAPS-002" in record.get("acceptance_evidence", ""):
            print("RDM-029 already updated; nothing to do")
            return
        record["acceptance_evidence"] = record["acceptance_evidence"] + EVIDENCE_ADDENDUM
        lines[index] = json.dumps(record, ensure_ascii=False)
        updated += 1
    if updated != 1:
        raise SystemExit(f"expected exactly one RDM-029 row, found {updated}")
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("RDM-029 updated with precise scope-gap evidence")


if __name__ == "__main__":
    main()
