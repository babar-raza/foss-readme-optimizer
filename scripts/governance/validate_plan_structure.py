"""Mechanical structural-integrity gate for the plan trio and the logs/ index.

Replaces prose-only governance (`GOVERNANCE.md` rules 2/6/11/12, `GOV-009`) with a real check that
runs in two places -- as a local pre-commit hook (rejects the commit itself, before anything can
be pushed or seen by another session) and as a required CI step (backstops a `--no-verify` commit
or a hookless clone). Decision #46: a foreign-section incident on 2026-07-22 showed that a rule
living only in prose is violated the moment a session doesn't check it first, and nothing catches
it until a human happens to notice. See `docs/architecture.md`'s own note on `presentation_
benchmarking` for a second, independent instance this exact script now closes.

Exit code 0 = all blocking checks pass (warnings may still print). Exit code 1 = at least one
blocking check failed. Never modifies anything -- read-only by design, same posture as `github_api/
client.py`.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MASTER_MD = REPO_ROOT / "plans" / "master.md"
REQUIREMENTS_MD = REPO_ROOT / "plans" / "requirements.md"
ARCHITECTURE_MD = REPO_ROOT / "docs" / "architecture.md"
LOGS_DIR = REPO_ROOT / "logs"
LOGS_INDEX = LOGS_DIR / "README.md"
SPECIALISTS_REGISTRY = REPO_ROOT / "src" / "readme_agent" / "specialists" / "registry.py"

# GOVERNANCE.md rule 2's fixed section order.
FIXED_SECTION_ORDER = (
    "Mission",
    "Status",
    "Decision Ledger",
    "Architecture",
    "Registry & Policy Config",
    "Validator Registry",
    "LLM Contract",
    "CI & Safety",
    "Reference Data",
    "Build Checklist",
    "Verification Checklist",
    "Changelog",
)

VALID_STATUSES = {
    "IMPLEMENTED",
    "PLANNED",
    "PARTIAL",
    "BACKLOG",
    "GOVERNANCE",
    "RESEARCH-GATED",
    "DEPRECATED",
    "SUPERSEDED",
}
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}

ID_RE = re.compile(r"^[A-Z]{2,5}-\d{3}$")
ROW_LENGTH_WARN_THRESHOLD = 1500
SHARD_DENSE_WARN_LINES = 1500

ENTRY_LINE_RE = re.compile(r"^-\s*(?:\[[^\]]+\]\s*)+\*\*\d{4}-\d{2}-\d{2}")
INDEX_ROW_RE = re.compile(r"^\|\s*\d{4}-\d{2}-\d{2}\s*\|")
SHARD_DIR_ROW_RE = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*`logs/([^`]+)`\s*\|\s*(\d+)\s*\|")

# GOV-022 (wave-entry reconciliation gate).
WAVE_CHECKLIST_RE = re.compile(r"^- \[(x| )\] Wave (\d+(?:\.\d+)?)\b", re.MULTILINE)
LOG_WAVE_TOKEN_RE = re.compile(r"Wave\s+(\d+)")


class Result:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def check_master_section_order(result: Result) -> None:
    if not MASTER_MD.exists():
        result.error("plans/master.md not found")
        return
    text = MASTER_MD.read_text(encoding="utf-8")
    headers = [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]
    if headers != list(FIXED_SECTION_ORDER):
        result.error(
            "plans/master.md's top-level `## ` sections do not match GOVERNANCE.md rule 2's "
            f"fixed order.\n    Expected: {list(FIXED_SECTION_ORDER)}\n    Found:    {headers}"
        )


STATUS_SECTION_LINE_CEILING = 40


def check_master_status_section_stays_terse(result: Result) -> None:
    """Wave 9.3 (2026-07-23) replaced `master.md`'s old hand-narrated Status section (251 lines,
    every paragraph duplicating its own Decision Ledger entry) with a short pointer into the
    generated `plans/status.md` (regenerate via `traceability_matrix.py`), `plans/roadmap.md`, and
    `logs/` -- per `GOVERNANCE.md` rule 1 (this file holds current state, never history). The old
    `check_master_status_mentions_latest_decision` check assumed Status would keep enumerating
    decision numbers by hand and is retired: under the new design it never will, by design, so
    that check would warn on every single future decision forever. This replacement check instead
    guards the actual property Wave 9.3 established: Status stays a short pointer, not a creeping
    re-narration of history that drifts back into what this file's Decision Ledger already
    records."""
    if not MASTER_MD.exists():
        return
    text = MASTER_MD.read_text(encoding="utf-8")
    status_start = text.find("\n## Status\n")
    ledger_start = text.find("\n## Decision Ledger\n")
    if status_start == -1 or ledger_start == -1:
        return
    status_text = text[status_start:ledger_start]
    line_count = len([line for line in status_text.splitlines() if line.strip()])
    if line_count > STATUS_SECTION_LINE_CEILING:
        result.warn(
            f"plans/master.md's Status section is {line_count} non-blank lines (over the "
            f"{STATUS_SECTION_LINE_CEILING}-line ceiling Wave 9.3 established) -- it may be "
            "drifting back into hand-narrated history instead of staying a pointer into "
            "plans/status.md/plans/roadmap.md/logs/."
        )


# ID | Priority | Status | Requirement | Acceptance evidence | Traceability
REQUIREMENTS_TABLE_COLUMNS = 6

_UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")


def _split_table_row(line: str) -> list[str]:
    """Split a Markdown table row into cells, honoring GFM's `\\|` escape -- a raw `.split("|")`
    misreads any cell containing an escaped pipe (a shell command like `a | b`, a Python union
    type like `str | None`) as an extra column boundary. Found live 2026-07-22: five real rows
    (`OPS-009`, `EFF-004`, `ORC-006`, `VER-005`, `SCL-005`) had exactly this defect before their
    pipes were escaped -- this splitter is what makes both this validator and any downstream
    traceability tooling read them correctly instead of silently mis-parsing them."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    cells = [cell.strip() for cell in _UNESCAPED_PIPE_RE.split(stripped)]
    return cells


