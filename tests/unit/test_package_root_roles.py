"""Package-root role classification and visitor-fact binding regressions."""

from pathlib import Path
from types import SimpleNamespace

from readme_agent.facts.repository_ingestion import ingest_repository_product_facts
from readme_agent.facts.root_roles import classify_package_root_roles
from readme_agent.profile.schema import PackageRoot, RepositoryProfile
from readme_agent.registry.models import PolicyProfile

FIXTURE = Path(__file__).parents[1] / "fixtures" / "package_root_roles" / "aspose-3d-foss-dotnet"
SOURCE_REVISION = "6a209e8fc3dfc305df39a417037e32a4d4c7b2be"


def _entry(family: str, ecosystem: str, platform: str | None = None):
    return SimpleNamespace(
        family=family,
        ecosystem=ecosystem,
        platform=platform or ecosystem,
        repo_name=f"{family}-{ecosystem}",
        active=True,
    )


def _empty_policy() -> PolicyProfile:
    return PolicyProfile.model_validate(
        {
            "schema_version": 2,
            "policy_profile": "root-role-control",
            "required_elements": {
                "license_mentioned": {"detected_license": "MIT"},
                "products_org_link": {
                    "url": "https://products.example.test/foss",
                    "family_url": "https://products.example.test",
                    "label": "FOSS",
                },
                "products_com_link": {
                    "url": "https://products.example.test/enterprise",
                    "family_url": "https://products.example.test",
                    "label": "Enterprise",
                },
                "relationship_explained": {"talking_points": []},
            },
            "block": {"word_limit": {"min": 1, "max": 100}},
        }
    )


def _dotnet_profile(*, reverse: bool = False, windows_paths: bool = False) -> RepositoryProfile:
    values = [
        ("src/converter", "src/converter/Converter.csproj"),
        ("src/main/Aspose.ThreeD", "src/main/Aspose.ThreeD/Aspose.ThreeD.csproj"),
        ("src/test/Aspose.ThreeD.Tests", "src/test/Aspose.ThreeD.Tests/Aspose.ThreeD.Tests.csproj"),
    ]
    if reverse:
        values.reverse()
    return RepositoryProfile(
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
        source_revision=SOURCE_REVISION,
        package_roots=[
            PackageRoot(
                path=path.replace("/", "\\") if windows_paths else path,
                ecosystem="net",
                manifest_path=manifest.replace("/", "\\") if windows_paths else manifest,
                confidence=1.0,
                evidence=f"found {Path(manifest).name}",
            )
            for path, manifest in values
        ],
    )


def test_real_dotnet_multi_root_selects_library_and_excludes_newer_secondary_targets():
    profile = _dotnet_profile(windows_paths=True)
    inventory = classify_package_root_roles(
        _entry("3d", "net"),
        profile,
        FIXTURE,
        SOURCE_REVISION,
    )

    assert inventory.selection_state == "selected"
    assert inventory.selected_product_manifest_path == "src/main/Aspose.ThreeD/Aspose.ThreeD.csproj"
    assert {record.manifest_path: record.role for record in inventory.roots} == {
        "src/converter/Converter.csproj": "converter",
        "src/main/Aspose.ThreeD/Aspose.ThreeD.csproj": "product",
        "src/test/Aspose.ThreeD.Tests/Aspose.ThreeD.Tests.csproj": "test",
    }
    product = next(record for record in inventory.roots if record.role == "product")
    assert product.parsed_identity["name"] == "Aspose.3D.FOSS"
    assert inventory.source_revision == SOURCE_REVISION

    candidates = ingest_repository_product_facts(
        _entry("3d", "net"),
        _empty_policy(),
        profile,
        FIXTURE,
        SOURCE_REVISION,
        root_roles=inventory,
    )
    coordinates = next(fact for fact in candidates if fact.field == "installation.coordinates")
    compatibility = next(fact for fact in candidates if fact.field == "product.compatibility")
    releases = next(fact for fact in candidates if fact.field == "release.state")

    assert [row["name"] for row in coordinates.value] == ["Aspose.3D.FOSS"]
    assert [row["minimum_runtime"] for row in compatibility.value] == ["netcoreapp3.1"]
    assert [row["version"] for row in releases.value] == ["26.1.0"]
    assert all(row["root_role"] == "product" for row in coordinates.value)


