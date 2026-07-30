"""Runtime admission tests for a frozen qualified trusted cohort."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from readme_agent import cli
from readme_agent.supervisor.trusted_cohort_restore import (
    restore_trusted_cohort_act_inputs,
)
from readme_agent.supervisor.trusted_cohort_runtime import (
    load_runtime_trusted_cohort,
    require_runtime_trusted_cohort_member,
    runtime_trusted_cohort_matrix,
)

CURRENT = Path("plans/investigations/evidence/trp-04p-qualified-trusted-cohort-v1/current.json")
ACT_INPUTS = Path("plans/investigations/evidence/trp-04p-act-workflow-inputs-v1/manifest.json")


def _manifest_path() -> Path:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    return Path(current["manifest_path"])


def test_current_frozen_cohort_emits_exact_three_member_matrix():
    cohort = load_runtime_trusted_cohort(_manifest_path())

    matrix = runtime_trusted_cohort_matrix(cohort)

    assert [item["repo"] for item in matrix["include"]] == [
        "aspose-note-foss/Aspose.Note-FOSS-for-Python",
        "aspose-page-foss/Aspose.Page-FOSS-for-Python",
        "aspose-pdf-foss/Aspose-PDF-FOSS-for-Python",
    ]
    assert all(item["cohort_id"] == cohort.cohort_id for item in matrix["include"])


def test_runtime_member_admission_fails_outside_frozen_cohort():
    with pytest.raises(ValueError, match="is not a member"):
        require_runtime_trusted_cohort_member(_manifest_path(), "org/not-enrolled")


def test_runtime_cohort_rejects_checksum_corruption(tmp_path):
    source = _manifest_path().parent
    copied = tmp_path / "cohort"
    shutil.copytree(source, copied)
    (copied / "manifest.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="checksum inventory is invalid"):
        load_runtime_trusted_cohort(copied / "manifest.json")


def test_act_inputs_restore_exact_runtime_and_state_idempotently(tmp_path):
    cohort = load_runtime_trusted_cohort(_manifest_path())
    runtime_root = tmp_path / "readme-poc"
    state_remote = tmp_path / "state.git"

    first = restore_trusted_cohort_act_inputs(
        cohort,
        input_manifest_path=ACT_INPUTS,
        runtime_root=runtime_root,
        state_remote=state_remote,
    )
    second = restore_trusted_cohort_act_inputs(
        cohort,
        input_manifest_path=ACT_INPUTS,
        runtime_root=runtime_root,
        state_remote=state_remote,
    )

    assert first == second
    assert first["qualified_count"] == 3
    assert (state_remote / "HEAD").is_file()


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
