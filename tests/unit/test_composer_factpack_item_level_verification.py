"""Owner review (2026-08-20), corrections 1/3/4: `composer_factpack.py`'s
`aspose_fact_records()` must never treat the imported corpus's own
provenance stamps (`api_public_surface.model_sha`, `dependency_claims.
repo_sha`) as content verification. Every test here proves the real,
item-level replacement: a class/dependency is only ever promoted into a
`verified` record when it is independently confirmed against the pinned
current repository clone (a real manifest for dependencies, real source
text for API symbols) -- never from SHA presence alone -- and every
unconfirmed item is preserved, in full, in a separate always-unverified
supporting record rather than discarded or laundered into the same
aggregate."""

from __future__ import annotations

from pathlib import Path

import pytest

from readme_agent.facts.aspose_detectors import (
    ApiPublicSurfaceDetectionV1,
    ApiSurfaceClassV1,
    ApiSurfaceMemberV1,
    ApiSurfaceModuleV1,
    ApiSymbolStateV1,
    DependencyClaimsDetectionV1,
)
from readme_agent.facts.composer_factpack import aspose_fact_records, build_aspose_detection_bundle

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_ROOT = _REPO_ROOT / "data" / "imported"
_ABSENT_FAMILY = "nonexistent-family-item-level-test"


def _base_bundle(tmp_path: Path, platform: str = "python"):
    """A bundle for a family the corpus has no real data for -- every
    detector degrades gracefully to empty/default (an already-proven
    pattern, see test_assess_source_staleness_absent_family_all_sources_
    degrade) -- so only the `dependency_claims`/`api_public_surface`
    fields this module overrides carry any signal."""

    return build_aspose_detection_bundle(
        _ABSENT_FAMILY, platform, data_root=_DATA_ROOT, clone_cache=tmp_path
    )


def _state(visibility: str = "public") -> ApiSymbolStateV1:
    return ApiSymbolStateV1(visibility=visibility, reachable="unknown", implemented="unknown")


def _class(name: str, *, visibility: str = "public") -> ApiSurfaceClassV1:
    return ApiSurfaceClassV1(
        name=name,
        description="",
        kind="class_definition",
        methods=(),
        properties=(),
        state=_state(visibility),
    )


def _verified_and_supporting(facts, field: str):
    verified = next(
        (f for f in facts if f.field == field and f.verification_state == "verified"), None
    )
    supporting = next(
        (f for f in facts if f.field == field and f.verification_state == "unverified"), None
    )
    return verified, supporting


# --- Correction 4: dependency claims -----------------------------------------


def test_dependency_claim_repo_sha_alone_never_verifies_without_a_current_manifest(tmp_path):
    """A `repo_sha` in the corpus's model.yaml is present, but the pinned
    clone has no manifest at all -- proving repo_sha existence alone never
    verifies content."""

    bundle = _base_bundle(tmp_path).model_copy(
        update={
            "dependency_claims": DependencyClaimsDetectionV1(
                claims=({"claim_id": "c1", "kind": "dependency", "text": "Depends on Pillow>=10"},),
                repo_sha="f" * 40,
            )
        }
    )

    facts = aspose_fact_records(
        bundle, family=_ABSENT_FAMILY, platform="python", clone_cache=tmp_path
    )
    verified, supporting = _verified_and_supporting(facts, "aspose.dependency_claims")

    assert verified is None
    assert supporting is not None
    assert supporting.value == [
        {"claim_id": "c1", "kind": "dependency", "text": "Depends on Pillow>=10"}
    ]


def test_dependency_claim_confirmed_against_current_manifest_splits_item_level(tmp_path):
    """One claim's package agrees with the pinned clone's own current
    pyproject.toml, the other does not -- both preserved, split into a
    verified record (confirmed only) and a supporting record (the rest),
    never a single aggregate flag covering both."""

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "1"\ndependencies = ["Pillow>=10.0"]\n',
        encoding="utf-8",
    )
    confirmed_claim = {"claim_id": "c1", "kind": "dependency", "text": "Depends on Pillow>=10.1.0"}
    unconfirmed_claim = {
        "claim_id": "c2",
        "kind": "dependency",
        "text": "Depends on totally-fake-package>=1.0",
    }
    bundle = _base_bundle(tmp_path).model_copy(
        update={
            "dependency_claims": DependencyClaimsDetectionV1(
                claims=(confirmed_claim, unconfirmed_claim), repo_sha=None
            )
        }
    )

    facts = aspose_fact_records(
        bundle, family=_ABSENT_FAMILY, platform="python", clone_cache=tmp_path
    )
    verified, supporting = _verified_and_supporting(facts, "aspose.dependency_claims")

    assert verified is not None
    assert verified.value == [confirmed_claim]
    assert supporting is not None
    assert supporting.value == [unconfirmed_claim]


