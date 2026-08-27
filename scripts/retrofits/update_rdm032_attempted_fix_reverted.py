#!/usr/bin/env python3
"""One-shot: append the outcome of an attempted (and reverted) RDM-032 fix.

Threading the section's heading text through as a fallback for the
namespace-scoping regex made the dead-code match succeed as designed, but a
live retry against the real failing repository made the symptom worse (one
oversized unit became two): the namespace-scoped projection for a
genuinely large namespace can itself exceed the already-small generic
capped fallback compact_prompt_fact_value() produces. Reverted before
committing. Full corrected writeup in the evidence doc.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/update_rdm032_attempted_fix_reverted.py`
Kept after use as the executable record of what was changed (repo layout
placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

EVIDENCE_ADDENDUM = (
    " RDM032-ATTEMPTED-FIX-REVERTED-002 (2026-08-27): implemented the direct fix "
    "(threading the section's raw heading-unit text through _bounded_fact_payloads as a "
    "fallback for _API_NAMESPACE) and it worked exactly as diagnosed -- the regex now "
    "matches. Unit tests passed (20/20), but a live retry against the real repository made "
    "the symptom WORSE: one oversized unit became two "
    "('unpacketizable-oversized-factual-unit-0040-table', "
    "'unpacketizable-oversized-factual-unit-0048-table'), and unit 0048 still failed. Root "
    "cause of the regression: composition_fact_payloads() already runs every fact through "
    "compact_prompt_fact_value(), a deliberately lossy, capped summary independent of "
    "namespace (measured ~3,572 chars for this repo's whole api.public_surface fact); the "
    "namespace-scoped projection this fix enables returns every class/member for one real "
    "namespace with no cap (measured ~45,622 chars for Core API alone) -- bigger than the "
    "capped fallback it replaces, the opposite of what scoping is for. Reverted before "
    "committing (git checkout, never landed on main). The correct fix must prefer whichever "
    "payload is smaller, not treat a namespace match as unconditionally better -- still open, "
    "needs a design decision (cap the namespace projection too? compare both sizes?) plus a "
    "large-synthetic-namespace regression test. Full writeup: plans/investigations/evidence/"
    "bounded-review-namespace-scoping-dead-code-2026-08-27/"
    "bounded-review-namespace-scoping-dead-code-2026-08-27.md."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("requirement_id") != "RDM-032":
            continue
        if "RDM032-ATTEMPTED-FIX-REVERTED-002" in record.get("acceptance_evidence", ""):
            print("RDM-032 already updated; nothing to do")
            return
        record["acceptance_evidence"] = record["acceptance_evidence"] + EVIDENCE_ADDENDUM
        lines[index] = json.dumps(record, ensure_ascii=False)
        updated += 1
    if updated != 1:
        raise SystemExit(f"expected exactly one RDM-032 row, found {updated}")
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("RDM-032 updated with attempted-fix-reverted evidence")


if __name__ == "__main__":
    main()
