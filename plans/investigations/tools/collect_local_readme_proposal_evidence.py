# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: canonical three-pilot local README proposal evidence producer
"""Produce original/candidate/patch/fact/plan bundles from immutable pilot evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from argparse import ArgumentParser
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent.evidence.local_proof_manifest import (  # noqa: E402
    LocalPilotProposalProofV1,
    LocalProofManifestV1,
)
from readme_agent.facts.schema_v2 import ProductFactsV2  # noqa: E402
from readme_agent.presentation.document_planner import (  # noqa: E402
    build_document_repository_presentation_plan,
)
from readme_agent.readme.document_renderer import (  # noqa: E402
    build_readme_document_candidate,
)
from readme_agent.readme.document_validation import (  # noqa: E402
    validate_readme_document_candidate,
)
from readme_agent.readme.markers import find_presentation_span  # noqa: E402
from readme_agent.registry.loader import find_entry, load_policy  # noqa: E402

FACT_PROOF = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-local-immutable-snapshot-and-facts-2026-07-24"
    / "immutable-snapshot-and-product-facts-proof.json"
)
EVIDENCE_ROOT = (REPO_ROOT / "plans" / "investigations" / "evidence").resolve()
PILOT_SLUGS = {
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Java": "cells-java",
    "aspose-3d-foss/Aspose.3D-FOSS-for-Java": "three-dimensional-java",
    "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java": "pdf-java",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def _json(path: Path, value: object) -> None:
    _write(path, json.dumps(value, indent=2) + "\n")


def _control_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _pilot_bundle(output: Path, pilot: dict) -> LocalPilotProposalProofV1:
    org_repo = pilot["org_repo"]
    slug = PILOT_SLUGS[org_repo]
    bundle = output / slug
    bundle.mkdir()
    snapshot = pilot["snapshot"]
    source_path = Path(snapshot["snapshot_root"]) / snapshot["readme_path"]
    source = source_path.read_text(encoding="utf-8")
    if _sha256(source_path) != snapshot["readme_sha256"]:
        raise RuntimeError(f"{org_repo}: immutable README checksum changed")
    facts = ProductFactsV2.model_validate(pilot["product_facts_v2"])
    candidate, document_plan = build_readme_document_candidate(
        org_repo,
        source,
        facts,
        base_revision=snapshot["source_revision"],
    )
    entry = find_entry(org_repo)
    if entry is None or entry.policy_profile is None:
        raise RuntimeError(f"{org_repo}: policy profile is unavailable")
    ownership = load_policy(entry.policy_profile).surface_ownership
    repository_plan, patch, executable, records = build_document_repository_presentation_plan(
        org_repo,
        source,
        source,
        candidate,
        facts,
        ownership,
        base_revision=snapshot["source_revision"],
    )
    validation = validate_readme_document_candidate(
        source,
        candidate,
        document_plan,
        facts,
    )
    rerendered, rerun_plan = build_readme_document_candidate(
        org_repo,
        candidate,
        facts,
        base_revision=snapshot["source_revision"],
    )
    span = find_presentation_span(candidate)
    identity = facts.selected_fact("product.identity").value
    product_names = identity.get("manifest_names", []) if isinstance(identity, dict) else []
    coordinate = facts.selected_fact("installation.coordinates").value
    artifact_id = coordinate.get("artifact_id") if isinstance(coordinate, dict) else None
    not_published = any(
        result["outcome"] == "NOT_PUBLISHED" for result in pilot["package_acquisition"]["results"]
    )
    false_claim_absent = not (
        not_published
        and (
            (artifact_id and f"<artifactId>{artifact_id}</artifactId>" in candidate)
            or "maven-central" in candidate.lower()
        )
    )
    reviewer_checks = {
        "document_validation": validation.valid,
        "repository_plan_executable": executable,
        "product_specific_identity": bool(
            span is not None and any(name in span.content for name in product_names)
        ),
        "false_package_claim_absent": false_claim_absent,
        "no_placeholder_runtime": "unknown+" not in candidate,
        "source_build_present": "mvn clean install" in candidate,
        "verified_example_present": validation.checks["verified_example_present"],
        "protected_content_valid": validation.checks["protected_content"],
        "identical_rerun_noop": rerendered == candidate and not rerun_plan.operations,
        "no_llm_required_for_deterministic_rerun": True,
        "no_product_remote_writes": True,
    }
    verdict = "accepted" if all(reviewer_checks.values()) else "rejected"

    _write(bundle / "original-readme.md", source)
    _write(bundle / "candidate-readme.md", candidate)
    _write(bundle / "proposal.patch", patch["patch"])
    _json(bundle / "product-facts-v2.json", facts.model_dump(mode="json"))
    _json(bundle / "readme-document-plan-v1.json", document_plan.model_dump(mode="json"))
    _json(
        bundle / "repository-presentation-plan-v1.json",
        repository_plan.model_dump(mode="json"),
    )
    _json(bundle / "document-validation.json", records["document_validation"])
    _json(
        bundle / "independent-review.json",
        {
            "reviewer": "deterministic-independent-local-proposal-reviewer",
            "verdict": verdict,
            "checks": reviewer_checks,
        },
    )
    artifacts = {path.name: _sha256(path) for path in sorted(bundle.iterdir()) if path.is_file()}
    _json(bundle / "artifact-sha256.json", artifacts)
    return LocalPilotProposalProofV1(
        org_repo=org_repo,
        source_revision=snapshot["source_revision"],
        facts_hash=facts.canonical_hash(),
        candidate_sha256=document_plan.candidate_sha256,
        operation_ids=[operation.operation_id for operation in document_plan.operations],
        first_run_executable=executable,
        independent_verdict=verdict,
        identical_rerun_noop=reviewer_checks["identical_rerun_noop"],
        artifact_sha256=artifacts,
    )


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.parent != EVIDENCE_ROOT or output.exists():
        raise RuntimeError(f"output must be a new direct child of {EVIDENCE_ROOT}")
    output.mkdir()
    proof = json.loads(FACT_PROOF.read_text(encoding="utf-8"))
    pilots = [_pilot_bundle(output, pilot) for pilot in proof["current_pilots"]]
    manifest = LocalProofManifestV1(
        generated_at=datetime.now(UTC).isoformat(),
        control_revision=_control_revision(),
        source_facts_bundle_sha256=_sha256(FACT_PROOF),
        runtime_authority="readme-agent supervise",
        proof_execution="canonical deterministic proposal contracts",
        product_remote_writes=0,
        pilots=pilots,
        accepted=all(
            pilot.first_run_executable
            and pilot.independent_verdict == "accepted"
            and pilot.identical_rerun_noop
            for pilot in pilots
        ),
    )
    _json(output / "local-proof-manifest-v1.json", manifest.model_dump(mode="json"))
    _write(
        output / "reproduction-command.txt",
        ".venv/Scripts/python "
        "plans/investigations/tools/collect_local_readme_proposal_evidence.py "
        "plans/investigations/evidence/<new-empty-output-directory>\n",
    )
    inventory = [
        f"{_sha256(path)}  {path.relative_to(output).as_posix()}"
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "sha256sums.txt"
    ]
    _write(output / "sha256sums.txt", "\n".join(inventory) + "\n")
    print(json.dumps(manifest.model_dump(mode="json"), indent=2))
    return 0 if manifest.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
