"""Reconstruct the durable mission-resume capsule from authoritative state.

Phase-12 machinery of the 2026-08-18 mission recovery: the capsule is the one
short document a cold-started (or compaction-recovered) agent reads FIRST. It
is DERIVED -- every line is reconstructed from durable state, never trusted
from memory -- and `--check` fails when the stored capsule is stale relative
to the durable sources it summarizes, so a session cannot silently resume
from an outdated picture.

Usage:
    .venv/Scripts/python scripts/governance/mission_resume_capsule.py            # rewrite capsule
    .venv/Scripts/python scripts/governance/mission_resume_capsule.py --check    # exit 1 if stale

Sources (all read-only):
- local durable mission/lifecycle state: `runs/local-poc-state/state.git` refs
- the live portfolio summary: `runs/readme-poc/portfolio-summary.json`
- blocked-decision and claim-disposition-ratchet records under `runs/readme-poc/`
- git HEAD of this repository
- the configured model identity (`src/readme_agent/env.py`)

Output: `plans/investigations/control/mission-resume-capsule.md`
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CAPSULE_PATH = REPO_ROOT / "plans" / "investigations" / "control" / "mission-resume-capsule.md"
STATE_GIT = REPO_ROOT / "runs" / "local-poc-state" / "state.git"
SUMMARY_PATH = REPO_ROOT / "runs" / "readme-poc" / "portfolio-summary.json"


def _git(*args: str, cwd: Path = REPO_ROOT) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    return result.stdout.strip()


def _state_refs() -> list[tuple[str, str, str]]:
    """(ref, head timestamp, subject) per durable state ref, newest first."""

    if not STATE_GIT.is_dir():
        return []
    raw = _git(
        "--git-dir",
        str(STATE_GIT),
        "for-each-ref",
        "--sort=-authordate",
        "--format=%(refname)%09%(authordate:iso-strict)%09%(subject)",
    )
    rows: list[tuple[str, str, str]] = []
    for line in raw.splitlines():
        parts = line.split("\t", maxsplit=2)
        if len(parts) == 3:
            rows.append((parts[0], parts[1], parts[2]))
    return rows


def _newest_state_timestamp(rows: list[tuple[str, str, str]]) -> str | None:
    return rows[0][1] if rows else None


def _mission_line(rows: list[tuple[str, str, str]]) -> str:
    for ref, stamp, subject in rows:
        if "mission__" in ref:
            return f"`{ref.rsplit('/', 1)[-1]}` — {subject} ({stamp})"
    return "(no durable mission ref in the local state store)"


def _portfolio_block() -> tuple[str, str | None]:
    try:
        summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "(no portfolio summary present)", None
    results = summary.get("results", [])
    counted: dict[str, int] = {}
    for row in results:
        counted[row.get("status", "?")] = counted.get(row.get("status", "?"), 0) + 1
    lines = [
        f"- generated_at: {summary.get('generated_at')}  "
        f"(registry_count={summary.get('registry_count')}, "
        f"slice_complete={summary.get('execution_slice_complete')})",
        "- statuses in last slice: "
        + ", ".join(f"{status}={count}" for status, count in sorted(counted.items())),
    ]
    blocked = [
        f"  - {row['org_repo']}: {str(row.get('blocked_reason'))[:110]}"
        for row in results
        if row.get("blocked_reason")
    ]
    if blocked:
        lines.append("- blocked members (last slice):")
        lines.extend(blocked)
    return "\n".join(lines), summary.get("generated_at")


def _decision_records() -> str:
    root = REPO_ROOT / "runs" / "readme-poc"
    if not root.is_dir():
        return "(none)"
    lines = []
    for path in sorted(root.glob("*/blocked-decision.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        lines.append(
            f"  - {record.get('org_repo')}: {str(record.get('blocked_reason'))[:90]} "
            f"(live_reproductions={record.get('consecutive_count')})"
        )
    ratchets = []
    for path in sorted(root.glob("*/claim-disposition-ratchet.json")):
        try:
            accepted = json.loads(path.read_text(encoding="utf-8")).get("accepted", {})
        except (OSError, json.JSONDecodeError):
            continue
        ratchets.append(f"  - {path.parent.name}: {len(accepted)} accepted verdict(s)")
    out = []
    if lines:
        out.append("- blocked-decision records (skip-cached until a dependency changes):")
        out.extend(lines)
    if ratchets:
        out.append("- claim-disposition ratchets:")
        out.extend(ratchets)
    return "\n".join(out) or "(none)"


def build_capsule() -> str:
    rows = _state_refs()
    portfolio, generated_at = _portfolio_block()
    head = _git("rev-parse", "HEAD")
    branch = _git("branch", "--show-current")
    newest_state = _newest_state_timestamp(rows)
    return f"""# Mission resume capsule (derived — regenerate, never hand-edit)

