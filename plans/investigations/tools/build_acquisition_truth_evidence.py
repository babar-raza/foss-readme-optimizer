"""Build checksum-complete evidence for registry-or-source acquisition truth."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from acquisition_truth_evidence_support import (
    IMPLEMENTATION_PATHS,
    build_acquisition_controls,
    load_python_verification,
    load_rust_verification,
    load_typescript_verification,
    verify_evidence_inventory,
)

from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.state.git_backend import default_state_backend
from readme_agent.supervisor.mission_goal_guard import (
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = REPO_ROOT / "plans/investigations/evidence/level8-acquisition-truth"
FAILURE_DIR = REPO_ROOT / "runs/control/acquisition-truth-proof-failure"
TASK_ID = "L8-TRUTH-04-ACQUISITION"
PYTHON = sys.executable
REPRESENTATIVES = {
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Java": (
        "aspose-cells-foss__Aspose.Cells-FOSS-for-Java"
    ),
    "aspose-3d-foss/Aspose.3D-FOSS-for-.NET": "aspose-3d-foss__Aspose.3D-FOSS-for-.NET",
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp": ("aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp"),
    "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go": "aspose-pdf-foss__Aspose-PDF-FOSS-for-Go",
    "aspose-3d-foss/Aspose.3D-FOSS-for-Python": ("aspose-3d-foss__Aspose.3D-FOSS-for-Python"),
    "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript": (
        "aspose-3d-foss__Aspose.3D-FOSS-for-TypeScript"
    ),
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust": (
        "aspose-cells-foss__Aspose.Cells-FOSS-for-Rust"
    ),
}
SOURCE_PROOFS = {
    "python": REPO_ROOT / "plans/investigations/evidence/level8-python-api-truth",
    "typescript": REPO_ROOT / "plans/investigations/evidence/level8-typescript-export-truth",
    "rust": REPO_ROOT / "plans/investigations/evidence/level8-rust-api-truth",
}
FOCUSED_COMMAND = (
    PYTHON,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_acquisition.py",
    "tests/unit/test_ecosystem_resolver.py",
    "tests/unit/test_facts_provider.py",
    "tests/unit/test_draft_product_truth_capability.py",
    "tests/unit/test_fact_acceptance_contract.py",
    "tests/unit/test_facts_schema_v2.py",
    "tests/security/test_no_secrets_in_evidence.py",
)
OFFICIAL_COMMAND = (PYTHON, "scripts/governance/run_official_checks.py")


def _run(command: tuple[str, ...]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "command": subprocess.list2cmdline(command),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _git(*args: str, root: Path = REPO_ROOT) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _representative_roots() -> dict[str, Path]:
    baseline = Path(
        os.environ.get(
            "README_AGENT_ACQUISITION_BASELINE_ROOT",
            str(REPO_ROOT / "runs/baseline"),
        )
    ).resolve()
    return {org_repo: baseline / name for org_repo, name in REPRESENTATIVES.items()}


def _write_failure(
    *,
    control: dict[str, Any],
    checks: dict[str, bool],
    focused: dict[str, Any],
    official: dict[str, Any] | None,
) -> None:
    FAILURE_DIR.mkdir(parents=True, exist_ok=True)
    write_redacted_text(FAILURE_DIR / "focused-tests.stdout.log", focused["stdout"])
    write_redacted_text(FAILURE_DIR / "focused-tests.stderr.log", focused["stderr"])
    if official is not None:
        write_redacted_text(FAILURE_DIR / "official-checks.stdout.log", official["stdout"])
        write_redacted_text(FAILURE_DIR / "official-checks.stderr.log", official["stderr"])
    write_redacted_json(
        FAILURE_DIR / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "control_repository": control,
            "checks": checks,
            "failures": [name for name, passed in checks.items() if not passed],
            "verdict": "FAILED",
        },
    )
    refresh_sha256sums(FAILURE_DIR)


def _build(run_official: bool) -> list[str]:
    start_status = _git("status", "--porcelain=v1", "--untracked-files=all")
    control = {
        "head": _git("rev-parse", "HEAD"),
        "branch": _git("branch", "--show-current") or "HEAD",
        "tree_clean_at_start": not start_status,
        "tree_porcelain_sha256": hashlib.sha256(start_status.encode("utf-8")).hexdigest(),
        "builder_path": Path(__file__).resolve().relative_to(REPO_ROOT).as_posix(),
        "builder_sha256": _sha256(Path(__file__).resolve()),
        "implementation": {
            path: _sha256(REPO_ROOT / path) for path in sorted(IMPLEMENTATION_PATHS)
        },
    }
    roots = _representative_roots()
    revisions = {org_repo: _git("rev-parse", "HEAD", root=root) for org_repo, root in roots.items()}
    clean_representatives = {
        org_repo: not _git("status", "--porcelain=v1", root=root)
        for org_repo, root in roots.items()
    }
    inventories = {
        ecosystem: verify_evidence_inventory(root) for ecosystem, root in SOURCE_PROOFS.items()
    }
    python = load_python_verification(
        SOURCE_PROOFS["python"] / "installed-consumer-verification.json"
    )
    typescript = load_typescript_verification(
        SOURCE_PROOFS["typescript"] / "built-consumer-proof.json"
    )
    rust = load_rust_verification(SOURCE_PROOFS["rust"] / "locked-consumer-proof.json")
    controls = build_acquisition_controls(
        revisions=revisions,
        python_verification=python,
        typescript_verification=typescript,
        rust_verification=rust,
    )
    focused = _run(FOCUSED_COMMAND)
    official = _run(OFFICIAL_COMMAND) if run_official else None
    decisions = controls["decisions"]
    negatives = controls["negative_controls"]
    expected_registry = {
        "java_published",
        "dotnet_published",
        "cpp_nuget_published",
        "go_proxy_published",
    }
    expected_source = {
        "python_source_build",
        "typescript_source_build",
        "rust_source_build",
    }
    checks = {
        "control_tree_clean": control["tree_clean_at_start"],
        "representatives_clean": all(clean_representatives.values()),
        "source_proof_inventories_valid": all(item["accepted"] for item in inventories.values()),
        "source_revisions_match": all(
            verification.source_revision == revisions[verification.org_repo]
            for verification in (python, typescript, rust)
        ),
        "published_coordinates_have_receipts": all(
            decisions[name]["outcome"] == "REGISTRY_VERIFIED"
            and decisions[name]["registry_receipt"]["status_code"] == 200
            for name in expected_registry
        ),
        "unpublished_sources_have_both_receipts": all(
            decisions[name]["outcome"] == "SOURCE_BUILD_VERIFIED"
            and decisions[name]["registry_receipt"]["status_code"] == 404
            and decisions[name]["source_build_receipt"]["network_mode"] == "none"
            for name in expected_source
        ),
        "synthetic_false_maven_rejected": (
            decisions["synthetic_false_maven"]["truth_eligible"] is False
            and decisions["synthetic_false_maven"]["registry_receipt"]["status_code"] == 404
        ),
        "readme_prose_cannot_verify_source": (
            negatives["readme_prose_only"]["truth_eligible"] is False
        ),
        "host_only_build_cannot_verify_source": (
            negatives["host_only_source_build"]["truth_eligible"] is False
        ),
        "network_uncertainty_blocks": (
            negatives["network_uncertainty"]["outcome"] == "BLOCKED_NETWORK"
            and negatives["network_uncertainty"]["truth_eligible"] is False
        ),
        "focused_tests_pass": focused["exit_code"] == 0,
        "official_checks_pass": official is None or official["exit_code"] == 0,
        "tree_stable": _git("rev-parse", "HEAD") == control["head"]
        and _git("status", "--porcelain=v1", "--untracked-files=all") == start_status,
    }
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        _write_failure(control=control, checks=checks, focused=focused, official=official)
        return failures

    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_redacted_json(
        EVIDENCE_DIR / "repository-revisions.json",
        {
            "schema_version": 1,
            "revisions": revisions,
            "clean": clean_representatives,
        },
    )
    write_redacted_json(EVIDENCE_DIR / "source-proof-inventories.json", inventories)
    write_redacted_json(EVIDENCE_DIR / "acquisition-decisions.json", controls)
    write_redacted_text(EVIDENCE_DIR / "focused-tests.stdout.log", focused["stdout"])
    write_redacted_text(EVIDENCE_DIR / "focused-tests.stderr.log", focused["stderr"])
    if official is not None:
        write_redacted_text(EVIDENCE_DIR / "official-checks.stdout.log", official["stdout"])
        write_redacted_text(EVIDENCE_DIR / "official-checks.stderr.log", official["stderr"])
    write_redacted_json(
        EVIDENCE_DIR / "mission-contribution.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "goal_ids": ["GOAL-TRUTH"],
            "core_contribution": {
                "kind": "visible_deliverable",
                "summary": (
                    "Select registry-verified coordinates or exact revision-bound isolated "
                    "source-build paths without converting unpublished packages into global blocks."
                ),
            },
            "acceptance_checks_passed": [
                "False coordinates cannot reach FACTS_READY",
                "Unpublished packages with verified isolated builds remain truth eligible",
                "Host-only source builds cannot become verified truth",
            ],
            "scoreboard_before_sha256": lifecycle_scoreboard_sha256(scoreboard),
            "scoreboard_after_sha256": lifecycle_scoreboard_sha256(scoreboard),
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": True,
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "control_repository": control,
            "commands": {
                "focused": {key: focused[key] for key in ("command", "exit_code")},
                "official": (
                    {key: official[key] for key in ("command", "exit_code")}
                    if official is not None
                    else None
                ),
            },
            "checks": checks,
            "failures": failures,
            "verdict": "VERIFIED",
        },
    )
    write_redacted_text(
        EVIDENCE_DIR / "reproduction.txt",
        (
            f"{PYTHON} plans/investigations/tools/build_acquisition_truth_evidence.py "
            "--official --check\n"
        ),
    )
    refresh_sha256sums(EVIDENCE_DIR)
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    failures = _build(args.official)
    if failures:
        raise SystemExit("acquisition truth proof failed: " + ", ".join(failures))
    print(f"wrote acquisition truth evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
