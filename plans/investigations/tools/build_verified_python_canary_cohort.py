# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: verified Python canary cohort evidence producer
"""Bind approved runtime bundles into one reproducible side-by-side cohort verdict."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent.capabilities.dispatcher import dispatch_tool_call  # noqa: E402
from readme_agent.evidence.writer import (  # noqa: E402
    refresh_sha256sums,
    sha256_file,
    verify_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.readme.document_hashing import sha256_hex  # noqa: E402
from readme_agent.readme.document_structure import parse_headings  # noqa: E402
from readme_agent.specialists.review_mechanical_observations import (  # noqa: E402
    visible_header_badge_row_count,
)
from readme_agent.state.git_backend import default_state_backend  # noqa: E402
from readme_agent.supervisor.mission_goal_guard import (  # noqa: E402
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)
from readme_agent.supervisor.mission_graph import load_mission_graph  # noqa: E402

VERIFIER_IDENTITY = "verified-python-canary-cohort-verifier-v1"
TASK_ID = "L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES"
GRAPH_PATH = REPO_ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
COMMON_HEADINGS = {
    "navigation",
    "at a glance",
    "key capabilities",
    "license",
    "scope and limitations",
}
LICENSE_BENEFIT_TERMS = ("use", "modification", "distribution", "commercial use")


def _json_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _navigation_labels(candidate: str, headings: list) -> list[str]:
    navigation = next(
        (
            heading
            for heading in headings
            if heading.level == 2 and heading.title.strip().casefold() == "navigation"
        ),
        None,
    )
    if navigation is None:
        return []
    body = candidate[navigation.start : navigation.section_end]
    labels: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- [", "* [", "+ [")) and "](#" in stripped:
            labels.append(stripped[3 : stripped.index("](#")].strip())
    return labels


def _mermaid(candidate: str) -> str:
    marker = "```mermaid"
    start = candidate.find(marker)
    if start < 0:
        return ""
    end = candidate.find("```", start + len(marker))
    return "" if end < 0 else candidate[start + len(marker) : end].strip()


def inspect_member(org_repo: str, bundle_dir: Path) -> tuple[dict, str, list[str]]:
    """Validate one repository-verified member and return its bound cohort record."""

    failures: list[str] = []
    required = (
        "manifest.json",
        "sha256sums.txt",
        "candidate/README.md",
        "facts/product-facts.json",
        "planning/readme-document-plan.json",
        "review/deterministic-validation.json",
        "review/final-verdict.json",
        "review/independent-agent-review.json",
        "review/no-op-proof.json",
    )
    for relative in required:
        if not (bundle_dir / relative).is_file():
            failures.append(f"{org_repo}:missing:{relative}")
    if failures:
        return {}, "", failures
    if not verify_sha256sums(bundle_dir):
        failures.append(f"{org_repo}:bundle_checksum_inventory_invalid")

    manifest = _json_object(bundle_dir / "manifest.json")
    plan = _json_object(bundle_dir / "planning" / "readme-document-plan.json")
    deterministic = _json_object(bundle_dir / "review" / "deterministic-validation.json")
    final_verdict = _json_object(bundle_dir / "review" / "final-verdict.json")
    no_op = _json_object(bundle_dir / "review" / "no-op-proof.json")
    candidate_path = bundle_dir / "candidate" / "README.md"
    candidate = candidate_path.read_text(encoding="utf-8")
    candidate_sha256 = sha256_hex(candidate)
    headings = list(parse_headings(candidate))
    h1_titles = [heading.title.strip() for heading in headings if heading.level == 1]
    h2_titles = [heading.title.strip() for heading in headings if heading.level == 2]
    navigation_labels = _navigation_labels(candidate, headings)
    expected_navigation = [title for title in h2_titles if title.casefold() != "navigation"]
    mermaid = _mermaid(candidate)
    title = h1_titles[0] if len(h1_titles) == 1 else ""
    license_heading = next(
        (
            heading
            for heading in headings
            if heading.level == 2 and heading.title.strip().casefold() == "license"
        ),
        None,
    )
    license_body = (
        candidate[license_heading.start : license_heading.section_end].casefold()
        if license_heading is not None
        else ""
    )

    checks = {
        "bundle_checksum_inventory": verify_sha256sums(bundle_dir),
        "manifest_repository": manifest.get("org_repo") == org_repo,
        "repository_verified_assurance": manifest.get("content_assurance") == "repository_verified",
        "manifest_complete": manifest.get("complete") is True,
        "lifecycle_no_op_proven": manifest.get("lifecycle_status") == "NO_OP_PROVEN",
        "candidate_hash_bound": manifest.get("candidate_hash")
        == plan.get("candidate_sha256")
        == no_op.get("candidate_hash")
        == candidate_sha256,
        "facts_hash_bound": manifest.get("facts_hash") == plan.get("facts_hash"),
        "deterministic_accepted": deterministic.get("verdict") == "accept",
        "independent_agent_approved": final_verdict.get("verdict") == "AGENT_APPROVED"
        and final_verdict.get("agent_approved") is True,
        "identical_rerun_no_op": no_op.get("verdict") == "NO_OP_PROVEN"
        and no_op.get("new_provider_call_count") == 0
        and no_op.get("patch_created") is False
        and no_op.get("duplicate_bundle_created") is False,
        "one_factual_h1": len(h1_titles) == 1 and title.casefold().endswith("foss for python"),
        "one_badge_row": visible_header_badge_row_count(candidate) == 1,
        "common_structural_shell": COMMON_HEADINGS.issubset(
            {heading.casefold() for heading in h2_titles}
        ),
        "complete_list_navigation": [label.casefold() for label in navigation_labels]
        == [label.casefold() for label in expected_navigation],
        "mermaid_uses_full_product_name": bool(mermaid) and title in mermaid,
        "license_benefits_visible": all(term in license_body for term in LICENSE_BENEFIT_TERMS),
        "no_redundant_other_platforms": "other platforms"
        not in {heading.casefold() for heading in h2_titles},
        "no_readme_copyright_line": "copyright ©" not in candidate.casefold(),
    }
    failures.extend(f"{org_repo}:{name}" for name, passed in checks.items() if not passed)
    member = {
        "org_repo": org_repo,
        "source_revision": manifest.get("source_revision"),
        "bundle_path": _display(bundle_dir),
        "bundle_manifest_sha256": sha256_file(bundle_dir / "manifest.json")[0],
        "bundle_inventory_sha256": sha256_file(bundle_dir / "sha256sums.txt")[0],
        "facts_sha256": sha256_file(bundle_dir / "facts" / "product-facts.json")[0],
        "plan_sha256": sha256_file(bundle_dir / "planning" / "readme-document-plan.json")[0],
        "template_sha256": plan.get("template_sha256"),
        "candidate_sha256": candidate_sha256,
        "independent_review_sha256": sha256_file(
            bundle_dir / "review" / "independent-agent-review.json"
        )[0],
        "no_op_proof_sha256": sha256_file(bundle_dir / "review" / "no-op-proof.json")[0],
        "title": title,
        "badge_rows": visible_header_badge_row_count(candidate),
        "h2_headings": h2_titles,
        "navigation_labels": navigation_labels,
        "mermaid_sha256": sha256_hex(mermaid),
        "checks": checks,
    }
    return member, candidate, failures


def build_report(specs: list[tuple[str, Path]], control_revision: str) -> dict:
    """Build an independent deterministic cohort review over sealed member evidence."""

    members: list[dict] = []
    candidates: list[tuple[str, str]] = []
    failures: list[str] = []
    for org_repo, bundle_dir in sorted(specs):
        member, candidate, member_failures = inspect_member(org_repo, bundle_dir)
        failures.extend(member_failures)
        if member:
            members.append(member)
            candidates.append((org_repo, candidate))

    dispatch = dispatch_tool_call(
        {
            "function": {
                "name": "verify_cross_pilot_specificity",
                "arguments": json.dumps(
                    {"pilots": [[org_repo, candidate] for org_repo, candidate in candidates]}
                ),
            }
        },
        {"read_only_local"},
    )
    cross = dispatch.result if dispatch.outcome == "executed" and dispatch.result else None
    if cross is None:
        failures.append(f"cross_pilot_dispatch:{dispatch.outcome}:{dispatch.error}")
    elif not cross.get("verified"):
        failures.extend(f"cross_pilot:{failure}" for failure in cross.get("failures", []))

    cohort_checks = {
        "expected_three_members": len(members) == 3,
        "shared_template_contract": len({member["template_sha256"] for member in members}) == 1,
        "distinct_candidate_hashes": len({member["candidate_sha256"] for member in members})
        == len(members),
        "distinct_mermaid_content": len({member["mermaid_sha256"] for member in members})
        == len(members),
        "all_member_checks_pass": all(all(member["checks"].values()) for member in members),
        "cross_pilot_specificity": bool(cross and cross.get("verified")),
    }
    failures.extend(name for name, passed in cohort_checks.items() if not passed)
    return {
        "schema_version": 1,
        "verifier_identity": VERIFIER_IDENTITY,
        "review_mode": "deterministic_side_by_side_over_agent_approved_members",
        "control_revision": control_revision,
        "member_count": len(members),
        "members": members,
        "cohort_checks": cohort_checks,
        "cross_pilot_specificity": cross,
        "verdict": "accepted" if not failures else "rejected",
        "failures": sorted(set(failures)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--member", action="append", required=True, metavar="ORG_REPO=BUNDLE_DIR")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    specs: list[tuple[str, Path]] = []
    for value in args.member:
        org_repo, separator, raw_path = value.partition("=")
        if not separator or len(org_repo.split("/")) != 2:
            raise ValueError(f"invalid --member value: {value}")
        specs.append((org_repo, (REPO_ROOT / raw_path).resolve()))

    control_revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    report = build_report(specs, control_revision)
    output = (REPO_ROOT / args.output).resolve()
    evidence_root = (REPO_ROOT / "plans" / "investigations" / "evidence").resolve()
    if output.parent != evidence_root:
        raise ValueError(f"--output must be a direct child of {evidence_root}")
    output.mkdir(parents=True, exist_ok=True)
    write_redacted_json(output / "cohort-review.json", report)
    write_redacted_text(
        output / "SUMMARY.md",
        "# Verified Python Canary Cohort\n\n"
        f"Verdict: **{report['verdict']}**\n\n"
        f"Members: {report['member_count']}\n\n"
        "This deterministic side-by-side review binds independently agent-approved, "
        "repository-verified bundles and the registered cross-pilot specificity verdict.\n",
    )
    write_redacted_text(
        output / "REPRODUCE.txt",
        "Run from the control repository root at the recorded control revision:\n"
        + " ".join(sys.argv)
        + "\n",
    )
    graph, _ = load_mission_graph(GRAPH_PATH)
    task = next(task for task in graph.taskcards if task.task_id == TASK_ID)
    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    scoreboard_hash = lifecycle_scoreboard_sha256(scoreboard)
    write_redacted_json(
        output / "mission-contribution.json",
        {
            "schema_version": 1,
            "task_id": task.task_id,
            "stage_goal_id": task.stage_goal_id,
            "goal_ids": task.goal_ids,
            "core_contribution": task.core_contribution.model_dump(mode="json"),
            "acceptance_checks_passed": task.acceptance_checks,
            "proof_refs": [
                "plans/investigations/evidence/verified-python-canary-cohort-v1/cohort-review.json",
                "plans/investigations/evidence/verified-python-canary-cohort-v1/SUMMARY.md",
            ],
            "scoreboard_before_sha256": scoreboard_hash,
            "scoreboard_after_sha256": scoreboard_hash,
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": report["verdict"] == "accepted",
        },
    )
    refresh_sha256sums(output)
    if not verify_sha256sums(output):
        raise RuntimeError("cohort evidence checksum inventory is invalid")
    print(json.dumps(report, indent=2))
    return 0 if report["verdict"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