Regenerated: {datetime.now(UTC).isoformat(timespec="seconds")}
Rebuild: `.venv/Scripts/python scripts/governance/mission_resume_capsule.py`
Staleness check (run at session start; exit 1 = stale): same command with `--check`.

## Mission

Deliver the complete local README candidate portfolio at Aspose.org quality parity
(`L8-PORT-01-LOCAL-README-PORTFOLIO-ASPOSE-PARITY`, lane readme-portfolio-delivery), using
`qwen3-next` via `https://llm.professionalize.com/v1` (exact provider id, live-confirmed; no
`qwen2-next` exists). Local only: no push, no PR, no target-repository writes. Aspose.org at
`D:/onedrive/Documents/GitHub/aspose.org` is a read-only behavioral reference (closure trace in
`plans/investigations/evidence/mission-recovery-2026-08-18/`).

## Non-goals

Remote writes of any kind; another blind portfolio loop over unchanged inputs; lowering
factuality/preservation/grounding gates to raise pass counts.

## Authoritative sources (read these, in order, before acting)

1. `plans/investigations/evidence/mission-recovery-2026-08-18/live-state-reconstruction.md`
2. `plans/investigations/evidence/mission-recovery-2026-08-18/failure-signature-ledger.md`
   (the engineering queue E1..E9 and signature clusters S1..S10)
3. `logs/2026-08-18.md` (tail) — what already landed, with commits
4. Durable state: `git --git-dir runs/local-poc-state/state.git for-each-ref`
5. `plans/master.md` Decision Ledger + `plans/GOVERNANCE.md` (process invariants)

## Repository

- branch `{branch}` @ `{head}`
- protected pre-existing dirt: `plans/requirements.md` (CRLF-only); untracked
  `plans/claude/moonlit-juggling-flurry.md` is `forbidden_paths` reference material.

## Durable mission state (local store)

- {_mission_line(rows)}
- newest state ref write: {newest_state}

## Portfolio (from `runs/readme-poc/portfolio-summary.json`)

{portfolio}

## Cached decisions

{_decision_records()}

## Resume commands

- Mission status (read-only): `./.venv/Scripts/python -m readme_agent.cli supervise
  --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml
  --mission-action status --execution-profile local_poc`
- Single-repo canary: `./.venv/Scripts/python -m readme_agent.cli supervise --repo <org/repo>
  --execution-profile local_poc --bounded-verified-canary
  --mission-task-id L8-PORT-01-LOCAL-README-PORTFOLIO-ASPOSE-PARITY
  --mission-observer readme-agent-supervisor`
- Portfolio pass: `bash scripts/retrofits/run_gate_a_local_poc_portfolio_loop.sh` (blocked
  members now skip via their dependency-bound blocked-decision records; `--retry-blocked`
  forces live re-runs).

## Publication boundary

Nothing leaves this machine. Candidates live under `runs/readme-poc/`; human review happens
locally. `GH_TOKEN` recipe and remote-write gates unchanged.
"""


def _staleness(capsule_text: str) -> list[str]:
    reasons = []
    rows = _state_refs()
    newest_state = _newest_state_timestamp(rows)
    if newest_state and newest_state not in capsule_text:
        reasons.append(f"newest durable state ref write {newest_state} is not in the capsule")
    head = _git("rev-parse", "HEAD")
    if head and head not in capsule_text:
        reasons.append(f"repository HEAD {head[:12]} is not in the capsule")
    _, generated_at = _portfolio_block()
    if generated_at and str(generated_at) not in capsule_text:
        reasons.append(f"portfolio summary generated_at {generated_at} is not in the capsule")
    return reasons


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 (listing reasons) when the stored capsule is stale vs durable state",
    )
    args = parser.parse_args()
    if args.check:
        try:
            stored = CAPSULE_PATH.read_text(encoding="utf-8")
        except OSError:
            print("capsule missing: regenerate with scripts/governance/mission_resume_capsule.py")
            return 1
        reasons = _staleness(stored)
        if reasons:
            print("capsule STALE:")
            for reason in reasons:
                print(f"  - {reason}")
            return 1
        print("capsule current")
        return 0
    CAPSULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CAPSULE_PATH.write_text(build_capsule(), encoding="utf-8", newline="\n")
    print(f"capsule rewritten: {CAPSULE_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
