#!/usr/bin/env python3
"""One-shot: log CORE-040 -- the `portfolio-proof` `full_pipeline_modes.py` engine discarding
`supervise_call`'s real process exit code, found and fixed during the autonomous mission-execution
phase on 2026-08-27 (originally documented as a "multiple effective controllers" finding, section
2.4, in plans/investigations/production-recovery-sprint-2026-08-27.md).

This is a plain defect fix against the repo's own existing Decision #100 ("`portfolio-proof`... must
not silently diverge from the supervisor's real per-repository outcome"), not a new architectural
decision -- so no new Decision Ledger entry, only a requirement row recording it, matching the
CORE-039 precedent's own note that a decision reference is optional when none is new.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/append_core040_supervise_exit_code_fix.py`
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
    "requirement_id": "CORE-040",
    "section": "9. Core engine and registry requirements",
    "status": "IMPLEMENTED",
    "priority": "P2",
    "requirement": (
        "`portfolio_proof_engine/full_pipeline_modes.py::_run_full_pipeline_cohort()` MUST "
        "capture and carry through the real integer return value of its "
        "`supervise_call(namespace)` dispatch, not discard it -- "
        "`stage_classifier.py::classify_repository_stage()` MUST accept an explicit "
        "`supervise_exit_code` parameter (default `None`, meaning no dispatch happened for "
        "this receipt) and `ProofStageReceiptV1` MUST record it, so a repository whose "
        "durable lifecycle state alone still classifies as a healthy-looking stage can be "
        "distinguished from one whose last dispatch actually exited non-zero."
    ),
    "acceptance_evidence": (
        "CORE040-SUPERVISE-EXIT-CODE-CAPTURED-001 (2026-08-27, autonomous execution phase): "
        "originally found during the production-recovery-sprint-2026-08-27 investigation "
        "(section 2.4, 'Multiple effective controllers' -- 'full_pipeline_modes.py:89 calls "
        "supervise_call(namespace) and never checks it; classification is entirely "
        "independent, post-hoc, from stage_classifier.py'). Fixed: added "
        "`supervise_exit_code: int | None = None` to `ProofStageReceiptV1` (contracts.py), "
        "threaded the same-named parameter through `classify_repository_stage()`'s "
        "signature and `common` dict (stage_classifier.py), and captured "
        "`exit_code = supervise_call(namespace)` at the single real call site "
        "(`_run_full_pipeline_cohort`, full_pipeline_modes.py), passing it into both the "
        "provisional and final `classify_repository_stage()` calls for that dispatch. "
        "`modes.py`'s two call sites and `intake_classification.py`'s two constructions "
        "never call `supervise_call` themselves, so they correctly leave the field at its "
        '`None` default -- confirmed via `grep -rln "classify_repository_stage(" src/ '
        "tests/`. New tests: "
        "`test_supervise_exit_code_defaults_to_none_when_the_caller_made_no_dispatch` and "
        "`test_supervise_exit_code_carries_through_unmodified_even_on_a_healthy_looking_"
        "stage` (test_portfolio_proof_engine_stage_classifier.py); "
        "`test_real_supervise_exit_code_flows_into_the_written_receipt` "
        "(test_portfolio_proof_engine_full_pipeline_modes.py) drives a fixture "
        "`supervise_call` that returns a nonzero exit code while still landing the "
        "repository in review-ready lifecycle state (reaching ACCEPTED), proving the code "
        "survives onto the written receipt where classification alone could not reveal it. "
        "All 61 portfolio-proof-engine unit tests pass; ruff/ruff-format/mypy clean on the "
        "full `portfolio_proof_engine` package (28 source files)."
    ),
    "traceability": (
        "Decision #100 (existing); production-recovery-sprint-2026-08-27.md section 2.4; "
        "found 2026-08-27 fixing production-recovery-sprint follow-on work"
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
    # Normalize to LF for regex/index work, restore CRLF on write -- the file is uniformly CRLF.
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

    # The status bullet block always starts with the first "- `" line after the count sentence
    # and runs until the blank line that precedes "Families:" -- exact wording of the
    # explanatory parenthetical in between is deliberately not matched, since it's free text.
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
    appended = _append_catalog_row()
    _refresh_requirements_md_summary()
    print(f"appended {appended} new catalog row(s); refreshed requirements.md summary")


if __name__ == "__main__":
    main()
