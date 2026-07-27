"""Build real registry and isolated-source controls for acquisition truth."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from readme_agent.ecosystems.resolver import ResolutionResult
from readme_agent.ecosystems.rust_api_schema import (
    RustPackageLayoutV1,
    RustPublicApiSurfaceV1,
)
from readme_agent.ecosystems.rust_format_truth import extract_rust_format_evidence
from readme_agent.ecosystems.rust_package_layout import pinned_rust_git_dependency
from readme_agent.ecosystems.typescript_api_schema import (
    TypeScriptPackageLayoutV1,
    TypeScriptPublicApiSurfaceV1,
)
from readme_agent.facts.acquisition import select_acquisition
from readme_agent.facts.example_execution import ExampleExecutionResultV1
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.isolated_execution_schema import IsolatedExecutionResultV1
from readme_agent.registry.loader import load_products
from readme_agent.registry.models import ProductEntry

IMPLEMENTATION_PATHS = (
    "src/readme_agent/ecosystems/registry_request.py",
    "src/readme_agent/ecosystems/resolver.py",
    "src/readme_agent/facts/acquisition.py",
    "src/readme_agent/facts/acquisition_schema.py",
    "src/readme_agent/facts/acceptance_contract.py",
    "src/readme_agent/facts/provider.py",
    "src/readme_agent/facts/schema_v2.py",
    "src/readme_agent/capabilities/draft_product_truth.py",
    "tests/unit/test_acquisition.py",
    "tests/unit/test_ecosystem_resolver.py",
    "tests/unit/test_facts_provider.py",
)


def verify_evidence_inventory(root: Path) -> dict[str, Any]:
    """Verify committed evidence bytes without regenerating its expensive proof."""

    inventory = root / "sha256sums.txt"
    repository_root = Path(
        subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
    )

    def committed_bytes(path: Path) -> bytes:
        relative = path.resolve().relative_to(repository_root.resolve()).as_posix()
        return subprocess.run(
            ["git", "-C", str(repository_root), "show", f"HEAD:{relative}"],
            check=True,
            capture_output=True,
        ).stdout

    mismatches: list[str] = []
    records: list[dict[str, str]] = []
    for line in inventory.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        observed = hashlib.sha256(committed_bytes(root / relative)).hexdigest()
        records.append({"path": relative, "sha256": observed})
        if observed != expected:
            mismatches.append(relative)
    verification = json.loads((root / "verification.json").read_text(encoding="utf-8"))
    return {
        "path": root.as_posix(),
        "verification_verdict": verification.get("verdict"),
        "inventory_sha256": hashlib.sha256(committed_bytes(inventory)).hexdigest(),
        "file_count": len(records),
        "mismatches": mismatches,
        "accepted": verification.get("verdict") == "VERIFIED" and not mismatches,
    }


def _diagnostic(isolated: IsolatedExecutionResultV1) -> ExampleExecutionResultV1:
    return ExampleExecutionResultV1(
        argv=isolated.argv,
        return_code=isolated.return_code,
        stdout=isolated.stdout,
        stderr=isolated.stderr,
        timed_out=isolated.timed_out,
        environment_names=isolated.environment_names,
        isolation_kind="isolated_result_projection",
    )


def load_python_verification(path: Path) -> LocalProductVerificationV1:
    """Load the canonical Python verifier output, which already uses the shared contract."""

    return LocalProductVerificationV1.model_validate_json(path.read_text(encoding="utf-8"))


def load_typescript_verification(path: Path) -> LocalProductVerificationV1:
    """Project the accepted TypeScript consumer proof into the shared verification contract."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    isolated = IsolatedExecutionResultV1.model_validate(payload["isolated_execution"])
    package = TypeScriptPackageLayoutV1.model_validate(payload["package"])
    surface = TypeScriptPublicApiSurfaceV1.model_validate(payload["surface"])
    accepted = payload["accepted"] is True and isolated.truth_eligible
    return LocalProductVerificationV1(
        org_repo=payload["org_repo"],
        source_revision=payload["source_revision"],
        ecosystem="typescript",
        outcome="SOURCE_BUILD_VERIFIED" if accepted else "BUILD_FAILED",
        detail=(
            "pinned built package and exact TypeScript consumer compiled"
            if accepted
            else "TypeScript source-build proof was not accepted"
        ),
        build=_diagnostic(isolated),
        example_compile=_diagnostic(isolated),
        isolated_execution=isolated if accepted else None,
        truth_eligible=accepted,
        verified_public_symbols=payload["verified_symbols"] if accepted else [],
        public_api_sha256=surface.canonical_hash() if accepted else None,
        typescript_package=package if accepted else None,
    )


