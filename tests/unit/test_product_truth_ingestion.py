"""Repository-evidence and disposable product-example verification contracts."""

import os
from pathlib import Path
from types import SimpleNamespace

from readme_agent.facts.example_execution import ExampleExecutionResultV1
from readme_agent.facts.local_verification import run_host_product_example_diagnostic
from readme_agent.facts.policy_evidence import evidence_failures
from readme_agent.facts.repository_ingestion import ingest_repository_product_facts
from readme_agent.profile.schema import PackageRoot, RepositoryProfile
from readme_agent.registry.models import PolicyProfile
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def _policy(evidence_path: str, symbol: str) -> PolicyProfile:
    return PolicyProfile.model_validate(
        {
            "schema_version": 2,
            "policy_profile": "acme-widget",
            "required_elements": {
                "license_mentioned": {"detected_license": "MIT"},
                "products_org_link": {
                    "url": "https://products.acme.test/widget/java/",
                    "family_url": "https://products.acme.test/widget/",
                    "label": "Widget",
                },
                "products_com_link": {
                    "url": "https://products.acme.example/widget/java/",
                    "family_url": "https://products.acme.example/widget/",
                    "label": "Widget",
                },
                "relationship_explained": {"talking_points": ["open_source_scope"]},
            },
            "block": {"word_limit": {"min": 10, "max": 100}},
            "product_truth": {
                "audience": ["Java developers."],
                "problems_solved": ["Process widgets."],
                "capabilities": [
                    {
                        "value": "Create widgets.",
                        "evidence_paths": [evidence_path],
                        "required_symbols": [symbol],
                    }
                ],
                "formats": [
                    {
                        "value": "Read WGT files.",
                        "evidence_paths": [evidence_path],
                        "required_symbols": [symbol],
                    }
                ],
                "limitations": [],
                "minimal_example": {
                    "language": "java",
                    "class_name": "ReadmeExample",
                    "code": "public class ReadmeExample {}",
                    "evidence_paths": [evidence_path],
                    "required_symbols": [symbol],
                },
            },
        }
    )


def _entry():
    return SimpleNamespace(
        family="widget",
        platform="java",
        ecosystem="java",
        active=True,
    )


def test_repository_assertion_requires_existing_path_and_symbol(tmp_path):
    (tmp_path / "pom.xml").write_text(
        "<groupId>org.acme</groupId><artifactId>widget</artifactId>"
        "<version>1.2.3</version><maven.compiler.target>17</maven.compiler.target>",
        encoding="utf-8",
    )
    source = tmp_path / "src" / "Widget.java"
    source.parent.mkdir()
    source.write_text("public class Widget {}", encoding="utf-8")
    profile = RepositoryProfile(
        org_repo="acme/widget",
        package_roots=[
            PackageRoot(
                path=".",
                ecosystem="java",
                manifest_path="pom.xml",
                confidence=1.0,
                evidence="found pom.xml",
            )
        ],
    )

    candidates = ingest_repository_product_facts(
        _entry(),
        _policy("src/Widget.java", "public class Widget"),
        profile,
        tmp_path,
        "abc1234",
    )

    capabilities = next(fact for fact in candidates if fact.field == "product.capabilities")
    coordinates = next(fact for fact in candidates if fact.field == "installation.coordinates")
    assert capabilities.verification_state == "verified"
    assert coordinates.value[0]["group_id"] == "org.acme"
    assert coordinates.value[0]["version"] == "1.2.3"


def test_manifest_compatibility_normalizes_every_ecosystem_runtime_contract(tmp_path):
    manifests = {
        "net/widget.csproj": (
            "<Project><PropertyGroup>"
            "<TargetFrameworks>net10.0;net8.0;netcoreapp3.1</TargetFrameworks>"
            "</PropertyGroup></Project>"
        ),
        "python/pyproject.toml": (
            '[project]\nname = "widget"\nversion = "1.0.0"\nrequires-python = ">=3.11"\n'
        ),
        "typescript/package.json": (
            '{"name":"widget","version":"1.0.0","engines":{"node":">=18,<22"}}'
        ),
        "cpp/CMakeLists.txt": ("cmake_minimum_required(VERSION 3.20)\nproject(widget)\n"),
        "rust/Cargo.toml": (
            '[package]\nname = "widget"\nversion = "1.0.0"\nrust-version = "1.75"\n'
        ),
    }
    observed_requirements = {}
    for relative_path, content in manifests.items():
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        package_root, manifest_name = relative_path.split("/", maxsplit=1)
        ecosystem = "net" if package_root == "net" else package_root
        profile = RepositoryProfile(
            org_repo=f"acme/widget-{ecosystem}",
            package_roots=[
                PackageRoot(
                    path=package_root,
                    ecosystem=ecosystem,
                    manifest_path=relative_path,
                    confidence=1.0,
                    evidence=f"found {manifest_name}",
                )
            ],
        )
        candidates = ingest_repository_product_facts(
            SimpleNamespace(
                family="widget",
                platform=ecosystem,
                ecosystem=ecosystem,
                active=True,
            ),
            _policy("src/Widget.java", "public class Widget"),
            profile,
            tmp_path,
            "abc1234",
        )
        compatibility = next(fact for fact in candidates if fact.field == "product.compatibility")
        row = compatibility.value[0]
        observed_requirements[ecosystem] = (
            row["runtime_label"],
            row["minimum_runtime"],
        )

    assert observed_requirements == {
        "cpp": ("CMake", "3.20"),
        "net": (".NET", "netcoreapp3.1"),
        "python": ("Python", ">=3.11"),
        "rust": ("Rust", "1.75"),
        "typescript": ("Node.js", ">=18,<22"),
    }


