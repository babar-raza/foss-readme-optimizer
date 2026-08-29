"""T1 instrumentation (plan: concurrent-agent consistency, 2026-08-29): near-zero-risk,
additive-only logging of `document_template_hash()`'s value alongside real work, to turn
"plausible dominant cost driver" (Decision #111/CORE-039's premise -- one global hash over
~50 files plus four broad globs invalidates every one of 34 repositories' cached composition
plans on any change anywhere in that surface) into either a confirmed number or evidence that
something else actually dominates, before committing multi-day engineering to CORE-039.

Purely observational: computes the same public `document_template_hash()` externally, once
per invocation, and appends to a local JSONL log under `runs/observability/` -- the same
gitignored, disposable tier every other `runs/` artifact already lives in. No new storage
tier, no change to any production code path; this is never imported by the pipeline itself.

Wire one invocation into the portfolio-pass wrapper (`run_gate_a_local_poc_portfolio_loop.sh`)
to build a real history over time; it is also safe to run by hand at any point.

Run: `.venv/Scripts/python scripts/governance/log_document_template_hash_observation.py`
Report: `.venv/Scripts/python scripts/governance/log_document_template_hash_observation.py --report`
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORY_PATH = REPO_ROOT / "runs" / "observability" / "document-template-hash-history.jsonl"


def _contributing_files() -> list[str]:
    """The same file set `document_template_hash()` reads, resolved the same way (including
    its glob patterns), reproduced here via its own public constants rather than duplicated
    literals -- so this can never silently drift from what the real function actually hashes."""

    from readme_agent.readme.document_templates import (
        DOCUMENT_CONTRACT_CATALOG_PATHS,
        DOCUMENT_CONTRACT_IMPLEMENTATION_GLOBS,
        DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS,
        DOCUMENT_TEMPLATE_NAMES,
        TEMPLATE_ROOT,
    )

    files: set[str] = set()
    for name in DOCUMENT_TEMPLATE_NAMES:
        files.add((TEMPLATE_ROOT / name).relative_to(REPO_ROOT).as_posix())
    files.update(DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS)
    files.update(DOCUMENT_CONTRACT_CATALOG_PATHS)
    for pattern in DOCUMENT_CONTRACT_IMPLEMENTATION_GLOBS:
        files.update(
            path.relative_to(REPO_ROOT).as_posix()
            for path in REPO_ROOT.glob(pattern)
            if path.is_file()
        )
    return sorted(files)


def _git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _changed_contributing_files(previous_head: str, current_head: str) -> list[str]:
    if previous_head == "unknown":
        return []
    # Same commit but different hash means the flip came from uncommitted working-tree
    # changes -- diff against the working tree instead of two (identical) revisions.
    args = (
        ["git", "diff", "--name-only", "HEAD"]
        if previous_head == current_head
        else ["git", "diff", "--name-only", previous_head, current_head]
    )
    result = subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return []
    changed = set(result.stdout.splitlines())
    return sorted(changed & set(_contributing_files()))


def _last_observation() -> dict | None:
    if not HISTORY_PATH.is_file():
        return None
    lines = [line for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines() if line]
    if not lines:
        return None
    return json.loads(lines[-1])


def _read_history() -> list[dict]:
    if not HISTORY_PATH.is_file():
        return []
    return [
        json.loads(line) for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines() if line
    ]


def observe() -> dict:
    from readme_agent.readme.document_templates import document_template_hash

    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    previous = _last_observation()
    current_hash = document_template_hash()
    current_head = _git_head()
    flipped = previous is not None and previous["template_hash"] != current_hash
    entry: dict = {
        "observed_at": datetime.now(UTC).isoformat(),
        "template_hash": current_hash,
        "git_head": current_head,
        "flipped": flipped,
    }
    if flipped:
        entry["changed_contributing_files"] = _changed_contributing_files(
            previous["git_head"], current_head
        )
    with HISTORY_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def report() -> None:
    history = _read_history()
    if not history:
        print("no observations recorded yet")
        return
    distinct_hashes = len({entry["template_hash"] for entry in history})
    flips = [entry for entry in history if entry.get("flipped")]
    print(f"observations: {len(history)}")
    print(f"distinct template_hash values: {distinct_hashes}")
    print(f"flips: {len(flips)}")
    for entry in flips:
        changed = entry.get("changed_contributing_files", [])
        head = entry["git_head"][:9] if entry["git_head"] != "unknown" else "unknown"
        print(f"  {entry['observed_at']} head={head} changed={changed}")


def main() -> int:
    if "--report" in sys.argv:
        report()
        return 0
    entry = observe()
    if entry["flipped"]:
        head = entry["git_head"][:9] if entry["git_head"] != "unknown" else "unknown"
        print(f"document_template_hash flipped at {entry['observed_at']} (head {head})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
