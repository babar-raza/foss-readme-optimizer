"""Negative controls for the independent README-proposal bundle verifier.

The verifier must reject tampered candidates/facts/operations/checksums, must
not be fooled by a producer's fake "accepted" review, and must reject a copied
or cross-pilot-leaking candidate. Each test copies the committed cells-java
bundle, tampers exactly one thing, and asserts rejection.

The live-registry acquisition ground-truth check (`_verify_acquisition_ground_
truth`) is mocked out (always passes) for all tests in this file EXCEPT
`TestAcquisitionGroundTruth`, which tests it directly with mocked resolver
results -- keeping the tampering tests offline/deterministic and focused on
what they actually test.
"""

import json
import shutil
from pathlib import Path

import pytest

from readme_agent.capabilities import registry as capability_registry
from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION
from readme_agent.ecosystems.resolver import ResolutionResult
from readme_agent.evidence.writer import write_readme_proposal_bundle
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.document_planner import (
    build_document_repository_presentation_plan,
)
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.registry.loader import load_policy, require_listed
from readme_agent.verification import readme_proposal_bundle as bundle_verifier
from readme_agent.verification.readme_proposal_bundle import (
    verify_cross_pilot_specificity,
    verify_readme_proposal_bundle,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
# Corrected 2026-07-24: repointed from level8-local-readme-proposals-2026-07-24/, whose candidates
# were rendered from pre-resolver-fix facts (see that bundle's own SUPERSEDED.md).
EVIDENCE = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-local-readme-proposals-corrected-acquisition-2026-07-24"
)


