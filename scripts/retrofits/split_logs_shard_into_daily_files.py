"""One-shot retrofit: split logs/2026-07.md (one monthly shard) into one shard per day.

Kept per GOVERNANCE.md placement rule 5 as the executable record of this transformation. See the
logs/2026-07-21.md entry this script itself appends to for the full rationale: the blind-agent
compliance test (proving decision #44) found the monthly shard already 3x over its own ~800-line
split guidance, and the user asked for day-granularity shards instead.

Splits both the "## Index" table and the "## Entries" list by each row/entry's own leading date,
writes one logs/<YYYY-MM-DD>.md per day found, deletes the now-superseded monthly file, and
rewrites logs/README.md's shard directory/maintenance text for day granularity. Self-verifies
entry and index-row counts are preserved before writing anything.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = REPO_ROOT / "logs"
MONTH_SHARD = LOGS_DIR / "2026-07.md"

ENTRY_START_RE = re.compile(r"^- \[[^\]]+\](?:\s\[[^\]]+\])*\s\*\*(\d{4}-\d{2}-\d{2})")
INDEX_ROW_RE = re.compile(r"^\| (\d{4}-\d{2}-\d{2}) \|")

INDEX_HEADER = [
    "| Date | Tags | Decisions | Requirements | Wave/Phase | Summary |",
    "|---|---|---|---|---|---|",
]


def split_by_leading_date(body: str, start_re: re.Pattern) -> dict[str, list[str]]:
    by_date: dict[str, list[str]] = {}
    current_date: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        if current_date is not None:
            by_date.setdefault(current_date, []).append("".join(current_lines))

    for line in body.splitlines(keepends=True):
        match = start_re.match(line)
        if match:
            flush()
            current_date = match.group(1)
            current_lines = [line]
        elif current_date is not None:
            current_lines.append(line)
    flush()
    return by_date


def main() -> None:
    text = MONTH_SHARD.read_text(encoding="utf-8")

    index_start = text.index("## Index")
    entries_start = text.index("## Entries")
    index_body = text[index_start:entries_start]
    entries_body = text[entries_start:]

    entries_by_date = split_by_leading_date(entries_body, ENTRY_START_RE)
    index_by_date = split_by_leading_date(index_body, INDEX_ROW_RE)

    total_entries = sum(len(v) for v in entries_by_date.values())
    total_index_rows = sum(len(v) for v in index_by_date.values())
    print(f"entries found: {total_entries} across {len(entries_by_date)} days")
    print(f"index rows found: {total_index_rows} across {len(index_by_date)} days")
    assert entries_by_date.keys() == index_by_date.keys(), "date sets must match exactly"
    assert total_entries == total_index_rows, "entry count must match index row count"

    dates = sorted(entries_by_date.keys())
    for date in dates:
        lines = [
            f"# Project log — {date}",
            "",
            "Back to [index](README.md).",
            "",
            "## Index",
            "",
            *INDEX_HEADER,
            *index_by_date[date],
            "",
            "## Entries",
            "",
            *entries_by_date[date],
        ]
        shard_text = "\n".join(lines).rstrip() + "\n"
        (LOGS_DIR / f"{date}.md").write_text(shard_text, encoding="utf-8")
        print(f"wrote logs/{date}.md: {len(entries_by_date[date])} entries")

    MONTH_SHARD.unlink()
    print(f"deleted {MONTH_SHARD}")

    directory_rows = "\n".join(
        f"| {date} | `logs/{date}.md` | {len(entries_by_date[date])} |" for date in dates
    )
    readme_text = f"""# Project Log — index

Dated historical record for `plans/master.md`, `plans/requirements.md`, and `plans/GOVERNANCE.md`.
None of those three narrates history (`GOVERNANCE.md` rule 1/6) — every "what changed and why"
question is answered here instead. Investigation findings/evidence still live in
`plans/investigations/` (unchanged) — this log is for dated narrative about the plan trio, not a
second home for research write-ups.

**What belongs here:** master-plan decisions and status changes, requirement additions/status
moves, GOVERNANCE.md rule changes, wave/phase completions, bugs found and fixed, backlog findings
logged, safety/credential incidents — anything this project would previously have written as a
Changelog line in `master.md` or `requirements.md`.

**Format**, one entry per change, first line only:
`- [tag] **YYYY-MM-DD** — <what changed> — <one-clause why>`
Multi-paragraph entries are fine for genuinely substantial changes (this log's own migrated
history is the precedent) — one-line is the default, not a hard cap.

**Tags** (first-line prefix, space-separated, source tag required, `incident` optional):
- `master` / `requirements` / `governance` — which document the change belongs to.
- `incident` — combine with a source tag for safety/credential/security incidents, so they stay
  independently greppable (`grep incident logs/*.md`) instead of buried in prose.

**Maintenance — two touches per new entry, same discipline as Decision Ledger + Changelog always
was:**
1. Append the entry to today's shard (`logs/<YYYY-MM-DD>.md`; create it, copying the shard header
   below, if this is the day's first entry).
2. Add one row to that shard's own local index table — pull the decision numbers / requirement
   IDs / wave-or-phase numbers straight out of the entry you just wrote; you already know them,
   this isn't a research step.
3. ~800 lines is the *typical-day* target this guidance is calibrated for, not a hard cap — an
   exceptionally dense single day (this project's own 2026-07-19, at 974 lines, is the precedent)
   is real content, not a sharding failure, and isn't force-split. Only split a single day further
   (`<YYYY-MM-DD>-a.md`/`-b.md`, chronological within the day) once it clears roughly double that
   (~1,500 lines) — same "split before you extend" smell test `GOVERNANCE.md` already applies to
   code (~300 lines/module), calibrated up for how dense one real day of this project can get.

**Shard directory**

| Date | File | Entries |
|---|---|---:|
{directory_rows}

**How to find an entry**: know the date → open that file directly, the filename *is* the date.
Know a decision number, requirement ID, or wave/phase → grep for it across `logs/*.md`, or check
the relevant day's own local index table first — it's built from exactly those identifiers.
"""
    (LOGS_DIR / "README.md").write_text(readme_text, encoding="utf-8")
    print("Rewrote logs/README.md for daily-shard granularity")


if __name__ == "__main__":
    main()
