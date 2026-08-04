"""Tests for ecosystem-scoped product-verification cache identities."""

from pathlib import Path

from readme_agent.facts.local_verification import local_verification_contract_hash
from readme_agent.facts.verification_contract import (
    verification_contract_files,
    verification_contract_hash,
)


def test_ecosystem_contract_excludes_unrelated_platform_adapters():
    python_files = verification_contract_files("python")
    net_files = verification_contract_files("net")

    assert "python_example_verifier.py" in python_files
    assert "dotnet_example_verifier.py" not in python_files
    assert "dotnet_example_verifier.py" in net_files
    assert "python_example_verifier.py" not in net_files


def test_ecosystem_aliases_share_the_same_contract():
    assert local_verification_contract_hash(".NET") == local_verification_contract_hash("net")
    assert local_verification_contract_hash("C++") == local_verification_contract_hash("cpp")


def test_dotnet_contract_covers_dependency_acquisition_and_schema():
    files = verification_contract_files("net")

    assert {
        "dotnet_dependency_acquisition.py",
        "dotnet_dependency_schema.py",
        "dotnet_lfs_acquisition.py",
        "dotnet_project_closure.py",
        "isolated_cleanup.py",
        "isolated_docker_control.py",
    }.issubset(files)


def test_shared_docker_control_and_dotnet_schema_mutations_invalidate_exact_scopes(tmp_path):
    root = Path(__file__).resolve().parents[2] / "src" / "readme_agent" / "facts"
    net_files = verification_contract_files("net")
    python_files = verification_contract_files("python")
    all_files = set(net_files) | set(python_files)
    for relative in all_files:
        source = root / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())

    net_before = verification_contract_hash(tmp_path, "net")
    python_before = verification_contract_hash(tmp_path, "python")
    docker_control = tmp_path / "isolated_docker_control.py"
    docker_control.write_bytes(docker_control.read_bytes() + b"\n# mutation\n")

    net_after_shared = verification_contract_hash(tmp_path, "net")
    python_after_shared = verification_contract_hash(tmp_path, "python")
    assert net_after_shared != net_before
    assert python_after_shared != python_before

    dotnet_schema = tmp_path / "dotnet_dependency_schema.py"
    dotnet_schema.write_bytes(dotnet_schema.read_bytes() + b"\n# mutation\n")

    assert verification_contract_hash(tmp_path, "net") != net_after_shared
    assert verification_contract_hash(tmp_path, "python") == python_after_shared


def test_global_compatibility_contract_covers_all_platforms():
    global_files = verification_contract_files()

    for required in (
        "python_example_verifier.py",
        "dotnet_example_verifier.py",
        "java_example_verifier.py",
        "typescript_example_verifier.py",
        "rust_example_verifier.py",
    ):
        assert required in global_files


def test_format_adapter_split_files_are_all_verification_inputs():
    files = verification_contract_files("python")

    assert {
        "aspose_org_dependency_snapshot.py",
        "aspose_org_format_adapter.py",
        "aspose_org_format_contract.py",
    }.issubset(files)
    assert "python_html_format_functionality.py" in files
    assert "verified_repository_examples.py" in files
    assert "deterministic_truth_salvage.py" in files
    assert "provider.py" in files
    assert "../supervisor/product_truth.py" in files
