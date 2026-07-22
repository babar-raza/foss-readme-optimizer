"""Wave 8.6 (item I, `VAL-016`/`RDM-020`) -- reads `data/template_clone_
findings.json` (produced by the periodic, standalone `scripts/data-refresh/
detect_template_clones.py` batch job) for one org_repo. Read-only,
deterministic, evidence-only -- never a sole verdict, matching `LLM-017`'s
own text.

Degrades honestly when the artifact doesn't exist yet or the repo was never
embedded (a failed fetch, or added to the registry after the last batch
run) -- `found=False`, never a crash, never a false "not flagged"."""

import json
from pathlib import Path

from readme_agent.capabilities.schema import CapabilityManifest

CAPABILITY_ID = "get_template_clone_findings"

_FINDINGS_PATH = Path("data") / "template_clone_findings.json"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Get template-clone findings",
    purpose="Read-only: whether this org_repo appears in the periodic embedding-similarity "
    "batch job's flagged pairs (likely template-clone or generic-prose content), and against "
    "which sibling repo. Evidence only -- never a sole verdict (VAL-016/RDM-020).",
    category="observability",
    owner="scripts.data-refresh.detect_template_clones",
    execution_type="deterministic_tool",
    required_inputs={"org_repo": "string"},
    produced_outputs={"found": "boolean", "flagged": "boolean", "flagged_against": "array"},
    preconditions=["the periodic batch job must have run at least once -- found=False otherwise"],
    required_permissions=["read_only_local"],
    side_effect_class="read_only_local",
    allowed_domains=[],  # unscoped -- general-planner-visible
    tools_used=["data/template_clone_findings.json"],
    failure_modes=["found=False when the artifact doesn't exist or this repo was never embedded"],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py"],
    requirement_ids=["VAL-016", "RDM-020"],
)


def execute(org_repo: str) -> dict:
    if not _FINDINGS_PATH.exists():
        return {"found": False, "flagged": False, "flagged_against": []}

    findings = json.loads(_FINDINGS_PATH.read_text(encoding="utf-8"))
    if org_repo not in findings.get("repos_embedded", []):
        return {"found": False, "flagged": False, "flagged_against": []}

    flagged_against = [
        pair["repo_b"] if pair["repo_a"] == org_repo else pair["repo_a"]
        for pair in findings.get("flagged_pairs", [])
        if org_repo in (pair["repo_a"], pair["repo_b"])
    ]
    return {"found": True, "flagged": bool(flagged_against), "flagged_against": flagged_against}
