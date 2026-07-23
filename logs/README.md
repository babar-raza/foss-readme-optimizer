# Project Log — index

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
| 2026-07-17 | `logs/2026-07-17.md` | 5 |
| 2026-07-18 | `logs/2026-07-18.md` | 26 |
| 2026-07-19 | `logs/2026-07-19.md` | 43 |
| 2026-07-20 | `logs/2026-07-20.md` | 22 |
| 2026-07-21 | `logs/2026-07-21.md` | 11 |
| 2026-07-22 | `logs/2026-07-22.md` | 13 |
| 2026-07-23 | `logs/2026-07-23.md` | 22 |

**How to find an entry**: know the date → open that file directly, the filename *is* the date.
Know a decision number, requirement ID, or wave/phase → grep for it across `logs/*.md`, or check
the relevant day's own local index table first — it's built from exactly those identifiers.
