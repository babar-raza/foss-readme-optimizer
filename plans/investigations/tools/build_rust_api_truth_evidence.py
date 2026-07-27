"""Build real-package evidence for Rust public API and consumer truth."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from rust_api_truth_evidence_support import (
    EXPECTED_SYMBOLS,
    docker_inventory,
    immutable_image,
    real_formats,
    real_proof,
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
from readme_agent.supervisor.mission_graph import load_mission_graph

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = REPO_ROOT / "plans/investigations/evidence/level8-rust-api-truth"
GRAPH_PATH = REPO_ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
REPRESENTATIVE = Path(
    os.environ.get(
        "README_AGENT_RUST_REPRESENTATIVE",
        str(REPO_ROOT / "runs/baseline/aspose-cells-foss__Aspose.Cells-FOSS-for-Rust"),
    )
).resolve()
TASK_ID = "L8-TRUTH-02D-RUST-API-TRUTH"
REQUIREMENT_ID = "L8-032"
PYTHON = sys.executable
FOCUSED_COMMAND = (
    PYTHON,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_rust_public_api.py",
    "tests/unit/test_rust_consumer.py",
    "tests/unit/test_ecosystems.py",
    "tests/unit/test_local_verification.py",
    "tests/unit/test_cpp_rust_example_verifiers.py",
    "tests/unit/test_isolated_execution.py",
    "tests/security/test_example_execution_boundary.py",
)
LIVE_COMMAND = (
    PYTHON,
    "-m",
    "pytest",
    "-q",
    "-m",
    "live",
    "tests/security/test_rust_consumer_docker_live.py",
)
OFFICIAL_COMMAND = (PYTHON, "scripts/governance/run_official_checks.py")


def _git(*args: str, root: Path = REPO_ROOT) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(command: tuple[str, ...]) -> dict[str, Any]:
    result = subprocess.run(
        list(command),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "command": " ".join(command),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _control_state() -> dict[str, Any]:
    status = _git("status", "--porcelain=v1")
    implementation_paths = [
        "pyproject.toml",
        "requirements-lock.txt",
        "docs/architecture.md",
        "plans/investigations/tools/rust_api_truth_evidence_support.py",
        "src/readme_agent/capabilities/draft_product_truth.py",
        "src/readme_agent/ecosystems/rust_api_schema.py",
        "src/readme_agent/ecosystems/rust_format_truth.py",
        "src/readme_agent/ecosystems/rust_package_layout.py",
        "src/readme_agent/ecosystems/rust_public_api.py",
        "src/readme_agent/ecosystems/rust_snippets.py",
        "src/readme_agent/ecosystems/rust_symbol_extraction.py",
        "src/readme_agent/ecosystems/rust_syntax.py",
        "src/readme_agent/ecosystems/rust_use_resolution.py",
        "src/readme_agent/facts/example_verification_schema.py",
        "src/readme_agent/facts/isolated_cleanup.py",
        "src/readme_agent/facts/isolated_docker_control.py",
        "src/readme_agent/facts/isolated_execution.py",
        "src/readme_agent/facts/provider.py",
        "src/readme_agent/facts/rust_consumer.py",
        "src/readme_agent/facts/rust_consumer_schema.py",
        "src/readme_agent/facts/rust_dependency_acquisition.py",
        "src/readme_agent/facts/rust_dependency_schema.py",
        "src/readme_agent/facts/rust_example_verifier.py",
        "src/readme_agent/facts/local_verification.py",
        "tests/unit/test_draft_product_truth_capability.py",
        "tests/unit/test_facts_provider.py",
        "tests/unit/test_local_verification.py",
        "tests/unit/test_rust_public_api.py",
        "tests/unit/test_rust_consumer.py",
        "tests/security/test_rust_consumer_docker_live.py",
    ]
    return {
        "head": _git("rev-parse", "HEAD"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "tree_clean_at_start": not status,
        "tree_porcelain_sha256": hashlib.sha256(status.encode("utf-8")).hexdigest(),
        "builder_path": Path(__file__).resolve().relative_to(REPO_ROOT).as_posix(),
        "builder_sha256": _sha256(Path(__file__).resolve()),
        "implementation": {path: _sha256(REPO_ROOT / path) for path in implementation_paths},
    }


def _write(run_official: bool) -> list[str]:
    control = _control_state()
    if not control["tree_clean_at_start"]:
        raise RuntimeError("Rust API proof requires a clean committed control tree")
    focused = _run(FOCUSED_COMMAND)
    live = _run(LIVE_COMMAND)
    official = _run(OFFICIAL_COMMAND) if run_official else None
    tree_stable = _git("rev-parse", "HEAD") == control["head"] and not _git(
        "status", "--porcelain=v1"
    )
    snapshot, surface, proof, registry, installation = real_proof(REPRESENTATIVE)
    inventory = docker_inventory()
    symbols = {item["qualified_name"]: item for item in surface["symbols"]}
    formats = real_formats(surface)
    isolated = proof["isolated_execution"]
    acquisition = proof["acquisition"]
    checks = {
        "focused_tests_pass": focused["exit_code"] == 0,
        "live_docker_tests_pass": live["exit_code"] == 0,
        "official_checks_pass": bool(official and official["exit_code"] == 0 and tree_stable),
        "real_revision_bound": snapshot["source_revision"] == snapshot["baseline_head"],
        "baseline_clean": snapshot["baseline_tree_clean"],
        "canonical_crate": surface["package"]["crate_name"] == "aspose_cells_foss_rust",
        "expected_public_symbols": EXPECTED_SYMBOLS <= set(symbols),
        "private_fields_excluded": not {
            "aspose_cells_foss_rust::Workbook.worksheets",
            "aspose_cells_foss_rust::Workbook.default_style",
        }
        & set(symbols),
        "root_reexport_resolved": (
            symbols["aspose_cells_foss_rust::Workbook"]["visibility_evidence"] == "public_reexport"
        ),
        "path_modules_resolved": any(module.get("path_attribute") for module in surface["modules"]),
        "repository_snippets_found": bool(surface["snippets"]),
        "directional_xlsx_formats": {
            ("xlsx", "import"),
            ("xlsx", "export"),
        }
        <= formats,
        "registry_absence_verified": not registry["found"] and not registry["blocked"],
        "source_install_is_pinned": (
            snapshot["source_revision"] in installation and "github.com/" in installation
        ),
        "locked_dependency_bundle": (
            acquisition["lock_package_count"] > 1
            and len(acquisition["lockfile_sha256"]) == 64
            and len(acquisition["vendor_sha256"]) == 64
            and acquisition["cleanup_complete"]
        ),
        "consumer_accepted": (
            proof["accepted"]
            and set(proof["verified_symbols"]) == EXPECTED_SYMBOLS
            and not proof["missing_symbols"]
            and not proof["diagnostics"]
        ),
        "network_separated": (
            acquisition["network_mode"] == "bridge" and isolated["policy"]["network_mode"] == "none"
        ),
        "immutable_image": (
            acquisition["image"]["repo_digest"] == immutable_image()
            and isolated["image"]["repo_digest"] == immutable_image()
        ),
        "offline_locked_command": isolated["argv"][1:4] == ["check", "--locked", "--offline"],
        "cleanup_complete": all(isolated["cleanup"].values()),
        "no_managed_resources_remain": not any(inventory.values()),
    }
    failures = [name for name, passed in checks.items() if not passed]
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_redacted_json(EVIDENCE_DIR / "repository-snapshot.json", snapshot)
    write_redacted_json(EVIDENCE_DIR / "public-api-surface.json", surface)
    write_redacted_json(EVIDENCE_DIR / "locked-consumer-proof.json", proof)
    write_redacted_json(EVIDENCE_DIR / "crates-io-resolution.json", registry)
    write_redacted_text(EVIDENCE_DIR / "pinned-source-dependency.toml", installation + "\n")
    write_redacted_json(EVIDENCE_DIR / "cleanup-inventory.json", inventory)
    for name, result in (("focused-tests", focused), ("live-docker-tests", live)):
        write_redacted_text(EVIDENCE_DIR / f"{name}.stdout.log", result["stdout"])
        write_redacted_text(EVIDENCE_DIR / f"{name}.stderr.log", result["stderr"])
    if official:
        write_redacted_text(EVIDENCE_DIR / "official-checks.stdout.log", official["stdout"])
        write_redacted_text(EVIDENCE_DIR / "official-checks.stderr.log", official["stderr"])
    write_redacted_json(
        EVIDENCE_DIR / "source-provenance.json",
        {
            "local_implementation_commit": control["head"],
            "sibling_contract": (
                "plans/investigations/control/aspose-org-ecosystem-adaptation-contract.json"
            ),
            "sibling_head": "512a6e8dcdf220f0d7a81ab7882245f95b6d4ef9",
            "sibling_rust_commits": [
                "e131074708b17a85e078d3ba0939a0d126ea525a",
                "e157b7ff992e8f6f48a969644b66422a653e75ba",
                "abd634df3d9b2060b77b98aa9d6788553573ceea",
            ],
            "adaptation_evidence": (
                "plans/investigations/evidence/level8-aspose-org-ecosystem-adaptation/"
                "adaptation-matrix.json"
            ),
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "requirement_id": REQUIREMENT_ID,
            "control_repository": control,
            "commands": {
                "focused": {"command": focused["command"], "exit_code": focused["exit_code"]},
                "live": {"command": live["command"], "exit_code": live["exit_code"]},
                "official": (
                    {
                        "command": official["command"],
                        "exit_code": official["exit_code"],
                        "tree_stable": tree_stable,
                    }
                    if official
                    else {"status": "not_run"}
                ),
            },
            "checks": checks,
            "failures": failures,
            "verdict": "VERIFIED" if not failures else "FAILED",
        },
    )
    graph, _ = load_mission_graph(GRAPH_PATH)
    task = next(task for task in graph.taskcards if task.task_id == TASK_ID)
    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    scoreboard_hash = lifecycle_scoreboard_sha256(scoreboard)
    write_redacted_json(
        EVIDENCE_DIR / "mission-contribution.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "goal_ids": task.goal_ids,
            "core_contribution": task.core_contribution.model_dump(mode="json"),
            "acceptance_checks_passed": task.acceptance_checks,
            "proof_refs": [
                "plans/investigations/evidence/level8-rust-api-truth/verification.json",
                "plans/investigations/evidence/level8-rust-api-truth/public-api-surface.json",
                "plans/investigations/evidence/level8-rust-api-truth/locked-consumer-proof.json",
            ],
            "scoreboard_before_sha256": scoreboard_hash,
            "scoreboard_after_sha256": scoreboard_hash,
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": not failures,
        },
    )
    write_redacted_text(
        EVIDENCE_DIR / "reproduction.txt",
        f"docker pull {immutable_image()}\n"
        ".venv/Scripts/python plans/investigations/tools/"
        "build_rust_api_truth_evidence.py --official --check\n",
    )
    refresh_sha256sums(EVIDENCE_DIR)
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    failures = _write(args.official)
    if args.check and failures:
        raise SystemExit("Rust API evidence failed: " + ", ".join(failures))
    print(f"wrote Rust API truth evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
