"""Governance log-entry generator.

Appends one dated `logs/` entry (creating the shard with its canonical header on a day's first
entry) plus its own local index row, then refreshes `logs/README.md`'s shard directory table --
so no session hand-edits these three surfaces independently and lets them drift out of sync
(exactly the drift found live 2026-07-22: a hand-written shard missing its own header/index
structure, and an index table two days stale). See `GOVERNANCE.md` rule 6 and decision #46.

The shard-formatting logic itself lives in `log_shard_writer.py`, shared with
`heal_log_coverage.py`'s auto-generated skeleton entries -- this script is a thin CLI over it for
hand-authored entries.

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
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from governance.log_shard_writer import write_entry  # noqa: E402


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

    try:
        entries = write_entry(
            date=args.date,
            tags=args.tags,
            decisions=args.decisions,
            requirements=args.requirements,
            wave_phase=args.wave_phase,
            title=args.title,
            summary=args.summary,
            body=body,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Appended entry to logs/{args.date}.md ({entries} entries); logs/README.md refreshed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