@pytest.mark.parametrize("platform", ["java", "net", "cpp", "go", "typescript"])
def test_dependency_claims_unbuilt_ecosystem_manifest_never_fabricates_a_verified_record(
    tmp_path, platform
):
    """`dependency_snapshot.py` honestly reports `applicable=False` for
    every ecosystem beyond python/rust -- proving that gap never silently
    becomes a fabricated confirmation for the other 5 registered
    platforms."""

    bundle = _base_bundle(tmp_path, platform).model_copy(
        update={
            "dependency_claims": DependencyClaimsDetectionV1(
                claims=({"claim_id": "c1", "kind": "dependency", "text": "Depends on anything"},),
                repo_sha="a" * 40,
            )
        }
    )

    facts = aspose_fact_records(
        bundle, family=_ABSENT_FAMILY, platform=platform, clone_cache=tmp_path
    )
    verified, supporting = _verified_and_supporting(facts, "aspose.dependency_claims")

    assert verified is None
    assert supporting is not None


# --- Corrections 1 & 3: api.public_surface -----------------------------------


def test_api_public_surface_model_sha_alone_never_verifies_an_unconfirmed_class(tmp_path):
    """`model_sha` present on the whole surface, but the pinned clone's
    source tree contains nothing matching this class's name -- proving
    model_sha existence alone never verifies content, and the class is
    preserved (not discarded) in a supporting record instead."""

    surface = ApiPublicSurfaceDetectionV1(
        modules=(ApiSurfaceModuleV1(module="widget", classes=(_class("GhostClass"),)),),
        model_sha="a" * 40,
    )
    bundle = _base_bundle(tmp_path).model_copy(update={"api_public_surface": surface})

    facts = aspose_fact_records(
        bundle, family=_ABSENT_FAMILY, platform="python", clone_cache=tmp_path
    )
    verified, supporting = _verified_and_supporting(facts, "api.public_surface")

    assert verified is None
    assert supporting is not None
    assert [c["name"] for c in supporting.value["classes"]] == ["GhostClass"]


def test_api_public_surface_item_level_split_confirms_only_the_repo_matched_class(tmp_path):
    """Two public classes, only one of which is mechanically present in the
    pinned clone's real source -- item-level qualification, not a blanket
    aggregate flag: the verified record carries only the confirmed class
    and its exports; the unconfirmed one is preserved in a separate,
    always-unverified supporting record."""

    (tmp_path / "widget.py").write_text("class RealClass:\n    pass\n", encoding="utf-8")
    surface = ApiPublicSurfaceDetectionV1(
        modules=(
            ApiSurfaceModuleV1(
                module="widget", classes=(_class("RealClass"), _class("GhostClass"))
            ),
        ),
        model_sha=None,
    )
    bundle = _base_bundle(tmp_path).model_copy(update={"api_public_surface": surface})

    facts = aspose_fact_records(
        bundle, family=_ABSENT_FAMILY, platform="python", clone_cache=tmp_path
    )
    verified, supporting = _verified_and_supporting(facts, "api.public_surface")

    assert verified is not None
    assert [c["name"] for c in verified.value["classes"]] == ["RealClass"]
    assert verified.value["modules"] == [{"module": "widget", "exports": ["RealClass"]}]
    assert supporting is not None
    assert [c["name"] for c in supporting.value["classes"]] == ["GhostClass"]


