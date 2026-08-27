#!/usr/bin/env python3
"""One-shot: update VER-012's evidence with the real fixes landed this session, and log
VER-014 for the new, distinct lifecycle-transition gap those fixes uncovered underneath.

Found and fixed while continuing the autonomous mission-execution phase on 2026-08-27,
picking up VER-012 (`tests/unit/test_supervisor_loop.py`'s 4 bounded-review fixture-gap
failures, previously root-caused but not fixed -- see
plans/investigations/evidence/windows-max-path-and-bounded-review-fixture-gaps-2026-08-26/
bounded-review-retry-fixture-gap-2026-08-26.md).

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/update_ver012_and_log_ver014.py`
Kept after use as the executable record of what was appended (repo layout placement rule 5).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"
REQUIREMENTS_MD_PATH = REPO_ROOT / "plans" / "requirements.md"

VER012_STATUS = "PARTIAL"
VER012_EVIDENCE = (
    "VER012-BOUNDED-RETRY-001 (2026-08-26): see prior evidence above -- root-caused but not "
    "fixed. VER012-FIXTURE-GROUNDING-002 (2026-08-27, autonomous execution phase): fixed the "
    "actual cause instead of implementing the retry-shape branch this row originally proposed "
    "-- the compact-grounding-retry crash never fires once the FIRST bounded-review attempt "
    "grounds cleanly, and both reasons it didn't were fixture bugs, not production bugs. "
    "(1) `_blind_accept()` hardcoded `criterion: 'clarity'`, but "
    "`bounded_visitor_scope.py::_CRITERIA_BY_ROOT['navigation']` excludes 'clarity' -- any "
    "bounded-review call scoped to a '## Navigation' anchor failed "
    "`bounded_visitor_scope_errors()` on attempt 1. Fixed by switching to "
    "'markdown_integrity', the one criterion present in every `_CRITERIA_BY_ROOT` entry and "
    "in `_DEFAULT_CRITERIA` (confirmed by direct enumeration, not assumption). (2) "
    "`_selected_fact_response()` only read `product_facts['selected_fact_ids']` (a dict, the "
    "merged-review path's shape) -- `bounded_review_execution_factual.py::"
    "execute_factual_packet()`'s own `fact_context` uses `accepted_fact_ids` (a list) for the "
    "bounded per-packet path instead, so every bounded factual review call found zero "
    "candidate fact IDs. Fixed by checking both keys. (3) Even with fact IDs resolved, a "
    "generic template bullet (e.g. 'Process Supported Content') has no literal fact-value "
    "phrase to quote -- traced `review_finding_grounding.py::validate_review_findings()` "
    "directly and confirmed `quoted_candidate_span` (must be a literal candidate substring) "
    "and `evidence_excerpt` (must relate to the cited fact's own evidence via "
    "`_fact_evidence_strings()`) are validated independently and need not overlap; added a "
    "fallback that pairs any literal candidate line with the fact's own source location "
    "(always in `_fact_evidence_strings()`'s evidence set verbatim). All three fixes are in "
    "`tests/review_role_fixture_support.py` only -- no production code changed for this part. "
    "VER012-MAXPATH-DISCOVERED-003 (2026-08-27): fixing the above surfaced a second, "
    "independent, real production bug the fixture fixes alone couldn't reach: "
    "`local_poc_replay_snapshots.py::materialize_transaction_snapshot()` copied the long, "
    "original `bundle_dir` (`<repo>/<40-char revision>/...`, measured up to 289 characters) "
    "via a plain `shutil.copytree()` with no Windows long-path handling, unlike its sibling "
    "`local_poc_review_cache_preservation.py` (already fixed for the identical class of bug "
    "this same investigation thread found on 2026-08-26). Confirmed live via the exact "
    "`[WinError 3] The system cannot find the path specified` warning naming a "
    "`_tx/~xxxxxxxx/review/bounded-packet-cache/<64-hex>.json` destination path measured at "
    "262 characters. Fixed by wrapping both the copy source (`bundle_dir`) and destination "
    "(`temporary`) with the module's own new `_long_path()` helper (same `win_long_path()` "
    "precedent `local_poc_review_cache_preservation.py`/`local_poc_superseded.py` already "
    "use). Separately, `local_poc_superseded.py::_write_deterministic_packet_cache_archive()` "
    "-- ironically the function this module built specifically to route around MAX_PATH by "
    "zipping the packet cache -- never wrapped its own `ZipFile()`/`rglob()`/`read_bytes()` "
    "calls with `_long_path()` either; confirmed live via a `FileNotFoundError` on "
    "`bounded-packet-cache.zip` from `refresh_sha256sums()` walking the archive's parent tree "
    "afterward (the archive was silently never written for a long enough repository path). "
    "Fixed the same way. `test_heterogeneous_local_poc_members_share_the_real_supervisor_path` "
    "now passes cleanly end to end -- 1 of the 4 originally tracked failures fully resolved, "
    "and a full regression sweep (`test_supervisor_loop.py` + the 146 tests across "
    "`test_specialists.py`/`test_readme_review_roles.py`/`test_separated_readme_review.py`, "
    "229 tests total) shows zero new regressions from any of the fixes above (226 passed, "
    "3 failed -- all 3 the pre-existing, now precisely re-diagnosed VER-014 gap below). "
    "ruff/ruff-format/mypy clean on all 3 changed files. Remaining 3 of 4: re-diagnosed as a "
    "third, distinct, NOT-yet-fixed defect -- see VER-014."
)

NEW_ROWS: list[dict] = [
    {
        "requirement_id": "VER-014",
        "section": "19. Autonomous runtime and capability requirements",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "The local-POC supervise loop's no-op/repair convergence logic MUST reach "
            "`NO_OP_PROVEN` for a second `supervise_repo()` call that independently reports "
            "`CONVERGED_NO_TRACKED_CHANGE`/`accepted_status='NO_CHANGE'` against durable state "
            "persisted from a first, accepted call, and MUST re-enter `AGENT_REVIEWING` for "
            "each genuine repair-then-revalidate cycle a repaired candidate triggers -- not "
            "silently plateau at `AGENT_APPROVED` or under-count review cycles."
        ),
        "acceptance_evidence": (
            "VER014-NOOP-AND-REPAIR-CYCLE-GAP-001 (2026-08-27, autonomous execution phase): "
            "found immediately after fixing VER-012's fixture-grounding and Windows MAX_PATH "
            "bugs (see VER-012's evidence) -- those fixes let bounded review run to real "
            "completion for the first time in these 3 tests, which is what exposed this "
            "distinct next-layer gap; it was invisible before because every affected repository "
            "was silently failing earlier in the pipeline. "
            "`test_local_poc_records_snapshot_and_profile_before_later_stages`: a second "
            "`supervise_repo()` call resumed from persisted-only state (simulating a process "
            "restart) correctly reports `second.status == 'CONVERGED_NO_TRACKED_CHANGE'` and "
            "`accepted_status == 'NO_CHANGE'`, but `lifecycle.status` stays `AGENT_APPROVED` "
            "instead of advancing to `NO_OP_PROVEN`. "
            "`test_local_poc_repairs_revalidates_and_rereviews_before_accepting`: "
            "`lifecycle.history` shows `AGENT_REVIEWING` exactly once where the test's own "
            "repair-then-revalidate-then-rereview scenario expects two independent entries "
            "(`statuses.count('AGENT_REVIEWING') == 1`, expected 2). "
            "`test_local_poc_byte_identical_repair_reroutes_before_rereview`: "
            "`result.status == 'CONVERGED_PROPOSAL_READY'` where the test's own byte-identical-"
            "repair scenario expects `'BLOCKED'`. Not yet determined whether these three share "
            "one root cause (most likely, given all three concern the same no-op/repair-cycle "
            "convergence layer) or are independent -- not investigated further this session; "
            "each needs direct tracing through the relevant lifecycle-transition code the same "
            "way VER-012's fixture bugs were traced, which is a genuinely separate, dedicated "
            "task from the MAX_PATH/fixture work that surfaced it."
        ),
        "traceability": (
            "GOV-014; VER-012; found 2026-08-27 immediately after fixing VER-012's "
            "fixture-grounding and Windows MAX_PATH bugs"
        ),
    },
]


def _update_catalog() -> int:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    existing_ids = {json.loads(line)["requirement_id"] for line in lines if line.strip()}

    updated_lines: list[str] = []
    for line in lines:
        record = json.loads(line)
        if record["requirement_id"] == "VER-012":
            record["status"] = VER012_STATUS
            record["acceptance_evidence"] = VER012_EVIDENCE
        updated_lines.append(json.dumps(record, ensure_ascii=False))

    new_rows = [row for row in NEW_ROWS if row["requirement_id"] not in existing_ids]
    for row in new_rows:
        record = {
            **row,
            "schema_version": 1,
            "legacy_line": len(updated_lines) + 1,
            "legacy_row_sha256": hashlib.sha256(
                f"native-authored:{row['requirement_id']}".encode()
            ).hexdigest(),
        }
        updated_lines.append(json.dumps(record, ensure_ascii=False))

    CATALOG_PATH.write_text("\n".join(updated_lines) + "\n", encoding="utf-8", newline="\n")
    return len(new_rows)


def _refresh_requirements_md_summary() -> None:
    """Same logic as `append_core040_supervise_exit_code_fix.py`'s own summary refresh --
    duplicated rather than imported, since one-shot retrofit scripts are kept standalone."""

    data = REQUIREMENTS_MD_PATH.read_bytes()
    original_text = data.decode("utf-8")
    if "\r\n" not in original_text:
        raise SystemExit("expected requirements.md to be CRLF-encoded; got no CRLF at all")
    text = original_text.replace("\r\n", "\n")

    catalog_text = CATALOG_PATH.read_text(encoding="utf-8")
    lines = [json.loads(line) for line in catalog_text.splitlines() if line.strip()]
    total = len(lines)
    status_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    for record in lines:
        status_counts[record["status"]] = status_counts.get(record["status"], 0) + 1
        family_match = re.match(r"^([A-Z0-9]+)-", record["requirement_id"])
        if family_match:
            family = family_match.group(1)
            family_counts[family] = family_counts.get(family, 0) + 1

    total_anchor = text.index("The catalog contains")
    total_pattern = re.compile(r"The catalog contains \*\*\d+\*\* requirements \([0-9-]+ -- ")
    new_total_prefix = f"The catalog contains **{total}** requirements (2026-08-27 -- "
    match = total_pattern.match(text, total_anchor)
    if match is None:
        raise SystemExit("failed to locate the catalog-count summary line")
    text = text[: match.start()] + new_total_prefix + text[match.end() :]
    after_total = match.start() + len(new_total_prefix)

    bullet_start = text.index("- `", after_total)
    families_anchor = text.index("Families: ", bullet_start)
    bullet_end = text.rindex("\n\n", bullet_start, families_anchor) + 1
    status_lines = "".join(
        f"- `{status}`: {count}\n" for status, count in sorted(status_counts.items())
    )
    text = text[:bullet_start] + status_lines + text[bullet_end:]

    families_line_pattern = re.compile(r"Families: .*?\.\n")
    families_text = ", ".join(
        f"`{family}` {count}" for family, count in sorted(family_counts.items())
    )
    text, count = families_line_pattern.subn(f"Families: {families_text}.\n", text, count=1)
    if count != 1:
        raise SystemExit("failed to locate the Families summary line")

    REQUIREMENTS_MD_PATH.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))


def main() -> None:
    new_row_count = _update_catalog()
    _refresh_requirements_md_summary()
    print(f"updated VER-012, appended {new_row_count} new row(s), refreshed requirements.md")


if __name__ == "__main__":
    main()
