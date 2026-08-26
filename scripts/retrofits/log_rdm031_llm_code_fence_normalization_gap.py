#!/usr/bin/env python3
"""One-shot: log the LLM-authored code-fence normalization gap found while
triaging the L8-PF-05/fleet-final2 portfolio pass on 2026-08-26.

Root-caused and written up in full at
plans/investigations/evidence/llm-authored-code-fence-normalization-gap-2026-08-26/
llm-authored-code-fence-normalization-gap-2026-08-26.md, but not fixed there:
the correct fix needs new markdown-fence-rewriting logic, a materially
different, higher-risk kind of change than this session's other additive-only
detection fixes, deferred for its own focused implementation and test pass.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/log_rdm031_llm_code_fence_normalization_gap.py`
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
        "requirement_id": "RDM-031",
        "section": "10. README generation requirements",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "LLM-authored section content (section_cluster_authoring.py's accepted units) "
            "MUST have its code fences run through the same "
            "`code_fence_presentation.py::normalize_code_snippet()` cleanup the deterministic "
            "template renderer already applies at every one of its own fence-emission sites, "
            "so `presentation.code_fence_spacing` never blocks on trailing whitespace or "
            "repeated blank lines the pipeline itself could have deterministically removed."
        ),
        "acceptance_evidence": (
            "RDM031-CODEFENCE-NORMALIZE-001: `presentation.code_fence_spacing` blocks three "
            "repositories in the fleet-final2-20260826 portfolio pass -- "
            "aspose-cells-foss/Aspose.Cells-FOSS-for-Go, "
            "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust, and "
            "aspose-slides-foss/Aspose.Slides-FOSS-for-.NET -- always alongside other "
            "concurrent blockers. Confirmed the deterministic template renderer already calls "
            "normalize_code_snippet() at every fence-emission site "
            "(verified_template_draft.py:367,380; verified_template_sections.py:323,379,413,"
            "495,507) while the agentic section-authoring path has no equivalent call anywhere, "
            "so an LLM-authored fence is inserted exactly as generated. Full writeup: "
            "plans/investigations/evidence/"
            "llm-authored-code-fence-normalization-gap-2026-08-26/"
            "llm-authored-code-fence-normalization-gap-2026-08-26.md. Not fixed directly: "
            "unlike this session's other additive-only detection fixes, the correct repair "
            "rewrites candidate text (add a normalize_all_code_fences() sibling using the same "
            "MarkdownIt tokenization inspect_code_fences() already relies on), which needs its "
            "own careful implementation and test pass given the risk of a wrong line-range "
            "calculation silently corrupting content rather than merely failing to unblock."
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
