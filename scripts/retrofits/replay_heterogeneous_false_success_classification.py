"""Replay historical specialist failures through the current terminal classifier."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from readme_agent.state.schema import DomainStateV1
from readme_agent.supervisor.convergence import final_status
from readme_agent.supervisor.task import TaskGraph

TARGET_REPOSITORIES = (
    "aspose-cells-foss/Aspose.Cells-FOSS-for-.NET",
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Python",
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp",
    "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go",
)


def _historical_status(log_text: str, repository: str) -> str:
    """Extract the recorded specialist failure from one repository's run section."""

    start_markers = (
        f"=== FIRST RUN: {repository} ===",
        f"{repository}: CONVERGED_NO_CHANGE",
    )
    starts = [log_text.find(marker) for marker in start_markers]
    starts = [position for position in starts if position >= 0]
    if not starts:
        raise ValueError(f"missing historical run section for {repository}")
    start = min(starts)
    next_section = log_text.find("=== FIRST RUN:", start + 1)
    section = log_text[start : next_section if next_section >= 0 else None]
    match = re.search(r'still failing \("(ERROR:.*?)"\)', section)
    if match is None:
        raise ValueError(f"missing specialist failure for {repository}")
    return match.group(1)


def replay(source_log: Path) -> dict[str, object]:
    """Return an evidence record proving all historical failures now block."""

    raw = source_log.read_bytes()
    text = raw.decode("utf-8")
    cases: list[dict[str, str]] = []
    for repository in TARGET_REPOSITORIES:
        historical_status = _historical_status(text, repository)
        outcome = final_status(
            TaskGraph(),
            applied_any_effect=False,
            specialist_results={
                "readme_presentation": DomainStateV1(
                    domain="readme_presentation",
                    accepted_status=historical_status,
                )
            },
        )
        if outcome.status != "BLOCKED":
            raise RuntimeError(
                f"false-success regression for {repository}: current status={outcome.status}"
            )
        expected_reason = f"specialist_failed:readme_presentation:{historical_status}"
        if outcome.blocked_reason != expected_reason:
            raise RuntimeError(f"wrong blocked reason for {repository}: {outcome.blocked_reason!r}")
        cases.append(
            {
                "repository": repository,
                "historical_terminal_status": "CONVERGED_NO_CHANGE",
                "historical_specialist_status": historical_status,
                "current_terminal_status": outcome.status,
                "current_blocked_reason": outcome.blocked_reason,
            }
        )
    return {
        "schema": "heterogeneous-false-success-classification-replay-v1",
        "source_log": source_log.as_posix(),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "classifier": "readme_agent.supervisor.convergence.final_status",
        "case_count": len(cases),
        "all_fail_closed": True,
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_log", type=Path)
    args = parser.parse_args()
    print(json.dumps(replay(args.source_log), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
