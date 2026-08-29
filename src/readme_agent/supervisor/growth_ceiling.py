"""Additive-only visibility into governance growth vs. delivery progress.

This project's own history already shows the pattern: 523 requirements, 113
decisions, and a 2,329-line mission graph accumulated over 43 days while
`no_op_proven` stayed at 0-1/34 the whole time -- discovered only by a
retrospective audit, not visible anywhere in routine status output. This
module makes it visible going forward, next to the other `mission-action
status` counters, instead of requiring another audit to notice a stall.

Never blocks anything and never raises past its own callers: a computation
failure here must not break `mission-action status`. Reuses git history
already on disk for requirements/decisions growth (no new storage), and the
same gitignored `runs/observability/` tier GOV-034 established for a small
rolling `no_op_proven` snapshot history -- needed because "delta over the
last N days" has no other durable record to compare against.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
NO_OP_PROVEN_HISTORY_PATH = REPO_ROOT / "runs" / "observability" / "no-op-proven-history.jsonl"
REQUIREMENTS_CATALOG_PATH = "plans/requirements/catalog.jsonl"
DECISIONS_CATALOG_PATH = "plans/decisions/catalog.jsonl"
DEFAULT_WINDOW_DAYS = 7


@dataclass(frozen=True)
class GrowthCeilingV1:
    window_days: int
    requirements_added: int | None
    decisions_added: int | None
    no_op_proven_delta: int | None


def _run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    # Explicit UTF-8, not the platform default (Windows' console codepage
    # cannot decode arbitrary repository content, e.g. an em-dash in a
    # requirement's text -- this crashed on first real use without it).
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _commit_n_days_ago(days: int) -> str | None:
    result = _run_git(["rev-list", "-1", f"--before={days} days ago", "HEAD"])
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None


def _file_line_count_at(revision: str, path: str) -> int:
    result = _run_git(["show", f"{revision}:{path}"])
    if result.returncode != 0:
        return 0
    return len([line for line in result.stdout.splitlines() if line.strip()])


def _catalog_growth(path: str, days: int) -> int | None:
    baseline_rev = _commit_n_days_ago(days)
    if baseline_rev is None:
        return None
    before = _file_line_count_at(baseline_rev, path)
    after = _file_line_count_at("HEAD", path)
    return after - before


def record_no_op_proven_observation(no_op_proven: int) -> None:
    """Append-only, mirrors `log_document_template_hash_observation.py`'s
    own pattern (GOV-034): one JSON line per invocation, never imported by
    a code path whose correctness depends on it."""

    NO_OP_PROVEN_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {"observed_at": datetime.now(UTC).isoformat(), "no_op_proven": no_op_proven}
    with NO_OP_PROVEN_HISTORY_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _no_op_proven_delta(current: int, days: int) -> int | None:
    if not NO_OP_PROVEN_HISTORY_PATH.is_file():
        return None
    cutoff = datetime.now(UTC).timestamp() - days * 86400
    oldest_in_window: int | None = None
    for line in NO_OP_PROVEN_HISTORY_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            observed_at = datetime.fromisoformat(entry["observed_at"]).timestamp()
        except (ValueError, KeyError):
            continue
        if observed_at <= cutoff:
            oldest_in_window = entry["no_op_proven"]
    if oldest_in_window is None:
        return None
    return current - oldest_in_window


def compute_growth_ceiling(
    *, no_op_proven: int, window_days: int = DEFAULT_WINDOW_DAYS
) -> GrowthCeilingV1:
    """Best-effort on every field independently -- one failing computation
    (e.g. git unavailable, or fewer than `window_days` of history so far)
    must not hide the others."""

    try:
        requirements_added = _catalog_growth(REQUIREMENTS_CATALOG_PATH, window_days)
    except Exception:  # noqa: BLE001 - one failing field must not hide the others
        requirements_added = None
    try:
        decisions_added = _catalog_growth(DECISIONS_CATALOG_PATH, window_days)
    except Exception:  # noqa: BLE001 - one failing field must not hide the others
        decisions_added = None
    try:
        no_op_proven_delta = _no_op_proven_delta(no_op_proven, window_days)
    except Exception:  # noqa: BLE001 - one failing field must not hide the others
        no_op_proven_delta = None
    return GrowthCeilingV1(
        window_days=window_days,
        requirements_added=requirements_added,
        decisions_added=decisions_added,
        no_op_proven_delta=no_op_proven_delta,
    )


def format_growth_ceiling(ceiling: GrowthCeilingV1) -> str:
    def _fmt(value: int | None) -> str:
        return "unknown" if value is None else str(value)

    return (
        f"growth_ceiling_{ceiling.window_days}d: "
        f"requirements_added={_fmt(ceiling.requirements_added)}, "
        f"decisions_added={_fmt(ceiling.decisions_added)}, "
        f"no_op_proven_delta={_fmt(ceiling.no_op_proven_delta)}"
    )