def _requirement_rows(text: str) -> list[tuple[str, str, str, int, int]]:
    """Return (id, status, priority, char_length, line_number) for every requirement row."""
    rows = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.startswith("| "):
            continue
        cells = _split_table_row(line)
        if len(cells) < 3:
            continue
        candidate_id = cells[0].strip("`")
        if not ID_RE.match(candidate_id):
            continue
        priority = cells[1].strip("`")
        status = cells[2].strip("`")
        rows.append((candidate_id, status, priority, len(line), lineno))
    return rows


def check_requirement_row_column_counts(result: Result) -> None:
    """A data row must split into exactly `REQUIREMENTS_TABLE_COLUMNS` cells under a real,
    escape-aware split -- an unescaped `|` inside a shell command or a Python union type (`str |
    None`) silently shifts every later cell in that row by one column, and a naive `.split("|")`
    (the exact bug this check exists to catch) would misread Acceptance-evidence content as
    Traceability or vice versa. Found and fixed for five real rows, 2026-07-22 -- this is the
    mechanical backstop so the class of defect fails CI/pre-commit instead of recurring silently."""
    if not REQUIREMENTS_MD.exists():
        return
    text = REQUIREMENTS_MD.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.startswith("| "):
            continue
        cells = _split_table_row(line)
        if not cells:
            continue
        candidate_id = cells[0].strip("`")
        if not ID_RE.match(candidate_id):
            continue
        if len(cells) != REQUIREMENTS_TABLE_COLUMNS:
            result.error(
                f"plans/requirements.md:{lineno} `{candidate_id}` splits into {len(cells)} cells, "
                f"expected {REQUIREMENTS_TABLE_COLUMNS} -- an unescaped `|` inside inline code "
                "(a shell pipe, a Python `X | None` union) is shifting later columns. Escape it "
                "as `\\|`."
            )


def check_requirements(result: Result) -> None:
    if not REQUIREMENTS_MD.exists():
        result.error("plans/requirements.md not found")
        return
    text = REQUIREMENTS_MD.read_text(encoding="utf-8")
    rows = _requirement_rows(text)
    seen: dict[str, int] = {}
    for req_id, status, priority, length, lineno in rows:
        if req_id in seen:
            result.error(
                f"plans/requirements.md:{lineno} duplicate requirement ID `{req_id}` "
                f"(first seen at line {seen[req_id]})"
            )
        else:
            seen[req_id] = lineno
        if status not in VALID_STATUSES:
            result.error(
                f"plans/requirements.md:{lineno} `{req_id}` has invalid Status `{status}` "
                f"(expected one of {sorted(VALID_STATUSES)})"
            )
        if priority not in VALID_PRIORITIES:
            result.error(
                f"plans/requirements.md:{lineno} `{req_id}` has invalid Priority `{priority}` "
                f"(expected one of {sorted(VALID_PRIORITIES)})"
            )
        if length > ROW_LENGTH_WARN_THRESHOLD:
            result.warn(
                f"plans/requirements.md:{lineno} `{req_id}` row is {length} chars "
                f"(over the {ROW_LENGTH_WARN_THRESHOLD}-char retrofit-on-touch guidance)"
            )


