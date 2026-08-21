"""Knowledge-application layer, selection tier -- bounded relevance
selection, freshness/corroboration gating, and the per-claim disposition
ledger. Tested against the REAL imported corpus, mirroring
`test_aspose_knowledge_claims.py`'s convention."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from readme_agent.facts.aspose_knowledge_selection import (
    _MAX_SELECTED_PER_KIND,
    _MIN_CONFIDENCE,
    select_knowledge_claims,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_ROOT = _REPO_ROOT / "data" / "imported"

# The real, current repo_sha recorded in data/imported/knowledge/3d/python/merged/model.yaml.
_3D_PYTHON_REPO_SHA = "ee05c1ba9153ef5916b7a108406c794f2e464d01"
# barcode/python: the only bundle among the three test fixtures used here that
# carries real claims of every kind this test file exercises (license,
# dependency, api/api_method) -- 3d/python has none of those three kinds.
_BARCODE_PYTHON_REPO_SHA = "53f2c3350b8171f2c8275e7b1a178f218695ac45"


@pytest.fixture
def clone_without_license(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def clone_with_mit_license(tmp_path: Path) -> Path:
    (tmp_path / "LICENSE").write_text("MIT License\n\nCopyright ...\n", encoding="utf-8")
    return tmp_path


def test_select_knowledge_claims_product_platform_matching_real_data(clone_without_license):
    result = select_knowledge_claims(
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision=_3D_PYTHON_REPO_SHA,
    )

    assert result.family == "3d"
    assert result.platform == "python"
    assert result.freshness == "current"
    assert result.selected_count > 0
    assert all(d.family == "3d" and d.platform == "python" for d in result.dispositions)


def test_select_knowledge_claims_unmatched_product_selects_nothing(clone_without_license):
    result = select_knowledge_claims(
        "nonexistent-family",
        "nonexistent-platform",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision=None,
    )

    assert result.selected_count == 0
    assert result.rejected_count == 0
    assert result.fact_records == ()
    assert result.freshness == "unknown_revision"


def test_select_knowledge_claims_uncorroborated_stale_claims_are_never_output_eligible(
    clone_without_license,
):
    """Gate R2 regression test for the exact defect the review flagged: a
    stale/unknown-revision claim with no independent corroboration must
    never become output-eligible, even at high confidence -- confidence
    scaling alone must never be what makes it eligible. `format_support`
    claims in the real 3d/python corpus are all confidence 1.0, so this
    proves the rejection is not merely a confidence-floor side effect."""

    result = select_knowledge_claims(
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision="0" * 40,  # deliberately wrong -- proves staleness rejection
    )

    assert result.freshness == "stale_revision"
    stale_rejections = [
        d
        for d in result.dispositions
        if not d.accepted and d.rejection_reason == "stale_revision_uncorroborated"
    ]
    assert stale_rejections  # at least one claim was actually rejected for staleness
    high_confidence_stale_rejections = [
        d for d in stale_rejections if (d.confidence or 0.0) >= _MIN_CONFIDENCE
    ]
    assert high_confidence_stale_rejections  # high confidence alone never rescues it
    # Never merely confidence-scaled into eligibility via the old threshold path.
    assert not any(
        not d.accepted and d.rejection_reason == "below_confidence_threshold"
        for d in result.dispositions
    )
    rejected_ids = {d.global_claim_id for d in stale_rejections}
    for fact in result.fact_records:
        for entry in fact.value:
            assert entry["claim_id"] not in rejected_ids


def test_select_knowledge_claims_no_current_license_file_stays_unverified(
    clone_without_license,
):
    """No LICENSE file present in the current clone -- the imported "Licensed
    under MIT" claim is never corroborated (nothing to compare against) and
    stays capped at unverified, proving current repository evidence (its
    absence, here) is never silently overridden by imported knowledge."""

    result = select_knowledge_claims(
        "barcode",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision=_BARCODE_PYTHON_REPO_SHA,
    )

    license_fact = next(
        (f for f in result.fact_records if f.field == "aspose.license_claims"), None
    )
    assert license_fact is not None
    assert license_fact.verification_state == "unverified"


def test_select_knowledge_claims_current_repo_evidence_wins_on_real_license_conflict(
    tmp_path,
):
    """A real, current Apache-2.0 LICENSE file directly contradicts the
    imported "Licensed under MIT" claim -- a genuine SPDX mismatch, not mere
    absence of evidence. Current repository evidence always wins: the claim
    is rejected outright (never merely downgraded), and no license fact is
    fabricated from the losing imported claim."""

    (tmp_path / "LICENSE").write_text(
        "Apache License\nVersion 2.0, January 2004\n\nTERMS AND CONDITIONS...\n",
        encoding="utf-8",
    )

    result = select_knowledge_claims(
        "barcode",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_BARCODE_PYTHON_REPO_SHA,
    )

    license_fact = next(
        (f for f in result.fact_records if f.field == "aspose.license_claims"), None
    )
    assert license_fact is None  # the losing imported claim never reaches output
    conflict_dispositions = [
        d
        for d in result.dispositions
        if d.kind == "license"
        and d.rejection_reason == "conflicts_with_current_repository_evidence"
    ]
    assert conflict_dispositions
    assert all(not d.accepted for d in conflict_dispositions)


_FBX_EXPORTER_SOURCE = (
    "from typing import TYPE_CHECKING\n"
    "import io\n\n"
    "from ..Exporter import Exporter\n\n"
    "if TYPE_CHECKING:\n"
    "    from .FbxSaveOptions import FbxSaveOptions\n"
    "    from aspose.threed import Scene\n\n\n"
    "class FbxExporter(Exporter):\n"
    "    def save(self, filename: str, scene: 'Scene', options: 'FbxSaveOptions' = None):\n"
    '        raise NotImplementedError("FBX export is not implemented")\n\n'
    "    def save_to_stream(self, stream: io.IOBase, scene: 'Scene', "
    "options: 'FbxSaveOptions' = None):\n"
    '        raise NotImplementedError("FBX export is not implemented")\n'
)


def test_select_knowledge_claims_fbx_positive_claim_conflicts_with_stub_implementation(tmp_path):
    """K1 mandatory red/green fixture: the real 3D corpus claim
    `CLM-3d-2d3c40` asserts "export support for Fbx via FbxExporter", but
    the real, current `FbxExporter.save`/`save_to_stream` both raise
    `NotImplementedError`. File existence alone used to be treated as
    corroboration (the K1 defect); now the cited implementation's actual
    content is checked, and the positive claim is rejected as a genuine
    conflict, never selected into an authorizing fact."""

    fbx_dir = tmp_path / "aspose" / "threed" / "formats" / "fbx"
    fbx_dir.mkdir(parents=True)
    (fbx_dir / "FbxExporter.py").write_text(_FBX_EXPORTER_SOURCE, encoding="utf-8")

    result = select_knowledge_claims(
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_3D_PYTHON_REPO_SHA,
    )

    positive = next(
        d for d in result.dispositions if d.global_claim_id == "3d/python/CLM-3d-2d3c40"
    )
    assert positive.corroboration == "conflict"
    assert positive.accepted is False
    assert positive.rejection_reason == "conflicts_with_current_repository_evidence"

    format_support_facts = [
        f for f in result.fact_records if f.field == "aspose.format_support_claims"
    ]
    for fact in format_support_facts:
        assert all(entry["claim_id"] != "3d/python/CLM-3d-2d3c40" for entry in fact.value)


def test_select_knowledge_claims_fbx_limitation_claim_stays_corroborated(tmp_path):
    """The mirror of the conflict above: the real limitation claim
    `CLM-3d-f966ea` ("Not implemented: FbxExporter.save in
    .../FbxExporter.py:13") cites the exact same stub, and is retained as
    corroborated/verified -- negative evidence supports a negative claim."""

    fbx_dir = tmp_path / "aspose" / "threed" / "formats" / "fbx"
    fbx_dir.mkdir(parents=True)
    (fbx_dir / "FbxExporter.py").write_text(_FBX_EXPORTER_SOURCE, encoding="utf-8")

    result = select_knowledge_claims(
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_3D_PYTHON_REPO_SHA,
    )

    limitation = next(
        d for d in result.dispositions if d.global_claim_id == "3d/python/CLM-3d-f966ea"
    )
    assert limitation.corroboration == "corroborated"
    assert limitation.accepted is True
    assert limitation.verification_state == "verified"


def test_select_knowledge_claims_fbx_dispositions_are_deterministic(tmp_path):
    fbx_dir = tmp_path / "aspose" / "threed" / "formats" / "fbx"
    fbx_dir.mkdir(parents=True)
    (fbx_dir / "FbxExporter.py").write_text(_FBX_EXPORTER_SOURCE, encoding="utf-8")

    kwargs = dict(
        family="3d",
        platform="python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_3D_PYTHON_REPO_SHA,
    )
    first = select_knowledge_claims(**kwargs)
    second = select_knowledge_claims(**kwargs)

    assert [d.model_dump(mode="json") for d in first.dispositions] == [
        d.model_dump(mode="json") for d in second.dispositions
    ]
    assert [f.model_dump(mode="json") for f in first.fact_records] == [
        f.model_dump(mode="json") for f in second.fact_records
    ]


_PDF_RENDERER_SOURCE = (
    '"""PDF renderer."""\n\n'
    "from __future__ import annotations\n\n"
    "from aspose_barcode_foss._internal.models.artifacts import RenderedArtifact\n"
    "from aspose_barcode_foss._internal.models.options import ResolvedRenderOptions\n"
    "from aspose_barcode_foss._internal.models.symbols import EncodedSymbol\n"
    "from aspose_barcode_foss._internal.models.text import TextLayout\n"
    "from aspose_barcode_foss._internal.renderers.base import Renderer\n\n\n"
    "class PdfRenderer(Renderer):\n"
    '    """Render a barcode into PDF or another vector-friendly artifact."""\n\n'
    "    def render(\n"
    "        self,\n"
    "        symbol: EncodedSymbol,\n"
    "        *,\n"
    "        layout: TextLayout,\n"
    "        options: ResolvedRenderOptions,\n"
    "    ) -> RenderedArtifact:\n"
    '        """Render an encoded symbol as PDF."""\n'
    "        raise NotImplementedError\n"
)


def test_select_knowledge_claims_barcode_pdf_positive_claim_conflicts_with_stub_implementation(
    tmp_path,
):
    """K1 mandatory red/green fixture: the real Barcode corpus claim
    `CLM-barcode-5c60a4` asserts "export support for Pdf via PdfRenderer",
    but the real, current `PdfRenderer.render` raises `NotImplementedError`.
    No simultaneous positive capability authorization when implementation
    evidence is negative."""

    pdf_dir = tmp_path / "src" / "aspose_barcode_foss" / "_internal" / "renderers"
    pdf_dir.mkdir(parents=True)
    (pdf_dir / "pdf.py").write_text(_PDF_RENDERER_SOURCE, encoding="utf-8")

    result = select_knowledge_claims(
        "barcode",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_BARCODE_PYTHON_REPO_SHA,
    )

    positive = next(
        d for d in result.dispositions if d.global_claim_id == "barcode/python/CLM-barcode-5c60a4"
    )
    assert positive.corroboration == "conflict"
    assert positive.accepted is False

    limitation = next(
        d for d in result.dispositions if d.global_claim_id == "barcode/python/CLM-barcode-ca5609"
    )
    assert limitation.corroboration == "corroborated"
    assert limitation.accepted is True
    assert limitation.verification_state == "verified"

    format_support_facts = [
        f for f in result.fact_records if f.field == "aspose.format_support_claims"
    ]
    for fact in format_support_facts:
        assert all(entry["claim_id"] != "barcode/python/CLM-barcode-5c60a4" for entry in fact.value)


_COLLADA_EXPORTER_SOURCE = (
    "from typing import TYPE_CHECKING\n"
    "import xml.etree.ElementTree as ET\n\n"
    "from ..Exporter import Exporter\n\n"
    "if TYPE_CHECKING:\n"
    "    from aspose.threed import Scene\n"
    "    from .ColladaSaveOptions import ColladaSaveOptions\n\n\n"
    "class ColladaExporter(Exporter):\n"
    "    def __init__(self):\n"
    "        super().__init__()\n"
    "        self._node_counter = 0\n\n"
    "    def supports_format(self, file_format) -> bool:\n"
    "        from .ColladaFormat import ColladaFormat\n"
    "        return isinstance(file_format, ColladaFormat)\n\n"
    "    def export(self, scene: 'Scene', stream, options: 'ColladaSaveOptions'):\n"
    "        content = self._write_collada(scene, options)\n"
    "        stream.write(content.encode('utf-8'))\n\n"
    "    def _write_collada(self, scene, options) -> str:\n"
    "        collada = ET.Element('COLLADA')\n"
    "        return ET.tostring(collada, encoding='unicode')\n"
)


def test_select_knowledge_claims_collada_class_level_citation_reflects_real_implementation(
    tmp_path,
):
    """K1 mandatory public/internal-distinction fixture: `ColladaExporter`
    is genuinely implemented (`supports_format`/`export` both have real
    bodies, not stubs), and its evidence is cited at the class-declaration
    line, not inside a specific method -- the class-wide fallback must
    correctly classify this as positive evidence and keep the real corpus
    claim `CLM-3d-cc8796` corroborated, proving the FBX-style rejection
    above is a genuine content check, not a blanket "class-line citation is
    always suspect" rule."""

    collada_dir = tmp_path / "aspose" / "threed" / "formats" / "collada"
    collada_dir.mkdir(parents=True)
    (collada_dir / "ColladaExporter.py").write_text(_COLLADA_EXPORTER_SOURCE, encoding="utf-8")

    result = select_knowledge_claims(
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_3D_PYTHON_REPO_SHA,
    )

    positive = next(
        d for d in result.dispositions if d.global_claim_id == "3d/python/CLM-3d-cc8796"
    )
    assert positive.corroboration == "corroborated"
    assert positive.accepted is True
    assert positive.verification_state == "verified"


_PNG_RENDERER_SOURCE = (
    '"""PNG renderer."""\n\n'
    "from __future__ import annotations\n\n"
    "import io\n\n"
    "import PIL.Image\n"
    "import PIL.ImageColor\n"
    "import PIL.ImageDraw\n"
    "import PIL.ImageFont\n\n"
    "from aspose_barcode_foss._internal.exceptions import RenderingError\n"
    "from aspose_barcode_foss._internal.models.artifacts import RenderedArtifact\n"
    "from aspose_barcode_foss._internal.models.options import ResolvedRenderOptions\n"
    "from aspose_barcode_foss._internal.models.symbols import EncodedSymbol\n"
    "from aspose_barcode_foss._internal.models.text import TextLayout\n"
    "from aspose_barcode_foss._internal.renderers._matrix import _iter_dark_runs\n"
    "from aspose_barcode_foss._internal.renderers.base import Renderer\n\n\n"
    "_ANCHOR_MAP: dict[str, str] = {\n"
    '    "start": "lt",\n'
    '    "middle": "mt",\n'
    '    "end": "rt",\n'
    "}\n\n\n"
    # The real cited evidence line (28) is the class declaration below --
    # the padding above faithfully reproduces the real file's leading
    # import/constant block so the line offset matches the real claim.
    "class PngRenderer(Renderer):\n"
    '    """Render a barcode into PNG output."""\n\n'
    "    def render(self, symbol, *, layout, options) -> RenderedArtifact:\n"
    '        """Render an encoded symbol as PNG."""\n'
    "        image_bytes = self._draw(symbol, layout, options)\n"
    "        return RenderedArtifact(data=image_bytes, media_type='image/png', backend='png')\n\n"
    "    def _draw(self, symbol, layout, options) -> bytes:\n"
    "        buf = io.BytesIO()\n"
    "        buf.write(b'\\x89PNG')\n"
    "        return buf.getvalue()\n"
)


def test_select_knowledge_claims_true_supported_export_reaches_verified(tmp_path):
    """Replaces the old placeholder-file expectation this test file used to
    encode (source_knowledge_truth audit finding): a claim whose cited
    implementation is genuinely real -- not a stub, not a bare comment -- is
    corroborated on real content, not merely because the cited file exists.
    Uses the real Barcode corpus claim `CLM-barcode-2794b6` ("export support
    for Png via PngRenderer"), whose cited `PngRenderer.render` is a real,
    working implementation."""

    png_dir = tmp_path / "src" / "aspose_barcode_foss" / "_internal" / "renderers"
    png_dir.mkdir(parents=True)
    (png_dir / "png.py").write_text(_PNG_RENDERER_SOURCE, encoding="utf-8")

    result = select_knowledge_claims(
        "barcode",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_BARCODE_PYTHON_REPO_SHA,
    )

    positive = next(
        d for d in result.dispositions if d.global_claim_id == "barcode/python/CLM-barcode-2794b6"
    )
    assert positive.corroboration == "corroborated"
    assert positive.accepted is True
    assert positive.verification_state == "verified"
    fact = next(f for f in result.fact_records if f.field == "aspose.format_support_claims")
    assert any(entry["claim_id"] == "barcode/python/CLM-barcode-2794b6" for entry in fact.value)


def test_select_knowledge_claims_corroborated_license_reaches_verified(clone_with_mit_license):
    """A real MIT LICENSE file in the current clone corroborates the
    imported "Licensed under MIT" claim -- it reaches `verified`, the one
    real corroboration path this layer implements."""

    result = select_knowledge_claims(
        "barcode",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=clone_with_mit_license,
        source_revision=_BARCODE_PYTHON_REPO_SHA,
    )

    license_fact = next(
        (f for f in result.fact_records if f.field == "aspose.license_claims"), None
    )
    assert license_fact is not None
    assert license_fact.verification_state == "verified"

    license_disposition = next(d for d in result.dispositions if d.kind == "license" and d.accepted)
    assert license_disposition.verification_state == "verified"


def test_select_knowledge_claims_bounded_selection_never_exceeds_cap(clone_without_license):
    """3d/python's real corpus has far more than `_MAX_SELECTED_PER_KIND`
    claims in several kinds (1400 api_method, 987 api, 112 feature, ...) --
    proves the cap is enforced against real over-supply, not merely
    documented."""

    result = select_knowledge_claims(
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision=_3D_PYTHON_REPO_SHA,
    )

    for fact in result.fact_records:
        assert len(fact.value) <= _MAX_SELECTED_PER_KIND

    cap_rejections = [
        d for d in result.dispositions if d.rejection_reason == "exceeds_selection_cap"
    ]
    assert cap_rejections  # the real corpus genuinely exceeds the cap for at least one kind


def test_select_knowledge_claims_selection_is_by_confidence_not_file_order(clone_without_license):
    """Selection ranks by confidence (descending) across the whole target
    FIELD (`format` and `format_support` share one field), never by
    claims.json's own insertion order -- the "not arbitrary first-N
    truncation" requirement. Every claim accepted into a field has
    confidence >= every claim rejected from that same field for exceeding
    the selection cap (grouped by field, not by raw `kind`, since two kinds
    can legitimately differ in typical confidence -- observed for real:
    `format_support` claims are always confidence 1.0, `format` claims
    range 0.75-0.95, so an all-format_support top-N is correct ranking
    behavior, not a bug)."""

    result = select_knowledge_claims(
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision=_3D_PYTHON_REPO_SHA,
    )

    by_field_accepted: dict[str, list[float]] = {}
    by_field_capped: dict[str, list[float]] = {}
    for d in result.dispositions:
        if d.confidence is None or d.resulting_fact_field is None:
            continue
        if d.accepted:
            by_field_accepted.setdefault(d.resulting_fact_field, []).append(d.confidence)
        elif d.rejection_reason == "exceeds_selection_cap":
            by_field_capped.setdefault(d.resulting_fact_field, []).append(d.confidence)

    assert by_field_capped  # the real corpus genuinely exceeds the cap for at least one field
    for field, capped_confidences in by_field_capped.items():
        accepted_confidences = by_field_accepted[field]
        assert min(accepted_confidences) >= max(capped_confidences)


def test_select_knowledge_claims_dependency_and_api_kinds_are_explicitly_never_selected(
    clone_without_license,
):
    """`dependency` (covered by the existing aspose.dependency_claims field)
    and `api*` (covered by the structural api_surface.json field) are
    rejected with an explicit, real reason -- never silently dropped and
    never duplicated across two divergent fact fields."""

    result = select_knowledge_claims(
        "barcode",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision=_BARCODE_PYTHON_REPO_SHA,
    )

    for kind, expected_reason in (
        ("dependency", "kind_covered_by_existing_dependency_claims_field"),
        ("api", "kind_covered_by_api_surface_field"),
        ("api_method", "kind_covered_by_api_surface_field"),
    ):
        matching = [d for d in result.dispositions if d.kind == kind]
        assert matching, f"expected real {kind!r} claims in the 3d/python corpus"
        assert all(not d.accepted and d.rejection_reason == expected_reason for d in matching)

    assert not any(f.field.startswith("aspose.dependency") for f in result.fact_records)
    assert not any(f.field.startswith("aspose.api") for f in result.fact_records)


def test_select_knowledge_claims_every_considered_claim_has_exactly_one_disposition(
    clone_without_license,
):
    """No silent-drop path: every claim in the real corpus for this
    product/platform appears in the disposition ledger exactly once."""

    from readme_agent.facts.aspose_knowledge_claims import load_knowledge_claims

    all_claims = load_knowledge_claims("barcode", "python", data_root=_DATA_ROOT)
    result = select_knowledge_claims(
        "barcode",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision=None,
    )

    disposed_ids = [d.global_claim_id for d in result.dispositions]
    assert len(disposed_ids) == len(set(disposed_ids))  # each claim disposed exactly once
    assert set(disposed_ids) == {claim.global_claim_id for claim in all_claims}
    assert result.selected_count + result.rejected_count == len(all_claims)


def test_select_knowledge_claims_min_confidence_threshold_is_real_and_positive():
    assert 0.0 < _MIN_CONFIDENCE <= 1.0


def test_select_knowledge_claims_platform_mismatched_keyword_never_leaks_into_another_platform(
    clone_without_license,
):
    """Negative test: selecting knowledge for one family/platform never
    returns claims tagged with a different family or platform -- proves
    the loader/selector is scoped correctly, not merely documented as such."""

    result = select_knowledge_claims(
        "cells",
        "java",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision=None,
    )

    for disposition in result.dispositions:
        assert disposition.family == "cells"
        assert disposition.platform == "java"
    for fact in result.fact_records:
        assert fact.source.location == "data/imported:cells/java"


def _write_synthetic_bundle(
    data_root: Path, family: str, platform: str, repo_sha: str, claims: list[dict]
) -> None:
    (data_root / "data").mkdir(parents=True, exist_ok=True)
    (data_root / "data" / "products.json").write_text(
        json.dumps([{"family": family, "platform": platform}]), encoding="utf-8"
    )
    bundle = data_root / "knowledge" / family / platform / "merged"
    bundle.mkdir(parents=True)
    (bundle / "claims.json").write_text(json.dumps(claims), encoding="utf-8")
    (bundle / "model.yaml").write_text(
        f"family: {family}\nplatform: {platform}\nrepo_sha: {repo_sha}\n", encoding="utf-8"
    )


def test_select_knowledge_claims_readme_overlap_frees_cap_slot_for_new_information(tmp_path):
    """Gate R3: the existing-README/duplication/section-need signal is not
    merely a tiebreaker cosmetic reorder -- it can change WHICH claims
    survive the selection cap. 8 high-confidence claims the README already
    states compete against 1 lower-confidence claim the README does not --
    the new-information claim must win a cap slot over one already-stated
    claim, proving ranking is genuinely multi-signal, not confidence+kind+id
    alone."""

    data_root = tmp_path / "data-root"
    clone_cache = tmp_path / "clone"
    clone_cache.mkdir()
    repo_sha = "f" * 40
    already_stated = [
        {
            "claim_id": f"ALREADY-{i}",
            "kind": "feature",
            "text": f"Supports scenario number {i} for advanced processing",
            "confidence": 0.9,
        }
        for i in range(8)
    ]
    new_information = {
        "claim_id": "NEW-INFO",
        "kind": "feature",
        "text": "Supports an entirely undocumented capability the README omits",
        "confidence": 0.55,
    }
    _write_synthetic_bundle(
        data_root, "synthfam", "python", repo_sha, [*already_stated, new_information]
    )
    (clone_cache / "README.md").write_text(
        "\n".join(c["text"] for c in already_stated), encoding="utf-8"
    )

    result = select_knowledge_claims(
        "synthfam",
        "python",
        data_root=data_root,
        clone_cache=clone_cache,
        source_revision=repo_sha,
    )

    selected_ids = {d.global_claim_id.rsplit("/", 1)[-1] for d in result.dispositions if d.accepted}
    assert "NEW-INFO" in selected_ids
    assert len(selected_ids) == _MAX_SELECTED_PER_KIND
    cap_rejected = [
        d
        for d in result.dispositions
        if not d.accepted and d.rejection_reason == "exceeds_selection_cap"
    ]
    assert len(cap_rejected) == 1
    assert cap_rejected[0].already_in_readme is True
    new_info_disposition = next(
        d for d in result.dispositions if d.global_claim_id.endswith("NEW-INFO")
    )
    assert new_info_disposition.already_in_readme is False
    assert new_info_disposition.accepted is True


def test_select_knowledge_claims_near_duplicate_claims_are_suppressed_not_double_selected(
    tmp_path,
):
    """Gate R3 duplication signal: two claims with identical normalized text
    (real corpus scout runs can emit near-duplicates across passes) never
    both consume a fact's value list -- the lower-ranked one is rejected
    with an explicit, inspectable reason, never silently kept as a
    redundant twin."""

    data_root = tmp_path / "data-root"
    clone_cache = tmp_path / "clone"
    clone_cache.mkdir()
    repo_sha = "a" * 40
    claims = [
        {
            "claim_id": "DUP-HIGH",
            "kind": "limitation",
            "text": "Does not support encrypted archives",
            "confidence": 0.9,
        },
        {
            "claim_id": "DUP-LOW",
            "kind": "limitation",
            "text": "does not support encrypted archives.",
            "confidence": 0.6,
        },
    ]
    _write_synthetic_bundle(data_root, "synthfam2", "python", repo_sha, claims)

    result = select_knowledge_claims(
        "synthfam2",
        "python",
        data_root=data_root,
        clone_cache=clone_cache,
        source_revision=repo_sha,
    )

    accepted = [d for d in result.dispositions if d.accepted]
    assert len(accepted) == 1
    assert accepted[0].global_claim_id.endswith("DUP-HIGH")
    duplicate_rejection = next(
        d for d in result.dispositions if d.global_claim_id.endswith("DUP-LOW")
    )
    assert duplicate_rejection.accepted is False
    assert duplicate_rejection.rejection_reason == "duplicate_of_higher_ranked_claim"


def test_select_knowledge_claims_search_intent_keyword_outranks_equal_confidence_claim(
    tmp_path,
):
    """Gate R3 search-intent signal: among two equally-confident,
    equally-uncorroborated, equally-not-in-README claims, the one naming a
    real, relevance-filtered SEO keyword for this product
    (`aspose_detectors.detect_relevant_seo_keywords`, reused rather than
    reinvented) ranks first."""

    data_root = tmp_path / "data-root"
    clone_cache = tmp_path / "clone"
    clone_cache.mkdir()
    repo_sha = "b" * 40
    claims = [
        {
            "claim_id": "NO-KEYWORD",
            "kind": "feature",
            "text": "Handles routine internal bookkeeping",
            "confidence": 0.7,
        },
        {
            "claim_id": "HAS-KEYWORD",
            "kind": "feature",
            "text": "synthfam3 python library provides a fast processing pipeline",
            "confidence": 0.7,
        },
    ]
    _write_synthetic_bundle(data_root, "synthfam3", "python", repo_sha, claims)
    keywords_dir = data_root / "keywords"
    keywords_dir.mkdir(parents=True)
    (keywords_dir / "synthfam3.json").write_text(
        json.dumps(
            [
                {
                    "sourcePath": ("content/products.aspose.org/en/synthfam3/python/_index.md"),
                    "keywords": ["synthfam3 python library"],
                }
            ]
        ),
        encoding="utf-8",
    )

    result = select_knowledge_claims(
        "synthfam3",
        "python",
        data_root=data_root,
        clone_cache=clone_cache,
        source_revision=repo_sha,
    )

    fact = next(f for f in result.fact_records if f.field == "aspose.feature_claims")
    ranked_claim_ids = [entry["claim_id"].rsplit("/", 1)[-1] for entry in fact.value]
    assert ranked_claim_ids.index("HAS-KEYWORD") < ranked_claim_ids.index("NO-KEYWORD")


def test_select_knowledge_claims_mixed_verified_and_unverified_never_merge_into_one_fact(
    tmp_path,
):
    """K1 mandatory red/green: a synthetic field with one genuinely
    corroborated item and two uncorroborated-but-fresh items must never
    become a single `verified` aggregate (the `verified_any` laundering
    defect this commit removes) -- the verified item gets its own
    authorizing fact, the two unverified items are visible only in a
    separate, non-authorizing supporting fact, and no unverified claim ID
    ever appears in the verified fact's value."""

    data_root = tmp_path / "data-root"
    clone_cache = tmp_path / "clone"
    repo_sha = "c" * 40
    real_dir = clone_cache / "pkg"
    real_dir.mkdir(parents=True)
    (real_dir / "widget.py").write_text(
        "class Widget:\n    def export(self):\n        return b'real bytes'\n",
        encoding="utf-8",
    )
    claims = [
        {
            "claim_id": "VERIFIED-ONE",
            "kind": "format_support",
            "text": "export support for PDF via Widget",
            "confidence": 0.9,
            "evidence": [{"file": "pkg/widget.py", "line": 2}],
        },
        {
            "claim_id": "UNVERIFIED-ONE",
            "kind": "format_support",
            "text": "export support for PNG via UndocumentedWriter",
            "confidence": 0.8,
            "evidence": [],
        },
        {
            "claim_id": "UNVERIFIED-TWO",
            "kind": "format_support",
            "text": "export support for SVG via UndocumentedWriter",
            "confidence": 0.7,
            "evidence": [],
        },
    ]
    _write_synthetic_bundle(data_root, "synthmix", "python", repo_sha, claims)

    result = select_knowledge_claims(
        "synthmix",
        "python",
        data_root=data_root,
        clone_cache=clone_cache,
        source_revision=repo_sha,
    )

    matching = [f for f in result.fact_records if f.field == "aspose.format_support_claims"]
    assert len(matching) == 2
    verified_fact = next(f for f in matching if f.verification_state == "verified")
    supporting_fact = next(f for f in matching if f.verification_state == "unverified")
    assert verified_fact.fact_id != supporting_fact.fact_id

    verified_claim_ids = {entry["claim_id"] for entry in verified_fact.value}
    supporting_claim_ids = {entry["claim_id"] for entry in supporting_fact.value}
    assert verified_claim_ids == {"synthmix/python/VERIFIED-ONE"}
    assert supporting_claim_ids == {
        "synthmix/python/UNVERIFIED-ONE",
        "synthmix/python/UNVERIFIED-TWO",
    }
    assert verified_claim_ids.isdisjoint(supporting_claim_ids)


def test_select_knowledge_claims_source_file_evidence_key_is_evaluated(tmp_path):
    """K1 mandatory red/green: LLM-enriched claims cite `source_file`, not
    `file` -- corroboration must actually resolve and check that key, not
    silently ignore it because the old code only ever read `file`."""

    data_root = tmp_path / "data-root"
    clone_cache = tmp_path / "clone"
    clone_cache.mkdir()
    repo_sha = "d" * 40
    (clone_cache / "README.md").write_text(
        "## Supported Formats\nThis library supports exporting to Widget format.\n",
        encoding="utf-8",
    )
    claims = [
        {
            "claim_id": "SOURCE-FILE-FRESH",
            "kind": "feature",
            "text": "The library supports exporting to Widget format.",
            "confidence": 0.9,
            "evidence": [
                {
                    "source_file": "README.md",
                    "snippet": "This library supports exporting to Widget format.",
                }
            ],
        }
    ]
    _write_synthetic_bundle(data_root, "synthsrc", "python", repo_sha, claims)

    result = select_knowledge_claims(
        "synthsrc",
        "python",
        data_root=data_root,
        clone_cache=clone_cache,
        source_revision=repo_sha,
    )

    disposition = next(
        d for d in result.dispositions if d.global_claim_id == "synthsrc/python/SOURCE-FILE-FRESH"
    )
    assert disposition.corroboration == "corroborated"
    assert disposition.verification_state == "verified"


def test_select_knowledge_claims_traversal_evidence_path_cannot_corroborate(tmp_path):
    """K1 mandatory red/green: an evidence path that escapes the pinned
    clone root via traversal must never resolve, let alone corroborate --
    real content one directory above the clone must stay invisible."""

    data_root = tmp_path / "data-root"
    clone_cache = tmp_path / "clone"
    clone_cache.mkdir()
    (tmp_path / "outside-secret.py").write_text(
        "class Anything:\n    def do(self):\n        return 1\n", encoding="utf-8"
    )
    repo_sha = "e" * 40
    claims = [
        {
            "claim_id": "TRAVERSAL",
            "kind": "feature",
            "text": "Claims a capability via a traversal path",
            "confidence": 0.9,
            "evidence": [{"file": "../outside-secret.py", "line": 2}],
        }
    ]
    _write_synthetic_bundle(data_root, "synthtrav", "python", repo_sha, claims)

    result = select_knowledge_claims(
        "synthtrav",
        "python",
        data_root=data_root,
        clone_cache=clone_cache,
        source_revision=repo_sha,
    )

    disposition = next(
        d for d in result.dispositions if d.global_claim_id == "synthtrav/python/TRAVERSAL"
    )
    assert disposition.corroboration == "uncorroborated"


def test_select_knowledge_claims_stale_snippet_cannot_corroborate(tmp_path):
    """K1 mandatory red/green: an enriched claim's cited snippet that no
    longer appears verbatim in the current file (captured from a
    since-refreshed README, per the real KGAP-003 finding) must never
    corroborate, even though the underlying fact might still be true."""

    data_root = tmp_path / "data-root"
    clone_cache = tmp_path / "clone"
    clone_cache.mkdir()
    (clone_cache / "README.md").write_text(
        "Current content, unrelated to the old captured snippet.\n", encoding="utf-8"
    )
    repo_sha = "f" * 40
    claims = [
        {
            "claim_id": "STALE-SNIPPET",
            "kind": "feature",
            "text": "The library supports an advanced processing mode.",
            "confidence": 0.9,
            "evidence": [
                {
                    "source_file": "README.md",
                    "snippet": "### Advanced Processing (Implemented)\n- Mode A\n- Mode B",
                }
            ],
        }
    ]
    _write_synthetic_bundle(data_root, "synthstale", "python", repo_sha, claims)

    result = select_knowledge_claims(
        "synthstale",
        "python",
        data_root=data_root,
        clone_cache=clone_cache,
        source_revision=repo_sha,
    )

    disposition = next(
        d for d in result.dispositions if d.global_claim_id == "synthstale/python/STALE-SNIPPET"
    )
    assert disposition.corroboration == "uncorroborated"


def test_select_knowledge_claims_api_kind_falls_back_to_selection_when_surface_is_empty(
    tmp_path,
):
    """K2 mandatory red/green: an empty/invalid structured API surface must
    never silently suppress api*-kind imported claims as "covered" -- with
    no usable `api_surface.json` for this product (no such file at all,
    here), they become normally selectable, corroborated fallback evidence
    like every other claim kind, instead of a blanket
    `kind_covered_by_api_surface_field` rejection that is not actually
    true."""

    data_root = tmp_path / "data-root"
    clone_cache = tmp_path / "clone"
    repo_sha = "9a" * 20
    real_dir = clone_cache / "pkg"
    real_dir.mkdir(parents=True)
    (real_dir / "widget.py").write_text(
        "class Widget:\n    def export(self):\n        return b'ok'\n", encoding="utf-8"
    )
    claims = [
        {
            "claim_id": "API-FALLBACK",
            "kind": "api_method",
            "text": "Widget.export() -> bytes",
            "confidence": 0.9,
            "evidence": [{"file": "pkg/widget.py", "line": 2}],
        }
    ]
    _write_synthetic_bundle(data_root, "synthapi", "python", repo_sha, claims)

    result = select_knowledge_claims(
        "synthapi",
        "python",
        data_root=data_root,
        clone_cache=clone_cache,
        source_revision=repo_sha,
    )

    disposition = next(
        d for d in result.dispositions if d.global_claim_id == "synthapi/python/API-FALLBACK"
    )
    assert disposition.rejection_reason != "kind_covered_by_api_surface_field"
    assert disposition.accepted is True
    assert disposition.corroboration == "corroborated"
    assert disposition.resulting_fact_field == "aspose.api_claims"
    fact = next(f for f in result.fact_records if f.field == "aspose.api_claims")
    assert any(entry["claim_id"] == "synthapi/python/API-FALLBACK" for entry in fact.value)


def test_select_knowledge_claims_api_claim_uncovered_by_a_real_surface_still_falls_back(
    tmp_path,
):
    """K1/K2-course-correction mandatory red/green: a product WITH a real,
    non-empty canonical API surface must not blanket-suppress every
    api*-kind claim as "covered" -- only a claim whose own named symbol
    genuinely appears in that surface is rejected; a claim naming a symbol
    the surface does not contain still falls through to the same
    selection/corroboration pipeline as any other kind."""

    data_root = tmp_path / "data-root"
    clone_cache = tmp_path / "clone"
    repo_sha = "8b" * 20
    real_dir = clone_cache / "pkg"
    real_dir.mkdir(parents=True)
    (real_dir / "other.py").write_text(
        "class OtherThing:\n    def run(self):\n        return b'ok'\n", encoding="utf-8"
    )
    claims = [
        {
            "claim_id": "COVERED",
            "kind": "api_method",
            "text": "Widget.export() -> bytes",
            "confidence": 0.9,
            "evidence": [],
        },
        {
            "claim_id": "UNCOVERED",
            "kind": "api_method",
            "text": "OtherThing.run() -> bytes",
            "confidence": 0.9,
            "evidence": [{"file": "pkg/other.py", "line": 2}],
        },
    ]
    _write_synthetic_bundle(data_root, "synthapi2", "python", repo_sha, claims)
    (data_root / "knowledge" / "synthapi2" / "python" / "merged" / "api_surface.json").write_text(
        json.dumps(
            [
                {
                    "name": "Widget",
                    "kind": "class_definition",
                    "visibility": "public",
                    "methods": [{"name": "export", "params": [], "return_type": "bytes"}],
                    "properties": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    result = select_knowledge_claims(
        "synthapi2",
        "python",
        data_root=data_root,
        clone_cache=clone_cache,
        source_revision=repo_sha,
    )

    covered = next(
        d for d in result.dispositions if d.global_claim_id == "synthapi2/python/COVERED"
    )
    assert covered.accepted is False
    assert covered.rejection_reason == "kind_covered_by_api_surface_field"

    uncovered = next(
        d for d in result.dispositions if d.global_claim_id == "synthapi2/python/UNCOVERED"
    )
    assert uncovered.rejection_reason != "kind_covered_by_api_surface_field"
    assert uncovered.accepted is True
    assert uncovered.resulting_fact_field == "aspose.api_claims"
