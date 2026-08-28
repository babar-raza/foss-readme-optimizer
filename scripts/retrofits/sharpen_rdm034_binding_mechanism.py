#!/usr/bin/env python3
"""One-shot: sharpen RDM-034's evidence with the exact binding mechanism found via static
tracing (read-only -- no debug instrumentation, no production code changed).

Found while continuing the autonomous mission-execution phase on 2026-08-28, in parallel
with a background full-portfolio retry-blocked pass.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/sharpen_rdm034_binding_mechanism.py`
Kept after use as the executable record of what was appended (repo layout placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

ADDENDUM = (
    " RDM034-BINDING-MECHANISM-002 (2026-08-28, autonomous execution phase): traced the "
    "claim-to-fact matching pipeline statically (read-only, no debug instrumentation, no "
    "production code changed) from `claim_accountability.py`'s `source_records` construction "
    "down through `presentation/verified_source_claim_matching.py`'s "
    "`equivalent_source_claim_resolution()`. Found the exact mechanism: this function tries "
    "`fact_bound_capability_candidate_claims()` first (matches a candidate claim placed under "
    "a 'template.section.key_capabilities.claim:' provenance binding in the same byte range); "
    "only if that returns no match does it fall through to "
    "`fact_bound_limitation_candidate_claims()` (`verified_source_limitation_matching.py`). "
    "Whichever path succeeds sets `capability_reformatted`/`limitation_reformatted`, which "
    "then selects between `_capability_equivalence_fact_ids()` (keeps every non-identity "
    "accepted fact) and `_limitation_equivalence_fact_ids()` for the resolution's "
    "`required_source_fact_ids`. The capability path's own strict, multi-condition matching "
    "(a same-byte-range key-capabilities provenance binding must exist, plus structured-"
    "coordinate or semantic-similarity thresholds) plausibly fails for this specific claim "
    "because the candidate composed 'heuristic PDF/A and PDF/UA checks' into the Scope-and-"
    "Limitations section rather than Key Capabilities -- a legitimate compositional choice "
    "given the hedging language, not necessarily a bug in the capability matcher itself. The "
    "real defect is downstream, in `_limitation_equivalence_fact_ids()` "
    "(`verified_source_claim_matching.py:72-89`): once routed onto the limitation path, it "
    "computes `limitation_ids` (facts in `fact_ids` whose field is `product.limitations`) but "
    "then unconditionally falls back to `facts.selected_fact_ids.get('product.limitations')` "
    "whenever `limitation_ids` is empty -- binding to the repository's selected limitations "
    "fact regardless of whether that fact's own text is what the claim actually supports. Its "
    "own docstring confirms this fallback was added deliberately to stop a different, earlier "
    "regression ('requiring [a limitation match] made routing suppress the exact source row "
    "and final resolution reject the same canonical row'), so removing the fallback outright "
    "would likely reintroduce that original bug -- the fix needs to distinguish 'no literal "
    "match because the claim genuinely is the limitation, just paraphrased' (fallback should "
    "fire) from 'no literal match because the claim is actually a different fact entirely, "
    "like this verbatim capabilities item' (fallback should not fire), which is exactly the "
    "kind of narrow, evidence-checked change RDM-029's own investigation cautioned this area "
    "needs rather than a blanket removal. `fact_bound_limitation_candidate_claims()` itself "
    "(the function that finds the 'exactly one' candidate claim triggering this path) was not "
    "traced this pass -- confirming whether IT also plays a role, or whether "
    "`_limitation_equivalence_fact_ids()`'s fallback is sufficient on its own to explain the "
    "symptom, is the next concrete step. Not attempted further this session, consistent with "
    "the blast-radius caution already recorded."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated_lines: list[str] = []
    found = False
    for line in lines:
        record = json.loads(line)
        if record["requirement_id"] == "RDM-034":
            found = True
            if "RDM034-BINDING-MECHANISM-002" not in record["acceptance_evidence"]:
                record["acceptance_evidence"] = record["acceptance_evidence"].rstrip() + ADDENDUM
        updated_lines.append(json.dumps(record, ensure_ascii=False))
    if not found:
        raise SystemExit("RDM-034 not found in catalog -- run the row-creation script first")

    CATALOG_PATH.write_text("\n".join(updated_lines) + "\n", encoding="utf-8", newline="\n")
    print("updated RDM-034 with the sharpened binding-mechanism diagnosis")


if __name__ == "__main__":
    main()
