"""Purely additive rendering of only the missing elements.

Never takes URLs from the LLM -- always substitutes the policy's canonical
URLs. pdf/java (missing only products_org_link) renders a one-line callout
addition with zero LLM involvement; cells/java (missing everything) renders
both spans, one of which carries the LLM-authored relationship paragraph.
"""

from urllib.parse import urlencode

from readme_agent.readme.gap_detector import GapReport
from readme_agent.registry.models import LinkSpec, PolicyProfile

_LINK_GAPS = ("products_org_link", "products_com_link")
_RESOURCES_GAPS = ("license_mentioned", "relationship_explained")


def _with_utm(spec: LinkSpec) -> str:
    if not spec.utm:
        return spec.url
    separator = "&" if "?" in spec.url else "?"
    return spec.url + separator + urlencode(spec.utm)


def _render_callout(link_gaps: list[str], policy: PolicyProfile) -> str:
    lines = []
    if "products_org_link" in link_gaps:
        spec = policy.required_elements.products_org_link
        lines.append(f"🆓 Open-source catalog: [{spec.label}]({spec.url})")
    if "products_com_link" in link_gaps:
        spec = policy.required_elements.products_com_link
        lines.append(f"💼 Commercial edition: [{spec.label}]({_with_utm(spec)})")
    return "> " + "  \n> ".join(lines)


def _render_resources(
    resources_gaps: list[str], policy: PolicyProfile, relationship_paragraph: str | None
) -> str:
    parts = ["### Related Aspose Resources", ""]

    if "license_mentioned" in resources_gaps:
        detected = policy.required_elements.license_mentioned.detected_license
        parts.append(f"- **License:** {detected}")

    org = policy.required_elements.products_org_link
    com = policy.required_elements.products_com_link
    parts.append(f"- **Open-source (FOSS) catalog:** [{org.label}]({org.url})")
    parts.append(f"- **Commercial edition:** [{com.label}]({_with_utm(com)})")

    if "relationship_explained" in resources_gaps and relationship_paragraph:
        parts.append("")
        parts.append(relationship_paragraph)

    return "\n".join(parts)


def render_missing_elements(
    gap_report: GapReport,
    policy: PolicyProfile,
    relationship_paragraph: str | None,
) -> dict[str, str]:
    """Returns {span_name: content}. Empty dict if fully compliant --
    a zero-gap repo (the 3d family) gets neither span."""
    spans: dict[str, str] = {}

    link_gaps = [g for g in gap_report.gaps if g in _LINK_GAPS]
    if link_gaps:
        spans["callout"] = _render_callout(link_gaps, policy)

    resources_gaps = [g for g in gap_report.gaps if g in _RESOURCES_GAPS]
    if resources_gaps:
        spans["resources"] = _render_resources(resources_gaps, policy, relationship_paragraph)

    return spans
