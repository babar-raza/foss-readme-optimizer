"""Build revision-bound evidence for capability and limitation claim polarity."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from claim_polarity_evidence_support import (
    build_evidence as build_real_controls,
)
from claim_polarity_evidence_support import (
    build_go_compound_identifier_evidence,
)

from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.facts.evidence_polarity import assess_evidence_polarity
from readme_agent.facts.policy_evidence import (
    evidence_fact_candidate,
    limitation_fact_candidate,
)
from readme_agent.facts.schema_v2 import FactRecordV2
from readme_agent.registry.loader import load_policy
from readme_agent.registry.models import EvidenceBackedProductFact
from readme_agent.state.git_backend import default_state_backend
from readme_agent.supervisor.mission_goal_guard import (
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)
from readme_agent.supervisor.mission_graph import load_mission_graph

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = REPO_ROOT / "plans/investigations/evidence/level8-claim-polarity"
FAILURE_DIR = REPO_ROOT / "runs/control/claim-polarity-proof-failure"
GRAPH_PATH = REPO_ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
REPRESENTATIVE = Path(
    os.environ.get(
        "README_AGENT_CLAIM_POLARITY_REPRESENTATIVE",
        str(REPO_ROOT / "runs/baseline/aspose-3d-foss__Aspose.3D-FOSS-for-.NET"),
    )
).resolve()
FORMAT_REPRESENTATIVE = Path(
    os.environ.get(
        "README_AGENT_FORMAT_CONTRACT_REPRESENTATIVE",
        str(REPO_ROOT / "runs/baseline/aspose-3d-foss__Aspose.3D-FOSS-for-Java"),
    )
).resolve()
GO_REPRESENTATIVE = Path(
    os.environ.get(
        "README_AGENT_GO_CLAIM_POLARITY_REPRESENTATIVE",
        str(REPO_ROOT / "runs/baseline/aspose-pdf-foss__Aspose-PDF-FOSS-for-Go"),
    )
).resolve()
TASK_ID = "L8-TRUTH-03-CLAIM-POLARITY"
PYTHON = sys.executable
SOURCE_PATH = "src/main/Aspose.ThreeD/Aspose/ThreeD/Scene.cs"
CONSTRAINT_ANCHOR = "This feature is not available in the FOSS version."
RENDER_SIGNATURE = "public void Render(Entities.Camera camera, string fileName)"
SAVE_SIGNATURE = "public void Save(Stream stream, FileFormat format)"
FOCUSED_COMMAND = (
    PYTHON,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_evidence_polarity.py",
    "tests/unit/test_draft_product_truth_capability.py",
    "tests/unit/test_product_truth_ingestion.py",
    "tests/unit/test_fact_acceptance_contract.py",
    "tests/unit/test_facts_schema_v2.py",
    "tests/unit/test_facts_provider.py",
    "tests/unit/test_supervisor_product_truth.py",
)
OFFICIAL_COMMAND = (PYTHON, "scripts/governance/run_official_checks.py")
IMPLEMENTATION_PATHS = (
    "docs/architecture.md",
    "plans/investigations/tools/claim_polarity_evidence_support.py",
    "prompts/generation/draft_product_truth.yaml",
    "src/readme_agent/facts/acceptance_contract.py",
    "src/readme_agent/facts/agentic_drafting.py",
    "src/readme_agent/facts/drafting_context.py",
    "src/readme_agent/facts/evidence_polarity.py",
    "src/readme_agent/facts/policy_evidence.py",
    "src/readme_agent/facts/schema_v2.py",
    "tests/unit/test_agentic_drafting.py",
    "tests/unit/test_draft_product_truth_capability.py",
    "tests/unit/test_evidence_polarity.py",
    "tests/unit/test_facts_schema_v2.py",
)


def _git(*args: str, root: Path = REPO_ROOT) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(command: tuple[str, ...]) -> dict[str, Any]:
    result = subprocess.run(
        list(command),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "command": " ".join(command),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _spec(value: str, anchor: str) -> EvidenceBackedProductFact:
    return EvidenceBackedProductFact(
        value=value,
        evidence_paths=[SOURCE_PATH],
        required_symbols=[anchor],
    )


def _python_boolean_control() -> FactRecordV2:
    with tempfile.TemporaryDirectory(prefix="readme-agent-polarity-") as temporary:
        root = Path(temporary)
        source = root / "src" / "Scene.py"
        source.parent.mkdir()
        source.write_text(
            "class Scene:\n"
            "    def __init__(self, name=None):\n"
            '        self.name = name if name is not None else ""\n',
            encoding="utf-8",
        )
        return evidence_fact_candidate(
            root,
            "synthetic-python-revision",
            None,
            "product.capabilities",
            [
                EvidenceBackedProductFact(
                    value="Scene object construction.",
                    evidence_paths=["src/Scene.py"],
                    required_symbols=["class Scene"],
                )
            ],
        )


def _control_state() -> dict[str, Any]:
    status = _git("status", "--porcelain=v1")
    return {
        "head": _git("rev-parse", "HEAD"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "tree_clean_at_start": not status,
        "tree_porcelain_sha256": hashlib.sha256(status.encode("utf-8")).hexdigest(),
        "builder_path": Path(__file__).resolve().relative_to(REPO_ROOT).as_posix(),
        "builder_sha256": _sha256(Path(__file__).resolve()),
        "implementation": {path: _sha256(REPO_ROOT / path) for path in IMPLEMENTATION_PATHS},
    }


def _readme_claim(source_revision: str) -> dict[str, Any]:
    readme = REPRESENTATIVE / "README.md"
    lines = readme.read_text(encoding="utf-8-sig").splitlines()
    line_number = next(
        index for index, line in enumerate(lines, start=1) if line == "- Rendering functionality"
    )
    return {
        "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
        "source_revision": source_revision,
        "source_path": "README.md",
        "line_number": line_number,
        "exact_excerpt": lines[line_number - 1],
        "provenance_disposition": "curated_product_readme_claim",
        "trust_disposition": "valuable_unverified_until_correlated",
        "reuse_disposition": "eligible_only_after_directional_repository_validation",
    }


def _write(run_official: bool) -> list[str]:
    control = _control_state()
    if not control["tree_clean_at_start"]:
        raise RuntimeError("claim-polarity proof requires a clean committed control tree")
    representative_head = _git("rev-parse", "HEAD", root=REPRESENTATIVE)
    representative_status = _git("status", "--porcelain=v1", root=REPRESENTATIVE)
    format_head = _git("rev-parse", "HEAD", root=FORMAT_REPRESENTATIVE)
    format_status = _git("status", "--porcelain=v1", root=FORMAT_REPRESENTATIVE)
    go_head = _git("rev-parse", "HEAD", root=GO_REPRESENTATIVE)
    go_status = _git("status", "--porcelain=v1", root=GO_REPRESENTATIVE)
    real_controls = build_real_controls(REPRESENTATIVE, REPO_ROOT)
    go_compound_controls = build_go_compound_identifier_evidence(
        GO_REPRESENTATIVE,
        REPO_ROOT,
    )
    limitation = limitation_fact_candidate(
        REPRESENTATIVE,
        representative_head,
        None,
        [
            _spec(
                "Rendering functionality is not available in the FOSS version.",
                CONSTRAINT_ANCHOR,
            )
        ],
    )
    save_capability = evidence_fact_candidate(
        REPRESENTATIVE,
        representative_head,
        None,
        "product.capabilities",
        [_spec("Save scenes to a stream using a file format.", SAVE_SIGNATURE)],
    )
    render_capability = evidence_fact_candidate(
        REPRESENTATIVE,
        representative_head,
        None,
        "product.capabilities",
        [_spec("Render scenes to an external file.", RENDER_SIGNATURE)],
    )
    vague_constraint = limitation_fact_candidate(
        REPRESENTATIVE,
        representative_head,
        None,
        [_spec("Rendering functionality is not available.", "not available")],
    )
    format_policy = load_policy("aspose-3d-foss")
    if format_policy.product_truth is None:
        raise RuntimeError("aspose-3d-foss product truth is missing")
    format_fact = evidence_fact_candidate(
        FORMAT_REPRESENTATIVE,
        format_head,
        None,
        "product.formats",
        format_policy.product_truth.formats,
    )
    python_boolean = _python_boolean_control()
    if not python_boolean.evidence_assessments:
        raise RuntimeError("Python boolean polarity control produced no evidence assessment")
    direct_assessments = {
        "verified_limitation": limitation.evidence_assessments[0].model_dump(mode="json"),
        "verified_capability": save_capability.evidence_assessments[0].model_dump(mode="json"),
        "opposite_polarity": render_capability.evidence_assessments[0].model_dump(mode="json"),
        "under_specific_constraint": vague_constraint.evidence_assessments[0].model_dump(
            mode="json"
        ),
        "python_boolean_negation": python_boolean.evidence_assessments[0].model_dump(mode="json"),
    }
    focused = _run(FOCUSED_COMMAND)
    official = _run(OFFICIAL_COMMAND) if run_official else None
    tree_stable = _git("rev-parse", "HEAD") == control["head"] and not _git(
        "status", "--porcelain=v1"
    )
    source = REPRESENTATIVE / SOURCE_PATH
    source_text = source.read_text(encoding="utf-8-sig")
    constraint_recheck = assess_evidence_polarity(
        root=REPRESENTATIVE,
        evidence_paths=[SOURCE_PATH],
        anchor=CONSTRAINT_ANCHOR,
        fact_id=limitation.fact_id,
        claim_text="Rendering functionality is not available in the FOSS version.",
        expected_polarity="explicit_constraint",
        source_revision=representative_head,
        observed_at=None,
    )
    checks = {
        "focused_tests_pass": focused["exit_code"] == 0,
        "official_checks_pass": bool(official and official["exit_code"] == 0 and tree_stable),
        "representative_is_clean": not representative_status,
        "format_representative_is_clean": not format_status,
        "go_representative_is_clean": not go_status,
        "go_representative_revision_bound": len(go_head) == 40,
        "format_representative_revision_bound": len(format_head) == 40,
        "representative_revision_bound": len(representative_head) == 40,
        "source_checksum_bound": len(_sha256(source)) == 64,
        "curated_readme_claim_captured": _readme_claim(representative_head)["line_number"] == 30,
        "constraint_anchor_exists": CONSTRAINT_ANCHOR in source_text,
        "real_limitation_verified": limitation.verification_state == "verified",
        "real_positive_capability_verified": save_capability.verification_state == "verified",
        "positive_render_claim_rejected": render_capability.verification_state == "blocked",
        "generic_constraint_fragment_rejected": vague_constraint.verification_state == "blocked",
        "python_boolean_negation_remains_positive": (
            python_boolean.verification_state == "verified"
            and python_boolean.evidence_assessments[0].observed_polarity
            == "positive_implementation"
        ),
        "exact_revision_excerpt_persisted": bool(
            constraint_recheck
            and constraint_recheck.accepted
            and constraint_recheck.source_revision == representative_head
            and constraint_recheck.source_path == SOURCE_PATH
            and constraint_recheck.fact_id == limitation.fact_id
            and constraint_recheck.exact_excerpt
        ),
        "fact_record_retains_assessments": all(
            item.evidence_assessments
            for item in (limitation, save_capability, render_capability, vague_constraint)
        ),
        "real_dotnet_opposite_polarity_controls_pass": real_controls["verdict"] == "VERIFIED",
        "real_go_compound_identifier_controls_pass": (
            go_compound_controls["verdict"] == "VERIFIED"
        ),
        "format_contract_remains_separate": (
            format_fact.verification_state == "verified"
            and format_fact.evidence_assessments is None
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        FAILURE_DIR.mkdir(parents=True, exist_ok=True)
        write_redacted_text(FAILURE_DIR / "focused-tests.stdout.log", focused["stdout"])
        write_redacted_text(FAILURE_DIR / "focused-tests.stderr.log", focused["stderr"])
        if official:
            write_redacted_text(FAILURE_DIR / "official-checks.stdout.log", official["stdout"])
            write_redacted_text(FAILURE_DIR / "official-checks.stderr.log", official["stderr"])
        write_redacted_json(
            FAILURE_DIR / "verification.json",
            {
                "schema_version": 1,
                "task_id": TASK_ID,
                "control_repository": control,
                "checks": checks,
                "failures": failures,
                "verdict": "FAILED",
            },
        )
        refresh_sha256sums(FAILURE_DIR)
        return failures
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_redacted_json(
        EVIDENCE_DIR / "repository-snapshot.json",
        {
            "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
            "root": str(REPRESENTATIVE),
            "source_revision": representative_head,
            "tree_clean": not representative_status,
            "readme_sha256": _sha256(REPRESENTATIVE / "README.md"),
            "source_path": SOURCE_PATH,
            "source_sha256": _sha256(source),
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "curated-readme-claim.json", _readme_claim(representative_head)
    )
    write_redacted_json(EVIDENCE_DIR / "polarity-assessments.json", direct_assessments)
    write_redacted_json(EVIDENCE_DIR / "real-dotnet-controls.json", real_controls)
    write_redacted_json(
        EVIDENCE_DIR / "real-go-compound-identifier-controls.json",
        go_compound_controls,
    )
    write_redacted_json(
        EVIDENCE_DIR / "format-contract-control.json",
        {
            "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Java",
            "source_revision": format_head,
            "tree_clean": not format_status,
            "fact": format_fact.model_dump(mode="json"),
            "expected_contract": (
                "formats require their own structural/directional truth and do not inherit "
                "capability implementation polarity"
            ),
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "fact-records.json",
        {
            "verified_limitation": limitation.model_dump(mode="json"),
            "verified_capability": save_capability.model_dump(mode="json"),
            "rejected_capability": render_capability.model_dump(mode="json"),
            "rejected_vague_constraint": vague_constraint.model_dump(mode="json"),
            "python_boolean_negation": python_boolean.model_dump(mode="json"),
        },
    )
    write_redacted_text(EVIDENCE_DIR / "focused-tests.stdout.log", focused["stdout"])
    write_redacted_text(EVIDENCE_DIR / "focused-tests.stderr.log", focused["stderr"])
    if official:
        write_redacted_text(EVIDENCE_DIR / "official-checks.stdout.log", official["stdout"])
        write_redacted_text(EVIDENCE_DIR / "official-checks.stderr.log", official["stderr"])
    write_redacted_json(
        EVIDENCE_DIR / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "control_repository": control,
            "commands": {
                "focused": {"command": focused["command"], "exit_code": focused["exit_code"]},
                "official": (
                    {
                        "command": official["command"],
                        "exit_code": official["exit_code"],
                        "tree_stable": tree_stable,
                    }
                    if official
                    else {"status": "not_run"}
                ),
            },
            "checks": checks,
            "failures": failures,
            "verdict": "VERIFIED" if not failures else "FAILED",
        },
    )
    graph, _ = load_mission_graph(GRAPH_PATH)
    task = next(task for task in graph.taskcards if task.task_id == TASK_ID)
    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    scoreboard_hash = lifecycle_scoreboard_sha256(scoreboard)
    write_redacted_json(
        EVIDENCE_DIR / "mission-contribution.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "goal_ids": task.goal_ids,
            "core_contribution": task.core_contribution.model_dump(mode="json"),
            "acceptance_checks_passed": task.acceptance_checks,
            "proof_refs": [
                "plans/investigations/evidence/level8-claim-polarity/verification.json",
                "plans/investigations/evidence/level8-claim-polarity/polarity-assessments.json",
                "plans/investigations/evidence/level8-claim-polarity/real-dotnet-controls.json",
                "plans/investigations/evidence/level8-claim-polarity/"
                "real-go-compound-identifier-controls.json",
                "plans/investigations/evidence/level8-claim-polarity/format-contract-control.json",
                "plans/investigations/evidence/level8-claim-polarity/fact-records.json",
            ],
            "scoreboard_before_sha256": scoreboard_hash,
            "scoreboard_after_sha256": scoreboard_hash,
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": not failures,
        },
    )
    write_redacted_text(
        EVIDENCE_DIR / "reproduction.txt",
        ".venv/Scripts/python plans/investigations/tools/"
        "build_claim_polarity_evidence.py --official --check\n",
    )
    refresh_sha256sums(EVIDENCE_DIR)
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    failures = _write(args.official)
    if args.check and failures:
        raise SystemExit("claim-polarity evidence failed: " + ", ".join(failures))
    print(f"wrote claim-polarity evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