def check_logs_shard_index_consistency(result: Result) -> None:
    if not LOGS_DIR.exists():
        return
    real_counts: dict[str, int] = {}
    for path in sorted(LOGS_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        shard_text = path.read_text(encoding="utf-8")
        entries = sum(1 for line in shard_text.splitlines() if ENTRY_LINE_RE.match(line))
        index_rows = sum(1 for line in shard_text.splitlines() if INDEX_ROW_RE.match(line))
        if entries != index_rows:
            result.error(
                f"logs/{path.name}: {entries} entries but {index_rows} local index-table rows "
                "-- these must match."
            )
        real_counts[path.stem] = entries
        line_count = len(shard_text.splitlines())
        if line_count > SHARD_DENSE_WARN_LINES:
            result.warn(
                f"logs/{path.name} is {line_count} lines (past the typical-day guidance) -- "
                "consider a same-day split per logs/README.md."
            )

    if not LOGS_INDEX.exists():
        result.error("logs/README.md not found")
        return
    index_text = LOGS_INDEX.read_text(encoding="utf-8")
    indexed: dict[str, int] = {}
    for line in index_text.splitlines():
        match = SHARD_DIR_ROW_RE.match(line)
        if match:
            indexed[match.group(1)] = int(match.group(3))

    for date, count in real_counts.items():
        if date not in indexed:
            result.error(
                f"logs/README.md's shard directory is missing an entry for logs/{date}.md "
                f"({count} real entries)."
            )
        elif indexed[date] != count:
            result.error(
                f"logs/README.md claims logs/{date}.md has {indexed[date]} entries; "
                f"the real count is {count}."
            )
    for date in indexed:
        if date not in real_counts:
            result.error(f"logs/README.md indexes logs/{date}.md, which does not exist.")


def check_specialist_module_map_completeness(result: Result) -> None:
    if not SPECIALISTS_REGISTRY.exists() or not ARCHITECTURE_MD.exists():
        return
    registry_text = SPECIALISTS_REGISTRY.read_text(encoding="utf-8")
    domains = set(re.findall(r"domain=(\w+)\.DOMAIN", registry_text))
    arch_text = ARCHITECTURE_MD.read_text(encoding="utf-8")
    missing = sorted(d for d in domains if f"{d}.py" not in arch_text)
    if missing:
        result.error(
            "docs/architecture.md's module map is missing a row for these registered "
            f"specialist modules: {missing} -- GOVERNANCE.md placement rule 2 requires the "
            "module map to be updated in the same change that adds a new src module."
        )


_USE_GIT = object()  # sentinel: "no override supplied, ask git for HEAD's version" -- tests pass
# an explicit str (or None, for "no git history available") instead of this default.


def _previous_master_md_text() -> str | None:
    """`plans/master.md` as it stood at HEAD, i.e. before whatever is currently being committed.
    Returns None (not an error -- there is nothing to diff against) if git history isn't
    available, e.g. a shallow clone or the very first commit."""
    try:
        completed = subprocess.run(
            ["git", "show", "HEAD:plans/master.md"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def _logged_wave_numbers(logs_dir: Path) -> set[str]:
    numbers: set[str] = set()
    if not logs_dir.exists():
        return numbers
    for path in logs_dir.glob("*.md"):
        if path.name == "README.md":
            continue
        shard_text = path.read_text(encoding="utf-8")
        numbers.update(m.group(1) for m in LOG_WAVE_TOKEN_RE.finditer(shard_text))
    return numbers


def check_wave_reconciliation_gate(
    result: Result,
    previous_master_text: str | None = _USE_GIT,  # type: ignore[assignment]
) -> None:
    """GOV-022: a Build Checklist wave item may not flip `[ ]` -> `[x]` in the same change with no
    logs/ entry whose Wave/Phase column names that wave. Deliberately diff-aware (compares the
    working copy against HEAD, not a static snapshot) so Waves 0-8 -- checked off before this gate
    or its logging tool existed -- are never retroactively flagged; only a wave newly checked off
    in the change under review is held to this bar. `previous_master_text` is an injectable seam
    for tests; production callers always take the `_USE_GIT` default."""
    if not MASTER_MD.exists():
        return
    if previous_master_text is _USE_GIT:
        previous_master_text = _previous_master_md_text()
    if previous_master_text is None:
        return
    current_text = MASTER_MD.read_text(encoding="utf-8")
    current_checked = {
        m.group(2) for m in WAVE_CHECKLIST_RE.finditer(current_text) if m.group(1) == "x"
    }
    previously_checked = {
        m.group(2) for m in WAVE_CHECKLIST_RE.finditer(previous_master_text) if m.group(1) == "x"
    }
    newly_checked = current_checked - previously_checked
    if not newly_checked:
        return
    logged = _logged_wave_numbers(LOGS_DIR)
    for wave in sorted(newly_checked, key=float):
        wave_int = wave.split(".")[0]
        if wave_int not in logged:
            result.error(
                f"plans/master.md's Build Checklist newly checks off Wave {wave} in this change, "
                f'but no logs/*.md entry\'s Wave/Phase column references "Wave {wave_int}" -- '
                "GOVERNANCE.md rule 11 (GOV-022) requires a reconciliation note in the same "
                "change that marks a wave done."
            )


def main() -> int:
    result = Result()
    check_master_section_order(result)
    check_master_status_section_stays_terse(result)
    check_requirements(result)
    check_requirement_row_column_counts(result)
    check_logs_shard_index_consistency(result)
    check_specialist_module_map_completeness(result)
    check_wave_reconciliation_gate(result)

    for warning in result.warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if result.errors:
        print(f"\n{len(result.errors)} blocking error(s), {len(result.warnings)} warning(s).")
        return 1
    print(f"Plan structure clean ({len(result.warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
