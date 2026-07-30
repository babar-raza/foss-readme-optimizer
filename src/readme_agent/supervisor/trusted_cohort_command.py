"""Command module for freezing and independently reconstructing a trusted cohort."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from readme_agent.evidence.writer import refresh_sha256sums, verify_sha256sums, write_redacted_json
from readme_agent.gitsafety.clone import remote_head_sha
from readme_agent.inspection.git_metadata import get_git_metadata
from readme_agent.registry.loader import PRODUCTS_PATH, load_products
from readme_agent.state.git_backend import default_state_backend
from readme_agent.supervisor.trusted_cohort import (
    build_qualified_trusted_cohort,
    verify_qualified_trusted_cohort,
    write_qualified_trusted_cohort,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=PRODUCTS_PATH)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args(argv)

    metadata = get_git_metadata(Path.cwd())
    if metadata.commit_sha is None:
        raise RuntimeError("cannot bind qualified cohort to control-repository HEAD")
    entries = load_products(args.registry)
    backend = default_state_backend()
    org_repos = [entry.org_repo for entry in entries]
    states = backend.load_many(org_repos)
    cohort = build_qualified_trusted_cohort(
        entries,
        states,
        registry_path=args.registry,
        control_revision=metadata.commit_sha,
        observe_head=remote_head_sha,
    )
    frozen, cohort_dir = write_qualified_trusted_cohort(cohort, output_root=args.output_root)

    reconstructed_states = backend.load_many(org_repos)
    reconstruction = verify_qualified_trusted_cohort(
        frozen,
        entries,
        reconstructed_states,
        registry_path=args.registry,
        control_revision=metadata.commit_sha,
        observe_head=remote_head_sha,
        cohort_dir=cohort_dir,
    )
    write_redacted_json(cohort_dir / "reconstruction.json", reconstruction)
    refresh_sha256sums(cohort_dir)
    if not reconstruction.passed or not verify_sha256sums(cohort_dir):
        raise RuntimeError("qualified trusted cohort reconstruction or checksum proof failed")
    print(
        json.dumps(
            {
                "cohort_id": frozen.cohort_id,
                "qualified_count": frozen.qualified_count,
                "registry_denominator": frozen.registry_denominator,
                "cohort_dir": str(cohort_dir.resolve()),
                "reconstruction_passed": reconstruction.passed,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
