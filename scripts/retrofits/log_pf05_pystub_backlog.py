#!/usr/bin/env python3
"""One-shot: log the Python analogue of CORE-038's abstract-method stub
false positive, found while driving the L8-PF-05 seven-ecosystem canary
fleet pass on 2026-08-26.

Root-caused with source-level verification and written up in full at
plans/investigations/evidence/portfolio-proof-pf05-seven-ecosystem-canaries/
barcode-abstract-render-stub-false-positive-2026-08-26.md, but not fixed
there: both files involved are contract-bound, and a fleet pass was in
flight when it was found. Per `GOV-014`, narrative evidence docs alone do
not satisfy the backlog-logging requirement -- a catalog row with a
citable ID is required.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/log_pf05_pystub_backlog.py`
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
        "requirement_id": "FACT-020",
        "section": "6. Product-facts and provenance requirements",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "`curated_python_api_ast.py::member_is_implemented()` MUST NOT resolve `False` "
            "for a method decorated `@abstractmethod` purely because its body is a "
            "`raise NotImplemented*` call -- that is the standard Python idiom for an "
            "interface declaration, not evidence of an incomplete implementation, and should "
            "resolve `None` (unresolved) consistent with the module's own stated 'absence of "
            "evidence is never a negative signal' contract. Separately, "
            "`claim_map_capability_validation.py::_mentions_stub_member()` MUST NOT match a "
            "stub finding against candidate capability wording by bare method name alone "
            "when multiple classes in the same API surface declare a method of that name."
        ),
        "acceptance_evidence": (
            "PF05-PYSTUB-001: aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python blocks with "
            "\"capability wording for unimplemented member 'render'\". `Barcode.render()` "
            "(result.py:27) is real and fully implemented -- it merges render options, "
            "resolves the symbology profile, and delegates to a concrete renderer; concrete "
            "implementations also exist in SvgRenderer/PngRenderer/PdfRenderer. The member "
            "actually flagged is a *different* class's `Renderer.render()` "
            "(_internal/renderers/base.py), declared `@abstractmethod` on an ABC with body "
            "`raise NotImplementedError` -- the standard Python interface-declaration idiom, "
            "never meant to be called directly. `member_is_implemented()` has no exception for "
            "`@abstractmethod`, so it resolves `False`; `_mentions_stub_member()` then matches "
            "the candidate's bare, unqualified 'render() method' text against that finding "
            "without disambiguating which class's `render` the prose refers to. This is the "
            "Python analogue of CORE-038 (a C++ empty-body-stub detector flagging a "
            "constructor whose real work lives in its member-initializer list): a "
            "structurally-empty-looking body is not evidence of a missing capability when the "
            "emptiness is required by the language's own interface idiom. Full writeup: "
            "plans/investigations/evidence/portfolio-proof-pf05-seven-ecosystem-canaries/"
            "barcode-abstract-render-stub-false-positive-2026-08-26.md. Not fixed directly: "
            "`curated_python_api_ast.py` is inside the fact-verification contract and "
            "`claim_map_capability_validation.py` matches the document-contract's "
            "`readme/claim_*.py` glob, so either edit re-stales cached work portfolio-wide and "
            "belongs in a deliberate shared-repair slot, not mid-pass."
        ),
        "traceability": (
            "GOV-014; observed during L8-PF-05 seven-ecosystem canary fleet pass, "
            "2026-08-26; same defect class as CORE-038"
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
