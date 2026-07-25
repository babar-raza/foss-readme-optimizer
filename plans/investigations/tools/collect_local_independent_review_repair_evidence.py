# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: analysis_or_evidence_only
"""Promote and verify one canonical local review/repair/no-op runtime proof."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json  # noqa: E402

EXPECTED_STAGES = [
    "SNAPSHOTTED",
    "PROFILED",
    "FACTS_COLLECTING",
    "FACTS_READY",
    "README_ASSESSED",
    "PLAN_READY",
    "CANDIDATE_GENERATED",
    "DETERMINISTIC_VALIDATED",
    "AGENT_REVIEWING",
    "AGENT_APPROVED",
    "NO_OP_PROVEN",
]


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _only_file(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if len(matches) != 1:
        raise ValueError(f"expected one {pattern!r} under {root}, found {len(matches)}")
    return matches[0]


def _validate_runtime(runs: Path) -> dict[str, object]:
    lifecycle_manifest_path = _only_file(runs, "readme-poc/*/*/manifest.json")
    lifecycle_root = lifecycle_manifest_path.parent
    manifest = _json(lifecycle_manifest_path)
    if manifest.get("lifecycle_status") != "NO_OP_PROVEN":
        raise ValueError("canonical lifecycle did not reach NO_OP_PROVEN")
    if manifest.get("complete") is not True:
        raise ValueError("canonical lifecycle is not complete")
    if manifest.get("completed_stages") != EXPECTED_STAGES:
        raise ValueError("canonical lifecycle stages are incomplete or out of order")

    review_root = lifecycle_root / "review"
    deterministic = _json(review_root / "deterministic-validation.json")
    independent = _json(review_root / "independent-agent-review.json")
    repair_history = _json(review_root / "repair-history.json")
    final_verdict = _json(review_root / "final-verdict.json")
    no_op = _json(review_root / "no-op-proof.json")
    if deterministic.get("verdict") != "accept":
        raise ValueError("final deterministic validation did not accept")
    if independent.get("verdict") != "ACCEPT":
        raise ValueError("final independent review did not accept")
    if final_verdict.get("verdict") != "AGENT_APPROVED":
        raise ValueError("final verdict is not AGENT_APPROVED")
    if len(repair_history) != 2:
        raise ValueError("expected the initial and repaired review records")
    if repair_history[0]["review"]["verdict"] != "REJECT_REPAIRABLE":
        raise ValueError("initial review was not repairable rejection")
    if repair_history[1]["review"]["verdict"] != "ACCEPT":
        raise ValueError("repaired candidate was not accepted")
    candidate_hashes = [item["candidate_sha256"] for item in repair_history]
    if len(set(candidate_hashes)) != 2:
        raise ValueError("repair did not produce a distinct candidate")
    if candidate_hashes[-1] != manifest.get("candidate_hash"):
        raise ValueError("accepted repaired candidate does not match lifecycle manifest")
    expected_no_op = {
        "verdict": "NO_OP_PROVEN",
        "candidate_hash": manifest["candidate_hash"],
        "patch_created": False,
        "duplicate_bundle_created": False,
        "agentic_review_reused": True,
    }
    if no_op != expected_no_op:
        raise ValueError("unchanged rerun did not satisfy the canonical no-op contract")

    proposal_dirs = sorted(
        path for path in (runs / "readme-proposal-bundles").glob("*/*") if path.is_dir()
    )
    if len(proposal_dirs) != 2:
        raise ValueError(f"expected exactly two proposal bundles, found {len(proposal_dirs)}")
    run_manifests = [
        (_json(path), path) for path in sorted((runs / "evidence").glob("*/manifest.json"))
    ]
    if len(run_manifests) != 2:
        raise ValueError(
            f"expected exactly two supervisor run manifests, found {len(run_manifests)}"
        )
    statuses = [item[0].get("status") for item in run_manifests]
    if statuses != ["CONVERGED_PROPOSAL_READY", "CONVERGED_NO_TRACKED_CHANGE"]:
        raise ValueError(f"unexpected supervisor run statuses: {statuses}")
    if any(item[0].get("effects") != [] for item in run_manifests):
        raise ValueError("local proof recorded a write effect")

    return {
        "schema_version": 1,
        "task_id": "L8-LOCAL-INDEPENDENT-REVIEW-REPAIR",
        "org_repo": manifest["org_repo"],
        "source_revision": manifest["source_revision"],
        "lifecycle_status": manifest["lifecycle_status"],
        "completed_stages": manifest["completed_stages"],
        "initial_candidate_sha256": candidate_hashes[0],
        "repaired_candidate_sha256": candidate_hashes[1],
        "proposal_bundle_count": len(proposal_dirs),
        "supervisor_run_statuses": statuses,
        "supervisor_run_count": len(run_manifests),
        "effect_count": 0,
        "repair_attempts": final_verdict["repair_attempts"],
        "deterministic_verdict": deterministic["verdict"],
        "independent_verdict": independent["verdict"],
        "no_op": no_op,
        "acceptance": "PASS",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    runs = args.runtime_root.resolve()
    output = args.output.resolve()
    if output.exists():
        raise ValueError(f"refusing to overwrite existing evidence directory: {output}")
    for required in ("evidence", "readme-poc", "readme-proposal-bundles"):
        if not (runs / required).is_dir():
            raise ValueError(f"missing canonical runtime directory: {runs / required}")

    summary = _validate_runtime(runs)
    output.mkdir(parents=True)
    shutil.copytree(runs / "evidence", output / "supervisor-runs")
    shutil.copytree(runs / "readme-poc", output / "readme-poc")
    shutil.copytree(runs / "readme-proposal-bundles", output / "readme-proposal-bundles")
    write_redacted_json(output / "proof-summary.json", summary)
    refresh_sha256sums(output)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
