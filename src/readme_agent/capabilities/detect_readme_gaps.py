"""Wraps readme.gap_detector.detect() -- scans a repo's baseline README for
the four required presentation elements, read-only. Same function Wave 1's
spike proved live (plans/investigations/agentic-loop-proof.md); the
clone+scan helper is promoted here as this capability's production home,
not duplicated from the spike script, which stays investigation evidence."""

from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.inspection import file_inventory
from readme_agent.license.auditor import detect_license
from readme_agent.paths import baseline_dir
from readme_agent.readme.gap_detector import detect as detect_gaps
from readme_agent.registry.loader import require_listed

CAPABILITY_ID = "detect_readme_gaps"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Detect README gaps",
    purpose="Read-only: scan the README for the four required presentation elements (license "
    "mention, org link, com link, relationship explanation) and count how many are missing.",
    category="readme_analysis",
    owner="readme_agent.readme.gap_detector",
    execution_type="deterministic_tool",
    required_inputs={"org_repo": "string"},
    produced_outputs={
        "license_mentioned": "boolean",
        "products_org_link": "boolean",
        "products_com_link": "boolean",
        "relationship_explained": "boolean",
        "total_gaps": "integer",
    },
    preconditions=[
        "org_repo must be listed in data/products.json (mode is irrelevant -- read-only)"
    ],
    required_permissions=["read_only_local"],
    side_effect_class="read_only_local",
    tools_used=["gitsafety.clone.clone_baseline", "readme.gap_detector.detect"],
    failure_modes=["NotAllowlistedError if org_repo is not listed in data/products.json"],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py"],
)


def _clone_and_scan(org_repo: str):
    entry = require_listed(org_repo)
    path = baseline_dir(entry.org, entry.repo_name)
    clone_baseline(entry, path)
    inventory = file_inventory.scan(path)
    readme_text = inventory.readme_path.read_text(encoding="utf-8") if inventory.readme_path else ""
    return entry, inventory, readme_text


def execute(org_repo: str) -> dict:
    _entry, inventory, readme_text = _clone_and_scan(org_repo)
    license_state = detect_license(None, inventory.license_path)
    gap_report = detect_gaps(readme_text, license_state.detected)
    flags = {
        "license_mentioned": gap_report.license_mentioned,
        "products_org_link": gap_report.products_org_link,
        "products_com_link": gap_report.products_com_link,
        "relationship_explained": gap_report.relationship_explained,
    }
    return {**flags, "total_gaps": sum(1 for v in flags.values() if not v)}
