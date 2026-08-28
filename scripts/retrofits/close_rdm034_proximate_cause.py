#!/usr/bin/env python3
"""One-shot: close the loop on RDM-034's diagnosis with the exact proximate cause found via
static tracing (read-only -- no debug instrumentation, no production code changed).

Found while continuing the autonomous mission-execution phase on 2026-08-28, continuing
directly from RDM034-BINDING-MECHANISM-002 in the same commit's evidence.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/close_rdm034_proximate_cause.py`
Kept after use as the executable record of what was appended (repo layout placement rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

ADDENDUM = (
    " RDM034-PROXIMATE-CAUSE-003 (2026-08-28, autonomous execution phase): traced "
    "`fact_bound_limitation_candidate_claims()`'s own match condition "
    "(`presentation/verified_source_limitation_matching.py`) down to its final gate, "
    "`public_limitations_equivalent(source_text, candidate_text)` "
    "(`readme/limitation_semantics.py:87-140`). Found the exact proximate cause: the "
    "function's hedge-word symmetry check (`_LIMITING_LANGUAGE.search()`, line 112-115) "
    "only rejects a pairing when exactly one side contains limiting-language vocabulary -- "
    "and `_LIMITING_LANGUAGE`'s own word list (line 16) includes `heuristic` alongside "
    "`not`/`no`/`only`/`unsupported`. The source claim ('Perform heuristic PDF/A and PDF/UA "
    "checks and conversions') uses 'heuristic' as a legitimate capability hedge -- an "
    "accurate qualifier on a real feature -- while the candidate's limitations paraphrase "
    "('...are heuristic signals, not certification-grade conformance') uses the same word "
    "as a genuine caveat; both contain it, so the symmetry check does not reject the pairing. "
    "With no earlier check disqualifying the pair either (both texts share the same "
    "`capability_domains()` result, PDF-family format tokens), the function reaches its "
    "final fallthrough at line 139-140: `semantically_repeats(normalized_left, "
    "normalized_right, threshold=0.5 if left_domains else 0.65)` -- 0.5 (the more permissive "
    "threshold, since `left_domains` is truthy here) against two strings sharing "
    "'PDF/A', 'PDF/UA', 'heuristic', and 'checks' verbatim plausibly clears that bar despite "
    "the two statements having opposite polarity (one asserts a capability, the other "
    "asserts a caveat about it). This is a generic lexical/semantic-similarity heuristic "
    "with no explicit capability-vs-caveat polarity discrimination -- 'heuristic' is simply "
    "the word that happens to make this specific pair collide; the same class of collision "
    "could recur for any capability claim whose hedge vocabulary overlaps a limitation's "
    "own wording. Not fixed: `_LIMITING_LANGUAGE`, `capability_domains()`, and "
    "`semantically_repeats()` are shared low-level primitives used across multiple claim-"
    "matching paths (including the capability-equivalence path's own `capability_"
    "discriminators()` sibling), so a change here needs portfolio-wide regression testing "
    "before landing, not a narrow single-repo verification -- consistent with the "
    "blast-radius caution already recorded. The concrete next step is adding "
    "capability-vs-caveat polarity as an explicit signal to `public_limitations_equivalent()` "
    "(e.g. requiring a genuine negation/failure marker on both sides, not just any shared "
    "hedge word) rather than special-casing 'heuristic' out of `_LIMITING_LANGUAGE`, which "
    "would likely just move the false-positive surface to the next word that plays both "
    "roles."
)


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    updated_lines: list[str] = []
    found = False
    for line in lines:
        record = json.loads(line)
        if record["requirement_id"] == "RDM-034":
            found = True
            if "RDM034-PROXIMATE-CAUSE-003" not in record["acceptance_evidence"]:
                record["acceptance_evidence"] = record["acceptance_evidence"].rstrip() + ADDENDUM
        updated_lines.append(json.dumps(record, ensure_ascii=False))
    if not found:
        raise SystemExit("RDM-034 not found in catalog -- run the row-creation script first")

    CATALOG_PATH.write_text("\n".join(updated_lines) + "\n", encoding="utf-8", newline="\n")
    print("updated RDM-034 with the closed-loop proximate-cause diagnosis")


if __name__ == "__main__":
    main()
