# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: independent immutable-snapshot and product-facts evidence verifier
"""Independently validate a pilot snapshot/facts evidence bundle and its checksums."""

from __future__ import annotations

import hashlib
import json
import sys
from argparse import ArgumentParser
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent.facts.schema_v2 import ProductFactsV2  # noqa: E402
from readme_agent.repository_snapshot import RepositorySnapshotV1  # noqa: E402

EVIDENCE_ROOT = (REPO_ROOT / "plans" / "investigations" / "evidence").resolve()
SECRET_NAME_PARTS = ("TOKEN", "SECRET", "PASSWORD", "PASSWD", "PRIVATE_KEY", "API_KEY")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_checksum_inventory(evidence_dir: Path) -> list[str]:
    failures: list[str] = []
    inventory = evidence_dir / "sha256sums.txt"
    for line in inventory.read_text(encoding="utf-8").splitlines():
        expected, filename = line.split("  ", 1)
        path = evidence_dir / filename
        if not path.is_file():
            failures.append(f"checksum target missing: {filename}")
        elif _sha256(path) != expected:
            failures.append(f"checksum mismatch: {filename}")
    return failures


def _verify_pilot(pilot: dict) -> list[str]:
    failures: list[str] = []
    snapshot = RepositorySnapshotV1.model_validate(pilot["snapshot"])
    facts = ProductFactsV2.model_validate(pilot["product_facts_v2"])
    if facts.org_repo != snapshot.org_repo:
        failures.append(f"{snapshot.org_repo}: facts repository mismatch")
    if facts.canonical_hash() != pilot["product_facts_v2_hash"]:
        failures.append(f"{snapshot.org_repo}: facts hash mismatch")
    if not pilot["snapshot_matches_current_upstream"]:
        failures.append(f"{snapshot.org_repo}: snapshot is not current upstream")
    if not pilot["core_facts_accepted"]:
        failures.append(f"{snapshot.org_repo}: core facts were not accepted")

    for field_name, fact_id in facts.selected_fact_ids.items():
        fact = facts.fact_by_id(fact_id)
        source = fact.source
        if source.source_type == "readme_claim":
            failures.append(f"{snapshot.org_repo}: selected README claim for {field_name}")
        if source.source_revision not in {None, snapshot.source_revision}:
            failures.append(
                f"{snapshot.org_repo}: mixed revision {source.source_revision} for {field_name}"
            )
        if source.source_revision is None and source.retrieved_at is None:
            failures.append(f"{snapshot.org_repo}: provenance time missing for {field_name}")
        if fact.verification_state not in {"verified", "policy_approved"}:
            failures.append(f"{snapshot.org_repo}: {field_name} is {fact.verification_state}")

    local = pilot["local_product_verification"]
    if local["outcome"] != "SOURCE_BUILD_VERIFIED":
        failures.append(f"{snapshot.org_repo}: source build/example not verified")
    for result_name in ("build", "example_compile"):
        result = local.get(result_name)
        if result is None or result["return_code"] != 0:
            failures.append(f"{snapshot.org_repo}: {result_name} did not pass")
            continue
        inherited = {name.upper() for name in result["environment_names"]}
        leaked = sorted(
            name
            for name in inherited
            if any(secret_part in name for secret_part in SECRET_NAME_PARTS)
        )
        if leaked:
            failures.append(f"{snapshot.org_repo}: secret-like environment names: {leaked}")
    return failures


def _refresh_checksums(evidence_dir: Path) -> None:
    lines = [
        f"{_sha256(path)}  {path.name}"
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
    parser.add_argument("evidence_dir", type=Path)
    args = parser.parse_args()
    evidence_dir = args.evidence_dir.resolve()
    if evidence_dir.parent != EVIDENCE_ROOT or not evidence_dir.is_dir():
        raise RuntimeError(f"evidence_dir must be an existing child of {EVIDENCE_ROOT}")
    report_path = evidence_dir / "independent-factuality-review.json"
    if report_path.exists():
        raise RuntimeError(f"refusing to replace existing review: {report_path}")

    failures = _verify_checksum_inventory(evidence_dir)
    proof_path = evidence_dir / "immutable-snapshot-and-product-facts-proof.json"
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    if not proof.get("accepted"):
        failures.append("producer did not accept its own proof")
    for scenario in proof["historical_scenarios"]:
        if not scenario["verified"]:
            failures.append(f"historical scenario failed: {scenario['scenario_id']}")
    for pilot in proof["current_pilots"]:
        failures.extend(_verify_pilot(pilot))

    cells = next(
        pilot
        for pilot in proof["current_pilots"]
        if pilot["org_repo"] == "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    )
    if not cells["readme_claim_conflicts"]:
        failures.append("Cells false Maven claim was not rejected")
    if not any(
        result["outcome"] == "NOT_PUBLISHED" for result in cells["package_acquisition"]["results"]
    ):
        failures.append("Cells Maven Central NOT_PUBLISHED result is missing")

    report = {
        "schema_version": 1,
        "reviewed_at": datetime.now(UTC).isoformat(),
        "reviewer": "deterministic-independent-factuality-verifier",
        "verdict": "accepted" if not failures else "rejected",
        "failures": failures,
        "reviewed_proof_sha256": _sha256(proof_path),
        "pilot_count": len(proof["current_pilots"]),
        "historical_scenario_count": len(proof["historical_scenarios"]),
    }
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _refresh_checksums(evidence_dir)
    print(json.dumps(report, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
