"""Load and validate immutable source proofs used by acquisition-truth evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from readme_agent.ecosystems.rust_format_truth import extract_rust_format_evidence
from readme_agent.ecosystems.rust_package_layout import pinned_rust_git_dependency
from readme_agent.facts.acquisition_pins import (
    python_acquisition_pins,
    rust_acquisition_pins,
    typescript_acquisition_pins,
)
from readme_agent.facts.example_execution import ExampleExecutionResultV1
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.isolated_execution_schema import IsolatedExecutionResultV1
from readme_agent.facts.rust_consumer_schema import RustConsumerProofV1
from readme_agent.facts.typescript_consumer_schema import TypeScriptConsumerProofV1


def verify_evidence_inventory(root: Path) -> dict[str, Any]:
    """Verify committed source-proof bytes without regenerating expensive evidence."""

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
    """Load accepted Python proof and retain its exact source-package pin."""

    verification = LocalProductVerificationV1.model_validate_json(path.read_text(encoding="utf-8"))
    package = verification.python_package
    pins = python_acquisition_pins(package) if verification.truth_eligible and package else []
    return verification.model_copy(update={"acquisition_dependency_pins": pins})


def load_typescript_verification(path: Path) -> LocalProductVerificationV1:
    """Project the complete typed TypeScript consumer proof into acquisition truth."""

    proof = TypeScriptConsumerProofV1.model_validate_json(path.read_text(encoding="utf-8"))
    accepted = proof.accepted and proof.surface is not None
    pins = typescript_acquisition_pins(proof)
    return LocalProductVerificationV1(
        org_repo=proof.org_repo,
        source_revision=proof.source_revision,
        ecosystem="typescript",
        outcome="SOURCE_BUILD_VERIFIED" if accepted else "BUILD_FAILED",
        detail=(
            "pinned built package and exact TypeScript consumer compiled"
            if accepted
            else "TypeScript source-build proof was not accepted"
        ),
        build=_diagnostic(proof.isolated_execution),
        example_compile=_diagnostic(proof.isolated_execution),
        isolated_execution=proof.isolated_execution if accepted else None,
        truth_eligible=accepted,
        verified_public_symbols=proof.verified_symbols if accepted else [],
        public_api_sha256=proof.surface.canonical_hash() if accepted and proof.surface else None,
        typescript_package=proof.package if accepted else None,
        acquisition_dependency_pins=pins,
    )


def load_rust_verification(path: Path) -> LocalProductVerificationV1:
    """Project the complete typed Rust consumer proof into acquisition truth."""

    proof = RustConsumerProofV1.model_validate_json(path.read_text(encoding="utf-8"))
    accepted = proof.accepted
    pins = rust_acquisition_pins(proof)
    return LocalProductVerificationV1(
        org_repo=proof.org_repo,
        source_revision=proof.source_revision,
        ecosystem="rust",
        outcome="SOURCE_BUILD_VERIFIED" if accepted else "BUILD_FAILED",
        detail=(
            "source-pinned crate and exact external Rust consumer passed locked offline Cargo check"
            if accepted
            else "Rust source-build proof was not accepted"
        ),
        build=_diagnostic(proof.isolated_execution),
        example_compile=_diagnostic(proof.isolated_execution),
        isolated_execution=proof.isolated_execution if accepted else None,
        truth_eligible=accepted,
        verified_public_symbols=proof.verified_symbols if accepted else [],
        public_api_sha256=proof.surface.canonical_hash() if accepted else None,
        rust_package=proof.package if accepted else None,
        rust_formats=extract_rust_format_evidence(proof.surface) if accepted else [],
        rust_source_dependency=(
            pinned_rust_git_dependency(
                proof.package,
                org_repo=proof.org_repo,
                source_revision=proof.source_revision,
            )
            if accepted
            else None
        ),
        acquisition_dependency_pins=pins,
    )
