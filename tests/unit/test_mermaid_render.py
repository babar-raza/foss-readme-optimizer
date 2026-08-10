"""Official Mermaid SVG geometry proof contracts."""

from __future__ import annotations

from readme_agent.readme.header_visual_models import MermaidNodeV1, ReadmeHeaderVisualV1
from readme_agent.verification.mermaid_render import (
    MermaidRenderError,
    verify_official_mermaid_render,
)


def _visual(count: int = 6) -> ReadmeHeaderVisualV1:
    nodes = [
        MermaidNodeV1(
            node_id="PRODUCT",
            role="product",
            label="Aspose.Note FOSS for Python",
            fact_ids=["identity"],
        ),
        MermaidNodeV1(
            node_id="I1",
            role="input",
            label="OneNote files",
            fact_ids=["formats"],
        ),
        *[
            MermaidNodeV1(
                node_id=f"C{index}",
                role="capability",
                label=f"Capability {index}",
                fact_ids=["capabilities"],
            )
            for index in range(1, count + 1)
        ],
        MermaidNodeV1(
            node_id="O1",
            role="output",
            label="PDF files",
            fact_ids=["formats"],
        ),
    ]
    return ReadmeHeaderVisualV1(
        title="Aspose.Note FOSS for Python",
        title_fact_ids=["identity"],
        diagram_nodes=nodes,
        mermaid_source="flowchart LR\n",
        mermaid_markdown="```mermaid\nflowchart LR\n```",
    )


def _svg(*, one_column: bool = False) -> bytes:
    groups = [
        '<g id="my-svg-flowchart-PRODUCT-1" transform="translate(400, -100)">'
        '<rect class="basic label-container" width="200" height="40"/></g>',
        '<g id="my-svg-flowchart-I1-0" transform="translate(100, -100)">'
        '<rect class="basic label-container" width="200" height="40"/></g>',
        '<g id="my-svg-flowchart-O1-9" transform="translate(1300, -100)">'
        '<rect class="basic label-container" width="200" height="40"/></g>',
    ]
    positions = [(700, -180), (700, -140), (700, -60), (1000, -180), (1000, -140), (1000, -60)]
    if one_column:
        positions = [(700, -180 + index * 40) for index in range(6)]
    groups.extend(
        f'<g id="my-svg-flowchart-C{index}-{index + 1}" transform="translate({x}, {y})">'
        '<rect class="basic label-container" width="250" height="30"/></g>'
        for index, (x, y) in enumerate(positions, start=1)
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1450 300" '
        'aria-roledescription="flowchart-v2">'
        + "".join(groups)
        + '<path id="my-svg-L_I1_PRODUCT_0"/>'
        + '<path id="my-svg-L_PRODUCT_CORE_0"/>'
        + '<path id="my-svg-L_CORE_O1_0"/>'
        + "</svg>"
    ).encode()


def test_official_render_proof_accepts_compact_two_column_geometry(tmp_path):
    proof = verify_official_mermaid_render(
        _visual(),
        renderer=lambda _source: _svg(),
        cache_dir=tmp_path,
    )

    assert proof.valid
    assert proof.checks["capability_columns_adaptive"]
    assert proof.checks["semantic_relationship_connectors_rendered"]
    assert proof.aspect_ratio > 4


def test_official_render_proof_rejects_six_capabilities_in_one_column(tmp_path):
    try:
        verify_official_mermaid_render(
            _visual(),
            renderer=lambda _source: _svg(one_column=True),
            cache_dir=tmp_path,
        )
    except MermaidRenderError as exc:
        assert "capability_columns_adaptive" in str(exc)
    else:
        raise AssertionError("invalid Mermaid geometry was accepted")


def test_official_render_proof_requires_every_semantic_node(tmp_path):
    incomplete = _svg().replace(b"my-svg-flowchart-C6-7", b"my-svg-flowchart-X6-7")

    try:
        verify_official_mermaid_render(
            _visual(),
            renderer=lambda _source: incomplete,
            cache_dir=tmp_path,
        )
    except MermaidRenderError as exc:
        assert "all_semantic_nodes_rendered" in str(exc)
    else:
        raise AssertionError("incomplete Mermaid render was accepted")


def test_official_render_proof_requires_only_evidence_present_endpoint_links(tmp_path):
    visual = _visual().model_copy(
        update={
            "diagram_nodes": [
                node for node in _visual().diagram_nodes if node.role not in {"input", "output"}
            ]
        }
    )
    svg = (
        _svg()
        .replace(b'<path id="my-svg-L_I1_PRODUCT_0"/>', b"")
        .replace(b'<path id="my-svg-L_CORE_O1_0"/>', b"")
    )

    proof = verify_official_mermaid_render(
        visual,
        renderer=lambda _source: svg,
        cache_dir=tmp_path,
    )

    assert proof.valid
    assert proof.checks["semantic_relationship_connectors_rendered"]


def test_official_render_proof_rejects_missing_present_endpoint_link(tmp_path):
    svg = _svg().replace(b'<path id="my-svg-L_CORE_O1_0"/>', b"")

    try:
        verify_official_mermaid_render(
            _visual(),
            renderer=lambda _source: svg,
            cache_dir=tmp_path,
        )
    except MermaidRenderError as exc:
        assert "semantic_relationship_connectors_rendered" in str(exc)
    else:
        raise AssertionError("missing evidence-present Mermaid connector was accepted")
