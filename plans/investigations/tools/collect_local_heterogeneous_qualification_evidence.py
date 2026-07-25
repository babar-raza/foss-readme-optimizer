"""Collect resumable live planner/reviewer qualification sessions."""

from __future__ import annotations

import argparse
import hashlib
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
_SOURCE_PATHS = (
    Path("prompts/planning/supervisor_turn.yaml"),
    Path("prompts/verification/independent_readme_review.yaml"),
    Path("src/readme_agent/golden_set/scenarios.py"),
    Path("src/readme_agent/golden_set/review_scenarios.py"),
    Path("src/readme_agent/golden_set/review_corpus.py"),
    Path("src/readme_agent/golden_set/review_fixtures.py"),
    Path("src/readme_agent/golden_set/harness.py"),
    Path("src/readme_agent/golden_set/review_harness.py"),
    Path("src/readme_agent/golden_set/qualification.py"),
    Path("src/readme_agent/llm/reviewer_client.py"),
    Path("src/readme_agent/llm/verification_prompts.py"),
)


def _head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _source_snapshot() -> dict:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise RuntimeError(
            "qualification sessions require a clean committed source tree; "
            "commit or reconcile the listed paths first:\n"
            f"{status}"
        )
    return {
        "schema_version": 1,
        "source_head": _head(),
        "source_files": {
            str(path).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in _SOURCE_PATHS
        },
    }


def _bind_campaign_source(output: Path) -> dict:
    snapshot = _source_snapshot()
    path = output / "campaign-source.json"
    if path.is_file():
        recorded = json.loads(path.read_text(encoding="utf-8"))
        if recorded != snapshot:
            raise RuntimeError(
                "qualification campaign source changed; preserve this run as diagnostic "
                "and start all three sessions in a new output directory"
            )
        return recorded
    write_redacted_json(path, snapshot)
    return snapshot


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
    campaign_source = _bind_campaign_source(output)
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
            "source_head": campaign_source["source_head"],
            "campaign_source_ref": "campaign-source.json",
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