def test_verified_non_python_api_members_enter_canonical_accountability_shape(tmp_path):
    """Imported receiver members remain usable by the shared exact-coordinate index."""

    (tmp_path / "document.go").write_text(
        "type Document struct{}\nfunc (d *Document) SetPassword(user string) {}\n",
        encoding="utf-8",
    )
    document = ApiSurfaceClassV1(
        name="Document",
        description="A PDF document.",
        kind="type_spec",
        methods=(
            ApiSurfaceMemberV1(
                name="SetPassword",
                doc="Configures encryption for the next save.",
                signature="SetPassword(user: string)",
            ),
        ),
        properties=(),
        state=_state(),
    )
    surface = ApiPublicSurfaceDetectionV1(
        modules=(ApiSurfaceModuleV1(module="Core API", classes=(document,)),),
        model_sha=None,
    )
    bundle = _base_bundle(tmp_path, "go").model_copy(update={"api_public_surface": surface})

    facts = aspose_fact_records(bundle, family=_ABSENT_FAMILY, platform="go", clone_cache=tmp_path)
    verified, _supporting = _verified_and_supporting(facts, "api.public_surface")

    assert verified is not None
    assert verified.value["classes"] == [
        {
            "name": "Document",
            "module": "Core API",
            "description": "A PDF document.",
            "kind": "type_spec",
            "members": [
                {
                    "name": "SetPassword",
                    "kind": "method",
                    "surface": "SetPassword(user: string)",
                    "doc": "Configures encryption for the next save.",
                    "declared_by": "Document",
                    "inherited": False,
                }
            ],
            "methods": [
                {
                    "name": "SetPassword",
                    "doc": "Configures encryption for the next save.",
                    "signature": "SetPassword(user: string)",
                }
            ],
            "properties": [],
            "state": {
                "visibility": "public",
                "reachable": "unknown",
                "implemented": "unknown",
            },
        }
    ]


def test_api_public_surface_unknown_visibility_never_enters_the_verified_exports_list(tmp_path):
    """Correction 3: even when the class's bare name IS present in the
    pinned clone's source (isolating that visibility, not text-matching, is
    the blocker here), an unknown-visibility entry must never share the
    verified record's `exports`/`classes` list with a confirmed-public one
    -- it stays in the supporting record, retained for reconciliation but
    never authorizing."""

    (tmp_path / "widget.py").write_text(
        "class RealClass:\n    pass\n\nclass MaybeClass:\n    pass\n", encoding="utf-8"
    )
    surface = ApiPublicSurfaceDetectionV1(
        modules=(
            ApiSurfaceModuleV1(
                module="widget",
                classes=(
                    _class("RealClass", visibility="public"),
                    _class("MaybeClass", visibility="unknown"),
                ),
            ),
        ),
        model_sha=None,
    )
    bundle = _base_bundle(tmp_path).model_copy(update={"api_public_surface": surface})

    facts = aspose_fact_records(
        bundle, family=_ABSENT_FAMILY, platform="python", clone_cache=tmp_path
    )
    verified, supporting = _verified_and_supporting(facts, "api.public_surface")

    assert verified is not None
    assert [c["name"] for c in verified.value["classes"]] == ["RealClass"]
    assert "MaybeClass" not in {c["name"] for c in verified.value["classes"]}
    assert "MaybeClass" not in [
        export for module in verified.value["modules"] for export in module["exports"]
    ]
    assert supporting is not None
    assert [c["name"] for c in supporting.value["classes"]] == ["MaybeClass"]


# --- Mandatory cross-ecosystem coverage: no product/family branch -----------

_PLATFORM_EXTENSIONS = [
    ("python", ".py"),
    ("net", ".cs"),
    ("java", ".java"),
    ("cpp", ".cpp"),
    ("go", ".go"),
    ("rust", ".rs"),
    ("typescript", ".ts"),
]


@pytest.mark.parametrize("platform,extension", _PLATFORM_EXTENSIONS)
def test_api_public_surface_item_level_confirmation_is_generic_across_every_platform(
    tmp_path, platform, extension
):
    """One fixture per registered platform, all driving the exact same
    generic word-boundary presence check against a data-driven extension
    table -- never a per-platform/family branch -- proving item-level
    repository qualification behaves identically everywhere."""

    (tmp_path / f"Sample{extension}").write_text(
        "// mentions RealSymbol somewhere in real source\nRealSymbol\n", encoding="utf-8"
    )
    surface = ApiPublicSurfaceDetectionV1(
        modules=(
            ApiSurfaceModuleV1(
                module="widget", classes=(_class("RealSymbol"), _class("GhostSymbol"))
            ),
        ),
        model_sha="b" * 40,
    )
    bundle = _base_bundle(tmp_path, platform).model_copy(update={"api_public_surface": surface})

    facts = aspose_fact_records(
        bundle, family=_ABSENT_FAMILY, platform=platform, clone_cache=tmp_path
    )
    verified, supporting = _verified_and_supporting(facts, "api.public_surface")

    assert verified is not None
    assert [c["name"] for c in verified.value["classes"]] == ["RealSymbol"]
    assert supporting is not None
    assert [c["name"] for c in supporting.value["classes"]] == ["GhostSymbol"]
