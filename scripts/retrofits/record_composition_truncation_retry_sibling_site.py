#!/usr/bin/env python
"""Record the composition-call sibling of RDM-033's truncation retry.

RDM-033 already required that a forced tool call must not fail closed on
`LLMTruncatedResponseError` when the content legitimately needed more output space, and
its recorded fix for `section_cluster_authoring.py` was exactly "reuse the established
repair-hint rebuild with a write-more-concisely instruction". That fix was landed at one
call site. `readme/agentic_composition.py::plan_readme_composition` -- a second forced
tool call, with the same failure mode -- never got it, and three portfolio repositories
have been sitting blocked on it.

Worse than an identical retry: `plan_readme_composition` does catch the error (it is an
`LLMError`), but its retry runs `_repair_hints()`, which appends the full
section-decision, phrase-option and diagram-role vocabularies. So the one retry
`MAX_AUTHORING_ATTEMPTS = 2` allows was strictly LONGER than the attempt that had
already overrun the 6000-token output ceiling, with nothing asking for brevity.

Recorded here rather than as a new requirement because it is the same requirement class
at a second site -- which is precisely the sibling-site sweep the sprint plan's repair
loop mandates. RDM-033's own text names only the section-cluster call and should be
widened when it is next revised; that is noted in the evidence.

Kept after use as the executable record of the edit -- see plans/GOVERNANCE.md,
"Repository layout", placement rule 5.

Run: .venv/Scripts/python scripts/retrofits/record_composition_truncation_retry_sibling_site.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

MARKER = "RDM033-COMPOSITION-CALL-SIBLING-001"

EVIDENCE = (
    " " + MARKER + " (2026-08-29, autonomous execution): sibling-site sweep found the same "
    "fail-closed-on-truncation defect at a second forced tool call that this requirement's "
    "original fix did not cover. `readme/agentic_composition.py::plan_readme_composition` "
    "catches `LLMTruncatedResponseError` (it subclasses `LLMError`) but answered it with "
    "`_repair_hints()`, which appends the full section-decision, phrase-option and "
    "diagram-role vocabularies -- so the single retry allowed by "
    "`MAX_AUTHORING_ATTEMPTS = 2` was strictly longer than the attempt that had already "
    "overrun the client's 6000-token output ceiling, and carried no instruction to write "
    "less. Measured blast radius: 3 portfolio repositories blocked on it with "
    "`presentation_plan:execution_error:LLMTruncatedResponseError`, truncating at 5184, "
    "7402 and 10698 characters of tool arguments "
    "(aspose-cells-foss/Aspose.Cells-FOSS-for-Go, aspose-cells-foss/Aspose.Cells-FOSS-for-.NET, "
    "aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp). Fixed by giving truncation its own retry "
    "branch that adds a fixed-size brevity directive "
    "(`agentic_composition_inputs.py::truncation_repair_hint`) and withholds "
    "`_repair_hints()`' repository-sized blocks. The authoritative diagram role vocabulary "
    "is deliberately KEPT on that retry: dropping it to save prompt space would trade a "
    "truncation failure for a grounding failure on invented labels, and an earlier draft of "
    "this fix did exactly that until its own test caught it. Cannot regress a passing path: "
    "truncation previously always ended in a hard failure. Two tests in "
    "`tests/unit/test_agentic_readme_composition.py` -- "
    "`test_truncated_composition_retries_more_concisely_instead_of_with_more_instructions` "
    "(brevity directive present, `_repair_hints` blocks absent, role vocabulary retained, "
    "growth bounded) and its negative control "
    "`test_non_truncation_failure_still_gets_the_full_deterministic_repair_hints` (a schema "
    "failure still receives the full vocabularies). Proved non-vacuous by disabling the new "
    "branch in place: the positive test fails, the negative control still passes. "
    "`_truncation_repair_hint` was moved to `agentic_composition_inputs.py` because "
    "`test_readme_composition_module_boundaries.py` caps `agentic_composition.py` at 300 "
    "lines and the fix pushed it to 308; that guard was respected, not relaxed. Impacted "
    "sweep 123 passed, mypy clean. Requirement stays PARTIAL, and its text should be widened "
    "when next revised: it names the section-cluster call, but the defect class covers every "
    "forced tool call with a bounded output budget. Live recovery of a real truncation is "
    "still pending a natural recurrence, same as the original entry."
)


def main() -> int:
    lines = CATALOG.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    found = False
    for line in lines:
        if not line.strip():
            updated.append(line)
            continue
        record = json.loads(line)
        if record.get("requirement_id") != "RDM-033":
            updated.append(line)
            continue
        found = True
        evidence = record.get("acceptance_evidence", "")
        if MARKER in evidence:
            print("RDM-033: already recorded, left unchanged")
            updated.append(line)
            continue
        record["acceptance_evidence"] = evidence.rstrip() + EVIDENCE
        updated.append(json.dumps(record, ensure_ascii=False))
        print("RDM-033: sibling-site evidence appended (status left PARTIAL)")

    if not found:
        print("error: RDM-033 not found in the catalog")
        return 1

    # newline="" keeps the catalog LF-only; the pinned catalog/coverage hashes are
    # computed over these bytes, and a text-mode write would CRLF-ify every record.
    with CATALOG.open("w", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(updated) + "\n")
    print(f"wrote {CATALOG.relative_to(REPO_ROOT).as_posix()} ({len(updated)} records)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
