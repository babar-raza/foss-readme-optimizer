#!/usr/bin/env python3
"""One-shot: append the precise, live-traced mechanism for RDM-029's gap 1
(fenced code examples get no resolution path) found on 2026-08-27, and why
a naive fix does not work.

Traced all 10 of aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET's previewed
blocking claims through assess_material_claims()+classify_source_claim_risk()
against the real vendor source. 8 share obligation_id="additional_examples",
which resolve_source_claims() has no dedicated branch for (only
"primary_example" is special-cased) -- confirmed the claim falls through to
a deliberate no-op (_raise_unresolved_preserve with required=False) and
silently produces zero resolutions. Confirmed naively extending
deferred_unverified_obligation_detail_resolution()'s allowed-obligation set
does not work (its candidate_core_present guard is already known False in
this exact failure case), and that the one function built for this kind of
per-example verification (deferred_unverified_source_example_resolution) is
Python-fence-specific by construction (_python_fence_content() rejects a
csharp fence, confirmed live) -- generalizing it is multi-ecosystem feature
work, not a one-line patch. Full writeup in the evidence doc.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/update_rdm029_precise_mechanism_traced.py`
Kept after use as the executable record of what was changed (repo layout
placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

EVIDENCE_ADDENDUM = (
    " RDM029-PRECISE-MECHANISM-TRACED-003 (2026-08-27): live-traced all 10 of "
    "aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET's previewed blocking claims through "
    "assess_material_claims()+classify_source_claim_risk() against the real vendor source. "
    'All share risk_class="mandatory_fact_resolution"; 2 (dependency prose, gap 2) have '
    'obligation_id="dependency_requirements"; 8 (fenced csharp examples, gap 1) have '
    'obligation_id="additional_examples". resolve_source_claims() '
    "(verified_source_claim_resolution_engine.py) only special-cases obligation_id=="
    '"primary_example" -- "additional_examples" falls through to a generic '
    "accepted_obligation_bindings() check (None for this repo), then to "
    "deferred_unverified_obligation_detail_resolution() which immediately returns None "
    '("additional_examples" is not in its hardcoded allowed set), then to a deliberate '
    "no-op (_raise_unresolved_preserve with required=False) -- confirmed by direct trace, "
    "not inference, this silently produces zero resolutions. Confirmed a naive fix (adding "
    '"additional_examples" to the allowed-obligation set) does not work: that function\'s '
    "first guard requires candidate_core_present, derived from the same "
    "accepted_obligation_bindings() call already known to return None here. The one function "
    "built for correct per-example verification "
    "(deferred_unverified_source_example_resolution) is Python-fence-specific by "
    "construction -- _python_fence_content() explicitly rejects a csharp fence (confirmed "
    "live: returns None). Generalizing it to the real failing case (.NET/C#) needs that "
    "ecosystem's fence-language detection and verification-fact shape too, not just an "
    "obligation_id gate change -- likely true for every other ecosystem's "
    "additional_examples claims as well. This is multi-ecosystem feature work; a rushed "
    "version risks a worse failure mode than the current crash-closed behavior (silently "
    "misclassifying a genuine example as safe to omit). Not attempted."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated = 0
    for index, line in enumerate(lines):
        record = json.loads(line)
        if record.get("requirement_id") != "RDM-029":
            continue
        if "RDM029-PRECISE-MECHANISM-TRACED-003" in record.get("acceptance_evidence", ""):
            print("RDM-029 already updated; nothing to do")
            return
        record["acceptance_evidence"] = record["acceptance_evidence"] + EVIDENCE_ADDENDUM
        lines[index] = json.dumps(record, ensure_ascii=False)
        updated += 1
    if updated != 1:
        raise SystemExit(f"expected exactly one RDM-029 row, found {updated}")
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("RDM-029 updated with precise mechanism trace")


if __name__ == "__main__":
    main()
