#!/usr/bin/env python3
"""One-shot: log production-hardening findings from an independent
first-principles assessment of the mission controller / fact-verification
pipeline (conducted while resuming L8-PF-05-SEVEN-ECOSYSTEM-CANARIES after
PF05-CXX-LINK-001, then again after that fix surfaced a C++ knowledge-claim
false positive) as `BACKLOG` rows in `plans/requirements/catalog.jsonl`, per
`GOV-014` -- these are non-blocking findings discovered outside the current
task's scope, not fixed as unrequested scope creep.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/log_pf05_mission_controller_hardening_backlog.py`
Kept after use as the executable record of what was appended (repo layout
placement rule 5 -- a one-shot script is never deleted "after use").
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

ROWS: list[dict] = [
    {
        "requirement_id": "CORE-035",
        "section": "9. Core engine and registry requirements",
        "status": "BACKLOG",
        "priority": "P1",
        "requirement": (
            "The fact-verification cache's common-file invalidation set "
            "(`facts/verification_contract.py::_COMMON_FILES`) SHOULD be reconciled with "
            "PF05's own `REPAIR_SHARED_ONCE -> RERUN_FAILED_ONLY` repair policy, or split into a "
            "narrower true-common set, so a shared-code fix does not silently mark unrelated, "
            "previously-passing repositories' facts stale across every ecosystem at once."
        ),
        "acceptance_evidence": (
            "Not implemented. Confirmed by direct source audit: `_COMMON_FILES` includes "
            "`provider.py` and other files edited whenever any ecosystem's fact-collection logic "
            "is fixed (e.g. commit 3a2ad3207); any such edit changes "
            "`local_verification_contract_hash()` for every ecosystem simultaneously. Live "
            "`mission status` (state_version 1639-1644, 2026-08-25) shows "
            "`stale_fact_contract_repositories` listing 23 of 33 repositories across every "
            "ecosystem while `raw_lifecycle_progress` shows work had reached `facts_ready=26`, "
            "consistent with this mechanism. Currently an efficiency cost (redundant "
            "re-verification), not a correctness defect."
        ),
        "traceability": "L8-034; independent production assessment, 2026-08-25",
    },
    {
        "requirement_id": "CORE-036",
        "section": "9. Core engine and registry requirements",
        "status": "BACKLOG",
        "priority": "P1",
        "requirement": (
            "`state/git_backend.py::GitStateBackend.save()` SHOULD add a read-after-write "
            "confirmation (re-fetch the ref after push and assert it equals the pushed commit "
            'SHA) before reporting `outcome="saved"`, and '
            "`tests/integration/test_state_git_backend_local_parallel.py::"
            "test_separate_process_workspaces_preserve_same_ref_cas` SHOULD be extended to "
            "assert the anomaly below cannot recur under induced timing pressure. This MUST land "
            "before `L8-PORT-01` enables more than one concurrent repository lane."
        ),
        "acceptance_evidence": (
            "Not implemented. `logs/2026-08-24.md`: clean-Linux CI run `32692104994` produced a "
            "`saved/saved` outcome for two concurrent writers on the same ref, where CAS "
            "semantics require exactly one `saved` and one `stale`. `save()` derives its outcome "
            "solely from git's push return code/stderr with no independent confirming read. No "
            "commit after 2026-08-24 touches `git_backend.py`; the cited regression test was last "
            "touched 2026-08-04, before the bug was found. The only response was a `master.md` "
            "policy line disabling parallel repository workers until proven safe -- currently a "
            "policy-level mitigation, not a code-level fix. Not currently blocking: single-writer "
            "operation is the enforced default and is unaffected."
        ),
        "traceability": "AGT-005/006; L8-052; independent production assessment, 2026-08-25",
    },
    {
        "requirement_id": "CORE-037",
        "section": "9. Core engine and registry requirements",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "`readme-agent supervise --mission-action status` SHOULD add a cheap staleness-drift "
            "check comparing durable `state_version` against the version cited in "
            "`plans/master.md`'s Status section (and any committed handover file), flagged when "
            "drift exceeds a threshold, so a stale narrative document or handover cannot mislead "
            "a resuming agent without an explicit signal."
        ),
        "acceptance_evidence": (
            "Not implemented. Observed directly this session: `plans/master.md`'s Status section "
            "(frozen 2026-08-24, cited state v1411) lagged live `mission status` "
            "(`durable_state_version` 1639 at the same wall-clock session) by over 200 state "
            "versions and a day; a handover narrative reaching this session independently "
            'described the wrong current failure ("Java timed out" vs. the durable '
            '`current_failure: PF05-CXX-LINK-001"). The documented authority hierarchy '
            "(`AGENTS.md`: durable state is sole authority, narrative is advisory) correctly "
            "prevented this from causing an incorrect action once cross-checked, but nothing "
            "currently forces that cross-check automatically."
        ),
        "traceability": "GOV-014; independent production assessment, 2026-08-25",
    },
    {
        "requirement_id": "EVID-006",
        "section": "13. Safety, security, and evidence requirements",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "`runs/pf05-seven-canaries/reduce_real_receipts.py`'s per-ecosystem `elapsed_seconds` "
            "figures SHOULD be replaced with real captured timing, or explicitly tagged "
            '(`"synthetic": true` / `"source": "placeholder"`), so a causal-reduction receipt '
            "cannot be mistaken for measured telemetry by a downstream consumer."
        ),
        "acceptance_evidence": (
            "Not implemented. Confirmed by direct source audit: the script hardcodes "
            "`elapsed_seconds=900.0` as a Python literal for the Java, Rust, and Go ecosystems; "
            "the corresponding JSON receipts cite this script as their own generator, not a "
            "captured process trace. The mission's own `causal-reduction.json` already "
            'self-classifies this as `classification: "unknown"` and declines to guess a root '
            "cause, so the mission's evidence trail is honest about not knowing the cause; the "
            "identical figure across three unrelated toolchains (JVM/Maven, Cargo, Go) is "
            "evidence the number is a placeholder ceiling rather than a measurement, and should "
            "not be allowed to look like one."
        ),
        "traceability": "L8-034; independent production assessment, 2026-08-25",
    },
    {
        "requirement_id": "CORE-038",
        "section": "9. Core engine and registry requirements",
        "status": "BACKLOG",
        "priority": "P1",
        "requirement": (
            'C++ `limitation` claims of the shape "Unimplemented stub (empty body): X in '
            "Y:Z\" SHOULD be corroborated against real source (or filtered) at this repo's own "
            "claim-consumption layer (`facts/aspose_knowledge_claims.py` / "
            "`facts/aspose_knowledge_selection.py`) before becoming `ProductFactsV2` facts, "
            "mirroring the existing LLM claim-disposition corroboration pattern -- never trust "
            "a raw claim without independently re-checking it against real repository files."
        ),
        "acceptance_evidence": (
            "Not implemented. Confirmed false positive with real evidence: "
            "`vendored_asposeorg/scripts/pipeline/extraction/scout.py::_detect_cpp_stubs()` "
            "flags any C++ `function_definition` whose `compound_statement` body is empty as an "
            "unimplemented stub, without checking for a sibling `field_initializer_list` -- so "
            "any constructor written in the idiomatic "
            "initializer-list-does-the-work/empty-body style is misclassified. Reproduced "
            "against `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`'s real "
            "`Aspose.Cells.Foss.Cpp/src/DateTime.cpp:77` (fetched at the exact snapshotted "
            "revision via `gh api`): the flagged constructor is fully implemented via its "
            "member-initializer list. This directly caused a "
            "`public_quality.contradiction_capability_symbol` false-positive blocking the C++ "
            "canary (`DateTime` described as both available and unimplemented). Not fixed in "
            "`scout.py` itself: that file is byte-integrity checked against a pinned "
            "`source_commit` manifest "
            "(`tests/unit/test_aspose_org_vendored_source.py::"
            "test_vendored_source_rejects_changed_bytes`), and any change to it would also "
            "shift `generator_sha256`, invalidating every already-cached C++ (and any other "
            "native-language) knowledge-generation bundle across the portfolio -- see "
            "`CORE-035`. Full evidence: "
            "`plans/investigations/evidence/portfolio-proof-pf05-seven-ecosystem-canaries/"
            "cxx-datetime-stub-false-positive-2026-08-25.md`."
        ),
        "traceability": (
            "CORE-035; PF05-CXX-LINK-001 follow-on; independent production assessment, 2026-08-25"
        ),
    },
]


def main() -> None:
    existing_ids = set()
    with CATALOG_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            existing_ids.add(json.loads(line)["requirement_id"])
    new_rows = [row for row in ROWS if row["requirement_id"] not in existing_ids]
    if not new_rows:
        print("no new rows to append (already present)")
        return
    with CATALOG_PATH.open("a", encoding="utf-8", newline="\n") as handle:
        for row in new_rows:
            row = {**row, "schema_version": 1}
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"appended {len(new_rows)} requirement rows to {CATALOG_PATH}")


if __name__ == "__main__":
    main()
