"""Collect resumable live planner/reviewer qualification sessions."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from readme_agent import env
from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.golden_set.auto_disable import evaluate_qualification_and_disable
from readme_agent.golden_set.qualification import (
    DeterministicQualificationResult,
    run_qualification_session,
    summarize_qualification,
)
from readme_agent.llm.planner_client import LivePlannerClient
from readme_agent.llm.reviewer_client import LiveIndependentReviewClient
from readme_agent.state.git_backend import default_state_backend

_SESSION_IDS = {
    "initial-discrimination",
    "stability-repetition",
    "independent-reproduction",
}


def _head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _load_sessions(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"qualification sessions must be a JSON array: {path}")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--session-id", choices=sorted(_SESSION_IDS), required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    output: Path = args.output
    sessions_path = output / "agentic-qualification-sessions.json"
    sessions = _load_sessions(sessions_path)
    existing_ids = {str(record["session_id"]) for record in sessions}
    if args.session_id not in existing_ids:
        base_url, api_key = env.llm_base_url(), env.llm_api_key()
        planner = LivePlannerClient(
            base_url,
            api_key,
            env.llm_model_for_job("supervisor_planning"),
        )
        reviewer = LiveIndependentReviewClient(
            base_url,
            api_key,
            env.llm_model_for_job("independent_readme_review"),
            max_tokens=2400,
        )
        session = run_qualification_session(args.session_id, planner, reviewer)
        sessions.append(session.as_record())
        write_redacted_json(sessions_path, sessions)

    deterministic = DeterministicQualificationResult(
        total=7,
        passed=7,
        evidence_refs=[
            "plans/investigations/evidence/level8-local-readme-assessment-composition-81a2d48",
            "plans/investigations/evidence/level8-local-independent-review-repair-ee221c7",
        ],
    )
    summary = summarize_qualification(sessions, deterministic)
    summary.update(
        {
            "source_head": _head(),
            "planner_model": env.llm_model_for_job("supervisor_planning"),
            "reviewer_model": env.llm_model_for_job("independent_readme_review"),
        }
    )
    summary_path = output / "agentic-qualification-summary.json"
    write_redacted_json(summary_path, summary)

    disabled = evaluate_qualification_and_disable(
        summary,
        default_state_backend(),
        evidence_ref=str(summary_path),
    )
    write_redacted_json(
        output / "route-enforcement.json",
        {
            "evaluated": summary["volume_complete"],
            "qualified": summary["qualified"],
            "disabled_routes": [status.model_dump(mode="json") for status in disabled],
        },
    )
    refresh_sha256sums(output)
    print(
        f"{args.session_id}: sessions={summary['session_count']} "
        f"evaluations={summary['total_evaluations']} "
        f"pass_rate={summary['pass_rate']} qualified={summary['qualified']}"
    )
    for job, route in summary["routes"].items():
        print(f"  {job}: {route['passed']}/{route['total']} ({route['pass_rate']})")
    return 0 if not summary["volume_complete"] or summary["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
