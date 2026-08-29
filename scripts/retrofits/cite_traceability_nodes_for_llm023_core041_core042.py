#!/usr/bin/env python
"""Give LLM-023, CORE-041 and CORE-042 the concrete pytest node citations they lacked.

`plans/investigations/tools/traceability_matrix.py --check` fails these three
`IMPLEMENTED` P1 rows with "closure cites neither a concrete pytest node nor a
committed evidence artifact". All three predate this sprint (commits `3e4da1b88`,
`67f66f6d9`, `f1efd83a2`) and all three describe real, landed work in prose -- what
is missing is a machine-checkable citation, not the work.

Each row already *names* its behaviour; this script appends the canonical
`file.py::Class::test_method` node that proves it. Every node below was collected
and run green before being cited (12 passed), so no citation here is aspirational:

  LLM-023  Decision #110 prose-quality cache, keyed on
           sha256(final_text) + PROSE_QUALITY_CONTRACT_VERSION, proving an
           unchanged rerun performs zero new judgment calls.
  CORE-041 `evidence/writer.py::_atomic_write_text()` long-path correctness --
           the `mkdir`/`NamedTemporaryFile` pair used the raw parent while only
           `os.replace()` used the long-path helper.
  CORE-042 `load_worker_receipt()` trusting an identity- and exit-code-consistent
           receipt from a legitimately nonzero-exit (BLOCKED) worker.

Kept after use as the executable record of the edit -- see plans/GOVERNANCE.md,
"Repository layout", placement rule 5.

Run: .venv/Scripts/python scripts/retrofits/cite_traceability_nodes_for_llm023_core041_core042.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

# requirement_id -> sentence appended to acceptance_evidence.
CITATIONS: dict[str, str] = {
    "LLM-023": (
        " Traceability citation (2026-08-29): the cache contract is proven by "
        "`tests/unit/test_capabilities.py::TestVerifyProseQuality::"
        "test_execute_reuses_a_cached_verdict_with_zero_new_calls` (a second call with an "
        "exhausted fixture client returns the cached verdict and makes zero new calls) and by "
        "the direct unit suite `tests/unit/test_prose_quality_cache.py`, which covers key "
        "derivation, the contract-version bump invalidation, and atomic write. All were "
        "collected and run green before this citation was added."
    ),
    "CORE-041": (
        " Traceability citation (2026-08-29): the long-path repair is proven by "
        "`tests/unit/test_evidence_writer.py::"
        "test_atomic_write_survives_a_destination_beyond_windows_max_path`, which writes to a "
        "destination at or beyond the 260-character MAX_PATH limit and fails against the "
        "pre-fix raw-parent `mkdir`/`NamedTemporaryFile` pair. Collected and run green before "
        "this citation was added."
    ),
    "CORE-042": (
        " Traceability citation (2026-08-29): the receipt-trust repair is proven by "
        "`tests/unit/test_portfolio_worker_integration.py::"
        "test_nonzero_exit_worker_with_an_exit_code_consistent_receipt_is_trusted`, with "
        "`test_failed_current_worker_cannot_reuse_a_stale_success_receipt` as its negative "
        "control -- together they show a legitimate BLOCKED worker's receipt is honoured while "
        "a stale or exit-code-inconsistent one is still discarded. Collected and run green "
        "before this citation was added."
    ),
}


def main() -> int:
    lines = CATALOG.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    applied: set[str] = set()
    for line in lines:
        if not line.strip():
            updated.append(line)
            continue
        record = json.loads(line)
        requirement_id = record.get("requirement_id")
        citation = CITATIONS.get(requirement_id)
        if citation is None:
            updated.append(line)
            continue
        evidence = record.get("acceptance_evidence", "")
        if "Traceability citation (2026-08-29)" in evidence:
            print(f"{requirement_id}: already cited, left unchanged")
            applied.add(requirement_id)
            updated.append(line)
            continue
        record["acceptance_evidence"] = evidence.rstrip() + citation
        applied.add(requirement_id)
        updated.append(json.dumps(record, ensure_ascii=False))
        print(f"{requirement_id}: citation appended")

    missing = set(CITATIONS) - applied
    if missing:
        print(f"error: requirement ids not found in the catalog: {sorted(missing)}")
        return 1

    # newline="" keeps the catalog LF-only, matching what git stores. A plain
    # write_text() on Windows translates every "\n" to "\r\n", which leaves the
    # git diff correct but changes the file's bytes on disk -- and the pinned
    # catalog/coverage hashes are computed over those bytes, so a byte-level
    # hash then disagrees with the text-mode one the coverage builder records.
    with CATALOG.open("w", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(updated) + "\n")
    print(f"wrote {CATALOG.relative_to(REPO_ROOT).as_posix()} ({len(updated)} records)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
