"""Build real-package evidence for TypeScript exports and consumer truth."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from typescript_export_truth_evidence_support import (
    EXPECTED_IMPORT,
    docker_inventory,
    immutable_image,
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
EVIDENCE_DIR = REPO_ROOT / "plans/investigations/evidence/level8-typescript-export-truth"
GRAPH_PATH = REPO_ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
REPRESENTATIVE = Path(
    os.environ.get(
        "README_AGENT_TYPESCRIPT_REPRESENTATIVE",
        str(REPO_ROOT / "runs/baseline/aspose-3d-foss__Aspose.3D-FOSS-for-TypeScript"),
    )
).resolve()
TASK_ID = "L8-TRUTH-02C-TYPESCRIPT-EXPORT-TRUTH"
REQUIREMENT_ID = "L8-031"
PYTHON = sys.executable
FOCUSED_COMMAND = (
    PYTHON,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_typescript_public_api.py",
    "tests/unit/test_ecosystems.py",
    "tests/unit/test_local_verification.py",
    "tests/security/test_example_execution_boundary.py",
)
LIVE_COMMAND = (
    PYTHON,
    "-m",
    "pytest",
    "-q",
    "-m",
    "live",
    "tests/security/test_typescript_consumer_docker_live.py",
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
        "src/readme_agent/ecosystems/typescript_api_schema.py",
        "src/readme_agent/ecosystems/typescript_package_layout.py",
        "src/readme_agent/facts/typescript_consumer.py",
        "src/readme_agent/facts/typescript_consumer_driver.js",
        "src/readme_agent/facts/typescript_consumer_schema.py",
        "src/readme_agent/facts/typescript_example_verifier.py",
        "src/readme_agent/facts/typescript_toolchain.py",
        "src/readme_agent/facts/local_verification.py",
        "tests/unit/test_typescript_public_api.py",
        "tests/security/test_typescript_consumer_docker_live.py",
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
        raise RuntimeError("TypeScript export proof requires a clean committed control tree")
    focused = _run(FOCUSED_COMMAND)
    live = _run(LIVE_COMMAND)
    official = _run(OFFICIAL_COMMAND) if run_official else None
    tree_stable = _git("rev-parse", "HEAD") == control["head"] and not _git(
        "status", "--porcelain=v1"
    )
    snapshot, accepted, stale = real_proof(REPRESENTATIVE)
    inventory = docker_inventory()
    surface = accepted.get("surface") or {}
    symbols = {item["qualified_name"] for item in surface.get("symbols", [])}
    expected_symbols = {"Node", "Node.childNodes", "Scene", "Scene.rootNode"}
    isolated = accepted.get("isolated_execution") or {}
    stale_isolated = stale.get("isolated_execution") or {}
    checks = {
        "focused_tests_pass": focused["exit_code"] == 0,
        "live_docker_tests_pass": live["exit_code"] == 0,
        "official_checks_pass": bool(official and official["exit_code"] == 0 and tree_stable),
        "real_revision_bound": snapshot["source_revision"] == snapshot["baseline_head"],
        "baseline_clean": snapshot["baseline_tree_clean"],
        "canonical_built_import": accepted["package"]["canonical_import"] == EXPECTED_IMPORT,
        "expected_public_symbols": expected_symbols <= symbols,
        "private_symbols_excluded": not any(
            part.startswith("_") for symbol in symbols for part in symbol.split(".")
        ),
        "built_consumer_accepted": (
            accepted["accepted"]
            and set(accepted["verified_symbols"]) == expected_symbols
            and not accepted["missing_symbols"]
            and not accepted["diagnostics"]
            and bool(accepted["built_artifact_sha256"])
        ),
        "stale_root_rejected": (
            not stale["accepted"]
            and "Scene" in stale["missing_symbols"]
            and any("cannot find module" in item.lower() for item in stale["diagnostics"])
        ),
        "compiler_pinned": accepted["toolchain"]["compiler_version"] == "5.8.3",
        "toolchain_archives_hashed": all(
            len(item["sha256"]) == 64 for item in accepted["toolchain"]["artifacts"]
        ),
        "network_denied": isolated.get("policy", {}).get("network_mode") == "none",
        "immutable_image": (
            isolated.get("image", {}).get("repo_digest") == immutable_image()
            and isolated.get("policy", {}).get("immutable_image") == immutable_image()
        ),
        "cleanup_complete": all(
            (result.get("cleanup") or {}).get("complete") for result in (isolated, stale_isolated)
        ),
        "no_managed_resources_remain": not any(inventory.values()),
    }
    failures = [name for name, passed in checks.items() if not passed]
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_redacted_json(EVIDENCE_DIR / "repository-snapshot.json", snapshot)
    write_redacted_json(EVIDENCE_DIR / "built-consumer-proof.json", accepted)
    write_redacted_json(EVIDENCE_DIR / "stale-root-rejection.json", stale)
    write_redacted_json(EVIDENCE_DIR / "public-api-surface.json", surface)
    write_redacted_json(EVIDENCE_DIR / "toolchain-lock.json", accepted["toolchain"])
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
            "adaptation_decision": (
                "use a pinned TypeScript compiler instead of the sibling regex extractor"
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
                "plans/investigations/evidence/level8-typescript-export-truth/verification.json",
                (
                    "plans/investigations/evidence/level8-typescript-export-truth/"
                    "built-consumer-proof.json"
                ),
                (
                    "plans/investigations/evidence/level8-typescript-export-truth/"
                    "stale-root-rejection.json"
                ),
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
        "build_typescript_export_truth_evidence.py --official --check\n",
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
        raise SystemExit("TypeScript export evidence failed: " + ", ".join(failures))
    print(f"wrote TypeScript export truth evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
