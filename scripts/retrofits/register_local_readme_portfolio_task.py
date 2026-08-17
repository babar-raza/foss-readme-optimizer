"""Register a dependency-free taskcard for the operator-directed mission: deliver
the complete local README.md candidate portfolio (data/products.json) at
Aspose.org quality parity, entirely local, no remote writes.

Context: L8-FRESH-00-FRESHNESS-SERVICE already covers "reuse the proven
Aspose.org README contract ... and process the complete portfolio to a local,
human-reviewable candidate bundle" almost verbatim, but it is gated behind
L8-VPY-05-PRODUCTION-ADMISSION because its full scope also covers standing up
an ONGOING autonomous freshness service wired into the scheduler -- a bigger
production commitment the operator has not asked for here. The operator's
current directive is narrower: reuse/harden the existing local_poc pipeline
(already proven this session -- 4/33 candidates AGENT_APPROVED, 1/33
NO_OP_PROVEN, see runs/readme-poc and the 2026-08-17 local_poc portfolio run
log) and deliver every achievable candidate for local human review. That
narrower scope has no production-transport prerequisite, so it is registered
as its own taskcard rather than force-claiming FRESH-00 out of its governed
dependency order (mission_control.claim_next_task rejects out-of-order claims
by design -- confirmed live: 'error: expected mission task ... is not
eligible').
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

GRAPH_PATH = Path("plans/investigations/control/level8-autonomous-mission-task-graph.yaml")

_TASK = {
    "task_id": "L8-PORT-01-LOCAL-README-PORTFOLIO-ASPOSE-PARITY",
    "mission_id": "LEVEL8-CENTRAL-REPOSITORY-PRESENTATION",
    "parent_task_id": None,
    "title": "Deliver the complete local README candidate portfolio at Aspose.org quality parity",
    "source_audit_finding": (
        "Operator directive (2026-08-17): take full ownership and deliver the complete local "
        "README.md candidate portfolio at the quality level of Aspose.org's proven "
        "repo-presenter-regen-full corpus (D:/onedrive/Documents/GitHub/aspose.org/reports/"
        "repo-presenter-regen-full, 31 candidates across 12 families/multiple platforms), using "
        "the aspose.org skill-development plan (C:/Users/prora/.claude/plans/"
        "d-users-prora-onedrive-documents-github-humble-tome.md, ~18.4k lines) as proven "
        "operational evidence. This session already ran the full 33-product portfolio through "
        "the existing --registry data/products.json --execution-profile local_poc path twice "
        "(fixing a real capability_dependencies type regression from the T3/T4 wiring and a "
        "Docker Desktop outage along the way): 4/33 reached CONVERGED_PROPOSAL_READY/"
        "AGENT_APPROVED (3D-Python, PDF-Python, Slides-Python, Words-Python), 1/33 "
        "CONVERGED_NO_TRACKED_CHANGE (NO_OP_PROVEN reuse), 15/33 BLOCKED on "
        "product_truth_not_ready:BLOCKED_MISSING_EVIDENCE (mostly non-Python ecosystems), 13/33 "
        "BLOCKED on specialist_failed:readme_presentation (11 genuine claim-accountability/"
        "presentation-rule holdouts plus 2 real execution bugs: 'source placements contain "
        "duplicate IDs' on Note-Python, 'valuable source detail has no canonical presentation "
        "destination' on Cells-.NET), and 1/33 BLOCKED on readonly_intake:BLOCKED_CLASSIFICATION "
        "(Aspose.PSD-FOSS-for-.NET has no ecosystem/policy_profile set in data/products.json)."
    ),
    "audit_classification": "partially_done",
    "priority": "P1",
    "lane": "readme-portfolio-delivery",
    "owner": "readme-agent-supervisor",
    "status": "TODO",
    "objective": (
        "Reconcile and harden the existing local README pipeline (readme/document_renderer.py, "
        "readme/document_validation.py, presentation/verified_template_*.py, the T3 aspose_checks "
        "bridge, and the T4 aspose_detectors/composer_factpack facts) against the proven "
        "Aspose.org refresh-readme/repo-presenter-regen-full contract and its skill-development "
        "plan, fix delivery-blocking defects surfaced by running the real portfolio (not "
        "synthetic fixtures), and regenerate the complete local candidate portfolio through the "
        "existing supervise/local_poc path until every product has either a validated candidate "
        "or a precisely documented genuine external blocker -- entirely local, no push, no PR, "
        "no remote-repository mutation."
    ),
    "why_it_matters": (
        "The system has not yet proven it can deliver README quality the product owner "
        "recognizes as matching Aspose.org's own proven output across the whole portfolio, only "
        "on a 4/33 slice -- closing that gap using the same proven contract, through the one "
        "governed pipeline, is the actual deliverable this mission graph exists to produce."
    ),
    "allowed_paths": [
        "src/readme_agent/",
        "tests/",
        "runs/readme-poc/",
        "plans/investigations/evidence/readme-portfolio-*",
        "docs/",
        "logs/",
        "data/products.json",
    ],
    "forbidden_paths": [
        "D:/onedrive/Documents/GitHub/aspose.org (read-only reference corpus and plan; never "
        "written to)",
        "production target repository remotes",
        "target default branches",
    ],
    "dependencies": [],
    "expected_outputs": [
        "A local README.md candidate under runs/readme-poc/ for every product in "
        "data/products.json where genuine evidence supports one",
        "A precise, per-product blocker ledger for every product that cannot yet produce a "
        "candidate, distinguishing genuine external-evidence gaps from fixable pipeline defects",
        "Regression tests for every pipeline defect fixed while reconciling against the proven "
        "Aspose.org contract",
    ],
    "acceptance_checks": [
        "Every candidate contains only verified public claims with exact source provenance",
        "Every candidate preserves useful verified content from the original README",
        "An unchanged rerun of any accepted candidate is proven idempotent (NO_OP_PROVEN)",
        "No target repository is modified and no remote-write or human-approval boundary is "
        "bypassed or weakened",
    ],
    "verification": [
        "Focused tests for each reused/adapted/fixed module",
        "Full governed suite green with zero new failures",
        "A real, full-portfolio local_poc run (not a fixture) as the acceptance oracle",
        "run_official_checks.py and validate_compact_authority.py both clean",
    ],
    "negative_controls": [
        "A candidate produced outside the tracked supervise lane cannot count as portfolio "
        "progress",
        "A candidate that fabricates or infers an unverified claim cannot pass validation",
        "An evidence directory alone, without a governed commit and mission transition, cannot "
        "close this task",
    ],
    "regression_checks": [
        "mission graph load and dependency resolution (active and deferred)",
        "existing README contract, T3/T4 aspose.org check and fact wiring, and validator suite",
        "no-op / freshness idempotency",
    ],
    "evidence_requirements": [
        "The per-product local_poc portfolio summary, per-repo candidate paths, and the blocker "
        "ledger for unresolved products",
    ],
    "rollback_or_recovery": (
        "This task only ever writes to this repository's own working tree and runs/readme-poc/; "
        "a bad change reverts by discarding the specific governed commit that applied it."
    ),
    "failure_reroute": (
        "A defect in shared supervisor/validator/composition machinery discovered while "
        "reconciling against the proven Aspose.org contract is fixed surgically at its own layer "
        "with regression tests, not patched inline inside this task."
    ),
    "closeout_rules": [
        "This task closes only once every product in the authoritative registry has either a "
        "validated local candidate or a precisely documented genuine external blocker, with a "
        "governed commit and passing tests -- not merely once some candidates exist",
    ],
    "goal_ids": ["GOAL-README", "GOAL-DELIVERY"],
    "core_contribution": {
        "kind": "visible_deliverable",
        "summary": (
            "Deliver the complete local README candidate portfolio the product owner can review, "
            "at the same proven quality bar as Aspose.org's own corpus."
        ),
    },
    "execution_focus": {
        "goal_id": "DELIVERY-README-PORTFOLIO-PARITY",
        "immediate_outcome": (
            "Raise the local_poc portfolio from 4/33 to every achievable candidate, matching the "
            "proven Aspose.org presentation and provenance contract."
        ),
        "repository_scope": ["platform:cross-platform"],
        "allowed_change_classes": [
            "shared_code",
            "repository_runtime",
            "factuality",
            "presentation",
        ],
        "next_goal_on_success": (
            "Feed the reconciled, hardened pipeline back into L8-FRESH-00-FRESHNESS-SERVICE once "
            "production admission unblocks the ongoing autonomous service."
        ),
    },
    "requirement_ids": [],
    "stage_goal_id": "GOAL-V0B-POST-PYTHON-SLICES",
    "concurrency_class": "repository_local_write_isolated",
    "campaign_id": "CAMP-GATE-B-AND-LATER",
}


def main() -> None:
    raw = yaml.safe_load(GRAPH_PATH.read_text(encoding="utf-8"))

    existing_ids = {task["task_id"] for task in raw["taskcards"]}
    if _TASK["task_id"] in existing_ids:
        raise SystemExit(f"{_TASK['task_id']} is already registered")

    raw["taskcards"].append(_TASK)

    # Match compact_active_authority.py's exact dump parameters so
    # re-serialization only touches the real data change.
    GRAPH_PATH.write_text(
        yaml.safe_dump(raw, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    print(f"registered {_TASK['task_id']}")
    print(f"active taskcards now: {len(raw['taskcards'])}")
    new_sha256 = hashlib.sha256(GRAPH_PATH.read_bytes()).hexdigest()
    print(f"graph sha256 will be recomputed on next load: {new_sha256}")


if __name__ == "__main__":
    main()
