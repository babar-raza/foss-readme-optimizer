"""Runtime admission tests for a frozen qualified trusted cohort."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from readme_agent import cli
from readme_agent.evidence.writer import refresh_sha256sums, sha256_file
from readme_agent.llm import prompt_registry
from readme_agent.readme.trusted_composition_candidate_validation import (
    TRUSTED_CANDIDATE_NORMALIZATION_VERSION,
)
from readme_agent.state.trusted_cohort_schema import QualifiedTrustedCohortIdentityV1
from readme_agent.supervisor.trusted_cohort import trusted_reviewer_standard_hash
from readme_agent.supervisor.trusted_cohort_restore import (
    restore_trusted_cohort_act_inputs,
)
from readme_agent.supervisor.trusted_cohort_runtime import (
    load_runtime_trusted_cohort,
    require_runtime_trusted_cohort_member,
    require_runtime_trusted_cohort_repair_member,
    runtime_trusted_cohort_matrix,
)

CURRENT = Path("plans/investigations/evidence/trp-04p-qualified-trusted-cohort-v1/current.json")
ACT_INPUTS = Path("plans/investigations/evidence/trp-04p-act-workflow-inputs-v1/manifest.json")


def _manifest_path() -> Path:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    return Path(current["manifest_path"])


def _copied_contract_manifest(tmp_path: Path, *, refresh_candidate_contracts: bool) -> Path:
    copied = tmp_path / "current-contract-cohort"
    shutil.copytree(_manifest_path().parent, copied)
    manifest = copied / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["registry_sha256"] = sha256_file(Path("data/products.json"))[0]
    if refresh_candidate_contracts:
        payload["reviewer_standard_sha256"] = trusted_reviewer_standard_hash()
        payload["prompt_registry_sha256"] = prompt_registry.content_hash()
        payload["candidate_normalization_version"] = TRUSTED_CANDIDATE_NORMALIZATION_VERSION
    payload["cohort_id"] = QualifiedTrustedCohortIdentityV1(
        control_revision=payload["control_revision"],
        registry_sha256=payload["registry_sha256"],
        reviewer_standard_sha256=payload["reviewer_standard_sha256"],
        prompt_registry_sha256=payload["prompt_registry_sha256"],
        candidate_normalization_version=payload["candidate_normalization_version"],
        member_bindings=tuple(
            {
                "org_repo": member["org_repo"],
                "repository_id": member["provider_identity"]["repository_id"],
                "source_revision": member["source_revision"],
                "candidate_sha256": member["candidate_sha256"],
                "bundle_manifest_sha256": member["bundle_manifest_sha256"],
                "bundle_inventory_sha256": member["bundle_inventory_sha256"],
                "state_version": member["state_version"],
            }
            for member in payload["members"]
        ),
    ).canonical_hash()
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    refresh_sha256sums(copied)
    return manifest


def _current_contract_manifest(tmp_path: Path) -> Path:
    return _copied_contract_manifest(tmp_path, refresh_candidate_contracts=True)


def test_preserved_frozen_cohort_fails_closed_after_registry_change():
    with pytest.raises(ValueError, match="registry hash no longer matches"):
        load_runtime_trusted_cohort(_manifest_path())


def test_preserved_frozen_cohort_fails_closed_after_reviewer_standard_change(tmp_path):
    with pytest.raises(ValueError, match="reviewer standard is stale"):
        load_runtime_trusted_cohort(
            _copied_contract_manifest(tmp_path, refresh_candidate_contracts=False)
        )


def test_current_contract_fixture_emits_exact_three_member_matrix(tmp_path):
    cohort = load_runtime_trusted_cohort(_current_contract_manifest(tmp_path))

    matrix = runtime_trusted_cohort_matrix(cohort)

    assert [item["repo"] for item in matrix["include"]] == [
        "aspose-note-foss/Aspose.Note-FOSS-for-Python",
        "aspose-page-foss/Aspose.Page-FOSS-for-Python",
        "aspose-pdf-foss/Aspose-PDF-FOSS-for-Python",
    ]
    assert all(item["cohort_id"] == cohort.cohort_id for item in matrix["include"])


def test_runtime_member_admission_fails_outside_frozen_cohort(tmp_path):
    with pytest.raises(ValueError, match="is not a member"):
        require_runtime_trusted_cohort_member(
            _current_contract_manifest(tmp_path),
            "org/not-enrolled",
        )


def test_local_repair_member_accepts_stale_candidate_contracts_but_not_outsiders(tmp_path):
    manifest = _copied_contract_manifest(tmp_path, refresh_candidate_contracts=False)
    member = require_runtime_trusted_cohort_repair_member(
        manifest,
        "aspose-note-foss/Aspose.Note-FOSS-for-Python",
    )
    assert member.org_repo == "aspose-note-foss/Aspose.Note-FOSS-for-Python"
    with pytest.raises(ValueError, match="is not a member"):
        require_runtime_trusted_cohort_repair_member(
            manifest,
            "org/not-enrolled",
        )


def test_runtime_cohort_rejects_checksum_corruption(tmp_path):
    source = _manifest_path().parent
    copied = tmp_path / "cohort"
    shutil.copytree(source, copied)
    (copied / "manifest.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="checksum inventory is invalid"):
        load_runtime_trusted_cohort(copied / "manifest.json")


def test_preserved_act_inputs_fail_closed_after_contract_change(tmp_path):
    cohort = load_runtime_trusted_cohort(_current_contract_manifest(tmp_path))
    runtime_root = tmp_path / "readme-poc"
    state_remote = tmp_path / "state.git"

    with pytest.raises(ValueError, match="ACT input manifest cohort does not match"):
        restore_trusted_cohort_act_inputs(
            cohort,
            input_manifest_path=ACT_INPUTS,
            runtime_root=runtime_root,
            state_remote=state_remote,
        )
    assert not state_remote.exists()


def test_act_profile_requires_dedicated_provider_before_any_repository_work(
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("README_AGENT_PRODUCTION_AUTH", "act_local")
    monkeypatch.delenv("ACT", raising=False)
    monkeypatch.setenv("GH_TOKEN", "ambient-token")

    exit_code = cli.main(
        [
            "supervise",
            "--repo",
            "org/repo",
            "--execution-profile",
            "act_poc",
            "--qualified-cohort-manifest",
            str(_manifest_path()),
        ]
    )

    assert exit_code == 2
    assert "ambient PAT variables are never accepted" in capsys.readouterr().err


def test_act_profile_requires_the_frozen_manifest(monkeypatch, capsys):
    monkeypatch.setenv("README_AGENT_PRODUCTION_AUTH", "act_local")
    monkeypatch.setenv("ACT", "true")
    monkeypatch.setenv("README_AGENT_ACT_GITHUB_TOKEN", "dedicated-token")

    exit_code = cli.main(
        [
            "supervise",
            "--repo",
            "org/repo",
            "--execution-profile",
            "act_poc",
        ]
    )

    assert exit_code == 2
    assert "requires --qualified-cohort-manifest" in capsys.readouterr().err


def test_local_profile_repair_rejects_a_nonmember_before_repository_work(tmp_path, capsys):
    exit_code = cli.main(
        [
            "supervise",
            "--repo",
            "org/not-enrolled",
            "--execution-profile",
            "local_poc",
            "--qualified-cohort-manifest",
            str(_copied_contract_manifest(tmp_path, refresh_candidate_contracts=False)),
        ]
    )

    assert exit_code == 2
    assert "is not a member" in capsys.readouterr().err
