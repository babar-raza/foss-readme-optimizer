#!/usr/bin/env python3
"""One-shot: add a third corroborating data point to FACT-018.

FACT-018 already documents `product.formats` under-reporting proven output
formats for aspose-note-foss/Python and aspose-3d-foss/Python. Live
investigation this session (chasing `format_direction_contradiction` as a
possible high-leverage linter bug) found a third instance in a third
ecosystem: aspose-pdf-foss/Aspose.PDF-FOSS-for-Java. The candidate's prose
accurately describes a real, verified `TiffDevice` class (confirmed present
in the API Method Index) rendering "multi-page TIFF output", but the
selected `product.formats:native-direction-evidence` fact only lists GIF and
BMP as verified outputs -- not TIFF, JPEG, or PNG, even though `JpegDevice`/
`PngDevice` are equally real. Root cause confirmed directly in
`facts/format_direction.py::_verified_example_literal_directions()`: the
"compiled-io-literal" evidence source scans exactly ONE verified example's
source code for output file-path literals: whatever formats that one example
happens to write become "verified"; every other real, working format the
class library supports is invisible to this fact, by construction. This is
not a new gap -- it is FACT-018's already-diagnosed mechanism, confirmed
recurring in a third ecosystem. No fix attempted (consistent with FACT-018's
own status: a prior enum/type-name-based repair was tried and reverted for
contradicting a deliberate safety guard; the fact collectors are inside the
fact-verification contract, so any fix re-stales every cached fact bundle
portfolio-wide).

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/corroborate_fact018_pdf_java_tiff.py`
Kept after use as the executable record of what was changed (repo layout
placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

EVIDENCE_ADDENDUM = (
    " FACT018-THIRD-ECOSYSTEM-CORROBORATION-002 (2026-08-27): a third instance, in a third "
    "ecosystem, found while live-investigating format_direction_contradiction as a possible "
    "high-leverage linter bug (it was not -- the linter is working as designed against a "
    "narrow, honest evidence source). aspose-pdf-foss/Aspose.PDF-FOSS-for-Java's candidate "
    'accurately describes a real, API-verified `TiffDevice` class rendering "multi-page TIFF '
    'output", but the selected product.formats fact lists only GIF and BMP as verified '
    "outputs -- not TIFF, JPEG, or PNG, even though JpegDevice/PngDevice are equally real "
    "classes in the same verified API surface. Root cause confirmed directly in "
    "facts/format_direction.py::_verified_example_literal_directions(): the compiled-io-"
    "literal evidence source scans exactly ONE verified example's source code for output "
    "file-path literals -- whatever formats that one example happens to write become "
    '"verified"; every other real, working format is invisible to this fact by '
    "construction, not because it is unsupported. Confirms this is FACT-018's already-"
    "diagnosed mechanism recurring, not a separate issue -- no new requirement logged, no fix "
    "attempted (consistent with FACT-018's own status and the prior reverted fix attempt)."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("requirement_id") != "FACT-018":
            continue
        if "FACT018-THIRD-ECOSYSTEM-CORROBORATION-002" in record.get("acceptance_evidence", ""):
            print("FACT-018 already updated; nothing to do")
            return
        record["acceptance_evidence"] = record["acceptance_evidence"] + EVIDENCE_ADDENDUM
        lines[index] = json.dumps(record, ensure_ascii=False)
        updated += 1
    if updated != 1:
        raise SystemExit(f"expected exactly one FACT-018 row, found {updated}")
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("FACT-018 updated with third-ecosystem corroboration")


if __name__ == "__main__":
    main()
