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


class TestPartialGapRendersOnlyWhatsMissing:
    """pdf/java's real gap shape: only products_org_link missing. Phase 21:
    everything renders into the single "resources" span now -- the retired
    "callout" span no longer exists as a render target."""

    def test_only_org_link_missing_renders_only_that_element(self):
        report = GapReport(
            license_mentioned=True,
            products_org_link=False,
            products_com_link=True,
            relationship_explained=True,
        )
        spans = render_missing_elements(report, _policy(), relationship_paragraph=None)

        assert set(spans.keys()) == {"resources"}
        assert "products.aspose.org" in spans["resources"]
        assert "products.aspose.com" not in spans["resources"]


class TestFullGapRendersOneSpanWithEveryElement:
    """cells/java's real gap shape: everything missing. Confirmed live before
    this change: the old two-span design rendered org/com links TWICE (once
    in callout, once unconditionally in resources) whenever both a link gap
    and a resources gap were present in the same run -- see
    runs/evidence/20260717-172958-b0ad/block.md. The merged renderer must
    render each element exactly once."""

    def test_all_gaps_renders_a_single_span(self):
        report = GapReport(
            license_mentioned=False,
            products_org_link=False,
            products_com_link=False,
            relationship_explained=False,
        )
        spans = render_missing_elements(
            report, _policy(), relationship_paragraph="This is the FOSS edition of Aspose.3D."
        )

        assert set(spans.keys()) == {"resources"}
        content = spans["resources"]
        assert content.count("products.aspose.org") == 1
        assert content.count("products.aspose.com") == 1
        assert "MIT" in content
        assert "This is the FOSS edition of Aspose.3D." in content

    def test_only_com_link_missing_omits_org_and_license_and_relationship(self):
        """Each element gates independently -- rendering one missing element
        must not drag in lines for elements that are NOT gaps."""
        report = GapReport(
            license_mentioned=True,
            products_org_link=True,
            products_com_link=False,
            relationship_explained=True,
        )
        spans = render_missing_elements(report, _policy(), relationship_paragraph=None)

        content = spans["resources"]
        assert "products.aspose.com" in content
        assert "products.aspose.org" not in content
        assert "License:" not in content


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

        assert policy.required_elements.products_org_link.url in spans["resources"]
        assert policy.required_elements.products_com_link.url in spans["resources"]

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
