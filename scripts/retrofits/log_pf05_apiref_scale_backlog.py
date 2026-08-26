#!/usr/bin/env python3
"""One-shot: log the API-Method-Index scale finding from the L8-PF-05
seven-ecosystem canary fleet pass on 2026-08-26.

Root-caused with source-level verification and written up in full at
plans/investigations/evidence/portfolio-proof-pf05-seven-ecosystem-canaries/
api-method-index-exceeds-review-budget-2026-08-26.md, but not fixed there:
the correct fix is a scale/curation policy change to a document-contract-bound
presentation module, needing deliberate product-level judgment about what
"top APIs" means, not a mechanical patch, and a fleet pass was in flight when
it was found.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/log_pf05_apiref_scale_backlog.py`
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
        "requirement_id": "RDM-028",
        "section": "10. README generation requirements",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "The API Method Index producer "
            "(`presentation/verified_template_api_method_index.py`) MUST apply a "
            "scale-appropriate cap on emitted rows for a genuinely large, non-duplicated API "
            "surface -- a bounded top-N set of members, with the remainder still reachable "
            "via the existing 'complete API reference under Documentation & Resources' "
            "pointer the template already promises -- consistent with idea.md's own language "
            "that 'top APIs' (not every API) stay visible and long inventories may be "
            "collapsed without dropping content."
        ),
        "acceptance_evidence": (
            "PF05-APIREF-SCALE-001: aspose-3d-foss/Aspose.3D-FOSS-for-.NET blocks with "
            '"bounded review is structurally blocked: '
            "('unpacketizable-oversized-factual-unit-0048-table',)\". Confirmed distinct from "
            "the already-fixed inherited-member duplication bug (604983413): this candidate's "
            "API Method Index has zero inherited rows -- 1079 distinct rows, 123,712 "
            "characters, larger than the entire rest of the 158,474-character candidate "
            "combined. `bounded_review_structure.py::_build_raw_units()` treats one "
            "contiguous Markdown table as one indivisible atomic unit by design (splitting "
            "mid-row would break per-row review coherence), so a table this large can never "
            "fit the 120,000-character packet budget even alone. That budget is not a safe "
            "lever to raise: it has no scale-justifying comment in source, but lines up with "
            "headroom under the LLM gateway's real usable context ceiling (~71k tokens for "
            "qwen3-next), so raising it risks trading a controlled rejection for a live "
            "provider context-overflow failure. Full writeup: "
            "plans/investigations/evidence/portfolio-proof-pf05-seven-ecosystem-canaries/"
            "api-method-index-exceeds-review-budget-2026-08-26.md. Not fixed directly: the "
            "producer file matches the document contract's `presentation/verified_*.py` "
            "glob, so editing it invalidates every cached composition plan portfolio-wide, "
            "and the fix requires a genuine curation-cutoff decision, not a mechanical patch."
        ),
        "traceability": (
            "GOV-014; observed during L8-PF-05 seven-ecosystem canary fleet pass, 2026-08-26"
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
