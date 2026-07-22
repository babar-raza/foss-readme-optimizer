"""One-shot retrofit: relocate master.md's and requirements.md's Changelog entries into logs/.

Kept per GOVERNANCE.md placement rule 5 as the executable record of this transformation, not
deleted after running. See Decision #44 / GOV-023 in plans/master.md and plans/requirements.md.

Splits each Changelog section into its top-level dated entries, tags each with its source
document, merges both into one chronological stream (stable sort by date only, so same-date ties
keep master's entry immediately before requirements' companion entry), and writes:

  - logs/README.md       -- small, stable index (format spec, tag vocabulary, shard directory)
  - logs/2026-07.md       -- the one shard needed today, with its own local index table plus the
                              full, verbatim (only source-tagged) entries

Every check below must pass before anything is written; on any mismatch the script raises instead
of writing partial output.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MASTER_PATH = REPO_ROOT / "plans" / "master.md"
REQUIREMENTS_PATH = REPO_ROOT / "plans" / "requirements.md"
LOGS_DIR = REPO_ROOT / "logs"

MASTER_HEADING = "## Changelog"
REQUIREMENTS_HEADING = "## 23. Changelog"

ENTRY_START_RE = re.compile(r"^- \*\*(\d{4}-\d{2}-\d{2})")
BOLD_PREFIX_RE = re.compile(r"^\*\*\d{4}-\d{2}-\d{2}[^*]*\*\*\s*")
DECISION_RE = re.compile(r"[Dd]ecisions?\s*#?\s*(\d+)(?:\s*[-–/]\s*#?(\d+))?")
REQ_ID_RE = re.compile(r"\b([A-Z]{2,5}-\d{3})\b")
WAVE_RE = re.compile(r"\bWave\s+(\d+[a-zA-Z]?)\b")
PHASE_RE = re.compile(r"\bPhase\s+(\d+[a-zA-Z]?)\b")
INCIDENT_RE = re.compile(r"GH_TOKEN.{0,400}expos|expos.{0,400}GH_TOKEN", re.IGNORECASE | re.DOTALL)

POINTER_TEMPLATE = (
    "\n\nFull history relocated to `logs/` (2026-07-21, index at `logs/README.md`). New entries"
    " are appended there, not here — see GOVERNANCE.md rule 6 and rule 12.\n"
)


def split_changelog(text: str, heading: str) -> tuple[str, str]:
    idx = text.index(heading)
    head = text[: idx + len(heading)]
    body = text[idx + len(heading) :]
    return head, body


def split_entries(body: str) -> list[str]:
    entries: list[str] = []
    current: list[str] = []
    for line in body.splitlines(keepends=True):
        if ENTRY_START_RE.match(line):
            if current:
                entries.append("".join(current))
            current = [line]
        elif current:
            current.append(line)
    if current:
        entries.append("".join(current))
    return entries


def entry_date(entry: str) -> str:
    match = ENTRY_START_RE.match(entry)
    assert match, f"entry missing leading date: {entry[:60]!r}"
    return match.group(1)


def tag_entry(entry: str, source: str) -> str:
    tags = f"[{source}]"
    if INCIDENT_RE.search(entry):
        tags += " [incident]"
    tagged, count = re.subn(r"^- ", f"- {tags} ", entry, count=1)
    assert count == 1, f"failed to tag entry: {entry[:60]!r}"
    return tagged


def extract_refs(entry: str) -> tuple[list[int], list[str], list[str]]:
    decisions: set[int] = set()
    for match in DECISION_RE.finditer(entry):
        start = int(match.group(1))
        if match.group(2):
            decisions.update(range(start, int(match.group(2)) + 1))
        else:
            decisions.add(start)
    reqs = sorted(set(REQ_ID_RE.findall(entry)))
    wave_phase = sorted(
        {f"Wave {w}" for w in WAVE_RE.findall(entry)}
        | {f"Phase {p}" for p in PHASE_RE.findall(entry)}
    )
    return sorted(decisions), reqs, wave_phase


def summary_of(entry: str) -> str:
    text = re.sub(r"^- ", "", entry, count=1)
    text = BOLD_PREFIX_RE.sub("", text, count=1)
    text = " ".join(text.split())
    text = re.sub(r"^—\s*", "", text)
    if len(text) > 140:
        text = text[:137].rstrip() + "..."
    return text.replace("|", "\\|")


def build_row(entry: str, source: str) -> str:
    date = entry_date(entry)
    decisions, reqs, wave_phase = extract_refs(entry)
    decisions_cell = ", ".join(f"#{d}" for d in decisions) or "—"
    reqs_cell = ", ".join(f"`{r}`" for r in reqs) or "—"
    wave_cell = ", ".join(wave_phase) or "—"
    tags_cell = source + (" incident" if INCIDENT_RE.search(entry) else "")
    return (
        f"| {date} | {tags_cell} | {decisions_cell} | {reqs_cell} | {wave_cell} | "
        f"{summary_of(entry)} |"
    )


def main() -> None:
    master_text = MASTER_PATH.read_text(encoding="utf-8")
    requirements_text = REQUIREMENTS_PATH.read_text(encoding="utf-8")

    master_head, master_body = split_changelog(master_text, MASTER_HEADING)
    req_head, req_body = split_changelog(requirements_text, REQUIREMENTS_HEADING)

    master_entries = split_entries(master_body)
    req_entries = split_entries(req_body)
    print(f"master.md entries found:       {len(master_entries)}")
    print(f"requirements.md entries found: {len(req_entries)}")
    assert len(master_entries) == 62, "expected 62 master.md changelog entries"
    assert len(req_entries) == 39, "expected 39 requirements.md changelog entries"

    tagged = [("master", e) for e in master_entries] + [("requirements", e) for e in req_entries]
    merged = sorted(tagged, key=lambda pair: entry_date(pair[1]))
    assert len(merged) == 101

    tagged_entries = [tag_entry(entry, source) for source, entry in merged]
    incident_count = sum(1 for e in tagged_entries if "[incident]" in e)
    print(f"entries tagged [incident]:     {incident_count}")

    # Self-verification: every original entry's own text (minus the tag we just inserted) must
    # still be present, unmodified, exactly once.
    for (source, original), tagged_text in zip(merged, tagged_entries, strict=True):
        without_tag = re.sub(r"^- \[[^\]]+\](?:\s\[[^\]]+\])?\s*", "- ", tagged_text, count=1)
        assert without_tag == original, f"content mismatch relocating a {source} entry"

    index_rows = [build_row(entry, source) for source, entry in merged]

    dates = [entry_date(e) for _, e in merged]
    first_date, last_date = min(dates), max(dates)
    print(f"date range: {first_date} .. {last_date}")

    LOGS_DIR.mkdir(exist_ok=True)

    shard_lines = [
        "# Project log — 2026-07",
        "",
        "Back to [index](README.md).",
        "",
        "## Index",
        "",
        "| Date | Tags | Decisions | Requirements | Wave/Phase | Summary |",
        "|---|---|---|---|---|---|",
        *index_rows,
        "",
        "## Entries",
        "",
        *tagged_entries,
    ]
    shard_text = "\n".join(shard_lines).rstrip() + "\n"
    (LOGS_DIR / "2026-07.md").write_text(shard_text, encoding="utf-8")

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
1. Append the entry to the current month's shard (`logs/<YYYY-MM>.md`; create it, copying the
   shard header, if this is the month's first entry).
2. Add one row to that shard's own local index table — pull the decision numbers / requirement
   IDs / wave-or-phase numbers straight out of the entry you just wrote; you already know them,
   this isn't a research step.
3. If a shard passes ~800 lines, split it at next touch into `<YYYY-MM>-a.md` / `<YYYY-MM>-b.md`
   by date, and update the shard directory table below — same "split before you extend" smell
   test `GOVERNANCE.md` already applies to code (~300 lines/module).

**Shard directory**

| Period | File | Entries | Date range |
|---|---|---:|---|
| 2026-07 | `logs/2026-07.md` | {len(merged)} | {first_date} – {last_date} |

**How to find an entry**: know the date → open that month's shard and search it. Know a decision
number, requirement ID, or wave/phase → grep for it across `logs/*.md`, or check the relevant
shard's own local index table first — it's built from exactly those identifiers.
"""
    (LOGS_DIR / "README.md").write_text(readme_text, encoding="utf-8")

    MASTER_PATH.write_text(master_head + POINTER_TEMPLATE, encoding="utf-8")
    REQUIREMENTS_PATH.write_text(req_head + POINTER_TEMPLATE, encoding="utf-8")

    print("Wrote logs/README.md and logs/2026-07.md")
    print("Replaced Changelog bodies in plans/master.md and plans/requirements.md")


if __name__ == "__main__":
    main()
