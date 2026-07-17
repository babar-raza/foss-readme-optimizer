"""Shared context every validator rule receives -- keeps rule signatures uniform."""

from dataclasses import dataclass, field

from readme_agent.llm.schema import LLMBlockResponse
from readme_agent.readme.gap_detector import GapReport
from readme_agent.registry.models import PolicyProfile


@dataclass
class ValidationContext:
    readme_text: str  # current work README content, after rendering (or unchanged)
    baseline_readme_text: str  # original content before any span insertion
    policy: PolicyProfile
    pre_render_gap_report: GapReport  # what was missing before this run rendered anything
    rendered_spans: dict[str, str] = field(default_factory=dict)  # span_name -> content, this run
    llm_response: LLMBlockResponse | None = None
    facts_hash: str = ""
    embedded_hash: str | None = None  # hash found in an existing span, if any
    detected_license: str | None = None
