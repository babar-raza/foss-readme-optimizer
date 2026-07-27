"""Examples run without inherited credentials, shell expansion, or unredacted output."""

import sys

from readme_agent.facts.example_execution import execute_example, secret_free_environment
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.local_verification import verify_local_product_example
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def test_secret_free_environment_drops_every_credential_like_name():
    environment = secret_free_environment(
        {
            "PATH": "safe-path",
            "GH_TOKEN": "ghp_syntheticSecretValue123456",
            "LLM_API_KEY": "sk-syntheticSecretValue123456",
            "GH_APP_PRIVATE_KEY": "private",
            "CUSTOM_PASSWORD": "password",
        }
    )

    assert environment["PATH"] == "safe-path"
    assert environment["CI"] == "true"
    assert "GH_TOKEN" not in environment
    assert "LLM_API_KEY" not in environment
    assert "GH_APP_PRIVATE_KEY" not in environment
    assert "CUSTOM_PASSWORD" not in environment


def test_execution_does_not_inherit_token_and_redacts_literal_output(tmp_path):
    fake_secret = "ghp_syntheticSecretValue123456"
    code = f"import os;print(os.getenv('GH_TOKEN'));print({fake_secret!r})"

    result = execute_example(
        [sys.executable, "-c", code],
        workspace=tmp_path,
        timeout_seconds=10,
        base_environment={"PATH": "", "GH_TOKEN": fake_secret},
    )

    assert result.return_code == 0
    assert result.stdout.splitlines()[0] == "None"
    assert fake_secret not in result.stdout
    assert "[REDACTED]" in result.stdout
    assert "GH_TOKEN" not in result.environment_names


def test_timeout_is_bounded(tmp_path):
    result = execute_example(
        [sys.executable, "-c", "while True: pass"],
        workspace=tmp_path,
        timeout_seconds=0.1,
        base_environment={},
    )

    assert result.return_code == 124
    assert result.timed_out is True


def test_host_execution_is_permanently_ineligible_for_product_truth(tmp_path, monkeypatch):
    (tmp_path / "example.py").write_text("print('evidence')\n", encoding="utf-8")
    result = execute_example(
        [sys.executable, "-c", "print('host diagnostic only')"],
        workspace=tmp_path,
        timeout_seconds=10,
        base_environment={},
    )
    assert result.isolation_kind == "host_secret_filtered"
    assert result.truth_eligible is False

    snapshot = RepositorySnapshotV1(
        org_repo="acme/widget",
        source_revision="abc1234",
        snapshot_root=str(tmp_path.resolve()),
        inventory_sha256="a" * 64,
        captured_at="2026-07-26T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.test/acme/widget.git",
            git_tree_sha256="a" * 64,
        ),
    )
    example = MinimalExamplePolicy(
        language="java",
        class_name="example",
        code="class Example {}",
        evidence_paths=["example.py"],
        required_symbols=[],
    )
    monkeypatch.setattr(
        "readme_agent.facts.local_verification.verify_repository_snapshot",
        lambda current: None,
    )
    monkeypatch.setattr(
        "readme_agent.facts.local_verification.run_host_product_example_diagnostic",
        lambda *_: (_ for _ in ()).throw(AssertionError("host verifier must not run")),
    )

    host_only = LocalProductVerificationV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="java",
        outcome="SOURCE_BUILD_VERIFIED",
        detail="host diagnostic attempted to claim success",
        build=result,
        truth_eligible=False,
    )
    verification = verify_local_product_example(
        snapshot,
        example,
        isolated_verifier=lambda *_: host_only,
    )

    assert verification.outcome == "ISOLATION_REQUIRED"
    assert verification.truth_eligible is False


def test_invalid_curated_example_is_a_typed_narrow_failure(tmp_path, monkeypatch):
    snapshot = RepositorySnapshotV1(
        org_repo="acme/widget",
        source_revision="abc1234",
        snapshot_root=str(tmp_path.resolve()),
        inventory_sha256="a" * 64,
        captured_at="2026-07-26T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.test/acme/widget.git",
            git_tree_sha256="a" * 64,
        ),
    )
    example = MinimalExamplePolicy(
        language="typescript",
        class_name="readme_example",
        code="import { Scene } from '@stale/package';",
        evidence_paths=["README.md"],
        required_symbols=["Scene"],
    )
    monkeypatch.setattr(
        "readme_agent.facts.local_verification.verify_repository_snapshot",
        lambda current: None,
    )

    def reject(*_):
        raise ValueError("package import is not compiler-resolved")

    verification = verify_local_product_example(
        snapshot,
        example,
        isolated_verifier=reject,
    )

    assert verification.outcome == "BUILD_FAILED"
    assert verification.truth_eligible is False
    assert "package import is not compiler-resolved" in verification.detail