def test_static_setup_py_compatibility_is_not_a_verified_fact(tmp_path):
    (tmp_path / "setup.py").write_text(
        """from setuptools import setup

setup(
    name="aspose-3d-foss",
    version="26.1.0",
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
""",
        encoding="utf-8",
    )
    profile = RepositoryProfile(
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        package_roots=[
            PackageRoot(
                path=".",
                ecosystem="python",
                manifest_path="setup.py",
                confidence=1.0,
                evidence="found setup.py",
            )
        ],
    )

    candidates = ingest_repository_product_facts(
        SimpleNamespace(
            family="3d",
            platform="python",
            ecosystem="python",
            active=True,
        ),
        _policy("setup.py", "setup"),
        profile,
        tmp_path,
        "ab1a2267",
    )

    compatibility = next(fact for fact in candidates if fact.field == "product.compatibility")
    assert compatibility.verification_state == "blocked"
    assert compatibility.value == {
        "reason": "immutable_snapshot_required",
        "manifest_path": "setup.py",
    }
    assert compatibility.source.location.endswith("#isolated-generated-PKG-INFO")
    assert compatibility.source.source_revision == "ab1a2267"
    assert (
        next(fact for fact in candidates if fact.field == "product.identity").verification_state
        == "verified"
    )
    assert (
        next(
            fact for fact in candidates if fact.field == "installation.coordinates"
        ).verification_state
        == "verified"
    )


def test_isolated_pkg_info_promotes_setup_py_compatibility(tmp_path, monkeypatch):
    (tmp_path / "setup.py").write_text(
        "from setuptools import setup\nsetup(name='widget')\n",
        encoding="utf-8",
    )
    profile = RepositoryProfile(
        org_repo="acme/widget",
        package_roots=[
            PackageRoot(
                path=".",
                ecosystem="python",
                manifest_path="setup.py",
                confidence=1.0,
                evidence="found setup.py",
            )
        ],
    )
    snapshot = RepositorySnapshotV1(
        org_repo="acme/widget",
        source_revision="a" * 40,
        snapshot_root=str(tmp_path.resolve()),
        inventory_sha256="b" * 64,
        captured_at="2026-08-05T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.test/acme/widget.git",
            git_tree_sha256="b" * 64,
        ),
    )
    metadata = SimpleNamespace(
        requires_python=">=3.7",
        python_classifier_versions=["3.7", "3.8", "3.9", "3.10", "3.11", "3.12"],
        pkg_info_sha256="c" * 64,
    )
    execution = SimpleNamespace(
        input_sha256="d" * 64,
        policy=SimpleNamespace(immutable_image="python@sha256:" + "e" * 64),
        cleanup=SimpleNamespace(complete=True),
    )
    proof = SimpleNamespace(
        truth_eligible=True,
        snapshot_inventory_sha256="b" * 64,
        manifest_sha256="f" * 64,
        driver_sha256="1" * 64,
        execution=execution,
        metadata=metadata,
        failure_reason=None,
    )
    monkeypatch.setattr(
        "readme_agent.facts.python_distribution_metadata_facts.local_fact_verification_allowed",
        lambda: True,
    )
    monkeypatch.setattr(
        "readme_agent.facts.python_distribution_metadata_facts.verify_python_distribution_metadata",
        lambda _snapshot, _selected: proof,
    )

    candidates = ingest_repository_product_facts(
        SimpleNamespace(
            family="widget",
            platform="python",
            ecosystem="python",
            active=True,
        ),
        _policy("setup.py", "setup"),
        profile,
        tmp_path,
        "a" * 40,
        snapshot=snapshot,
    )

    compatibility = next(fact for fact in candidates if fact.field == "product.compatibility")
    assert compatibility.verification_state == "verified"
    assert compatibility.value[0]["minimum_runtime"] == ">=3.7"
    assert compatibility.value[0]["supported_runtime_versions"][-1] == "3.12"
    assert compatibility.value[0]["metadata_proof"] == {
        "truth_eligible": True,
        "snapshot_inventory_sha256": "b" * 64,
        "manifest_sha256": "f" * 64,
        "driver_sha256": "1" * 64,
        "input_sha256": "d" * 64,
        "container_image": "python@sha256:" + "e" * 64,
        "pkg_info_sha256": "c" * 64,
        "cleanup_complete": True,
    }
    assert compatibility.source.location.endswith(":" + "c" * 64)


