"""RPOC-042: run local-product-example verification against exactly one
registered repo, in a fresh, disposable clone -- the isolated Actions job
`facts/example_execution.py`'s own docstring already anticipated
("production package installation still belongs in a disposable isolated
Actions job") but that no execution profile wires today.

Root cause this addresses (confirmed, not re-derived here): every real
GitHub Actions execution profile (`supervisor/execution_profile.py`'s
`github_observe`/`github_proposal`/`github_apply`) sets
`verify_local_product_facts=False`, so a routine `supervise` run never
actually compiles/runs a repo's minimal example in CI -- only a local
`local_dry_run` invocation does. Flipping that flag on inside those three
profiles would silently change production behavior for every routine run,
not just for this narrow, explicit, matrix-driven purpose -- so this script
(invoked by `.github/workflows/local-product-example-verification.yml`)
calls `facts/local_verification.py::verify_local_product_example()`
directly instead. That function has no dependency on the
`local_fact_verification_allowed()` ContextVar gate (that gate only matters
inside `facts/provider.py::_local_verification_facts`, reached through
`supervise_repo()`'s own `repository_snapshot_scope()`) -- this script never
goes through either, so calling it directly is not a loophole around the
gate, it is simply a different, explicit call path the gate was never meant
to cover.

Thin CLI wrapper (`plans/GOVERNANCE.md` placement rule 2): all real logic --
cloning (`gitsafety/clone.py::clone_baseline`), snapshotting
(`repository_snapshot.py::capture_repository_snapshot`), and building/
compiling the exact policy example (`facts/local_verification.py`, and for
Java repos `facts/java_toolchain.py`'s auto-provisioning) -- lives in
`src/readme_agent/`. This file only parses arguments, orchestrates the call
sequence once per repo, and reports a JSON result. The calling workflow
provisions each matrix entry's non-Java toolchain (`actions/setup-dotnet`/
`-python`/`-node`/`-go`) before invoking this script; Java needs no such
step -- `java_toolchain.provision_jdk()` downloads its own checksum-verified
JDK on demand.

Usage:
    python scripts/ci/verify_local_product_example.py --org-repo ORG/REPO
    python scripts/ci/verify_local_product_example.py --org-repo ORG/REPO --output result.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from readme_agent import paths
from readme_agent.errors import (
    ConfigError,
    GitSafetyError,
    NotAllowlistedError,
    RepositorySnapshotError,
)
from readme_agent.facts.local_verification import verify_local_product_example
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.registry.loader import load_policy, require_listed
from readme_agent.repository_snapshot import capture_repository_snapshot

# Every exception verify_local_product_example()'s own call chain can raise
# for a reason that is NOT this script's bug: an unlisted repo, a malformed
# policy file, a clone/snapshot failure, or (until RPOC-035 registers the
# other four ecosystems' verifiers) `ValueError("no local example verifier
# registered for ...")`. Each is a reportable, expected outcome for this
# pipeline -- never a crash -- mirroring java_toolchain.py's own "this
# function never crashes" convention.
_EXPECTED_FAILURE_TYPES = (
    ConfigError,
    NotAllowlistedError,
    GitSafetyError,
    RepositorySnapshotError,
    ValueError,
)


def _write_output(output: Path | None, payload: dict) -> None:
    if output is None:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--org-repo", required=True, help="'org/repo', must already be listed in data/products.json"
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="Optional path to write the JSON result"
    )
    args = parser.parse_args(argv)

    try:
        entry = require_listed(args.org_repo)
        if entry.policy_profile is None:
            raise ValueError(f"{args.org_repo} has no policy_profile configured")
        policy = load_policy(entry.policy_profile)
        if policy.product_truth is None:
            raise ValueError(
                f"{args.org_repo}'s policy ({entry.policy_profile}) has no "
                "product_truth.minimal_example configured -- nothing to compile/run"
            )

        baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
        print(f"Cloning {entry.clone_url} (fresh, disposable) -> {baseline_path}", file=sys.stderr)
        clone_baseline(entry, baseline_path)
        snapshot = capture_repository_snapshot(entry, baseline_path)

        example = policy.product_truth.minimal_example
        print(
            f"Verifying {args.org_repo}@{snapshot.source_revision} ({example.language}) ...",
            file=sys.stderr,
        )
        result = verify_local_product_example(snapshot, example)
    except _EXPECTED_FAILURE_TYPES as exc:
        # "BLOCKED_TOOLCHAIN" is one of LocalProductVerificationV1's own outcome
        # literals (facts/local_verification.py) -- reused here even though this
        # branch also covers pre-verification failures (unlisted repo, missing
        # policy, clone/snapshot failure) because every one of those is, from a
        # CI-reader's perspective, the same "could not establish a verified
        # build" signal, never a distinct third category worth inventing.
        payload = {
            "org_repo": args.org_repo,
            "outcome": "BLOCKED_TOOLCHAIN",
            "detail": str(exc),
        }
        _write_output(args.output, payload)
        print(json.dumps(payload, indent=2))
        print(f"BLOCKED: {args.org_repo}: {exc}", file=sys.stderr)
        return 1

    payload = result.model_dump(mode="json")
    _write_output(args.output, payload)
    print(json.dumps(payload, indent=2))

    if result.outcome != "SOURCE_BUILD_VERIFIED":
        print(f"FAILED: {args.org_repo}: {result.outcome} -- {result.detail}", file=sys.stderr)
        return 1

    print(f"OK: {args.org_repo}: {result.outcome}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
