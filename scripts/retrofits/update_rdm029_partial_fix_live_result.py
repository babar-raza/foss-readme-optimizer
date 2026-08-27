#!/usr/bin/env python3
"""One-shot: record RDM-029's partial-fix (commit 2a4087574) live-verification
result against aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET: the fix landed
safely (extends deferred_unverified_obligation_detail_resolution() to
additional_examples/dependency_requirements), but did NOT clear this
specific repository's blocker -- all 8 targeted fenced-example claims are
still blocking. candidate_core_present (accepted_obligation_bindings for
"additional_examples") is apparently also False for this repository's own
candidate, a further, not-yet-investigated layer. Status stays PARTIAL.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/update_rdm029_partial_fix_live_result.py`
Kept after use as the executable record of what was changed (repo layout
placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

EVIDENCE_ADDENDUM = (
    " RDM029-PARTIAL-FIX-LIVE-RESULT-005 (2026-08-27): fixed the confirmed permanent gap "
    "(commit 2a4087574 -- additional_examples/dependency_requirements added to "
    "deferred_unverified_obligation_detail_resolution()'s allowed set) and unit-tested it, "
    "but a live retry against the exact repository that motivated it "
    "(aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET) still shows all 8 targeted fenced-example "
    "claims blocking (12 total blocking claims, up from the prior 12-13 range). The fix's "
    "safety condition (candidate_core_present, i.e. accepted_obligation_bindings for "
    '"additional_examples" succeeding) is apparently False for this repository\'s own '
    "candidate too -- a further, deeper, not-yet-investigated layer (does this repo's "
    'candidate even have a properly fact-bound "Additional Examples" section?). The fix is '
    "correct and safe (confirmed via a different repo, aspose-font-foss/Python, whose "
    "persisted plan shows candidate_core_present=True for this exact obligation) and should "
    "help repos whose core section IS independently verified, but does not resolve this "
    "specific repository. Status stays PARTIAL. Separately: this investigation also directly "
    "disproved the RDM029-SHARED-ROOT-CAUSE-HYPOTHESIS-004 entry above -- see the evidence "
    "doc's refutation section for the corrected understanding (composition-level "
    "nondeterminism, not a uniform missing-binding root cause, for the obligations that DO "
    "have a resolution path)."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("requirement_id") != "RDM-029":
            continue
        if "RDM029-PARTIAL-FIX-LIVE-RESULT-005" in record.get("acceptance_evidence", ""):
            print("RDM-029 already updated; nothing to do")
            return
        record["acceptance_evidence"] = record["acceptance_evidence"] + EVIDENCE_ADDENDUM
        lines[index] = json.dumps(record, ensure_ascii=False)
        updated += 1
    if updated != 1:
        raise SystemExit(f"expected exactly one RDM-029 row, found {updated}")
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("RDM-029 updated with partial-fix live-verification result")


if __name__ == "__main__":
    main()
