"""Resolve the 2026-07-23 semantic closure findings without laundering overclaims."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

from semantic_closure_test_inventory import TEST_GROUPS

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = REPO_ROOT / "plans" / "requirements.md"
MATRIX = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "implementation-truth-matrix-2026"
    / "matrix.json"
)
REPORT = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-semantic-closure-verification.json"
)
REPORT_REF = REPORT.relative_to(REPO_ROOT).as_posix()
PRIOR_REPORT = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-wave0-semantic-closure"
    / "semantic-closure-verification.json"
)
PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
PIPE = re.compile(r"(?<!\\)\|")

DOWNGRADES = {
    "GOV-009": (
        "The validator checks IDs, enums, section order, logs, and module maps, but not the row's "
        "claimed phase/decision-reference validity or bidirectional master traceability."
    ),
    "RDM-001": (
        "The renderer rejects new callouts and migration removes them, but overwrite-scenario "
        "fixtures intentionally still contain legacy callout spans, contradicting the literal "
        "claim that fixtures no longer contain them."
    ),
    "CORE-001": (
        "Aspose-specific facts remain in generic production modules including commands.py, "
        "readme/renderer.py, and validation/rules/prominence.py, so they are not confined to "
        "registry and policy data."
    ),
    "CORE-006": (
        "The registry now contains 31 entries, 26 of them non-disabled; the three Java pilot roles "
        "remain identifiable, but the row's 'three enabled repositories' wording is no longer true."
    ),
    "OPS-003": (
        "readme-agent-run.yml is manual and dry-run, but its job grants contents: write for the "
        "Git-ref state backend and consumes secrets, so the literal read-only workflow claim is "
        "false."
    ),
    "SAFE-005": (
        "readme-agent-run.yml exposes only dry_run, but its run job overrides permissions to "
        "contents: write for durable state, contradicting the literal read-only-content claim."
    ),
    "MEM-002": (
        "State-version CAS and per-repository locks exist, and domain acceptance records an "
        "upstream revision, but the backend CAS is not itself conditioned on a freshly re-read "
        "upstream revision."
    ),
    "PRL-001": (
        "Identical facts_hash retries find the existing PR, but a changed candidate/facts hash can "
        "select a new branch; update/supersede/drift reconciliation remains open as PRL-009."
    ),
    "AUTH-003": (
        "The loader targets config/authorization, but the claimed empty directory is not present "
        "in the committed tree and no committed profile demonstrates the location contract."
    ),
}

REFERENCE_GROUPS: dict[str, tuple[str, ...]] = {
    "src/readme_agent/readme/gap_detector.py": ("CORE-010",),
    "src/readme_agent/gitsafety/_git.py": ("CORE-013",),
    "src/readme_agent/cli.py": ("CORE-002", "CORE-026", "CORE-027"),
    "src/readme_agent/paths.py": ("CORE-031",),
    ".github/workflows/ci.yml": ("OPS-002", "SAFE-004", "NFR-004"),
    ".github/workflows/update-products-registry.yml": ("OPS-008",),
    "docs/presentation-standard.md": ("DOC-003", "DOC-004"),
    "plans/investigations/reference-repository-benchmark.md": ("DOC-003",),
    "docs/github-surface-control.md": ("DOC-005",),
    "plans/investigations/llm-gateway-context-ceiling-corrected.md": ("LLM-019",),
    "src/readme_agent/env.py": ("LLM-013",),
    "src/readme_agent/state/backend.py": ("MEM-003",),
    "logs/2026-07-19.md": ("RUN-003",),
    "scripts/retrofits/prove_open_presentation_pr_live.py": ("PRL-004",),
    "src/readme_agent/evidence/writer.py": ("SAFE-008", "SAFE-009"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _split(line: str) -> list[str]:
    return [cell.strip() for cell in PIPE.split(line.strip()[1:-1])]


def _proof_maps() -> tuple[dict[str, list[str]], dict[str, list[dict[str, object]]]]:
    selectors: dict[str, list[str]] = defaultdict(list)
    references: dict[str, list[dict[str, object]]] = defaultdict(list)
    for selector, requirement_ids in TEST_GROUPS.items():
        for requirement_id in requirement_ids:
            selectors[requirement_id].append(selector)
    for raw_path, requirement_ids in REFERENCE_GROUPS.items():
        path = REPO_ROOT / raw_path
        if not path.is_file():
            raise SystemExit(f"semantic proof reference is missing: {raw_path}")
        metadata = {"path": raw_path, "bytes": path.stat().st_size, "sha256": _sha256(path)}
        for requirement_id in requirement_ids:
            references[requirement_id].append(metadata)
    return selectors, references


def _rewrite_requirements(
    original: str, finding_ids: set[str], supported_ids: set[str]
) -> tuple[str, dict[str, dict[str, str]]]:
    dispositions: dict[str, dict[str, str]] = {}
    output: list[str] = []
    for line in original.splitlines():
        if not line.startswith("| "):
            output.append(line)
            continue
        cells = _split(line)
        requirement_id = cells[0].strip("`") if len(cells) == 6 else ""
        if requirement_id not in finding_ids:
            output.append(line)
            continue
        if requirement_id == "MEM-003":
            cells[4] = cells[4].replace(
                "tests/unit/test_state_backend.py::FakeStateBackend",
                "tests/unit/test_state_backend.py::TestFakeStateBackendCAS",
            )
        for marker in (
            " Semantic audit correction (2026-07-23):",
            " Semantic closure proof (2026-07-23):",
            " Semantic proof (2026-07-23):",
            " Audit correction:",
            " Proof:",
        ):
            cells[4] = cells[4].split(marker, 1)[0]
        if requirement_id in DOWNGRADES:
            cells[2] = "PARTIAL"
            note = f"Audit correction: `{REPORT_REF}` (`{requirement_id}`)."
            disposition = "downgraded_to_partial"
        else:
            assert requirement_id in supported_ids
            note = f"Proof: `{REPORT_REF}` (`{requirement_id}`)."
            disposition = "preserved_implemented_with_exact_proof"
        cells[4] = f"{cells[4]} {note}"
        output.append("| " + " | ".join(cells) + " |")
        dispositions[requirement_id] = {"disposition": disposition, "note": note}
    return "\n".join(output) + "\n", dispositions


def main() -> int:
    requirements_sha256_before = _sha256(REQUIREMENTS)
    original = REQUIREMENTS.read_text(encoding="utf-8")
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    finding_rows = matrix["rows_with_high_confidence_findings"]
    finding_ids = {row["id"] for row in finding_rows}
    prior_report_path = REPORT if REPORT.is_file() else PRIOR_REPORT
    if not finding_ids and prior_report_path.is_file():
        prior_report = json.loads(prior_report_path.read_text(encoding="utf-8"))
        finding_rows = [
            {
                "id": row["requirement_id"],
                "high_confidence_findings": row["prior_findings"],
            }
            for row in prior_report["proof_rows"]
        ]
        finding_ids = {row["id"] for row in finding_rows}
    if len(finding_ids) != 85:
        raise SystemExit(f"expected the audited 85 findings, found {len(finding_ids)}")
    if not set(DOWNGRADES) <= finding_ids:
        raise SystemExit("downgrade inventory no longer matches the finding set")

    selectors, references = _proof_maps()
    supported_ids = finding_ids - set(DOWNGRADES)
    uncovered = supported_ids - (set(selectors) | set(references))
    if uncovered:
        raise SystemExit(f"supported findings lack exact proof mappings: {sorted(uncovered)}")

    unique_selectors = sorted({selector for values in selectors.values() for selector in values})
    command = [str(PYTHON), "-m", "pytest", "-q", *unique_selectors]
    run = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if run.returncode != 0:
        raise SystemExit(f"focused semantic proof run failed:\n{run.stdout}\n{run.stderr}")

    rewritten, dispositions = _rewrite_requirements(original, finding_ids, supported_ids)
    proof_rows = []
    finding_by_id = {row["id"]: row for row in finding_rows}
    for requirement_id in sorted(finding_ids):
        proof_rows.append(
            {
                "requirement_id": requirement_id,
                "prior_findings": finding_by_id[requirement_id]["high_confidence_findings"],
                **dispositions[requirement_id],
                "downgrade_reason": DOWNGRADES.get(requirement_id),
                "pytest_selectors": selectors.get(requirement_id, []),
                "committed_references": references.get(requirement_id, []),
            }
        )

    REQUIREMENTS.write_text(rewritten, encoding="utf-8")
    report = {
        "schema_version": 1,
        "mission_id": "LEVEL8-CENTRAL-REPOSITORY-PRESENTATION",
        "task_id": "L8-WAVE0-SEMANTIC-CLOSURE-EVIDENCE",
        "observed_at": "2026-07-23",
        "result": "PASS",
        "requirements_source_sha256_before": requirements_sha256_before,
        "requirements_source_sha256_after": _sha256(REQUIREMENTS),
        "findings_consumed": len(finding_ids),
        "implemented_closures_preserved": len(supported_ids),
        "overclaims_downgraded_to_partial": len(DOWNGRADES),
        "pytest": {
            "command": command,
            "selector_count": len(unique_selectors),
            "returncode": run.returncode,
            "stdout": run.stdout,
            "stderr": run.stderr,
        },
        "proof_rows": proof_rows,
        "negative_controls": [
            "No finding is closed by a path-only citation without a requirement-specific report "
            "entry.",
            "Every preserved IMPLEMENTED row maps to a focused pytest selector or "
            "checksum-addressed committed reference.",
            "Every literal contradiction found during source/workflow inspection is downgraded, "
            "not explained away.",
        ],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Verified {len(supported_ids)} closures; downgraded {len(DOWNGRADES)} overclaims.")
    print(run.stdout.strip())
    print(f"Written: {REPORT_REF}")
    print("Updated: plans/requirements.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
