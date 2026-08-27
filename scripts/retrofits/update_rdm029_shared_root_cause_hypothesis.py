#!/usr/bin/env python3
"""One-shot: append a third RDM-029 obligation case (major_capabilities, the
most-stuck repo in the portfolio: 33-34 consecutive escalation_alert
failures) and the resulting hypothesis that gaps 1/2 and this third case
share ONE upstream root cause (candidate_content_provenance not carrying an
obligation-matching binding), not three independent per-obligation gaps.
Not confirmed -- needs live pipeline instrumentation to verify. Full writeup
in the evidence doc.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/update_rdm029_shared_root_cause_hypothesis.py`
Kept after use as the executable record of what was changed (repo layout
placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

EVIDENCE_ADDENDUM = (
    " RDM029-SHARED-ROOT-CAUSE-HYPOTHESIS-004 (2026-08-27): traced "
    "aspose-font-foss/Aspose.Font-FOSS-for-Python (the most-stuck repo in the portfolio: "
    "33-34 consecutive escalation_alert failures across every fleet pass this session). Its "
    'one blocking claim is a THIRD obligation, obligation_id="major_capabilities" (a source '
    'capability table). Unlike gaps 1/2, "major_capabilities" IS in '
    "deferred_unverified_obligation_detail_resolution()'s allowed set, and its capability-"
    "specific guard (_capability_anchor_matches) was tested directly against the real claim "
    "text and real product.capabilities fact -- it returns True, ruling it out as the "
    "blocker. By elimination the actual blocker must be candidate_core_present (i.e. "
    'accepted_obligation_bindings("major_capabilities", ...) returning None), the exact same '
    "upstream condition already identified for gap 1. Hypothesis: gaps 1, 2, and this case "
    "may be symptoms of ONE shared upstream problem (candidate_content_provenance not "
    "carrying an obligation-matching binding), not three independent per-obligation gaps -- "
    "if true, the highest-leverage fix is in how provenance gets recorded during composition, "
    "not three new per-obligation resolution functions. NOT confirmed: this is a hypothesis "
    "from two data points, not a full trace of accepted_obligation_bindings()'s live runtime "
    "inputs (candidate_content_provenance is in-memory pipeline state, not a persisted "
    "artifact this investigation had static access to). Recommended next step if picked up: "
    "instrument the real composition pipeline to check whether candidate_content_provenance "
    "for a live blocked run contains ANY matching-prefix bindings at all, before assuming a "
    "per-obligation fix is even the right shape."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("requirement_id") != "RDM-029":
            continue
        if "RDM029-SHARED-ROOT-CAUSE-HYPOTHESIS-004" in record.get("acceptance_evidence", ""):
            print("RDM-029 already updated; nothing to do")
            return
        record["acceptance_evidence"] = record["acceptance_evidence"] + EVIDENCE_ADDENDUM
        lines[index] = json.dumps(record, ensure_ascii=False)
        updated += 1
    if updated != 1:
        raise SystemExit(f"expected exactly one RDM-029 row, found {updated}")
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("RDM-029 updated with shared root-cause hypothesis")


if __name__ == "__main__":
    main()
