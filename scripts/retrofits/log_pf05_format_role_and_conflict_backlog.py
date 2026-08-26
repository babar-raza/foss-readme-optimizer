#!/usr/bin/env python3
"""One-shot: log two open, non-blocking fact-layer defects found while driving
the L8-PF-05 seven-ecosystem canary fleet pass on 2026-08-26.

Both were root-caused with source-level verification and written up in full at
plans/investigations/evidence/portfolio-proof-pf05-seven-ecosystem-canaries/,
but neither was fixed there: both require editing files inside the fact or
acceptance contract, and a fleet pass was in flight when they were found. Per
`GOV-014`, narrative evidence docs alone do not satisfy the backlog-logging
requirement -- a catalog row with a citable ID is required, so this adds one
for each.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/log_pf05_format_role_and_conflict_backlog.py`
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
        "requirement_id": "FACT-018",
        "section": "6. Product-facts and provenance requirements",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "`product.formats` extraction MUST promote a format to an accepted output (or "
            "input) role when the repository itself proves the direction via evidence the "
            "pipeline already collects -- a `SaveFormat`/`FileFormat` enum member naming the "
            "format, a `*SaveOptions`/`*Exporter` public type for it, or (strongest, and the "
            "only evidence source not already ruled out) a verified example whose executed "
            "output is that format."
        ),
        "acceptance_evidence": (
            "PF05-FORMAT-ROLE-001: `aspose-note-foss/Aspose.Note-FOSS-for-Python`'s accepted "
            "`product.formats` is literally `['Input format: Microsoft OneNote (.one)']` -- no "
            "output format at all -- while the repository ships `examples/export_pdf.py` "
            'calling `doc.Save("out.pdf", SaveFormat.Pdf)`, asserts the output starts with '
            "`%PDF`, compares generated PDFs against golden files, and defines "
            "`list(SaveFormat) == [SaveFormat.Pdf]`: PDF export is the package's only output "
            "capability. `aspose-3d-foss/Aspose.3D-FOSS-for-Python` similarly under-declares "
            "COLLADA/FBX export, which a dedicated `test_collada_exporter.py` and a "
            "`ColladaSaveOptions` type both prove. Both candidates are correct; "
            "`presentation.format_direction_contradiction` is rejecting them against facts "
            "that are wrong, not against the repositories. A repair using enum members or "
            "type names (evidence sources 1 and 2) was implemented and reverted (commit "
            "1ff210e60, reverted 58b945b1a) after it was found to contradict an existing, "
            "deliberate test guard "
            "(`test_api_reference_does_not_infer_format_support_from_type_names`) that a type "
            "name must never establish format support, declared or not. Only evidence source 3 "
            "(verified example output) remains untried and does not conflict with that guard. "
            "Full writeup: "
            "plans/investigations/evidence/portfolio-proof-pf05-seven-ecosystem-canaries/"
            "format-role-facts-underreport-output-formats-2026-08-26.md. Not fixed directly: "
            "`product.formats` collectors are inside the fact-verification contract "
            "(`facts/verification_contract.py`), so editing them re-stales every cached fact "
            "bundle portfolio-wide (measured 2026-08-26: editing a single "
            "`facts/acceptance_contract.py`-component file alone dropped the mission "
            "scoreboard's `facts_ready` from 23/34 to 0/34) and belongs in a deliberate "
            "shared-repair slot with a full re-run behind it, not mid-pass."
        ),
        "traceability": (
            "GOV-014; observed during L8-PF-05 seven-ecosystem canary fleet pass, "
            "2026-08-26; commits 1ff210e60, 58b945b1a"
        ),
    },
    {
        "requirement_id": "FACT-019",
        "section": "6. Product-facts and provenance requirements",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "When an accepted `product.limitations` fact and an accepted `product.capabilities` "
            "fact assert opposite polarity about the same discriminator-sharing subject, and "
            "the capability fact's source citation includes a real implementation file the "
            "limitation's source does not, the limitation SHOULD be re-verified against that "
            "implementation before acceptance -- or flagged `has_unresolved_conflict` so "
            "downstream composition can omit the losing side with a governed disposition "
            "instead of silently emitting a visitor-facing contradiction."
        ),
        "acceptance_evidence": (
            "PF05-BARCODE-CONFLICT-001: `aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python`'s "
            'accepted `product.capabilities` reads "Code 128 generation with automatic optimal '
            'Code Set switching."; its accepted `product.limitations` reads "GS1, ECI, bytes / '
            "binary input, FNC handling, Code Set A/C, Shift, and code-set switching are "
            'unsupported." (source: bootstrap.py:84, a hardcoded string literal, not derived '
            "from inspecting the encoder). Verified against the real encoder: "
            "`src/aspose_barcode_foss/_internal/encoders/code128.py` implements Code Set A/B/C "
            "inter-set switching including SHIFT (lines 260-508). The capability is true and "
            "source-verified; the limitation is stale. Both facts are independently accepted, "
            "so `public_quality.contradiction_capability_phrase` correctly reports the "
            "contradiction it was built to catch -- the check is not the defect, the input "
            "facts are. Full writeup: "
            "plans/investigations/evidence/portfolio-proof-pf05-seven-ecosystem-canaries/"
            "barcode-code-set-switching-fact-conflict-2026-08-26.md. Not fixed directly: "
            "resolving it correctly is fact-conflict-resolution work (contract-bound); "
            "weakening the presentation-layer contradiction check instead was considered and "
            "rejected as the same class of mistake as the reverted `1ff210e60` change."
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
