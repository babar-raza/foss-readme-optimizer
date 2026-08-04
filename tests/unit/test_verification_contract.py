"""Tests for ecosystem-scoped product-verification cache identities."""

from readme_agent.facts.local_verification import local_verification_contract_hash
from readme_agent.facts.verification_contract import verification_contract_files


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
