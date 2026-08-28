#!/usr/bin/env python3
"""One-shot: log CORE-041 -- the shared `evidence/writer.py::_atomic_write_text()` primitive's
missing Windows long-path handling on `mkdir`/`NamedTemporaryFile`, found via a real live
portfolio-worker crash and fixed with an empirically-validated reproduction.

Found and fixed while continuing the autonomous mission-execution phase on 2026-08-28, during
a user-approved full portfolio retry-blocked pass (Docker Desktop was the first blocker, fixed
separately; this is a second, independent defect found once Docker was available).

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/append_core041_atomic_write_long_path_fix.py`
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
    "requirement_id": "CORE-041",
    "section": "9. Core engine and registry requirements",
    "status": "IMPLEMENTED",
    "priority": "P1",
    "requirement": (
        "`evidence/writer.py::_atomic_write_text()` -- the shared atomic-write primitive "
        "behind `write_redacted_json()`/`write_redacted_text()`/`refresh_sha256sums()` and "
        "every other durable evidence write in this codebase -- MUST apply the same Windows "
        "long-path handling (`win_long_path()`/`_write_target()`) to its `mkdir` and "
        "`tempfile.NamedTemporaryFile(dir=...)` calls that it already applied to its final "
        "`os.replace()`, so a write under an already-long evidence path (portfolio worker "
        "receipts, deeply nested repository bundles, etc.) does not raise `[WinError 206] "
        "The filename or extension is too long` before ever reaching the long-path-safe part "
        "of the write."
    ),
    "acceptance_evidence": (
        "CORE041-ATOMIC-WRITE-LONGPATH-001 (2026-08-28, autonomous execution phase): found "
        "live during a full portfolio retry-blocked pass (Docker Desktop had just been "
        "started to fix a separate, first blocker -- see the same day's log). 5 of 6 "
        "processed repositories in iteration 1 were reported as `SYSTEM_FAILURE` in the "
        "portfolio's aggregate summary with zero per-repo diagnostic text anywhere in stdout/"
        "stderr. Traced via `runs/portfolio-workers/<hash>/batch-report.json` (written but "
        "not surfaced anywhere else) to find the real traceback for one repository "
        "(aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python): a "
        "`FileNotFoundError`/`OSError` inside `portfolio_worker_runtime.py::"
        "run_portfolio_worker()`'s `write_redacted_json(_receipt_path(args), ...)` call, "
        "bottoming out in `evidence/writer.py::_atomic_write_text()`'s `mkdir`/"
        "`NamedTemporaryFile` pair -- both used the raw, unwrapped `path.parent`, while only "
        "the function's final `os.replace()` call used the module's own `_write_target()` "
        "long-path helper. Confirmed the mechanism empirically before fixing: an isolated "
        "reproduction script using the unfixed logic against a 298-character path raised "
        "`[WinError 206] The filename or extension is too long` exactly as seen in the real "
        "traceback; the same script using `_write_target()`-wrapped `mkdir`/"
        "`NamedTemporaryFile(dir=...)` at 293 characters (well past Windows' 260-character "
        "MAX_PATH) completed the full write-temp-then-replace cycle correctly, including "
        "confirming `win_long_path()` is idempotent when re-applied to an already-prefixed "
        "path and that `os.path.join()` preserves the `\\\\?\\` prefix on a joined child path. "
        "Fixed `_atomic_write_text()` to wrap `path.parent` once via `_write_target()` before "
        "both the `os.makedirs()` call and the `NamedTemporaryFile(dir=...)` call. Also fixed "
        "a related, separately-real observability gap in the same investigation: "
        "`commands_supervision.py`'s worker-failure branch (the code path that classifies a "
        "crashed worker as portfolio-level `SYSTEM_FAILURE`) never printed anything about "
        "which repository failed or why -- unlike its sibling success-path branch, which "
        "does -- even though the real reason (`worker_result.exit_classification`, "
        "`stderr_excerpt`) was already available there; only the aggregate `system_failed=N` "
        "count and the `batch-report.json` file (not otherwise surfaced) carried any signal. "
        "Added a matching print there. Verified: `test_evidence_writer.py`, "
        "`test_portfolio_worker_integration.py`, `test_cli.py`, and "
        "`test_portfolio_proof_engine_repository_worker_pool.py` (138 tests) all pass; a full "
        "clean-tree suite run afterward (`tree_changed_during_run: false`, `dirty_tree: true` "
        "expected for the uncommitted fix itself) shows **4 failed, 5458 passed, 1 skipped** "
        "-- the same 4 pre-existing VER-014/RDM-034 failures, zero new regressions from a "
        "change to this widely-shared primitive. ruff/ruff-format/mypy clean on both files."
    ),
    "traceability": (
        "found 2026-08-28 during a user-approved full portfolio retry-blocked pass, second "
        "of two independent blockers found in the same pass (first was Docker Desktop not "
        "running, an environment issue, not a code defect)"
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
