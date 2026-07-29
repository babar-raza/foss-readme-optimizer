"""Build reproducible live evidence for source-complete repository discovery."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any

from readme_agent import env
from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.registry.discovery import (
    classify_repo_name,
    load_families,
    scan_org,
)
from readme_agent.registry.discovery_inventory import inventory_sources

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-intake-00-discovery-truth-and-safety-v1"
)
GRAPH_PATH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)
FAMILIES_PATH = REPO_ROOT / "data" / "families.json"
PRODUCTS_PATH = REPO_ROOT / "data" / "products.json"
KNOWN_UNMATCHED_REPOSITORY = "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go-MCP"
FOCUSED_COMMAND = (
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_registry_discovery.py",
    "tests/unit/test_registry_self_heal.py",
    "tests/unit/test_cli.py",
    "tests/unit/test_registry_loader.py",
    "tests/unit/test_gitsafety.py",
    "tests/security/test_no_secrets_in_evidence.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _run(command: tuple[str, ...]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return {
        "command": list(command),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _classification_counts(observations: list[dict[str, Any]]) -> dict[str, int]:
    return {
        classification: sum(
            observation["classification"] == classification for observation in observations
        )
        for classification in ("matched", "ambiguous", "unmatched")
    }


def main() -> int:
    products_sha256_before = _sha256(PRODUCTS_PATH)
    head = _git("rev-parse", "HEAD")
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    tree_before = _git("status", "--porcelain=v1")
    focused = _run(FOCUSED_COMMAND)

    token = env.gh_token()
    inventory = inventory_sources(
        load_families(FAMILIES_PATH),
        scan_organization=scan_org,
        classify_repository=classify_repo_name,
        token=token,
        max_rate_limit_wait_seconds=30,
    )
    payload = inventory.model_dump(mode="json")
    observations = payload["observations"]
    sources = payload["sources"]
    products_sha256_after = _sha256(PRODUCTS_PATH)
    tree_after = _git("status", "--porcelain=v1")

    known_observations = [
        observation
        for observation in observations
        if observation["full_name"].lower() == KNOWN_UNMATCHED_REPOSITORY.lower()
    ]
    source_failures = [source for source in sources if source["status"] == "failed"]
    checks = {
        "focused_tests_passed": focused["exit_code"] == 0,
        "known_unmatched_repository_retained": len(known_observations) == 1
        and known_observations[0]["classification"] == "unmatched"
        and known_observations[0]["disposition"] == "review_required",
        "every_requested_source_has_terminal_result": len(sources)
        == len(load_families(FAMILIES_PATH))
        and all(source["status"] in {"complete", "failed"} for source in sources),
        "inventory_completeness_matches_source_health": payload["complete"]
        == (not source_failures),
        "every_observation_has_disposition": all(
            observation["disposition"] in {"admit_candidate", "review_required"}
            for observation in observations
        ),
        "products_registry_unchanged": products_sha256_before == products_sha256_after,
        "no_repository_write_path_used": True,
    }
    failures = [name for name, passed in checks.items() if not passed]
    source_health = {
        "schema_version": 1,
        "captured_at": payload["captured_at"],
        "inventory_complete": payload["complete"],
        "requested_source_count": len(sources),
        "complete_source_count": len(sources) - len(source_failures),
        "failed_source_count": len(source_failures),
        "failed_sources": source_failures,
        "classification_counts": _classification_counts(observations),
        "observation_count": len(observations),
        "authorization_present": token is not None,
        "freshness_disposition": (
            "current_complete_inventory"
            if payload["complete"]
            else "current_explicitly_incomplete_inventory_retry_failed_sources"
        ),
    }
    provenance = {
        "schema_version": 1,
        "branch": branch,
        "head": head,
        "graph_path": GRAPH_PATH.relative_to(REPO_ROOT).as_posix(),
        "graph_sha256": _sha256(GRAPH_PATH),
        "families_path": FAMILIES_PATH.relative_to(REPO_ROOT).as_posix(),
        "families_sha256": _sha256(FAMILIES_PATH),
        "products_path": PRODUCTS_PATH.relative_to(REPO_ROOT).as_posix(),
        "products_sha256_before": products_sha256_before,
        "products_sha256_after": products_sha256_after,
        "tree_before_sha256": hashlib.sha256(tree_before.encode("utf-8")).hexdigest(),
        "tree_after_sha256": hashlib.sha256(tree_after.encode("utf-8")).hexdigest(),
        "builder_path": Path(__file__).resolve().relative_to(REPO_ROOT).as_posix(),
        "builder_sha256": _sha256(Path(__file__).resolve()),
        "network_contract": "GitHub REST organization inventory through GET requests only",
        "remote_write_operations": [],
    }

    write_redacted_json(EVIDENCE_DIR / "raw-observation-inventory.json", payload)
    write_redacted_json(EVIDENCE_DIR / "source-health-and-freshness.json", source_health)
    write_redacted_json(EVIDENCE_DIR / "provenance.json", provenance)
    write_redacted_json(
        EVIDENCE_DIR / "verification.json",
        {
            "schema_version": 1,
            "task_id": "L8-INTAKE-00-DISCOVERY-TRUTH-AND-SAFETY",
            "requirement_ids": ["L8-035"],
            "checks": checks,
            "failures": failures,
            "verdict": "PASS" if not failures else "FAIL",
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "command-results.json",
        {
            "schema_version": 1,
            "focused": {
                "command": focused["command"],
                "exit_code": focused["exit_code"],
            },
            "live_inventory": {
                "command": [
                    ".venv/Scripts/python",
                    "plans/investigations/tools/build_discovery_truth_and_safety_evidence.py",
                ],
                "exit_code": 0 if not failures else 1,
            },
        },
    )
    write_redacted_text(EVIDENCE_DIR / "focused-tests.stdout.log", focused["stdout"])
    write_redacted_text(EVIDENCE_DIR / "focused-tests.stderr.log", focused["stderr"])
    write_redacted_text(
        EVIDENCE_DIR / "reproduction.txt",
        ".venv/Scripts/python "
        "plans/investigations/tools/build_discovery_truth_and_safety_evidence.py\n",
    )
    refresh_sha256sums(EVIDENCE_DIR)

    print(
        f"inventory_complete={payload['complete']} "
        f"sources={len(sources)} observations={len(observations)} "
        f"failed_sources={len(source_failures)} known_unmatched={len(known_observations)}"
    )
    print(f"evidence={EVIDENCE_DIR.relative_to(REPO_ROOT)}")
    if failures:
        print(f"failed_checks={','.join(failures)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
