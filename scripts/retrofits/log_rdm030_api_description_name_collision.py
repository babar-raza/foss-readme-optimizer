#!/usr/bin/env python3
"""One-shot: log the API-reference description name-collision bug found while
triaging the L8-PF-05/fleet-final2 portfolio pass on 2026-08-26.

Root-caused with a live, direct reproduction against the real
aspose-pdf-foss/Aspose.PDF-FOSS-for-Java product facts and written up in full
at plans/investigations/evidence/api-reference-description-name-collision-2026-08-26/
api-reference-description-name-collision-2026-08-26.md, but not fixed there:
the fix touches a presentation/verified_*.py module, invalidating every
repository's cached composition plan portfolio-wide -- unsafe while the
fleet-final2-20260826 portfolio pass is actively in flight. Also a real design
choice between two compatible repair directions, not a mechanical patch.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/log_rdm030_api_description_name_collision.py`
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
        "requirement_id": "RDM-030",
        "section": "10. README generation requirements",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "The API Method Index/Type-Description producer "
            "(`presentation/verified_template_api_descriptions.py`, "
            "`presentation/verified_template_api_text.py::role_sentence()`) MUST NOT let "
            "unrelated types collide on an identical rendered description. Prefer the "
            "type's own already-collected Javadoc `description` from "
            "`api.public_surface` when it is non-generic, and/or harden the "
            "name-derivation fallback so a type's empty-suffix-strip family-name fallback "
            "cannot coincidentally match a different type's explicit name prefix."
        ),
        "acceptance_evidence": (
            "RDM030-APIREF-COLLISION-001: aspose-pdf-foss/Aspose.PDF-FOSS-for-Java blocks "
            'with "ValueError: compiled verified presentation is invalid: API reference '
            'contains duplicated descriptions", reproduced identically across two separate '
            "fleet runs at the same revision (fleet-final2-20260826.log, "
            "portfolio-proof-fleet-20260826.log). Root-caused via live reproduction: "
            "role_sentence() renders both `PdfFont` (strip 'Font' suffix -> 'Pdf' -> "
            "public_noun='PDF') and `Font` (empty suffix strip -> family fallback 'pdf' -> "
            "public_noun='PDF') to the byte-identical sentence 'Represents a PDF font "
            "through the Aspose.PDF API.', despite the real ProductFactsV2 already carrying "
            "distinct Javadoc for each (verified: PdfFont='Abstract base class for all PDF "
            "font types (ISO 32000-1:2008, section 9.5).'; Font='Represents a font used in "
            "PDF documents.') that the renderer never reads -- grep for "
            "item.get('description') across presentation/ returns nothing. Full writeup: "
            "plans/investigations/evidence/api-reference-description-name-collision-2026-08-26/"
            "api-reference-description-name-collision-2026-08-26.md. Not fixed directly: "
            "the touched files match document_templates.py's presentation/verified_*.py "
            "glob, invalidating every repository's cached composition plan portfolio-wide -- "
            "unsafe mid-fleet-pass -- and choosing between the two compatible repair "
            "directions is a real design decision."
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