def test_root_order_and_path_separator_do_not_change_inventory_hash():
    forward = classify_package_root_roles(
        _entry("3d", "net"),
        _dotnet_profile(),
        FIXTURE,
        SOURCE_REVISION,
    )
    reversed_windows = classify_package_root_roles(
        _entry("3d", "net"),
        _dotnet_profile(reverse=True, windows_paths=True),
        FIXTURE,
        SOURCE_REVISION,
    )

    assert forward == reversed_windows
    assert forward.canonical_hash() == reversed_windows.canonical_hash()


def test_java_and_python_single_roots_are_selected(tmp_path):
    controls = (
        ("java", "pom.xml", "<groupId>org.acme</groupId><artifactId>widget</artifactId>"),
        (
            "python",
            "pyproject.toml",
            '[project]\nname = "widget-foss"\nversion = "1.0.0"\n',
        ),
    )
    for ecosystem, manifest, content in controls:
        root = tmp_path / ecosystem
        root.mkdir()
        (root / manifest).write_text(content, encoding="utf-8")
        profile = RepositoryProfile(
            org_repo=f"acme/widget-{ecosystem}",
            package_roots=[
                PackageRoot(
                    path=".",
                    ecosystem=ecosystem,
                    manifest_path=manifest,
                    confidence=1.0,
                    evidence=f"found {manifest}",
                )
            ],
        )

        inventory = classify_package_root_roles(
            _entry("widget", ecosystem),
            profile,
            root,
            "control-revision",
        )

        assert inventory.selection_state == "selected"
        assert inventory.selected_product_manifest_path == manifest
        assert inventory.roots[0].role == "product"


def test_all_secondary_roles_are_typed_without_repository_specific_rules(tmp_path):
    role_paths = {
        "test": "tests",
        "sample": "examples",
        "converter": "converter",
        "generator": "codegen",
        "benchmark": "benchmarks",
        "build_tool": "tools",
    }
    roots = []
    product = tmp_path / "src" / "main"
    product.mkdir(parents=True)
    (product / "pyproject.toml").write_text(
        '[project]\nname = "widget-foss"\nversion = "1"\n',
        encoding="utf-8",
    )
    roots.append(
        PackageRoot(
            path="src/main",
            ecosystem="python",
            manifest_path="src/main/pyproject.toml",
            confidence=1.0,
            evidence="product",
        )
    )
    for relative in role_paths.values():
        path = tmp_path / relative
        path.mkdir(parents=True)
        (path / "pyproject.toml").write_text(
            f'[project]\nname = "widget-{relative}"\nversion = "1"\n',
            encoding="utf-8",
        )
        roots.append(
            PackageRoot(
                path=relative,
                ecosystem="python",
                manifest_path=f"{relative}/pyproject.toml",
                confidence=1.0,
                evidence=relative,
            )
        )
    profile = RepositoryProfile(org_repo="acme/widget", package_roots=roots)

    inventory = classify_package_root_roles(
        _entry("widget", "python"),
        profile,
        tmp_path,
        "roles-revision",
    )

    roles = {record.path: record.role for record in inventory.roots}
    assert roles["src/main"] == "product"
    for expected_role, path in role_paths.items():
        assert roles[path] == expected_role


def test_ambiguous_product_roots_block_only_dependent_manifest_facts(tmp_path):
    roots = []
    for relative in ("alpha", "beta"):
        path = tmp_path / relative
        path.mkdir()
        (path / "pyproject.toml").write_text(
            f'[project]\nname = "{relative}"\nversion = "1"\n',
            encoding="utf-8",
        )
        roots.append(
            PackageRoot(
                path=relative,
                ecosystem="python",
                manifest_path=f"{relative}/pyproject.toml",
                confidence=1.0,
                evidence=relative,
            )
        )
    profile = RepositoryProfile(org_repo="acme/widget", package_roots=roots)
    entry = _entry("widget", "python")
    inventory = classify_package_root_roles(entry, profile, tmp_path, "ambiguous-revision")

    assert inventory.selection_state == "ambiguous"
    assert inventory.selected_product_manifest_path is None
    assert {record.role for record in inventory.roots} == {"unknown"}

    candidates = ingest_repository_product_facts(
        entry,
        _empty_policy(),
        profile,
        tmp_path,
        "ambiguous-revision",
        root_roles=inventory,
    )
    by_field = {fact.field: fact for fact in candidates}
    assert by_field["product.identity"].verification_state == "verified"
    assert by_field["product.platforms"].verification_state == "verified"
    for field in ("installation.coordinates", "product.compatibility", "release.state"):
        assert by_field[field].verification_state == "blocked"
        assert by_field[field].value["selection_state"] == "ambiguous"
