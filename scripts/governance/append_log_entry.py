"""Governance log-entry generator.

Appends one dated `logs/` entry (creating the shard with its canonical header on a day's first
entry) plus its own local index row, then refreshes `logs/README.md`'s shard directory table --
so no session hand-edits these three surfaces independently and lets them drift out of sync
(exactly the drift found live 2026-07-22: a hand-written shard missing its own header/index
structure, and an index table two days stale). See `GOVERNANCE.md` rule 6 and decision #46.

Standalone; never imported by `src/`. Usage:

    python scripts/governance/append_log_entry.py \\
        --date 2026-07-22 --tags master incident \\
        --decisions 46 --requirements GOV-009 GOV-014 \\
        --wave-phase "Wave 9" \\
        --title "Removed 10 foreign sections from master.md; added Decision 46." \\
        --summary "Short one-line index-table summary." \\
        --body-file /path/to/full_entry_body.md
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = REPO_ROOT / "logs"
INDEX_FILE = LOGS_DIR / "README.md"

INDEX_TABLE_HEADER = "| Date | Tags | Decisions | Requirements | Wave/Phase | Summary |\n"
INDEX_TABLE_SEPARATOR = "|---|---|---|---|---|---|\n"

ENTRY_LINE_RE = re.compile(r"^-\s*(?:\[[^\]]+\]\s*)+\*\*\d{4}-\d{2}-\d{2}")
INDEX_ROW_RE = re.compile(r"^\|\s*\d{4}-\d{2}-\d{2}\s*\|")
SHARD_DIR_ROW_RE = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*`logs/([^`]+)`\s*\|\s*(\d+)\s*\|")


def shard_path(date: str) -> Path:
    return LOGS_DIR / f"{date}.md"


def shard_header(date: str) -> str:
    return (
        f"# Project log — {date}\n\n"
        "Back to [index](README.md).\n\n"
        "## Index\n\n"
        f"{INDEX_TABLE_HEADER}{INDEX_TABLE_SEPARATOR}"
    )


def build_index_row(
    date: str,
    tags: list[str],
    decisions: list[str],
    requirements: list[str],
    wave_phase: list[str],
    summary: str,
) -> str:
    tags_s = " ".join(tags) if tags else "—"
    dec_s = ", ".join(f"#{d}" for d in decisions) if decisions else "—"
    req_s = ", ".join(f"`{r}`" for r in requirements) if requirements else "—"
    wave_s = ", ".join(wave_phase) if wave_phase else "—"
    return f"| {date} | {tags_s} | {dec_s} | {req_s} | {wave_s} | {summary} |\n"


def build_entry_block(tags: list[str], date: str, title: str, body: str) -> str:
    tag_s = " ".join(tags)
    return f"- [{tag_s}] **{date} — {title}** {body.strip()}\n"


def insert_index_row(text: str, row: str) -> str:
    """Insert `row` as the last row of the `## Index` table, before `## Entries`."""
    entries_marker = "\n## Entries\n"
    idx = text.index(entries_marker)
    head, tail = text[:idx], text[idx:]
    if not head.endswith("\n"):
        head += "\n"
    return f"{head}{row}{tail}"


def append_entry_block(text: str, block: str) -> str:
    if not text.endswith("\n"):
        text += "\n"
    if not text.endswith("\n\n"):
        text += "\n"
    return text + block


def ensure_shard(date: str) -> str:
    path = shard_path(date)
    if not path.exists():
        return shard_header(date) + "\n## Entries\n\n"
    return path.read_text(encoding="utf-8")


def count_entries(text: str) -> int:
    return sum(1 for line in text.splitlines() if ENTRY_LINE_RE.match(line))


def count_index_rows(text: str) -> int:
    return sum(1 for line in text.splitlines() if INDEX_ROW_RE.match(line))


def refresh_shard_directory(index_text: str) -> str:
    """Recompute every shard's real entry count and rewrite the shard-directory table."""
    real_counts: dict[str, int] = {}
    for path in sorted(LOGS_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        date = path.stem
        real_counts[date] = count_entries(path.read_text(encoding="utf-8"))

    lines = index_text.splitlines(keepends=True)

    def _is_table_line(line: str) -> bool:
        return bool(SHARD_DIR_ROW_RE.match(line)) or line.strip() == "| Date | File | Entries |"

    table_start = next(i for i, line in enumerate(lines) if _is_table_line(line))
    table_end = table_start
    while table_end < len(lines) and (
        lines[table_end].strip().startswith("|") or SHARD_DIR_ROW_RE.match(lines[table_end])
    ):
        table_end += 1

    header_line = "| Date | File | Entries |\n"
    sep_line = "|---|---|---:|\n"
    new_rows = [
        f"| {date} | `logs/{date}.md` | {count} |\n" for date, count in sorted(real_counts.items())
    ]
    return (
        "".join(lines[:table_start])
        + header_line
        + sep_line
        + "".join(new_rows)
        + "".join(lines[table_end:])
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--tags", nargs="+", required=True)
    parser.add_argument("--decisions", nargs="*", default=[])
    parser.add_argument("--requirements", nargs="*", default=[])
    parser.add_argument("--wave-phase", nargs="*", default=[], dest="wave_phase")
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True, help="Short index-table summary")
    body_group = parser.add_mutually_exclusive_group(required=True)
    body_group.add_argument("--body")
    body_group.add_argument("--body-file")
    args = parser.parse_args()

    body = args.body if args.body else Path(args.body_file).read_text(encoding="utf-8")

    shard_text = ensure_shard(args.date)
    row = build_index_row(
        args.date, args.tags, args.decisions, args.requirements, args.wave_phase, args.summary
    )
    block = build_entry_block(args.tags, args.date, args.title, body)
    shard_text = insert_index_row(shard_text, row)
    shard_text = append_entry_block(shard_text, block)

    entries = count_entries(shard_text)
    index_rows = count_index_rows(shard_text)
    if entries != index_rows:
        raise SystemExit(
            f"Self-verification failed: {entries} entries but {index_rows} index rows in "
            f"logs/{args.date}.md -- not writing anything."
        )

    shard_path(args.date).write_text(shard_text, encoding="utf-8")

    index_text = INDEX_FILE.read_text(encoding="utf-8")
    INDEX_FILE.write_text(refresh_shard_directory(index_text), encoding="utf-8")

    print(f"Appended entry to logs/{args.date}.md ({entries} entries); logs/README.md refreshed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
