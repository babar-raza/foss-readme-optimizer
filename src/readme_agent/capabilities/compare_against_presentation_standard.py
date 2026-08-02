"""Wave 8.6: ongoing runtime comparison against `docs/presentation-
standard.md`'s codified rules -- closes a gap found in an external-review
reconciliation session (this project's own one-time human research fed a
static standard document, but nothing made comparison against it an ongoing
runtime check). Reads the standard doc fresh at call time and interpolates
its text into the prompt, rather than duplicating its content as static
prompt text (`GOVERNANCE.md` placement rule 7: "state a fact in its one
home... never restate it").

Deliberately stateless like every other capability (decision #26(b)): reads
the current on-disk README and the standard doc fresh, no durable state of
its own. `client` is accepted but deliberately NOT declared in
`required_inputs`/`optional_inputs` -- never offered in the tool schema,
exists only for deterministic test/wiring callers, exactly as `render_
readme_candidate.py`'s own `llm_mode`/`fixture_response_path` convention
already establishes."""

import hashlib
import re
from pathlib import Path

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field

from readme_agent import paths
from readme_agent.capabilities.domains import PRESENTATION_BENCHMARKING
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.env import llm_api_key, llm_base_url, llm_model_for_job
from readme_agent.errors import ValidationFailure
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.inspection import file_inventory
from readme_agent.llm.analysis_client import AnalysisResult, LiveAnalysisClient
from readme_agent.llm.analysis_prompts import build_presentation_standard_compliance_messages
from readme_agent.registry.loader import require_listed

CAPABILITY_ID = "compare_against_presentation_standard"

_STANDARD_DOC_PATH = Path("docs") / "presentation-standard.md"
_VISUAL_ABSENCE_CLAIM = re.compile(r"\b(?:no|without)\s+(?:useful\s+)?(?:visuals?|diagram)s?\b")
_CI_PRESENCE_CLAIM = re.compile(r"\b(?:includes?|contains?|has|shows?)\b[^.]{0,80}\bci badge\b")
_CI_ABSENCE_CLAIM = re.compile(r"\b(?:no|without)\s+ci badge\b")


class ReadmeStructuralObservationsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    has_mermaid: bool
    ci_badge_count: int = Field(ge=0)


class PresentationBenchmarkConsistencyV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    valid: bool
    contradictions: list[str]


def _check_structural_consistency(
    criteria_results: list[dict], observations: ReadmeStructuralObservationsV1
) -> PresentationBenchmarkConsistencyV1:
    """Reject benchmark narratives that contradict exact Markdown structure."""

    contradictions: list[str] = []
    for item in criteria_results:
        if not isinstance(item, dict):
            continue
        dimension = str(item.get("dimension", "unknown"))
        note = str(item.get("note", "")).casefold()
        if observations.has_mermaid and _VISUAL_ABSENCE_CLAIM.search(note):
            contradictions.append(f"{dimension}: claims no visual despite Mermaid input")
        if observations.ci_badge_count == 0 and _CI_PRESENCE_CLAIM.search(note):
            contradictions.append(f"{dimension}: claims a CI badge that is absent")
        if observations.ci_badge_count > 0 and _CI_ABSENCE_CLAIM.search(note):
            contradictions.append(f"{dimension}: claims no CI badge despite observed badge")
    return PresentationBenchmarkConsistencyV1(
        valid=not contradictions,
        contradictions=contradictions,
    )


MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Compare against presentation standard",
    purpose="Read-only: compares the current README against the codified rules in "
    "docs/presentation-standard.md via a structured LLM analysis call, returning per-dimension "
    "satisfied/not-satisfied findings. Evidence for the planner and independent_verification's "
    "requirement mapping (VAL-005) -- never a blocking gate on its own.",
    category="presentation_benchmarking",
    owner="readme_agent.capabilities.compare_against_presentation_standard",
    execution_type="agentic_analysis",
    required_inputs={"org_repo": "string"},
    optional_inputs={"candidate_text": "string"},
    produced_outputs={
        "criteria_results": "array",
        "overall_summary": "string",
        "input_source": "string",
        "input_sha256": "string",
        "structural_observations": "object",
        "structural_consistency": "object",
    },
    preconditions=[
        "org_repo must be listed in data/products.json",
        "candidate_text, if supplied, is compared instead of the current on-disk README -- "
        "absent, this capability reads the current on-disk README fresh",
    ],
    required_permissions=["read_only_network"],
    side_effect_class="read_only_network",
    allowed_domains=[PRESENTATION_BENCHMARKING],
    model_route="presentation_standard_compliance",
    tools_used=["llm.analysis_client.LiveAnalysisClient"],
    failure_modes=["LLMError propagates as execution_error on any gateway failure"],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py"],
    requirement_ids=["VAL-005"],
)


def execute(
    org_repo: str,
    candidate_text: str | None = None,
    *,
    client=None,
) -> dict:
    entry = require_listed(org_repo)

    if candidate_text is not None:
        readme_text = candidate_text
        input_source = "candidate_text"
    else:
        baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
        clone_baseline(entry, baseline_path)
        inventory = file_inventory.scan(baseline_path)
        readme_text = (
            inventory.readme_path.read_text(encoding="utf-8") if inventory.readme_path else ""
        )
        input_source = "baseline_readme"

    tokens = MarkdownIt("commonmark").parse(readme_text)
    observations = ReadmeStructuralObservationsV1(
        has_mermaid=any(
            token.type == "fence" and token.info.strip().casefold() == "mermaid" for token in tokens
        ),
        ci_badge_count=len(
            re.findall(r"!\[[^\]]*\]\([^)]*actions/workflows/[^)]*badge[^)]*\)", readme_text)
        ),
    )

    standard_excerpt = _STANDARD_DOC_PATH.read_text(encoding="utf-8")

    resolved_client = client or LiveAnalysisClient(
        llm_base_url(),
        llm_api_key(),
        llm_model_for_job("presentation_standard_compliance"),
        job="presentation_standard_compliance",
        prompt_id="presentation_standard_compliance",
    )
    messages = build_presentation_standard_compliance_messages(
        org_repo, readme_text, standard_excerpt
    )
    result: AnalysisResult = resolved_client.analyze(messages)
    criteria_results = result.parsed.get("criteria_results", [])
    consistency = _check_structural_consistency(criteria_results, observations)
    if not consistency.valid:
        raise ValidationFailure(
            "presentation benchmark contradicts deterministic README structure: "
            + "; ".join(consistency.contradictions)
        )

    return {
        "criteria_results": criteria_results,
        "overall_summary": result.parsed.get("overall_summary", ""),
        "input_source": input_source,
        "input_sha256": hashlib.sha256(readme_text.encode("utf-8")).hexdigest(),
        "structural_observations": observations.model_dump(mode="json"),
        "structural_consistency": consistency.model_dump(mode="json"),
    }