def load_rust_verification(path: Path) -> LocalProductVerificationV1:
    """Project the accepted locked Cargo proof into the shared verification contract."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    isolated = IsolatedExecutionResultV1.model_validate(payload["isolated_execution"])
    package = RustPackageLayoutV1.model_validate(payload["package"])
    surface = RustPublicApiSurfaceV1.model_validate(payload["surface"])
    accepted = payload["accepted"] is True and isolated.truth_eligible
    return LocalProductVerificationV1(
        org_repo=payload["org_repo"],
        source_revision=payload["source_revision"],
        ecosystem="rust",
        outcome="SOURCE_BUILD_VERIFIED" if accepted else "BUILD_FAILED",
        detail=(
            "source-pinned crate and exact external Rust consumer passed locked offline Cargo check"
            if accepted
            else "Rust source-build proof was not accepted"
        ),
        build=_diagnostic(isolated),
        example_compile=_diagnostic(isolated),
        isolated_execution=isolated if accepted else None,
        truth_eligible=accepted,
        verified_public_symbols=payload["verified_symbols"] if accepted else [],
        public_api_sha256=surface.canonical_hash() if accepted else None,
        rust_package=package if accepted else None,
        rust_formats=extract_rust_format_evidence(surface) if accepted else [],
        rust_source_dependency=(
            pinned_rust_git_dependency(
                package,
                org_repo=payload["org_repo"],
                source_revision=payload["source_revision"],
            )
            if accepted
            else None
        ),
    )


def _entry(org_repo: str) -> ProductEntry:
    return next(entry for entry in load_products() if entry.org_repo == org_repo)


def _receipt_resolution(decision: dict[str, Any]) -> ResolutionResult:
    receipt = decision["registry_receipt"]
    return ResolutionResult(
        found=receipt["found"],
        detail=receipt["detail"],
        registry_label=receipt["registry_label"],
        request_url=receipt["request_url"],
        status_code=receipt["status_code"],
        response_sha256=receipt["response_sha256"],
        retrieved_at=receipt["retrieved_at"],
    )


def build_acquisition_controls(
    *,
    revisions: dict[str, str],
    python_verification: LocalProductVerificationV1,
    typescript_verification: LocalProductVerificationV1,
    rust_verification: LocalProductVerificationV1,
) -> dict[str, Any]:
    """Resolve seven real ecosystems plus deterministic fail-closed controls."""

    cases = (
        ("java_published", "aspose-cells-foss/Aspose.Cells-FOSS-for-Java", None),
        ("dotnet_published", "aspose-3d-foss/Aspose.3D-FOSS-for-.NET", None),
        ("cpp_nuget_published", "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp", None),
        ("go_proxy_published", "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go", None),
        (
            "python_source_build",
            python_verification.org_repo,
            python_verification,
        ),
        (
            "typescript_source_build",
            typescript_verification.org_repo,
            typescript_verification,
        ),
        ("rust_source_build", rust_verification.org_repo, rust_verification),
    )
    decisions: dict[str, dict[str, Any]] = {}
    for name, org_repo, verification in cases:
        decision = select_acquisition(
            entry=_entry(org_repo),
            source_revision=revisions[org_repo],
            local_verification=verification,
            unavailable_detail="no accepted isolated source-build proof",
        )
        decisions[name] = decision.model_dump(mode="json")

    synthetic = ProductEntry(
        family="readme-agent-nonexistent-acquisition-control",
        platform="java",
        repo_name="readme-agent-nonexistent-acquisition-control",
        repo_url=(
            "https://github.com/readme-agent-controls/readme-agent-nonexistent-acquisition-control"
        ),
        clone_url=(
            "https://github.com/readme-agent-controls/"
            "readme-agent-nonexistent-acquisition-control.git"
        ),
        active=True,
        discovered_via="negative-control",
        mode="dry_run",
        ecosystem="java",
        policy_profile=None,
    )
    false_coordinate = select_acquisition(
        entry=synthetic,
        source_revision="synthetic-negative-control",
        local_verification=None,
        unavailable_detail="no source proof for synthetic false coordinate",
    )
    decisions["synthetic_false_maven"] = false_coordinate.model_dump(mode="json")

    python_prior = decisions["python_source_build"]
    receipt_resolution = _receipt_resolution(python_prior)
    no_source = select_acquisition(
        entry=_entry(python_verification.org_repo),
        source_revision=python_verification.source_revision,
        local_verification=None,
        unavailable_detail="README prose is not source-build proof",
        resolution=receipt_resolution,
    )
    host_only = python_verification.model_copy(
        update={
            "outcome": "ISOLATION_REQUIRED",
            "detail": "host-only diagnostic is ineligible",
            "isolated_execution": None,
            "truth_eligible": False,
            "verified_public_symbols": [],
            "public_api_sha256": None,
            "python_package": None,
        }
    )
    host_only_decision = select_acquisition(
        entry=_entry(python_verification.org_repo),
        source_revision=python_verification.source_revision,
        local_verification=host_only,
        unavailable_detail="host-only diagnostic is ineligible",
        resolution=receipt_resolution,
    )
    network_uncertain = select_acquisition(
        entry=_entry(python_verification.org_repo),
        source_revision=python_verification.source_revision,
        local_verification=python_verification,
        unavailable_detail="network unavailable",
        resolution=ResolutionResult(
            found=False,
            detail="synthetic network uncertainty",
            blocked=True,
            registry_label="PyPI",
            request_url=python_prior["registry_receipt"]["request_url"],
        ),
    )
    return {
        "decisions": decisions,
        "negative_controls": {
            "readme_prose_only": no_source.model_dump(mode="json"),
            "host_only_source_build": host_only_decision.model_dump(mode="json"),
            "network_uncertainty": network_uncertain.model_dump(mode="json"),
        },
    }
