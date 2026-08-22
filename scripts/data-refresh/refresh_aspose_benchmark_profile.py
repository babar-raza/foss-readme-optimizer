#!/usr/bin/env python3
"""Freeze and freshly audit the current Aspose.org README benchmark in isolation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

from readme_agent.facts.aspose_benchmark_profile import refresh_benchmark_profile


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_upstream_runner(aspose_root: Path):
    pipeline_root = aspose_root / "scripts" / "pipeline"
    module_path = pipeline_root / "commands" / "foss" / "readme_refresh_run.py"
    if not module_path.is_file():
        raise FileNotFoundError(f"Aspose.org README audit runner is missing: {module_path}")
    sys.path.insert(0, str(pipeline_root))
    spec = importlib.util.spec_from_file_location("asposeorg_readme_refresh_run", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Aspose.org README audit runner: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, module_path


def _audit_runner(aspose_root: Path, frozen_reports_root: Path) -> dict[str, Any]:
    module, module_path = _load_upstream_runner(aspose_root)
    module.configure(
        repo_root=aspose_root,
        reports_root=frozen_reports_root,
        clone_cache_root=aspose_root / "runs" / ".clone_cache",
        candidate_tree_name="repo-presenter-regen-full",
    )
    original_exclusions = module._load_registry_exclusions

    def complete_benchmark_exclusions() -> list[dict[str, Any]]:
        return [item for item in original_exclusions() if item.get("match") != "family_platform"]

    module._load_registry_exclusions = complete_benchmark_exclusions
    result = module.audit_portfolio()
    checks_path = (
        aspose_root / "scripts" / "pipeline" / "commands" / "foss" / "readme_refresh_checks.py"
    )
    result["audit_runner"] = {
        "readme_refresh_run_sha256": _sha256(module_path),
        "readme_refresh_checks_sha256": _sha256(checks_path),
        "checks_module_version": getattr(module.checks, "CHECKS_MODULE_VERSION", None),
        "denominator_adaptation": (
            "family/platform exclusions were ignored only on the frozen benchmark copy so the "
            "local 31-candidate development denominator, including cells/typescript, was audited"
        ),
        "source_repository_mutated": False,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--aspose-root",
        type=Path,
        default=Path("D:/onedrive/Documents/GitHub/aspose.org"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("runs/multi-agent/L8-PF-01-KNOWLEDGE-ACCEPTANCE-IDENTITY/benchmark-snapshot"),
    )
    args = parser.parse_args()
    receipt = refresh_benchmark_profile(
        args.aspose_root,
        args.output_root,
        audit_runner=_audit_runner,
    )
    print(
        "benchmark profile: "
        f"verdict={receipt['verdict']}, "
        f"candidates={receipt['denominator']['candidate_count']}, "
        f"clean={receipt['fresh_audit']['clean_count']}, "
        f"dirty={receipt['fresh_audit']['dirty_count']}"
    )


if __name__ == "__main__":
    main()
