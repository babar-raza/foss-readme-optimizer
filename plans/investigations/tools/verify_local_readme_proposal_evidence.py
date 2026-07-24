# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: independent local README-proposal evidence verifier
"""Independently verify a finished README-proposal evidence directory.

Consumes a producer's evidence directory (per-pilot bundles + top-level
sha256sums.txt) and re-derives every claim from scratch via the production
verification seam, then writes its own verdict under a reviewer identity
distinct from the producer (VER-001). It never trusts the producer's
per-pilot independent-review.json or manifest.
"""

from __future__ import annotations

import hashlib
import json
import sys
from argparse import ArgumentParser
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent.verification.readme_proposal_bundle import (  # noqa: E402
    VERIFIER_IDENTITY,
    verify_cross_pilot_specificity,
    verify_readme_proposal_bundle,
)

EVIDENCE_ROOT = (REPO_ROOT / "plans" / "investigations" / "evidence").resolve()
SECRET_NAME_PARTS = ("TOKEN", "SECRET", "PASSWORD", "PASSWD", "PRIVATE_KEY", "API_KEY")
REVIEW_NAME = "independent-readme-proposal-review.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_checksum_inventory(evidence_dir: Path) -> list[str]:
    failures: list[str] = []
    inventory = evidence_dir / "sha256sums.txt"
    if not inventory.is_file():
        return ["sha256sums.txt is missing"]
    for line in inventory.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, filename = line.split("  ", 1)
        path = evidence_dir / filename
        if not path.is_file():
            failures.append(f"checksum target missing: {filename}")
        elif _sha256(path) != expected:
            failures.append(f"checksum mismatch: {filename}")
    return failures


def _secret_name_scan(evidence_dir: Path) -> list[str]:
    return [
        f"secret-like artifact name: {path.relative_to(evidence_dir).as_posix()}"
        for path in sorted(evidence_dir.rglob("*"))
        if path.is_file() and any(part in path.name.upper() for part in SECRET_NAME_PARTS)
    ]


def _refresh_checksums(evidence_dir: Path) -> None:
    inventory = [
        f"{_sha256(path)}  {path.relative_to(evidence_dir).as_posix()}"
        for path in sorted(evidence_dir.rglob("*"))
        if path.is_file() and path.name != "sha256sums.txt"
    ]
    (evidence_dir / "sha256sums.txt").write_text(
        "\n".join(inventory) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("evidence_dir", type=Path)
    args = parser.parse_args()
    evidence_dir = args.evidence_dir.resolve()
    if evidence_dir.parent != EVIDENCE_ROOT or not evidence_dir.is_dir():
        raise RuntimeError(f"evidence_dir must be an existing child of {EVIDENCE_ROOT}")
    report_path = evidence_dir / REVIEW_NAME
    if report_path.exists():
        raise RuntimeError(f"refusing to replace existing review: {report_path}")

    failures = _verify_checksum_inventory(evidence_dir)
    failures.extend(_secret_name_scan(evidence_dir))

    pilot_dirs = sorted(
        path
        for path in evidence_dir.iterdir()
        if path.is_dir() and (path / "readme-document-plan-v1.json").is_file()
    )
    if not pilot_dirs:
        failures.append("no pilot bundles found")

    bundle_reports: list[dict] = []
    pilots_for_cross: list[tuple[str, str]] = []
    for bundle_dir in pilot_dirs:
        verdict = verify_readme_proposal_bundle(bundle_dir)
        bundle_reports.append({"slug": bundle_dir.name, **verdict.model_dump(mode="json")})
        failures.extend(verdict.failures)
        pilots_for_cross.append(
            (verdict.org_repo, (bundle_dir / "candidate-readme.md").read_text(encoding="utf-8"))
        )

    cross = verify_cross_pilot_specificity(pilots_for_cross)
    failures.extend(cross.failures)

    report = {
        "schema_version": 1,
        "reviewed_at": datetime.now(UTC).isoformat(),
        "reviewer": VERIFIER_IDENTITY,
        "verdict": "accepted" if not failures else "rejected",
        "failures": failures,
        "pilot_count": len(pilot_dirs),
        "bundle_reports": bundle_reports,
        "cross_pilot": cross.model_dump(mode="json"),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    _refresh_checksums(evidence_dir)
    print(json.dumps(report, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
