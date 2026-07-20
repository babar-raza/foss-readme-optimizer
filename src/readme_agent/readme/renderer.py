"""Purely additive rendering of only the missing elements, into a single
owned span.

Never takes URLs from the LLM -- always substitutes the policy's canonical
URLs. pdf/java (missing only products_org_link) renders a one-line addition
with zero LLM involvement; cells/java (missing everything) renders the full
resources block, including the LLM-authored relationship paragraph.

Phase 21 (decision #9 as corrected): the former "callout" span, rendered
immediately after the H1, is retired. Its link content now merges into this
module's single "resources" span instead of a separate, more prominent
placement -- both because a promotional banner right under the H1 is exactly
what decision #9 forbids, and because the two-span design had a real,
confirmed duplication bug: org/com links were rendered twice (once in
callout, once unconditionally in resources) whenever both a link gap and a
resources gap were present in the same run (see runs/evidence/
20260717-172958-b0ad/block.md for the real, pre-fix example). This module now
renders each element into resources exactly once, gated on whether that
specific element is actually a gap.
"""

from urllib.parse import urlencode

from readme_agent.readme.gap_detector import GapReport
from readme_agent.registry.models import LinkSpec, PolicyProfile


def _with_utm(spec: LinkSpec) -> str:
    if not spec.utm:
        return spec.url
    separator = "&" if "?" in spec.url else "?"
    return spec.url + separator + urlencode(spec.utm)


def _render_resources(
    gaps: list[str], policy: PolicyProfile, relationship_paragraph: str | None
) -> str:
    parts = ["### Related Aspose Resources", ""]

    if "license_mentioned" in gaps:
        detected = policy.required_elements.license_mentioned.detected_license
        parts.append(f"- **License:** {detected}")

    if "products_org_link" in gaps:
        org = policy.required_elements.products_org_link
        parts.append(f"- **Open-source (FOSS) catalog:** [{org.label}]({org.url})")

    if "products_com_link" in gaps:
        com = policy.required_elements.products_com_link
        parts.append(f"- **Commercial edition:** [{com.label}]({_with_utm(com)})")

    if "relationship_explained" in gaps and relationship_paragraph:
        parts.append("")
        parts.append(relationship_paragraph)

    return "\n".join(parts)


def render_missing_elements(
    gap_report: GapReport,
    policy: PolicyProfile,
    relationship_paragraph: str | None,
) -> dict[str, str]:
    """Returns {span_name: content}. Empty dict if fully compliant -- a
    zero-gap repo (the 3d family) gets no span. Every missing element renders
    into the single owned "resources" span, exactly once per element."""
    if not gap_report.gaps:
        return {}
    return {"resources": _render_resources(gap_report.gaps, policy, relationship_paragraph)}
