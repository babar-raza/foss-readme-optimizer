#!/usr/bin/env python3
"""One-shot: log CORE-042 -- the portfolio worker-pool's `load_worker_receipt()` rejecting
every valid, legitimately-nonzero-exit receipt (BLOCKED dispositions, not only genuine
crashes), found and fixed in the same live portfolio pass that surfaced CORE-041.

Found and fixed while continuing the autonomous mission-execution phase on 2026-08-28.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/append_core042_worker_receipt_exit_code_fix.py`
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

NEW_ROW = {
    "requirement_id": "CORE-042",
    "section": "9. Core engine and registry requirements",
    "status": "IMPLEMENTED",
    "priority": "P1",
    "requirement": (
        "`portfolio_worker_dispatch.py::load_worker_receipt()` MUST NOT reject a worker's "
        "receipt solely because its process exit code was nonzero -- `cmd_supervise` returns "
        "a nonzero exit code for a completed, legitimate non-error disposition (e.g. "
        "`BLOCKED`), not only for a genuine crash. It MUST instead accept a "
        "`CHILD_NONZERO_EXIT` worker's receipt when it passes every existing identity check "
        "(registry revision, org_repo, invocation ID, source revision) AND the receipt's own "
        "recorded `result.exit_code` agrees with the process's actual observed "
        "`return_code` -- the additional consistency check needed to keep rejecting a stale "
        "or `finally`-block-corrupted receipt (see the existing "
        "`test_failed_current_worker_cannot_reuse_a_stale_success_receipt` regression test, "
        "which this change must continue to pass unmodified)."
    ),
    "acceptance_evidence": (
        "CORE042-WORKER-RECEIPT-EXITCODE-001 (2026-08-28, autonomous execution phase): found "
        "immediately after fixing CORE-041 in the same live portfolio pass -- a relaunch "
        "still showed `SYSTEM_FAILURE [worker=CHILD_NONZERO_EXIT]` for 6 repositories, but "
        "each one's own `stdout_excerpt` in `batch-report.json` showed a completely normal, "
        "successfully-completed `BLOCKED (...)` disposition from `cmd_supervise` itself -- "
        "the underlying work had fully succeeded. Traced to `load_worker_receipt()`'s first "
        "gate: `if not worker_result.succeeded or worker_result.exit_classification != "
        "'SUCCEEDED': return None` -- discarding every valid receipt whenever the CLI's own "
        "exit code was nonzero, regardless of whether that nonzero code represented a real "
        "crash or a legitimate BLOCKED outcome. Proved this structurally before fixing: "
        "`run_portfolio_worker()` (`portfolio_worker_runtime.py`) writes its receipt only "
        "after `invoke(args)` returns without raising, so a receipt passing every identity "
        "check is strong evidence of a clean run regardless of exit code -- but not airtight "
        "on its own, since the function's own `finally: reset_registry_revision(token)` "
        "cleanup step runs *after* the receipt write and *could* itself fail, producing a "
        "process exit code that disagrees with what the already-written receipt honestly "
        "recorded. Confirmed this exact edge case was already covered by an existing test, "
        "`test_failed_current_worker_cannot_reuse_a_stale_success_receipt` (a receipt "
        "claiming `exit_code=0` while the observed `return_code=1` must still be rejected), "
        "which failed against an initial, too-broad fix (accepting any `CHILD_NONZERO_EXIT` "
        "unconditionally). Landed the narrower, correct fix instead: accept "
        "`CHILD_NONZERO_EXIT` receipts, but additionally require `receipt.result.exit_code "
        "== worker_result.return_code` -- the one field a genuinely consistent, "
        "current-invocation receipt can never disagree with itself on. Added a new "
        "regression test, `test_nonzero_exit_worker_with_an_exit_code_consistent_receipt_"
        "is_trusted`, covering the real-world scenario this fixes (a `BLOCKED` disposition "
        "whose receipt honestly agrees with the observed nonzero exit); the pre-existing "
        "stale-receipt test still passes unmodified. Also discovered and deliberately left "
        "unchanged: `portfolio.py::PortfolioPocSummaryV1.system_failure_count` counts every "
        "`blocked_category == 'agent_fixable'` BLOCKED repository alongside genuine "
        "`SYSTEM_FAILURE` ones in its aggregate count -- a separate, apparently intentional "
        "reporting decision (most BLOCKED dispositions in this codebase use exactly that "
        "category), out of scope for this fix. Fixed the Gate A driver script "
        "(`run_gate_a_local_poc_portfolio_loop.sh`) accordingly: its stop-on-failure check "
        "briefly used that same aggregate `system_failed=N` field earlier the same day (see "
        "CORE-041's own commit), which would have stopped on every ordinary blocked "
        "repository given the above; reverted to the literal per-repo `SYSTEM_FAILURE` "
        "line, now accurate again after both this fix and CORE-041's own per-repo print fix. "
        "`test_portfolio_worker_integration.py` (7/7, all passing), `test_cli.py`, "
        "`test_portfolio_proof_engine_repository_worker_pool.py`, and "
        "`test_evidence_writer.py` (139 tests total) pass; a full clean-tree suite run "
        "afterward (`tree_changed_during_run` clean) shows **4 failed, 5459 passed, 1 "
        "skipped** -- the same 4 pre-existing VER-014/RDM-034 failures plus one new passing "
        "test, zero new regressions. ruff/ruff-format/mypy clean."
    ),
    "traceability": (
        "found 2026-08-28 during the same user-approved full portfolio retry-blocked pass "
        "that found CORE-041, immediately after that fix landed"
    ),
}


def _append_catalog_row() -> int:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    existing_ids = {json.loads(line)["requirement_id"] for line in lines if line.strip()}
    if NEW_ROW["requirement_id"] in existing_ids:
        return 0
    record = {
        **NEW_ROW,
        "schema_version": 1,
        "legacy_line": len(lines) + 1,
        "legacy_row_sha256": hashlib.sha256(
            f"native-authored:{NEW_ROW['requirement_id']}".encode()
        ).hexdigest(),
    }
    lines.append(json.dumps(record, ensure_ascii=False))
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return 1


def _refresh_requirements_md_summary() -> None:
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
    new_total_prefix = f"The catalog contains **{total}** requirements (2026-08-28 -- "
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
    new_row_count = _append_catalog_row()
    _refresh_requirements_md_summary()
    print(f"appended {new_row_count} new row(s), refreshed requirements.md")


if __name__ == "__main__":
    main()
