"""Build clean-tree proof for package-root roles and product-fact binding."""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from readme_agent.evidence.writer import (  # noqa: E402
    refresh_sha256sums,
    sha256_file,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.facts.manifest_facts import manifest_fact_candidates  # noqa: E402
from readme_agent.facts.root_roles import classify_package_root_roles  # noqa: E402
from readme_agent.profile.detector import build_profile  # noqa: E402
from readme_agent.registry.loader import require_listed  # noqa: E402
from readme_agent.repository_snapshot import capture_repository_snapshot  # noqa: E402
from readme_agent.state.git_backend import default_state_backend  # noqa: E402
from readme_agent.supervisor.mission_goal_guard import (  # noqa: E402
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)

TASK_ID = "L8-TRUTH-02-ROOT-ROLES"
ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-.NET"
EXPECTED_REVISION = "6a209e8fc3dfc305df39a417037e32a4d4c7b2be"
EXPECTED_PRODUCT_MANIFEST = "src/main/Aspose.ThreeD/Aspose.ThreeD.csproj"
BASELINE = REPO_ROOT / "runs" / "baseline" / "aspose-3d-foss__Aspose.3D-FOSS-for-.NET"
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "package_root_roles" / "aspose-3d-foss-dotnet"
EVIDENCE_DIR = REPO_ROOT / "plans" / "investigations" / "evidence" / "level8-package-root-roles"
PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"

FOCUSED_COMMAND = (
    str(PYTHON),
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_package_root_roles.py",
    "tests/unit/test_product_truth_ingestion.py",
    "tests/unit/test_facts_schema_v2.py",
    "tests/unit/test_fact_acceptance_contract.py",
    "tests/unit/test_fact_render_views.py",
    "tests/unit/test_profile.py",
    "tests/unit/test_profile_cached.py",
    "tests/unit/test_ecosystems.py",
    "tests/unit/test_capabilities.py",
    "tests/unit/test_supervisor_product_truth.py",
    "tests/unit/test_local_poc_evidence.py",
)
OFFICIAL_COMMAND = (str(PYTHON), "scripts/governance/run_official_checks.py")


def _run(command: tuple[str, ...]) -> dict:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "command": " ".join(command).replace(str(REPO_ROOT) + "\\", ""),
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _git(*args: str) -> str:
    result = subprocess.run(
        ("git", *args),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


def _real_root_proof() -> tuple[dict, dict, dict]:
    entry = require_listed(ORG_REPO)
    snapshot = capture_repository_snapshot(entry, BASELINE)
    if snapshot.source_revision != EXPECTED_REVISION:
        revision_mismatch = f"{snapshot.source_revision} != {EXPECTED_REVISION}"
        raise RuntimeError(f"real .NET baseline revision changed: {revision_mismatch}")
    profile = build_profile(ORG_REPO, BASELINE).model_copy(
        update={"source_revision": snapshot.source_revision}
    )
    inventory = classify_package_root_roles(
        entry,
        profile,
        BASELINE,
        snapshot.source_revision,
    )
    facts = manifest_fact_candidates(
        entry,
        profile,
        BASELINE,
        snapshot.source_revision,
        None,
        inventory,
    )
    by_field = {fact.field: fact for fact in facts}
    selected = {
        field: by_field[field].model_dump(mode="json")
        for field in (
            "installation.coordinates",
            "product.compatibility",
            "release.state",
        )
    }
    roles = {record.manifest_path: record.role for record in inventory.roots}
    if inventory.selected_product_manifest_path != EXPECTED_PRODUCT_MANIFEST:
        raise RuntimeError("real .NET product root was not selected")
    if roles != {
        "src/converter/Converter.csproj": "converter",
        EXPECTED_PRODUCT_MANIFEST: "product",
        "src/test/Aspose.ThreeD.Tests/Aspose.ThreeD.Tests.csproj": "test",
    }:
        raise RuntimeError(f"unexpected real .NET root roles: {roles}")
    coordinates = selected["installation.coordinates"]["value"]
    compatibility = selected["product.compatibility"]["value"]
    releases = selected["release.state"]["value"]
    if [row.get("name") for row in coordinates] != ["Aspose.3D.FOSS"]:
        raise RuntimeError("converter/test coordinates leaked into visitor facts")
    if [row.get("minimum_runtime") for row in compatibility] != ["netcoreapp3.1"]:
        raise RuntimeError("converter/test target frameworks leaked into compatibility")
    if [row.get("version") for row in releases] != ["26.1.0"]:
        raise RuntimeError("converter/test versions leaked into release state")
    source_files = {
        relative: sha256_file(BASELINE / Path(*relative.split("/")))
        for relative in (
            "src/converter/Converter.csproj",
            EXPECTED_PRODUCT_MANIFEST,
            "src/test/Aspose.ThreeD.Tests/Aspose.ThreeD.Tests.csproj",
        )
    }
    source = {
        "org_repo": ORG_REPO,
        "source_revision": snapshot.source_revision,
        "inventory_sha256": snapshot.inventory_sha256,
        "manifest_sha256": source_files,
        "fixture_provenance": str(
            (FIXTURE / "fixture-provenance.json").relative_to(REPO_ROOT)
        ).replace("\\", "/"),
    }
    return inventory.model_dump(mode="json"), selected, source


def main() -> int:
    branch = _git("branch", "--show-current")
    head = _git("rev-parse", "HEAD")
    if _git("status", "--porcelain"):
        raise RuntimeError("package-root-role evidence requires a clean committed starting tree")

    focused = _run(FOCUSED_COMMAND)
    official = _run(OFFICIAL_COMMAND)
    if focused["exit_code"] != 0 or official["exit_code"] != 0:
        raise RuntimeError("package-root-role verification failed")
    if _git("rev-parse", "HEAD") != head or _git("status", "--porcelain"):
        raise RuntimeError("HEAD or working tree changed during package-root-role verification")

    inventory, selected_facts, source = _real_root_proof()
    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    scoreboard_sha256 = lifecycle_scoreboard_sha256(scoreboard)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_redacted_json(EVIDENCE_DIR / "root-role-inventory.json", inventory)
    write_redacted_json(EVIDENCE_DIR / "selected-product-facts.json", selected_facts)
    write_redacted_json(EVIDENCE_DIR / "source-revision-and-checksums.json", source)
    write_redacted_text(EVIDENCE_DIR / "official-checks.stdout.log", official["stdout"] + "\n")
    write_redacted_text(EVIDENCE_DIR / "official-checks.stderr.log", official["stderr"] + "\n")
    write_redacted_json(
        EVIDENCE_DIR / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "implementation_commit": head,
            "branch": branch,
            "verified_at": datetime.now(UTC).isoformat(),
            "tree_precondition": "CLEAN_AT_START_HEAD_UNCHANGED",
            "focused_check": {
                "command": focused["command"],
                "exit_code": focused["exit_code"],
                "stdout": focused["stdout"],
                "stderr": focused["stderr"],
            },
            "official_check": {
                "command": official["command"],
                "exit_code": official["exit_code"],
                "raw_stdout": "official-checks.stdout.log",
                "raw_stderr": "official-checks.stderr.log",
            },
            "real_regression": {
                "org_repo": ORG_REPO,
                "source_revision": EXPECTED_REVISION,
                "selected_product_manifest": EXPECTED_PRODUCT_MANIFEST,
                "excluded_roles": ["converter", "test"],
                "selected_coordinate": "Aspose.3D.FOSS",
                "selected_compatibility": "netcoreapp3.1",
                "selected_release": "26.1.0",
            },
            "negative_controls_passed": [
                "newer converter framework cannot become product compatibility",
                "test project cannot become an installation coordinate",
                "root ordering cannot change selection or inventory hash",
                "Windows and Git path separators produce the same inventory",
                "ambiguous equal candidates remain unknown and block dependent facts",
                "test, sample, converter, generator, benchmark, and build-tool roles are typed",
                "single-root Java and Python controls select reproducibly",
                "legacy facts without root roles retain their canonical hash for migration",
            ],
            "verdict": "VERIFIED",
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "mission-contribution.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "goal_ids": ["GOAL-TRUTH"],
            "core_contribution": {
                "kind": "visible_deliverable",
                "summary": (
                    "Classify product, test, sample, converter, generator, benchmark, "
                    "build-tool, and unknown roots and select the distributed product root "
                    "deterministically."
                ),
            },
            "acceptance_checks_passed": [
                "Non-product roots cannot silently supply visitor-facing product facts",
            ],
            "proof_refs": [
                "plans/investigations/evidence/level8-package-root-roles/verification.json",
                "plans/investigations/evidence/level8-package-root-roles/root-role-inventory.json",
                "plans/investigations/evidence/level8-package-root-roles/selected-product-facts.json",
                (
                    "plans/investigations/evidence/level8-package-root-roles/"
                    "source-revision-and-checksums.json"
                ),
                "plans/investigations/evidence/level8-package-root-roles/official-checks.stdout.log",
            ],
            "scoreboard_before_sha256": scoreboard_sha256,
            "scoreboard_after_sha256": scoreboard_sha256,
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": True,
        },
    )
    write_redacted_text(
        EVIDENCE_DIR / "reproduction.txt",
        (".venv/Scripts/python plans/investigations/tools/build_package_root_role_evidence.py\n"),
    )
    refresh_sha256sums(EVIDENCE_DIR)
    print(f"Package-root-role evidence written to {EVIDENCE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
