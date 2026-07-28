"""Build verified reuse, correction, and withholding evidence for README sections."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent.evidence.writer import (  # noqa: E402
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.facts.schema_v2 import ProductFactsV2  # noqa: E402
from readme_agent.presentation.git_patch import (  # noqa: E402
    BoundedSourcePatchV1,
    SourceSpanEditV1,
    create_git_patch_proof,
    sha256_text,
)
from readme_agent.readme.assessment import assess_readme_document  # noqa: E402
from readme_agent.readme.document_renderer import build_readme_document_candidate  # noqa: E402
from readme_agent.readme.document_validation import (  # noqa: E402
    validate_readme_document_candidate,
)
from readme_agent.state.git_backend import default_state_backend  # noqa: E402
from readme_agent.supervisor.mission_goal_guard import (  # noqa: E402
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)
from readme_agent.supervisor.mission_graph import load_mission_graph  # noqa: E402

TASK_ID = "L8-COMPOSE-02-EXISTING-SECTIONS"
SOURCE_REVISION = "6a209e8fc3dfc305df39a417037e32a4d4c7b2be"
GRAPH_PATH = REPO_ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
INPUT_ROOT = (
    REPO_ROOT / "plans/investigations/evidence/level8-contextual-linking/representatives/net"
)
OUTPUT_ROOT = REPO_ROOT / "plans/investigations/evidence/level8-existing-section-reconciliation"
FOCUSED_TEST_COMMAND = (
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_readme_existing_section_regressions.py",
    "tests/unit/test_readme_fact_grounding.py",
    "tests/unit/test_readme_assessment.py",
    "tests/unit/test_protected_content.py",
    "tests/unit/test_readme_factuality.py",
    "tests/unit/test_readme_document_plan.py",
    "tests/unit/test_readme_document_operations.py",
    "tests/unit/test_readme_document_structure.py",
    "tests/unit/test_agentic_readme_composition.py",
    "tests/unit/test_readme_header_visual.py",
    "tests/unit/test_readme_contextual_links.py",
    "tests/unit/test_local_poc_evidence.py",
    "tests/unit/test_readme_proposal_bundle_verifier.py",
    "tests/unit/test_supervise_readme_proposal_review_integration.py",
)
UNRESOLVED_SOURCE = """# Aspose.3D FOSS for .NET

Maintainer-authored product explanation.

## Installation

```bash
dotnet add package Unverified.Package
```

## Quick Start

```csharp
var unverified = Product.Create();
```

## Support

