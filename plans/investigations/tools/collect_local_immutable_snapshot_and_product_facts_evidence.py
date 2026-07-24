# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: immutable-snapshot and pilot ProductFactsV2 acceptance-evidence producer
"""Prove current and checksum-addressed historical pilot truth without product writes."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from argparse import ArgumentParser
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent import paths  # noqa: E402
from readme_agent.capabilities.verify_package_acquisition import (  # noqa: E402
    execute as verify_acquisition,
)
from readme_agent.facts.provider import collect_product_facts  # noqa: E402
from readme_agent.facts.schema import ProductFactsV1  # noqa: E402
from readme_agent.facts.schema_v2 import ProductFactsV2  # noqa: E402
from readme_agent.gitsafety.clone import clone_baseline, remote_head_sha  # noqa: E402
from readme_agent.readme.claim_verification import find_claim_conflicts  # noqa: E402
from readme_agent.registry.loader import require_listed  # noqa: E402
from readme_agent.repository_snapshot import (  # noqa: E402
    capture_repository_snapshot,
    repository_snapshot_scope,
    verify_repository_snapshot,
)

DEFAULT_EVIDENCE_DIR = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-local-immutable-snapshot-and-facts-2026-07-24"
)
SCENARIO_MANIFEST = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "repository_scenarios"
    / "level8-local-idea-fidelity-pilots.json"
)
CORE_FIELDS = (
    "product.identity",
    "product.audience",
    "product.problems_solved",
    "product.capabilities",
    "product.formats",
    "product.platforms",
    "installation.coordinates",
    "installation.verified_acquisition",
    "example.minimal",
    "documentation.links",
    "release.state",
    "product.limitations",
    "product.compatibility",
    "product.license",
    "support.routes",
    "relationship.commercial_foss",
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git(root: Path, *args: str, binary: bool = False):
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=not binary,
        encoding=None if binary else "utf-8",
        errors=None if binary else "replace",
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace") if binary else result.stderr
        raise RuntimeError(f"git {' '.join(args)} failed for {root}: {stderr}")
    return result.stdout


def _prepare_evidence_dir(evidence_dir: Path) -> None:
    governed_root = (REPO_ROOT / "plans" / "investigations" / "evidence").resolve()
    if evidence_dir.parent != governed_root or not evidence_dir.name.startswith(
        "level8-local-immutable-snapshot-and-facts-"
    ):
        raise RuntimeError(f"evidence output must be a named child of {governed_root}")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    existing = list(evidence_dir.iterdir())
    if existing:
        raise RuntimeError(f"refusing to replace non-empty evidence directory: {evidence_dir}")


def _verify_historical_scenario(scenario: dict, baseline: Path) -> dict:
    revision = scenario["source_revision"]
    present = subprocess.run(
        ["git", "-C", str(baseline), "cat-file", "-e", f"{revision}^{{commit}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
        check=False,
    )
    if present.returncode != 0:
        _git(baseline, "fetch", "--depth", "1", "origin", revision)
    readme = _git(baseline, "show", f"{revision}:README.md", binary=True)
    blob = str(_git(baseline, "rev-parse", f"{revision}:README.md")).strip()
    actual_sha = _sha256_bytes(readme)
    return {
        **scenario,
        "actual_readme_git_blob": blob,
        "actual_readme_sha256": actual_sha,
        "readme_bytes": len(readme),
        "verified": (
            blob == scenario["readme_git_blob"] and actual_sha == scenario["readme_sha256"]
        ),
    }


def _pilot_proof(org_repo: str, java_home: Path | None) -> dict:
    entry = require_listed(org_repo)
    baseline = clone_baseline(entry, paths.baseline_dir(entry.org, entry.repo_name))
    snapshot = capture_repository_snapshot(entry, baseline)
    previous_java_home = os.environ.get("README_AGENT_JAVA_HOME")
    if java_home is not None:
        os.environ["README_AGENT_JAVA_HOME"] = str(java_home)
    try:
        with repository_snapshot_scope(
            snapshot,
            allow_local_fact_verification=True,
        ):
            facts_result = collect_product_facts(org_repo)
            acquisition = verify_acquisition(org_repo)
            readme = (
                (snapshot.root_path / snapshot.readme_path).read_text(
                    encoding="utf-8",
                    errors="replace",
                )
                if snapshot.readme_path is not None
                else ""
            )
        verify_repository_snapshot(snapshot)
    finally:
        if previous_java_home is None:
            os.environ.pop("README_AGENT_JAVA_HOME", None)
        else:
            os.environ["README_AGENT_JAVA_HOME"] = previous_java_home

    facts = ProductFactsV2.model_validate(facts_result["product_facts_v2"])
    facts_v1 = ProductFactsV1.from_capability_results(
        facts_result,
        acquisition_results=acquisition["results"],
    )
    conflicts = [
        {
            "coordinate": finding.claimed_coordinate,
            "outcome": finding.verification_outcome,
            "detail": finding.verification_detail,
        }
        for finding in find_claim_conflicts(readme, facts_v1)
    ]
    states = {field: facts.selected_fact(field).verification_state for field in CORE_FIELDS}
    upstream = remote_head_sha(entry.clone_url)
    return {
        "org_repo": org_repo,
        "snapshot": snapshot.model_dump(mode="json"),
        "current_upstream_revision": upstream,
        "snapshot_matches_current_upstream": upstream == snapshot.source_revision,
        "product_facts_v2": facts.model_dump(mode="json"),
        "product_facts_v2_hash": facts.canonical_hash(),
        "selected_fact_states": states,
        "local_product_verification": facts_result["local_product_verification"],
        "package_acquisition": acquisition,
        "readme_claim_conflicts": conflicts,
        "core_facts_accepted": all(
            state in {"verified", "policy_approved"} for state in states.values()
        ),
    }


def _write_checksums(evidence_dir: Path) -> None:
    lines = [
        f"{_sha256_bytes(path.read_bytes())}  {path.name}"
        for path in sorted(evidence_dir.iterdir())
        if path.is_file() and path.name != "sha256sums.txt"
    ]
    (evidence_dir / "sha256sums.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--java-home", type=Path)
    args = parser.parse_args()
    evidence_dir = args.evidence_dir.resolve()
    java_home = args.java_home.resolve() if args.java_home else None
    if java_home is not None and not (java_home / "bin" / "javac.exe").is_file():
        raise RuntimeError(f"--java-home does not contain bin/javac.exe: {java_home}")
    _prepare_evidence_dir(evidence_dir)

    scenarios = json.loads(SCENARIO_MANIFEST.read_text(encoding="utf-8"))["scenarios"]
    pilots: list[dict] = []
    historical: list[dict] = []
    for scenario in scenarios:
        org_repo = scenario["org_repo"]
        pilots.append(_pilot_proof(org_repo, java_home))
        entry = require_listed(org_repo)
        baseline = paths.baseline_dir(entry.org, entry.repo_name)
        historical.append(_verify_historical_scenario(scenario, baseline))

    cells = next(
        proof
        for proof in pilots
        if proof["org_repo"] == "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    )
    # Corrected 2026-07-24: the prior acceptance gate REQUIRED cells' Maven package to
    # resolve NOT_PUBLISHED and its README claim to be flagged conflicting. That premise was
    # itself wrong -- org.aspose:aspose-cells-foss IS published on Maven Central; the old
    # search.maven.org Solr endpoint just never indexed the org.aspose group. With the fixed
    # resolver (repo1.maven.org), the correct, honest outcome is REGISTRY_VERIFIED and an
    # EMPTY conflict list -- the opposite assertion. See
    # plans/investigations/evidence/package-acquisition-ground-truth-2026-07-24/.
    accepted = (
        all(item["verified"] for item in historical)
        and all(item["snapshot_matches_current_upstream"] for item in pilots)
        and all(item["core_facts_accepted"] for item in pilots)
        and any(
            item["outcome"] == "REGISTRY_VERIFIED"
            for item in cells["package_acquisition"]["results"]
        )
        and not cells["readme_claim_conflicts"]
    )
    proof = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "task_id": "L8-LOCAL-IMMUTABLE-SNAPSHOT-AND-FACTS",
        "accepted": accepted,
        "historical_scenarios": historical,
        "current_pilots": pilots,
    }
    (evidence_dir / "immutable-snapshot-and-product-facts-proof.json").write_text(
        json.dumps(proof, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    reproduction = (
        ".venv/Scripts/python "
        "plans/investigations/tools/"
        "collect_local_immutable_snapshot_and_product_facts_evidence.py "
        "--evidence-dir <new-empty-evidence-directory> --java-home <jdk-21-home>\n"
    )
    (evidence_dir / "reproduction-command.txt").write_text(
        reproduction,
        encoding="utf-8",
        newline="\n",
    )
    _write_checksums(evidence_dir)
    print(json.dumps({"evidence_dir": str(evidence_dir), "accepted": accepted}, indent=2))
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
