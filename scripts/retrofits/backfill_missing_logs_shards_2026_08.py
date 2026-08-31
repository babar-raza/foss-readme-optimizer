"""One-shot retrofit: writes the hand-authored logs/ entries backfilling the 10 real days
(2026-08-01, 08-03, 08-04, 08-06, 08-08, 08-21, 08-22, 08-23, 08-25, 08-31) that landed
governed-file commits with no logs/<date>.md shard, discovered by a full-history audit and closed
mechanically by scripts/governance/{audit,heal}_log_coverage.py going forward (see the decision
recording that redesign in plans/decisions/catalog.jsonl and logs/2026-08-31.md). These 10 days
predate that mechanism, so they're backfilled here with real narrative -- root cause, fix, tests,
commit hashes -- at the same depth as logs/2026-08-11.md's precedent, not with an auto-skeleton.

Entries were researched by reading each day's full commit diffs (git show <sha>) plus whatever
plans/decisions/catalog.jsonl or plans/requirements/catalog.jsonl rows those commits added, then
supplied here as a JSON file matching scripts/governance/append_log_entry.py's field shape:
[{"date", "tags", "decisions", "requirements", "wave_phase", "title", "summary", "body"}, ...].

Run once per day's batch (logs/README.md's shared shard-directory table means each day gets its
own commit, so this is invoked once per day rather than once for the whole backfill):

    python scripts/retrofits/backfill_missing_logs_shards_2026_08.py --entries-json <path>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from governance.log_shard_writer import write_entry  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries-json", required=True, type=Path)
    args = parser.parse_args()

    entries = json.loads(args.entries_json.read_text(encoding="utf-8"))
    for entry in entries:
        count = write_entry(**entry)
        print(f"wrote logs/{entry['date']}.md ({count} entries so far)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
