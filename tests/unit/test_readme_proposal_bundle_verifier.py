"""Negative controls for the independent README-proposal bundle verifier.

The verifier must reject tampered candidates/facts/operations/checksums, must
not be fooled by a producer's fake "accepted" review, and must reject a copied
or cross-pilot-leaking candidate. Each test copies the committed cells-java
bundle, tampers exactly one thing, and asserts rejection.
"""

import json
import shutil
from pathlib import Path

import pytest

from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.verification.readme_proposal_bundle import (
    verify_cross_pilot_specificity,
    verify_readme_proposal_bundle,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = (
    REPO_ROOT / "plans" / "investigations" / "evidence" / "level8-local-readme-proposals-2026-07-24"
)


def _refresh_artifact_checksums(bundle: Path) -> None:
    """Re-stamp artifact-sha256.json as an attacker who fixed the checksums would."""
    artifacts = {
        path.name: sha256_hex(path.read_bytes())
        for path in sorted(bundle.iterdir())
        if path.is_file() and path.name != "artifact-sha256.json"
    }
    (bundle / "artifact-sha256.json").write_text(
        json.dumps(artifacts, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


@pytest.fixture
def bundle(tmp_path) -> Path:
    dst = tmp_path / "cells-java"
    shutil.copytree(EVIDENCE / "cells-java", dst)
    return dst


class TestAcceptsUntampered:
    def test_untampered_bundle_verifies(self, bundle):
        verdict = verify_readme_proposal_bundle(bundle)
        assert verdict.verified, verdict.failures
        assert all(verdict.checks.values())


class TestRejectsTampering:
    def test_tampered_candidate_rejected_despite_refreshed_checksums_and_fake_review(self, bundle):
        candidate = bundle / "candidate-readme.md"
        candidate.write_text(
            candidate.read_text(encoding="utf-8") + "\nInjected line.\n",
            encoding="utf-8",
            newline="\n",
        )
        # Attacker also fixes the checksums and forges an "accepted" review.
        _refresh_artifact_checksums(bundle)
        (bundle / "independent-review.json").write_text(
            json.dumps({"reviewer": "x", "verdict": "accepted", "checks": {}}) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        verdict = verify_readme_proposal_bundle(bundle)
        assert not verdict.verified
        assert verdict.checks["independent_reconstruction_byte_identical"] is False
        assert verdict.checks["candidate_hash_matches_plan"] is False

    def test_tampered_checksum_rejected(self, bundle):
        hashes = json.loads((bundle / "artifact-sha256.json").read_text(encoding="utf-8"))
        hashes["original-readme.md"] = "0" * 64
        (bundle / "artifact-sha256.json").write_text(
            json.dumps(hashes, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        verdict = verify_readme_proposal_bundle(bundle)
        assert not verdict.verified
        assert verdict.checks["artifact_checksums_match"] is False

    def test_tampered_plan_operation_rejected(self, bundle):
        plan = json.loads((bundle / "readme-document-plan-v1.json").read_text(encoding="utf-8"))
        assert plan["operations"], "fixture must have at least one operation"
        plan["operations"][0]["replacement_text"] += "\nSMUGGLED\n"
        (bundle / "readme-document-plan-v1.json").write_text(
            json.dumps(plan, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        _refresh_artifact_checksums(bundle)
        verdict = verify_readme_proposal_bundle(bundle)
        assert not verdict.verified
        assert verdict.checks["reconstructed_plan_matches"] is False

    def test_tampered_fact_rejected(self, bundle):
        facts = json.loads((bundle / "product-facts-v2.json").read_text(encoding="utf-8"))
        audience_id = facts["selected_fact_ids"]["product.audience"]
        for fact in facts["facts"]:
            if fact["fact_id"] == audience_id:
                fact["value"] = ["TAMPERED audience claim."]
        (bundle / "product-facts-v2.json").write_text(
            json.dumps(facts, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        _refresh_artifact_checksums(bundle)
        verdict = verify_readme_proposal_bundle(bundle)
        assert not verdict.verified
        assert verdict.checks["facts_hash_matches_plan"] is False

    def test_copied_foreign_candidate_rejected(self, bundle):
        # Pass off the PDF pilot's candidate as this (cells) bundle's candidate.
        foreign = (EVIDENCE / "pdf-java" / "candidate-readme.md").read_text(encoding="utf-8")
        (bundle / "candidate-readme.md").write_text(foreign, encoding="utf-8", newline="\n")
        _refresh_artifact_checksums(bundle)
        verdict = verify_readme_proposal_bundle(bundle)
        assert not verdict.verified
        assert verdict.checks["independent_reconstruction_byte_identical"] is False

    def test_missing_artifact_rejected(self, bundle):
        (bundle / "proposal.patch").unlink()
        verdict = verify_readme_proposal_bundle(bundle)
        assert not verdict.verified
        assert verdict.checks["all_artifacts_present"] is False


class TestCrossPilotSpecificity:
    def _real_pilots(self):
        pilots = []
        for slug, org_repo in (
            ("cells-java", "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"),
            ("three-dimensional-java", "aspose-3d-foss/Aspose.3D-FOSS-for-Java"),
            ("pdf-java", "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java"),
        ):
            text = (EVIDENCE / slug / "candidate-readme.md").read_text(encoding="utf-8")
            pilots.append((org_repo, text))
        return pilots

    def test_accepts_distinct_real_candidates(self):
        verdict = verify_cross_pilot_specificity(self._real_pilots())
        assert verdict.verified, verdict.failures

    def test_rejects_duplicate_candidates(self):
        pilots = self._real_pilots()
        pilots[1] = (pilots[1][0], pilots[0][1])  # 3D "candidate" is a copy of cells'
        verdict = verify_cross_pilot_specificity(pilots)
        assert not verdict.verified
        assert verdict.checks["candidates_distinct"] is False

    def test_rejects_foreign_token_leak(self):
        pilots = self._real_pilots()
        cells_repo, cells_text = pilots[0]
        pilots[0] = (cells_repo, cells_text + "\nSee also Aspose.PDF.\n")
        verdict = verify_cross_pilot_specificity(pilots)
        assert not verdict.verified
        assert verdict.checks["no_cross_pilot_identity_leak"] is False

    def test_rejects_candidate_missing_own_identity(self):
        pilots = self._real_pilots()
        pilots[0] = (pilots[0][0], "Generic README with no product name.\n")
        verdict = verify_cross_pilot_specificity(pilots)
        assert not verdict.verified
        assert verdict.checks["each_candidate_has_own_identity"] is False