def test_missing_or_escaped_evidence_blocks_only_technical_assertion(tmp_path):
    profile = RepositoryProfile(org_repo="acme/widget")
    candidates = ingest_repository_product_facts(
        _entry(),
        _policy("../outside.java", "inventedSymbol"),
        profile,
        tmp_path,
        "abc1234",
    )

    capabilities = next(fact for fact in candidates if fact.field == "product.capabilities")
    audience = next(fact for fact in candidates if fact.field == "product.audience")
    assert capabilities.verification_state == "blocked"
    assert "escapes snapshot" in capabilities.value["evidence_failures"][0]
    assert audience.verification_state == "policy_approved"


def test_identifier_evidence_does_not_match_inside_a_different_symbol(tmp_path):
    source = tmp_path / "Node.cs"
    source.write_text(
        "public class Node { public BoundingBox Bounds { get; } }",
        encoding="utf-8",
    )

    failures = evidence_failures(tmp_path, ["Node.cs"], ["Box"])

    assert failures == ["required evidence symbol missing: Box"]


def test_agentic_example_may_keep_one_real_anchor_when_an_extra_anchor_is_missing(tmp_path):
    source = tmp_path / "Scene.cs"
    source.write_text("public class Scene {}\n", encoding="utf-8")

    failures = evidence_failures(
        tmp_path,
        ["Scene.cs"],
        ["Scene", "MissingBox"],
        allow_partial_symbols=True,
    )

    assert failures == []


def test_file_path_without_a_claim_anchor_is_not_technical_evidence(tmp_path):
    (tmp_path / "Widget.java").write_text("public class Widget {}", encoding="utf-8")

    failures = evidence_failures(tmp_path, ["Widget.java"], [])

    assert failures == ["required evidence symbol missing: at least one exact anchor is required"]


def test_blank_claim_anchor_is_not_technical_evidence(tmp_path):
    (tmp_path / "Widget.java").write_text("public class Widget {}", encoding="utf-8")

    failures = evidence_failures(tmp_path, ["Widget.java"], [" "])

    assert failures == ["required evidence symbol missing: blank anchors are invalid"]


def test_disposable_example_verification_does_not_write_snapshot(tmp_path, monkeypatch):
    source = tmp_path / "src" / "Widget.java"
    source.parent.mkdir()
    source.write_text("public class Widget {}", encoding="utf-8")
    snapshot = RepositorySnapshotV1(
        org_repo="acme/widget",
        source_revision="abc1234",
        snapshot_root=str(tmp_path.resolve()),
        inventory_sha256="a" * 64,
        captured_at="2026-07-24T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.test/acme/widget.git",
            git_tree_sha256="a" * 64,
        ),
    )
    example = _policy("src/Widget.java", "public class Widget").product_truth.minimal_example
    observed_workspaces: list[Path] = []

    def successful_execution(argv, *, workspace, timeout_seconds, base_environment=None):
        observed_workspaces.append(workspace)
        return ExampleExecutionResultV1(
            argv=argv,
            return_code=0,
            stdout="",
            stderr="",
            timed_out=False,
            environment_names=[],
        )

    monkeypatch.setattr(
        "readme_agent.facts.local_verification.verify_repository_snapshot",
        lambda snapshot: None,
    )
    monkeypatch.setattr(
        "readme_agent.facts.local_verification.shutil.which",
        lambda executable: f"C:/{executable}.exe",
    )
    monkeypatch.setattr(
        "readme_agent.facts.local_verification.execute_example",
        successful_execution,
    )
    monkeypatch.setattr("readme_agent.facts.local_verification.env.java_home", lambda: None)
    # RPOC-041: `_verify_java` now auto-detects/auto-provisions the JDK via
    # `java_toolchain` instead of resolving `javac` off PATH -- fake a
    # provisioned JDK home (with a real `bin/javac[.exe]`, since `_verify_java`
    # checks the file exists) rather than letting this test reach the real
    # Adoptium network.
    fake_jdk_home = tmp_path / "fake-provisioned-jdk"
    javac_name = "javac.exe" if os.name == "nt" else "javac"
    (fake_jdk_home / "bin").mkdir(parents=True)
    (fake_jdk_home / "bin" / javac_name).write_text("", encoding="utf-8")
    monkeypatch.setattr(
        "readme_agent.facts.local_verification.java_toolchain.provision_jdk",
        lambda major: fake_jdk_home,
    )

    result = run_host_product_example_diagnostic(snapshot, example)

    assert result.outcome == "SOURCE_BUILD_VERIFIED"
    assert result.truth_eligible is False
    assert len(observed_workspaces) == 2
    assert observed_workspaces[0] != tmp_path
    assert not (tmp_path / "ReadmeExample.java").exists()
    assert not (tmp_path / "target").exists()
