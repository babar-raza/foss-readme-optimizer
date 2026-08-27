#!/usr/bin/env python3
"""One-shot: log the bounded-review namespace-scoping dead-code defect found
while investigating a recurring "unpacketizable-oversized-factual-unit"
failure on aspose-3d-foss/Aspose.3D-FOSS-for-.NET on 2026-08-27.

Root-caused with a direct, live reproduction and written up in full at
plans/investigations/evidence/bounded-review-namespace-scoping-dead-code-2026-08-27/
bounded-review-namespace-scoping-dead-code-2026-08-27.md, but not fixed there:
the correct repair needs a real design decision on how to reliably recover a
table unit's owning namespace (the current signal structurally can never
work), not a one-line patch.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/log_rdm032_bounded_review_namespace_scoping_dead_code.py`
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
        "requirement_id": "RDM-032",
        "section": "10. README generation requirements",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "`_bounded_fact_payloads()` (`src/readme_agent/specialists/"
            "bounded_review_packers.py`) MUST reliably scope a namespace table's cited "
            "`api.public_surface` fact down to that table's own namespace before falling back "
            "to the complete, unscoped fact -- its current signal (regex-searching the table "
            "unit's own rendered text for a `Namespace (`...`)` heading) can never match, "
            "since a table unit's text never includes its preceding heading (a separate unit), "
            "making the scoping optimization dead code for every repository, not just the "
            "one it was observed failing for."
        ),
        "acceptance_evidence": (
            "RDM032-NAMESPACE-SCOPING-DEAD-CODE-001 (2026-08-27): "
            "aspose-3d-foss/Aspose.3D-FOSS-for-.NET fails identically across two independent "
            "fleet passes with 'bounded review is structurally blocked: "
            "(\\'unpacketizable-oversized-factual-unit-0048-table\\',)'. Confirmed live: the "
            "complete api.public_surface fact for this repository serializes to 1,251,842 "
            "characters (over 10x the 120,000-char DEFAULT_BOUNDED_PACKET_BUDGET_CHARS), while "
            "the actually rendered API reference table across all three real namespaces is only "
            "26,438 characters total (292 rows). Traced _API_NAMESPACE's regex "
            "(r'Namespace \\(`([^`]+)`\\)') against bounded_review_structure.py's table-unit "
            "construction (lines 127-145): a kind='table' unit's char_start begins at the "
            "table's own header row, never including the preceding markdown heading, so "
            "namespace_match is always None and the unscoped fallback always fires. Ruled out "
            "RDM-030 as a contributing cause: this repository's API reference has zero "
            "description collisions (api_reference_markdown() renders no 'Declares' clauses), "
            "so the RDM-030 disambiguation code path never executes here. Not contract-bound "
            "(bounded_review_packers.py matches none of document_templates.py's "
            "DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS/_GLOBS), so a fix carries no portfolio-wide "
            "cache-invalidation cost, unlike RDM-029/RDM-030. Full writeup: "
            "plans/investigations/evidence/bounded-review-namespace-scoping-dead-code-2026-08-27/"
            "bounded-review-namespace-scoping-dead-code-2026-08-27.md."
        ),
        "traceability": (
            "GOV-014; found while investigating a recurring bounded-review structural "
            "failure during the 2026-08-27 post-RDM030 fleet passes"
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