@pytest.fixture(autouse=True)
def _mock_acquisition_ground_truth_passes(request, monkeypatch):
    """Tests in this file (other than TestAcquisitionGroundTruth, which tests
    this exact function directly) verify candidate/fact/plan/checksum
    tampering, not live acquisition truth -- mocked to always pass so they
    stay offline and focused."""
    if request.cls is TestAcquisitionGroundTruth:
        return
    monkeypatch.setattr(
        bundle_verifier, "_verify_acquisition_ground_truth", lambda org_repo, facts: (True, "")
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
    original = "# Aspose.Cells FOSS for Java\n\nOpen-source spreadsheet processing for Java.\n"
    (dst / "original-readme.md").write_text(original, encoding="utf-8", newline="\n")
    facts = ProductFactsV2.model_validate(
        json.loads((dst / "product-facts-v2.json").read_text(encoding="utf-8"))
    )
    archived_plan = json.loads((dst / "readme-document-plan-v1.json").read_text(encoding="utf-8"))
    revision = archived_plan["immutable_base_revision"]
    candidate, _document_plan = build_readme_document_candidate(
        facts.org_repo,
        original,
        facts,
        base_revision=revision,
    )
    entry = require_listed(facts.org_repo)
    assert entry.policy_profile is not None
    presentation_plan, patch, executable, records = build_document_repository_presentation_plan(
        facts.org_repo,
        original,
        original,
        candidate,
        facts,
        load_policy(entry.policy_profile).surface_ownership,
        base_revision=revision,
    )
    assert executable
    write_readme_proposal_bundle(
        dst,
        original_readme=original,
        immutable_source_readme=original,
        candidate_readme=candidate,
        patch_text=patch["patch"],
        product_facts_v2=facts.model_dump(mode="json"),
        readme_assessment_v1=records["readme_assessment"],
        readme_document_plan_v1=records["readme_document_plan"],
        claim_map_v1=records["claim_map"],
        repository_presentation_plan_v1=presentation_plan.model_dump(mode="json"),
        document_validation=records["document_validation"],
    )
    return dst


class TestAcceptsUntampered:
    def test_untampered_bundle_verifies(self, bundle):
        verdict = verify_readme_proposal_bundle(bundle)
        assert verdict.verified, verdict.failures
        assert all(verdict.checks.values())

    def test_work_clone_preimage_may_differ_from_immutable_source(self, bundle):
        immutable_source = (bundle / "immutable-source-readme.md").read_text(encoding="utf-8")
        candidate = (bundle / "candidate-readme.md").read_text(encoding="utf-8")
        facts = ProductFactsV2.model_validate_json(
            (bundle / "product-facts-v2.json").read_text(encoding="utf-8")
        )
        revision = json.loads(
            (bundle / "readme-document-plan-v1.json").read_text(encoding="utf-8")
        )["immutable_base_revision"]
        current_work = immutable_source + "\n<!-- stale work-clone-only state -->\n"
        entry = require_listed(facts.org_repo)
        assert entry.policy_profile is not None
        presentation_plan, patch, executable, records = build_document_repository_presentation_plan(
            facts.org_repo,
            immutable_source,
            current_work,
            candidate,
            facts,
            load_policy(entry.policy_profile).surface_ownership,
            base_revision=revision,
        )
        assert executable
        write_readme_proposal_bundle(
            bundle,
            original_readme=current_work,
            immutable_source_readme=immutable_source,
            candidate_readme=candidate,
            patch_text=patch["patch"],
            product_facts_v2=facts.model_dump(mode="json"),
            readme_assessment_v1=records["readme_assessment"],
            readme_document_plan_v1=records["readme_document_plan"],
            claim_map_v1=records["claim_map"],
            repository_presentation_plan_v1=presentation_plan.model_dump(mode="json"),
            document_validation=records["document_validation"],
        )

        verdict = verify_readme_proposal_bundle(bundle)

        assert verdict.verified, verdict.failures
        assert verdict.checks["source_hash_matches_plan"]
        assert verdict.checks["native_git_apply_produces_candidate"]


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

    def test_tampered_agentic_plan_is_schema_checked(self, bundle):
        plan_path = bundle / "agentic-composition-plan-v1.json"
        plan_path.write_text('{"schema_version": 1, "unexpected": true}\n', encoding="utf-8")
        _refresh_artifact_checksums(bundle)
        verdict = verify_readme_proposal_bundle(bundle)
        assert not verdict.verified
        assert verdict.checks["schemas_valid"] is False

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


class _FakeFact:
    def __init__(self, value):
        self.value = value


class _FakeFacts:
    """Duck-typed stand-in for ProductFactsV2 -- `_verify_acquisition_ground_truth`
    only ever calls `.selected_fact("installation.verified_acquisition")`."""

    def __init__(self, method):
        self._method = method

    def selected_fact(self, field):
        assert field == "installation.verified_acquisition"
        return _FakeFact({"method": self._method})


def _fake_entry(family="cells", ecosystem="java"):
    from types import SimpleNamespace

    return SimpleNamespace(
        family=family,
        ecosystem=ecosystem,
        org="aspose-cells-foss",
        repo_name="Aspose.Cells-FOSS-for-Java",
    )


class TestAcquisitionGroundTruth:
    """Direct tests of `_verify_acquisition_ground_truth` -- the check that would
    have caught this session's own bug: a candidate whose facts say source_build
    for a package that IS actually published, or the reverse."""

    def test_registry_verified_and_recorded_registry_method_accepts(self, monkeypatch):
        monkeypatch.setattr(bundle_verifier, "require_listed", lambda org_repo: _fake_entry())
        monkeypatch.setattr(
            bundle_verifier, "resolve", lambda eco, coord: ResolutionResult(True, "found")
        )
        ok, detail = bundle_verifier._verify_acquisition_ground_truth(
            "aspose-cells-foss/Aspose.Cells-FOSS-for-Java", _FakeFacts("maven_central")
        )
        assert ok, detail

    def test_not_published_and_recorded_source_build_accepts(self, monkeypatch):
        monkeypatch.setattr(bundle_verifier, "require_listed", lambda org_repo: _fake_entry())
        monkeypatch.setattr(
            bundle_verifier, "resolve", lambda eco, coord: ResolutionResult(False, "not found")
        )
        ok, detail = bundle_verifier._verify_acquisition_ground_truth(
            "aspose-cells-foss/Aspose.Cells-FOSS-for-Java", _FakeFacts("source_build")
        )
        assert ok, detail

    def test_published_but_recorded_source_build_rejects(self, monkeypatch):
        """The exact bug this session found: a package IS published, but the
        bundle's facts still say source_build -- the install was wrongly stripped."""
        monkeypatch.setattr(bundle_verifier, "require_listed", lambda org_repo: _fake_entry())
        monkeypatch.setattr(
            bundle_verifier, "resolve", lambda eco, coord: ResolutionResult(True, "found")
        )
        ok, detail = bundle_verifier._verify_acquisition_ground_truth(
            "aspose-cells-foss/Aspose.Cells-FOSS-for-Java", _FakeFacts("source_build")
        )
        assert not ok
        assert "wrongly stripped" in detail

    def test_not_published_but_recorded_registry_method_rejects(self, monkeypatch):
        """The opposite error: a package is NOT published, but the bundle's facts
        assert a registry install anyway -- a fabricated claim."""
        monkeypatch.setattr(bundle_verifier, "require_listed", lambda org_repo: _fake_entry())
        monkeypatch.setattr(
            bundle_verifier, "resolve", lambda eco, coord: ResolutionResult(False, "not found")
        )
        ok, detail = bundle_verifier._verify_acquisition_ground_truth(
            "aspose-cells-foss/Aspose.Cells-FOSS-for-Java", _FakeFacts("maven_central")
        )
        assert not ok
        assert "cannot be verified" in detail

    def test_blocked_network_is_inconclusive_not_a_failure(self, monkeypatch):
        monkeypatch.setattr(bundle_verifier, "require_listed", lambda org_repo: _fake_entry())
        monkeypatch.setattr(
            bundle_verifier,
            "resolve",
            lambda eco, coord: ResolutionResult(False, "network error", blocked=True),
        )
        ok, detail = bundle_verifier._verify_acquisition_ground_truth(
            "aspose-cells-foss/Aspose.Cells-FOSS-for-Java", _FakeFacts("source_build")
        )
        assert ok
        assert "blocked" in detail

    def test_unlisted_org_repo_rejects(self, monkeypatch):
        def raise_not_listed(org_repo):
            raise ValueError("not listed")

        monkeypatch.setattr(bundle_verifier, "require_listed", raise_not_listed)
        ok, detail = bundle_verifier._verify_acquisition_ground_truth(
            "not/listed", _FakeFacts("source_build")
        )
        assert not ok

    def test_no_ecosystem_configured_is_not_applicable(self, monkeypatch):
        monkeypatch.setattr(
            bundle_verifier, "require_listed", lambda org_repo: _fake_entry(ecosystem=None)
        )
        ok, detail = bundle_verifier._verify_acquisition_ground_truth(
            "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp", _FakeFacts("source_build")
        )
        assert ok


class TestCapabilityRegistration:
    """RPOC-050/051/052: `verify_readme_proposal_bundle`/`verify_cross_pilot_
    specificity` are now real, registered capabilities
    (`capabilities/verify_readme_proposal_bundle.py`/`capabilities/verify_
    cross_pilot_specificity.py`), dispatchable via `dispatch_tool_call()`
    like every other capability in this project -- not just importable, bare
    functions. This is what actually closes `check_verifiers_are_wired.py`'s
    own finding against these two functions; the tests below exercise the
    real dispatch path end to end, against the same real fixture bundles the
    tests above already use directly."""

    _PERMISSIONS = {"read_only_local", "read_only_network"}

    def test_verify_readme_proposal_bundle_is_registered_with_a_real_manifest(self):
        manifest = capability_registry.get("verify_readme_proposal_bundle")
        assert manifest is not None
        assert manifest.owner == "readme_agent.verification.readme_proposal_bundle"
        assert manifest.side_effect_class == "read_only_network"
        assert manifest.allowed_domains == [INDEPENDENT_VERIFICATION]
        assert capability_registry.get_executor("verify_readme_proposal_bundle") is not None

    def test_verify_cross_pilot_specificity_is_registered_with_a_real_manifest(self):
        manifest = capability_registry.get("verify_cross_pilot_specificity")
        assert manifest is not None
        assert manifest.owner == "readme_agent.verification.readme_proposal_bundle"
        assert manifest.side_effect_class == "read_only_local"
        # Deliberately unscoped -- see capabilities/verify_cross_pilot_specificity.py's
        # own module docstring for why this one has no single owning domain.
        assert manifest.allowed_domains == []
        assert capability_registry.get_executor("verify_cross_pilot_specificity") is not None

    def test_dispatching_the_bundle_capability_accepts_a_real_untampered_bundle(self, bundle):
        dispatch = dispatch_tool_call(
            {
                "function": {
                    "name": "verify_readme_proposal_bundle",
                    "arguments": json.dumps({"bundle_dir": str(bundle)}),
                }
            },
            self._PERMISSIONS,
            caller_domain=INDEPENDENT_VERIFICATION,
        )
        assert dispatch.outcome == "executed", dispatch.error
        assert dispatch.result is not None
        assert dispatch.result["verified"] is True, dispatch.result["failures"]
        assert dispatch.result["org_repo"] == "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"

    def test_dispatching_the_bundle_capability_rejects_a_real_tampered_bundle(self, bundle):
        """The capability wrapper must not silently swallow a real rejection
        -- same tampering technique `TestRejectsTampering` already proves
        against the bare function, now proven against the dispatched
        capability instead."""
        candidate = bundle / "candidate-readme.md"
        candidate.write_text(
            candidate.read_text(encoding="utf-8") + "\nInjected line.\n",
            encoding="utf-8",
            newline="\n",
        )
        _refresh_artifact_checksums(bundle)

        dispatch = dispatch_tool_call(
            {
                "function": {
                    "name": "verify_readme_proposal_bundle",
                    "arguments": json.dumps({"bundle_dir": str(bundle)}),
                }
            },
            self._PERMISSIONS,
            caller_domain=INDEPENDENT_VERIFICATION,
        )
        assert dispatch.outcome == "executed", dispatch.error
        assert dispatch.result is not None
        assert dispatch.result["verified"] is False
        assert dispatch.result["checks"]["independent_reconstruction_byte_identical"] is False

    def test_dispatching_the_bundle_capability_outside_its_domain_is_denied(self, bundle):
        """`verify_readme_proposal_bundle` is scoped to `INDEPENDENT_VERIFICATION`
        (`capabilities/domains.py`) -- an unscoped or wrong-domain caller must be
        rejected before the underlying verifier ever runs, the same domain-isolation
        enforcement every other domain-scoped capability in this project gets."""
        dispatch = dispatch_tool_call(
            {
                "function": {
                    "name": "verify_readme_proposal_bundle",
                    "arguments": json.dumps({"bundle_dir": str(bundle)}),
                }
            },
            self._PERMISSIONS,
            caller_domain=None,
        )
        assert dispatch.outcome == "rejected_domain_denied"

    def test_dispatching_the_cross_pilot_capability_accepts_real_distinct_candidates(self):
        pilots = [
            [org_repo, (EVIDENCE / slug / "candidate-readme.md").read_text(encoding="utf-8")]
            for slug, org_repo in (
                ("cells-java", "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"),
                ("three-dimensional-java", "aspose-3d-foss/Aspose.3D-FOSS-for-Java"),
                ("pdf-java", "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java"),
            )
        ]
        dispatch = dispatch_tool_call(
            {
                "function": {
                    "name": "verify_cross_pilot_specificity",
                    "arguments": json.dumps({"pilots": pilots}),
                }
            },
            self._PERMISSIONS,
        )
        assert dispatch.outcome == "executed", dispatch.error
        assert dispatch.result is not None
        assert dispatch.result["verified"] is True, dispatch.result["failures"]

    def test_dispatching_the_cross_pilot_capability_rejects_a_duplicate_candidate(self):
        cells_text = (EVIDENCE / "cells-java" / "candidate-readme.md").read_text(encoding="utf-8")
        pilots = [
            ["aspose-cells-foss/Aspose.Cells-FOSS-for-Java", cells_text],
            ["aspose-3d-foss/Aspose.3D-FOSS-for-Java", cells_text],  # copy of cells' own candidate
        ]
        dispatch = dispatch_tool_call(
            {
                "function": {
                    "name": "verify_cross_pilot_specificity",
                    "arguments": json.dumps({"pilots": pilots}),
                }
            },
            self._PERMISSIONS,
        )
        assert dispatch.outcome == "executed", dispatch.error
        assert dispatch.result is not None
        assert dispatch.result["verified"] is False
        assert dispatch.result["checks"]["candidates_distinct"] is False
