from pathlib import Path

from readme_agent.readme.gap_detector import GapReport
from readme_agent.readme.renderer import render_missing_elements
from readme_agent.registry.loader import load_policy

REPO_ROOT = Path(__file__).resolve().parents[2]


def _policy():
    return load_policy("aspose-3d-foss", REPO_ROOT / "config" / "policies")


class TestFullyCompliantRendersNothing:
    def test_zero_gaps_returns_empty_dict(self):
        report = GapReport(
            license_mentioned=True,
            products_org_link=True,
            products_com_link=True,
            relationship_explained=True,
        )
        assert render_missing_elements(report, _policy(), relationship_paragraph=None) == {}


class TestPartialGapRendersOnlyCallout:
    """pdf/java's real gap shape: only products_org_link missing."""

    def test_only_org_link_missing_renders_only_callout(self):
        report = GapReport(
            license_mentioned=True,
            products_org_link=False,
            products_com_link=True,
            relationship_explained=True,
        )
        spans = render_missing_elements(report, _policy(), relationship_paragraph=None)

        assert set(spans.keys()) == {"callout"}
        assert "products.aspose.org" in spans["callout"]
        assert "products.aspose.com" not in spans["callout"]


class TestFullGapRendersBothSpans:
    """cells/java's real gap shape: everything missing."""

    def test_all_gaps_renders_both_spans(self):
        report = GapReport(
            license_mentioned=False,
            products_org_link=False,
            products_com_link=False,
            relationship_explained=False,
        )
        spans = render_missing_elements(
            report, _policy(), relationship_paragraph="This is the FOSS edition of Aspose.3D."
        )

        assert set(spans.keys()) == {"callout", "resources"}
        assert "products.aspose.org" in spans["callout"]
        assert "products.aspose.com" in spans["callout"]
        assert "MIT" in spans["resources"]
        assert "This is the FOSS edition of Aspose.3D." in spans["resources"]


class TestRendererNeverInventsUrls:
    def test_rendered_urls_come_only_from_policy(self):
        report = GapReport(
            license_mentioned=False,
            products_org_link=False,
            products_com_link=False,
            relationship_explained=False,
        )
        policy = _policy()
        spans = render_missing_elements(report, policy, relationship_paragraph="prose")

        assert policy.required_elements.products_org_link.url in spans["callout"]
        assert policy.required_elements.products_com_link.url in spans["callout"]

    def test_relationship_gap_without_llm_paragraph_omits_prose_gracefully(self):
        report = GapReport(
            license_mentioned=True,
            products_org_link=True,
            products_com_link=True,
            relationship_explained=False,
        )
        spans = render_missing_elements(report, _policy(), relationship_paragraph=None)
        assert "resources" in spans
        # No LLM paragraph supplied -- must not crash, and must not fabricate one.
        assert "None" not in spans["resources"]
