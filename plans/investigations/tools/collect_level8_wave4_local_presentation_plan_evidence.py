# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: Wave-4 local presentation-plan acceptance-evidence producer
"""Run local Wave-4 planning gates and write checksum-complete evidence."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from argparse import ArgumentParser
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent import paths  # noqa: E402
from readme_agent.facts.provider import collect_product_facts  # noqa: E402
from readme_agent.facts.schema_v2 import ProductFactsV2  # noqa: E402
from readme_agent.gitsafety.clone import clone_baseline  # noqa: E402
from readme_agent.inspection.file_inventory import scan  # noqa: E402
from readme_agent.presentation.git_patch import sha256_text  # noqa: E402
from readme_agent.presentation.planner import (  # noqa: E402
    build_repository_presentation_plan,
)
from readme_agent.readme.markers import upsert_span  # noqa: E402
from readme_agent.registry.loader import require_listed  # noqa: E402
from readme_agent.registry.surface_ownership import (  # noqa: E402
    SurfaceOwnershipMapV1,
)
from readme_agent.specialists.readme_factuality import (  # noqa: E402
    evaluate_candidate_factuality,
)

DEFAULT_EVIDENCE_DIR = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-wave4-local-presentation-plan-foundation-2026-07-23"
)
STRONG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
CONFLICT_REPO = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
EVIDENCE_FILENAMES = {
    "complete-non-live-test-suite.log",
    "focused-presentation-contract-tests.log",
    "independent-verification.json",
    "official-static-quality-gates.log",
    "real-repository-presentation-proof.json",
    "repository-snapshot.json",
    "sha256sums.txt",
    "wave4-local-acceptance-summary.json",
}
IMPLEMENTATION_PATHS = (
    "docs/architecture.md",
    "plans/investigations/tools/collect_level8_wave4_local_presentation_plan_evidence.py",
    "scripts/retrofits/record_level8_wave4_local_presentation_plan_requirement_truth.py",
    "src/readme_agent/capabilities/build_presentation_plan.py",
    "src/readme_agent/capabilities/render_readme_candidate.py",
    "src/readme_agent/capabilities/registry.py",
    "src/readme_agent/presentation/claim_validation.py",
    "src/readme_agent/presentation/git_patch.py",
    "src/readme_agent/presentation/markdown_structure.py",
    "src/readme_agent/presentation/planner.py",
    "src/readme_agent/presentation/schema.py",
    "src/readme_agent/readme/candidate_models.py",
    "src/readme_agent/readme/candidate_pipeline.py",
    "src/readme_agent/specialists/readme_presentation.py",
    "src/readme_agent/validation/rules/talking_points.py",
    "src/readme_agent/validation/registry.py",
    "tests/unit/test_build_presentation_plan_capability.py",
    "tests/unit/test_git_patch.py",
    "tests/unit/test_markdown_structure.py",
    "tests/unit/test_mission_control.py",
    "tests/unit/test_presentation_plan_schema.py",
    "tests/unit/test_presentation_planner.py",
)


def _sha256(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()


def _refresh_checksums(evidence_dir: Path) -> None:
    lines = [
        f"{_sha256(path)}  {path.name}"
        for path in sorted(evidence_dir.iterdir())
        if path.is_file() and path.name != "sha256sums.txt"
    ]
    (evidence_dir / "sha256sums.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )


def _prepare_evidence_dir(evidence_dir: Path) -> None:
    governed_root = (REPO_ROOT / "plans" / "investigations" / "evidence").resolve()
    if evidence_dir.parent != governed_root or not evidence_dir.name.startswith(
        "level8-wave4-local-presentation-plan-foundation-"
    ):
        raise RuntimeError(f"refusing to replace evidence outside {governed_root}")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for path in evidence_dir.iterdir():
        if not path.is_file() or path.name not in EVIDENCE_FILENAMES:
            raise RuntimeError(f"refusing to replace unexpected evidence artifact {path}")
        path.unlink()


def _run(command: list[str], timeout_seconds: int) -> dict:
    started = datetime.now(UTC)
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "command": command,
        "return_code": completed.returncode,
        "started_at": started.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "output": completed.stdout,
    }


def _write_log(path: Path, results: list[dict]) -> None:
    sections = [
        f"$ {subprocess.list2cmdline(result['command'])}\n"
        f"return_code={result['return_code']}\n"
        f"started_at={result['started_at']}\n"
        f"finished_at={result['finished_at']}\n\n"
        f"{result['output'].rstrip()}\n"
        for result in results
    ]
    path.write_text("\n".join(sections), encoding="utf-8", newline="\n")


def _resume_result(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(f"cannot resume without existing test log {path}")
    codes = re.findall(r"^return_code=(\d+)$", path.read_text(encoding="utf-8"), re.MULTILINE)
    if len(codes) != 1:
        raise RuntimeError(f"{path.name} does not contain exactly one command")
    return {"return_code": int(codes[0])}


def _repository_text(org_repo: str) -> tuple[str, str]:
    entry = require_listed(org_repo)
    baseline = paths.baseline_dir(entry.org, entry.repo_name)
    clone_baseline(entry, baseline)
    inventory = scan(baseline)
    if inventory.readme_path is None:
        raise RuntimeError(f"{org_repo} has no README")
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=baseline,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    ).stdout.strip()
    return inventory.readme_path.read_text(encoding="utf-8"), revision


def _facts_and_ownership(org_repo: str) -> tuple[ProductFactsV2, SurfaceOwnershipMapV1]:
    result = collect_product_facts(org_repo)
    return (
        ProductFactsV2.model_validate(result["product_facts_v2"]),
        SurfaceOwnershipMapV1.model_validate(result["surface_ownership"]),
    )


def _candidate(readme: str) -> str:
    content = (
        "### Related Aspose Resources\n\n"
        "- **License:** MIT\n"
        "- [FOSS catalog](https://products.aspose.org/cells/java/)\n"
        "- [Commercial edition](https://products.aspose.com/cells/java/)\n\n"
        "This repository is the open-source edition; the commercial edition provides "
        "broader support."
    )
    return upsert_span(readme, "resources", content, "b" * 64)


def _real_repository_proof() -> dict:
    strong_text, strong_revision = _repository_text(STRONG_REPO)
    strong_facts, strong_ownership = _facts_and_ownership(STRONG_REPO)
    strong_plan, strong_patch, strong_executable = build_repository_presentation_plan(
        STRONG_REPO,
        strong_text,
        strong_text,
        strong_facts,
        strong_ownership,
        base_revision=strong_revision,
    )

    conflict_text, conflict_revision = _repository_text(CONFLICT_REPO)
    conflict_facts, conflict_ownership = _facts_and_ownership(CONFLICT_REPO)
    conflict_candidate = _candidate(conflict_text)
    conflict_plan, conflict_patch, conflict_executable = build_repository_presentation_plan(
        CONFLICT_REPO,
        conflict_text,
        conflict_candidate,
        conflict_facts,
        conflict_ownership,
        base_revision=conflict_revision,
    )
    factuality = evaluate_candidate_factuality(
        CONFLICT_REPO,
        conflict_text,
        conflict_candidate,
        {"read_only_local", "read_only_network"},
    )
    action = conflict_plan.actions[0]
    return {
        "schema_version": 1,
        "captured_at": datetime.now(UTC).isoformat(),
        "strong_existing_readme": {
            "repository": STRONG_REPO,
            "source_revision": strong_revision,
            "facts_hash": strong_plan.facts_hash,
            "finding_count": len(strong_plan.findings),
            "finding_dimensions": [finding.dimension for finding in strong_plan.findings],
            "action_count": len(strong_plan.actions),
            "unchanged_candidate": strong_patch is None,
            "plan_executable": strong_executable,
        },
        "conflicting_readme_candidate": {
            "repository": CONFLICT_REPO,
            "source_revision": conflict_revision,
            "facts_hash": conflict_plan.facts_hash,
            "finding_count": len(conflict_plan.findings),
            "action": action.model_dump(mode="json"),
            "plan_executable": conflict_executable,
            "git_apply_check_passed": bool(
                conflict_patch and conflict_patch.git_apply_check_passed
            ),
            "outside_spans_preserved": bool(
                conflict_patch and conflict_patch.outside_spans_preserved
            ),
            "source_sha256": sha256_text(conflict_text),
            "candidate_sha256": sha256_text(conflict_candidate),
            "final_factuality_valid": factuality.valid,
            "positive_false_claims": [
                {key: value for key, value in finding.items() if key != "readme_excerpt"}
                for finding in factuality.claim_conflicts
            ],
        },
    }


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("evidence_dir", nargs="?", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--resume-after-tests", action="store_true")
    parser.add_argument("--rerun-full-suite", action="store_true")
    parser.add_argument("--refresh-checksums", action="store_true")
    args = parser.parse_args()
    evidence_dir = args.evidence_dir.resolve()
    if args.refresh_checksums:
        _refresh_checksums(evidence_dir)
        return 0
    if not args.resume_after_tests:
        _prepare_evidence_dir(evidence_dir)
    python = str(REPO_ROOT / ".venv" / "Scripts" / "python.exe")

    official_commands = [
        [python, "-m", "ruff", "check", "."],
        [python, "-m", "ruff", "format", "--check", "."],
        [python, "-m", "mypy", "src"],
        ["actionlint"],
        [python, "scripts/governance/validate_plan_structure.py"],
        [python, "plans/investigations/tools/extract_requirements.py", "--check"],
        [python, "plans/investigations/tools/coverage_classify.py", "--check"],
        [
            python,
            "scripts/governance/build_level8_requirement_taskcard_coverage.py",
            "--check",
        ],
    ]
    official = [_run(command, 240) for command in official_commands]
    _write_log(evidence_dir / "official-static-quality-gates.log", official)
    focused = _run(
        [
            python,
            "-m",
            "pytest",
            "-q",
            "tests/unit/test_markdown_structure.py",
            "tests/unit/test_git_patch.py",
            "tests/unit/test_build_presentation_plan_capability.py",
            "tests/unit/test_presentation_plan_schema.py",
            "tests/unit/test_presentation_planner.py",
            "tests/unit/test_capabilities.py",
            "tests/unit/test_specialists.py",
            "tests/unit/test_readme_factuality.py",
            "tests/unit/test_protected_content.py",
        ],
        600,
    )
    _write_log(evidence_dir / "focused-presentation-contract-tests.log", [focused])
    if args.resume_after_tests and not args.rerun_full_suite:
        full = _resume_result(evidence_dir / "complete-non-live-test-suite.log")
    else:
        full = _run([python, "-m", "pytest", "-q"], 1_200)
        _write_log(evidence_dir / "complete-non-live-test-suite.log", [full])

    real_proof = _real_repository_proof()
    (evidence_dir / "real-repository-presentation-proof.json").write_text(
        json.dumps(real_proof, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    snapshot = {
        "captured_at": datetime.now(UTC).isoformat(),
        "head": _run(["git", "rev-parse", "HEAD"], 30)["output"].strip(),
        "working_tree_status": _run(["git", "status", "--short"], 30)["output"].splitlines(),
        "implementation_file_sha256": {
            path: _sha256(REPO_ROOT / path)
            for path in IMPLEMENTATION_PATHS
            if (REPO_ROOT / path).is_file()
        },
    }
    (evidence_dir / "repository-snapshot.json").write_text(
        json.dumps(snapshot, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    conflict = real_proof["conflicting_readme_candidate"]
    strong = real_proof["strong_existing_readme"]
    technical = (
        all(result["return_code"] == 0 for result in official)
        and focused["return_code"] == 0
        and full["return_code"] == 0
        and strong["finding_count"] == 10
        and strong["action_count"] == 0
        and conflict["finding_count"] == 10
        and conflict["git_apply_check_passed"]
        and conflict["outside_spans_preserved"]
        and not conflict["final_factuality_valid"]
        and any(
            finding["verification_outcome"] == "NOT_PUBLISHED"
            for finding in conflict["positive_false_claims"]
        )
    )
    independent_path = evidence_dir / "independent-verification.json"
    independent = (
        json.loads(independent_path.read_text(encoding="utf-8"))
        if independent_path.is_file()
        else None
    )
    independently_accepted = bool(
        independent and independent.get("verdict") in {"accepted", "accepted_no_blocking_findings"}
    )
    summary = {
        "schema_version": 1,
        "producer": str(Path(__file__).relative_to(REPO_ROOT)).replace("\\", "/"),
        "generated_at": datetime.now(UTC).isoformat(),
        "task_id": "L8-WAVE4-LOCAL-PRESENTATION-PLAN-FOUNDATION",
        "official_static_quality_gates_passed": all(
            result["return_code"] == 0 for result in official
        ),
        "focused_contract_tests_passed": focused["return_code"] == 0,
        "complete_non_live_test_suite_passed": full["return_code"] == 0,
        "real_read_only_repository_proof_passed": technical,
        "technical_acceptance_gates_passed": technical,
        "independent_verification_passed": independently_accepted,
        "all_local_acceptance_gates_passed": technical and independently_accepted,
        "parent_wave4_remains_blocked_by": [
            "Wave 2 hosted GitHub App/LLM/recovery proof and parent Wave 3 closure",
            "complete cross-surface planning and archetype-specific rendering",
            "100-case three-session agentic golden-set threshold",
        ],
    }
    (evidence_dir / "wave4-local-acceptance-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    _refresh_checksums(evidence_dir)
    print(json.dumps(summary, indent=2))
    return 0 if summary["all_local_acceptance_gates_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
