#!/usr/bin/env python3
"""One-shot: log a recurring LLMTruncatedResponseError pattern found during
the 2026-08-27 post-RDM030 full fleet pass -- three independent repos across
three different ecosystems all failed identically at the presentation_plan
stage with a truncated forced-tool-call JSON response.

Not root-caused to full certainty (the exact call site was not confirmed via
a live traceback), but strong structural evidence points to
`llm/section_author_client.py`'s `MAX_OUTPUT_TOKENS = 2048`: the error
prefix (`presentation_plan:execution_error`) matches where
`section_cluster_authoring` calls happen in `specialists/readme_presentation.py`,
and that client's own docstring says it never retries on a schema/parse
failure (`response_max_attempts=1`), matching the observed one-shot failures.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/log_rdm033_section_authoring_token_truncation.py`
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
        "requirement_id": "RDM-033",
        "section": "10. README generation requirements",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "The section-cluster authoring LLM call MUST NOT silently fail closed with "
            "LLMTruncatedResponseError when a cluster's legitimate authored content genuinely "
            "needs more than `llm/section_author_client.py::MAX_OUTPUT_TOKENS` (2048) tokens -- "
            "either raise the budget to a value proven sufficient for the largest observed "
            "real cluster, or add a bounded one-shot retry with a larger budget specifically "
            "for a finish_reason='length' truncation (distinct from `response_max_attempts=1`'s "
            "existing no-retry-on-parse-failure policy, which is about semantic/schema errors, "
            "not a budget that was simply too small)."
        ),
        "acceptance_evidence": (
            "RDM033-SECTION-AUTHORING-TRUNCATION-001 (2026-08-27): three independent "
            "repositories across three different ecosystems failed identically in the same "
            "fleet pass (fleet-post-heal-20260827.log) with "
            "'specialist_failed:readme_presentation:ERROR:presentation_plan:execution_error:"
            "LLMTruncatedResponseError: forced tool call response was truncated: Expecting ',' "
            "delimiter' -- aspose-words-foss/Python (char 2906), aspose-cells-foss/Rust "
            "(char 2892), aspose-cells-foss/Go (char 8466). Traced the raise site "
            "(llm/verifier_client.py:207-216): triggers when the forced-tool-call `arguments` "
            "JSON fails to parse AND the provider's finish_reason=='length' (token budget "
            "exhausted mid-JSON). Not root-caused to full certainty via a live traceback, but "
            "the error prefix (presentation_plan:execution_error) matches where "
            "'section_cluster_authoring' calls happen in specialists/readme_presentation.py, "
            "and that client (llm/section_author_client.py) sets MAX_OUTPUT_TOKENS=2048 with "
            'response_max_attempts=1 ("this client never retries on a schema/parse failure" '
            "per its own docstring) -- matching the observed one-shot failures with no "
            "self-healing on retry. Not yet confirmed whether 2048 is simply too small for some "
            "legitimately large clusters, or whether the LLM is producing pathologically "
            "verbose output that should itself be bounded differently."
        ),
        "traceability": ("GOV-014; found during the 2026-08-27 post-RDM030 full fleet pass triage"),
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