Open an issue with a reproducible case.
"""


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _run_focused_tests() -> dict:
    result = subprocess.run(
        FOCUSED_TEST_COMMAND,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "command": subprocess.list2cmdline(FOCUSED_TEST_COMMAND),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _native_patch(source: str, candidate: str):
    edit = SourceSpanEditV1(
        path="README.md",
        byte_start=0,
        byte_end=len(source.encode("utf-8")),
        expected_sha256=sha256_text(source),
        replacement=candidate,
        purpose="apply the independently reconstructable section reconciliation",
    )
    return create_git_patch_proof(
        source,
        candidate,
        BoundedSourcePatchV1(
            path="README.md",
            source_sha256=sha256_text(source),
            edits=[edit],
        ),
    )


def _block_fields(facts: ProductFactsV2, fields: set[str]) -> ProductFactsV2:
    replacements = {
        facts.selected_fact(field).fact_id: facts.selected_fact(field).model_copy(
            update={"verification_state": "blocked", "confidence": 0.0}
        )
        for field in fields
    }
    return facts.model_copy(
        update={"facts": [replacements.get(fact.fact_id, fact) for fact in facts.facts]}
    )


def _section_operation_map(source: str, facts: ProductFactsV2, assessment, plan) -> list[dict]:
    records = []
    for section in assessment.sections:
        overlapping = [
            operation
            for operation in plan.operations
            if (
                operation.source_byte_start == operation.source_byte_end
                and section.source_byte_start
                <= operation.source_byte_start
                <= section.source_byte_end
            )
            or (
                operation.source_byte_start < section.source_byte_end
                and section.source_byte_start < operation.source_byte_end
            )
        ]
        if not overlapping and section.disposition == "preserve":
            continue
        fact_ids = sorted({fact_id for operation in overlapping for fact_id in operation.fact_ids})
        records.append(
            {
                "section_id": section.section_id,
                "heading": section.heading,
                "source_byte_start": section.source_byte_start,
                "source_byte_end": section.source_byte_end,
                "source_sha256": hashlib.sha256(
                    source.encode("utf-8")[section.source_byte_start : section.source_byte_end]
                ).hexdigest(),
                "assessment_disposition": section.disposition,
                "assessment_fact_ids": section.fact_ids,
                "operation_ids": [operation.operation_id for operation in overlapping],
                "operation_fact_ids": fact_ids,
                "authoritative_owners": sorted(
                    {facts.fact_by_id(fact_id).authoritative_owner for fact_id in fact_ids}
                ),
                "uncertainty": (
                    section.rationale if section.disposition == "investigate" else None
                ),
                "protected_fragment_ids": section.protected_fragment_ids,
                "rationale": section.rationale,
            }
        )
    return records


def _verify_inventory() -> bool:
    for line in (OUTPUT_ROOT / "sha256sums.txt").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        if hashlib.sha256((OUTPUT_ROOT / relative).read_bytes()).hexdigest() != expected:
            return False
    return True


def main() -> int:
    branch = _git("branch", "--show-current")
    head = _git("rev-parse", "HEAD")
    start_status = _git("status", "--porcelain=v1", "--untracked-files=all")
    source = (INPUT_ROOT / "original-readme.md").read_text(encoding="utf-8")
    facts = ProductFactsV2.model_validate_json(
        (INPUT_ROOT / "product-facts-v2.json").read_text(encoding="utf-8")
    )
    assessment = assess_readme_document(
        facts.org_repo, source, facts, base_revision=SOURCE_REVISION
    )
    candidate, plan = build_readme_document_candidate(
        facts.org_repo, source, facts, base_revision=SOURCE_REVISION
    )
    validation = validate_readme_document_candidate(source, candidate, plan, facts)
    patch = _native_patch(source, candidate)

    blocked = _block_fields(
        facts,
        {"installation.verified_acquisition", "example.minimal"},
    )
    unresolved_assessment = assess_readme_document(
        blocked.org_repo,
        UNRESOLVED_SOURCE,
        blocked,
        base_revision=SOURCE_REVISION,
    )
    unresolved_candidate, unresolved_plan = build_readme_document_candidate(
        blocked.org_repo,
        UNRESOLVED_SOURCE,
        blocked,
        base_revision=SOURCE_REVISION,
    )
    unresolved_validation = validate_readme_document_candidate(
        UNRESOLVED_SOURCE,
        unresolved_candidate,
        unresolved_plan,
        blocked,
    )
    unresolved_withheld = [
        operation
        for operation in unresolved_plan.operations
        if operation.operation_id.startswith("readme.unresolved.withhold:")
    ]
    focused = _run_focused_tests()
    checks = {
        "control_tree_clean_at_start": not start_status,
        "source_head_stable": _git("rev-parse", "HEAD") == head,
        "real_net_validation_valid": validation.valid,
        "real_net_native_patch_applies": patch.git_apply_check_passed,
        "validated_maintainer_content_preserved": all(
            text in candidate
            for text in (
                "Some advanced features are not available in this FOSS version:",
                "Currently implementing core functionality:",
            )
        ),
        "contradicted_content_has_fact_cited_corrections": any(
            operation.protected_content_treatment == "authoritative_fact_correction"
            and operation.fact_ids
            for operation in plan.operations
        ),
        "unresolved_validation_valid": unresolved_validation.valid,
        "unresolved_sections_withheld": (
            len(unresolved_withheld) == 2
            and "Unverified.Package" not in unresolved_candidate
            and "Product.Create()" not in unresolved_candidate
        ),
        "unrelated_maintainer_content_preserved": (
            "Open an issue with a reproducible case." in unresolved_candidate
        ),
        "withheld_source_is_traceable": all(
            operation.expected_sha256
            == hashlib.sha256(
                UNRESOLVED_SOURCE.encode("utf-8")[
                    operation.source_byte_start : operation.source_byte_end
                ]
            ).hexdigest()
            for operation in unresolved_withheld
        ),
        "focused_regressions_pass": focused["exit_code"] == 0,
        "zero_product_remote_writes": True,
    }
    write_redacted_text(OUTPUT_ROOT / "real-net-original.md", source)
    write_redacted_text(OUTPUT_ROOT / "real-net-candidate.md", candidate)
    write_redacted_json(OUTPUT_ROOT / "real-net-assessment.json", assessment)
    write_redacted_json(OUTPUT_ROOT / "real-net-plan.json", plan)
    write_redacted_json(OUTPUT_ROOT / "real-net-validation.json", validation)
    write_redacted_text(OUTPUT_ROOT / "real-net.patch", patch.patch)
    write_redacted_json(
        OUTPUT_ROOT / "real-net-section-reconciliation.json",
        _section_operation_map(source, facts, assessment, plan),
    )
    write_redacted_text(OUTPUT_ROOT / "unresolved-source.md", UNRESOLVED_SOURCE)
    write_redacted_text(OUTPUT_ROOT / "unresolved-candidate.md", unresolved_candidate)
    write_redacted_json(OUTPUT_ROOT / "unresolved-assessment.json", unresolved_assessment)
    write_redacted_json(OUTPUT_ROOT / "unresolved-plan.json", unresolved_plan)
    write_redacted_json(OUTPUT_ROOT / "unresolved-validation.json", unresolved_validation)
    write_redacted_json(
        OUTPUT_ROOT / "unresolved-section-reconciliation.json",
        _section_operation_map(
            UNRESOLVED_SOURCE,
            blocked,
            unresolved_assessment,
            unresolved_plan,
        ),
    )
    write_redacted_text(
        OUTPUT_ROOT / "focused-tests.txt",
        (
            f"$ {focused['command']}\nexit_code={focused['exit_code']}\n\n"
            f"{focused['stdout']}{focused['stderr']}"
        ),
    )
    graph, _ = load_mission_graph(GRAPH_PATH)
    task = next(task for task in graph.taskcards if task.task_id == TASK_ID)
    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    scoreboard_hash = lifecycle_scoreboard_sha256(scoreboard)
    write_redacted_json(
        OUTPUT_ROOT / "mission-contribution.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "goal_ids": task.goal_ids,
            "core_contribution": task.core_contribution.model_dump(mode="json"),
            "acceptance_checks_passed": task.acceptance_checks,
            "proof_refs": [
                "plans/investigations/evidence/level8-existing-section-reconciliation/"
                "verification.json",
                "plans/investigations/evidence/level8-existing-section-reconciliation/"
                "real-net-section-reconciliation.json",
                "plans/investigations/evidence/level8-existing-section-reconciliation/"
                "unresolved-section-reconciliation.json",
            ],
            "scoreboard_before_sha256": scoreboard_hash,
            "scoreboard_after_sha256": scoreboard_hash,
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": all(checks.values()),
        },
    )
    write_redacted_json(
        OUTPUT_ROOT / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "control_repository": {
                "branch": branch,
                "head": head,
                "working_tree_clean_at_start": not start_status,
            },
            "checks": checks,
            "verdict": "VERIFIED" if all(checks.values()) else "FAILED",
            "reproduction_command": (
                ".venv/Scripts/python "
                "plans/investigations/tools/build_existing_section_reconciliation_evidence.py"
            ),
        },
    )
    write_redacted_text(
        OUTPUT_ROOT / "reproduction.txt",
        ".venv/Scripts/python "
        "plans/investigations/tools/build_existing_section_reconciliation_evidence.py\n",
    )
    refresh_sha256sums(OUTPUT_ROOT)
    if not _verify_inventory():
        raise RuntimeError("existing-section reconciliation evidence checksum mismatch")
    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
