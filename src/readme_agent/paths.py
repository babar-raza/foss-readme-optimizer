"""Resolution of the disposable, git-ignored runtime directory.

Deliberately cwd-relative (not repo-root-walking) so local dev (run from the
repo root) and a GitHub Actions runner (checkout puts cwd at repo root)
resolve identically with zero path-detection magic.
"""

import hashlib
import os
from pathlib import Path


def runs_dir() -> Path:
    override = os.environ.get("README_AGENT_RUNS_DIR")
    base = Path(override) if override else Path.cwd() / "runs"
    return base


def baseline_dir(org: str, repo: str) -> Path:
    return runs_dir() / "baseline" / f"{org}__{repo}"


def work_dir(org: str, repo: str) -> Path:
    """Deliberately stable across invocations, unlike baseline (always fresh)
    and evidence (always run_id-scoped): since this tool never pushes, the
    *only* place idempotency (a second run finding its own prior marker span
    and skipping the LLM) can live is a persistent local work clone. A fresh
    work clone every run would make "run twice, zero new diff" fictional."""
    return runs_dir() / "work" / f"{org}__{repo}"


def pr_work_dir(org: str, repo: str) -> Path:
    """TC-08/`PRL-007`: structurally separate from `work_dir()` -- the one
    clone location `open_presentation_pr` may use, deliberately never
    neutered (`gitsafety.clone.create_pr_clone()`, the opposite of
    `create_work_clone()`'s own `neuter_push()` call). No other capability
    may read or write here, and this function's result may never be passed
    to any capability that assumes `verify_push_blocked()` would pass."""
    return runs_dir() / "pr_work" / f"{org}__{repo}"


def evidence_dir(run_id: str) -> Path:
    return runs_dir() / "evidence" / run_id


def readme_proposal_bundle_dir(org: str, repo: str, run_id: str) -> Path:
    """RPOC-050/051: one materialized 8-file README-proposal evidence bundle
    (`verification/readme_proposal_bundle.py::_REQUIRED_ARTIFACTS`) per repo
    per run -- `run_id`-scoped like `evidence_dir()` (a fresh bundle every
    run, never overwritten in place), but under its own top-level category so
    it is never mistaken for -- or accidentally swept up by tooling that
    walks -- the general supervise-run evidence tree."""
    return runs_dir() / "readme-proposal-bundles" / f"{org}__{repo}" / run_id


def readme_poc_root() -> Path:
    """Stable root for the derived, full-registry local README-POC report."""
    return runs_dir() / "readme-poc"


def readme_poc_repository_dir(org: str, repo: str, source_revision: str) -> Path:
    """Revision-addressed local-POC artifact root for one immutable snapshot."""
    if not source_revision or any(char not in "0123456789abcdef" for char in source_revision):
        raise ValueError("source_revision must be a lowercase hexadecimal Git revision")
    return readme_poc_root() / f"{org}__{repo}" / source_revision


def readme_poc_campaign_repository_dir(
    campaign_id: str,
    org: str,
    repo: str,
    source_revision: str,
) -> Path:
    """Compact immutable receipt root for one repository campaign identity.

    Full identities remain in validated request/receipt documents.  The path uses
    compact aliases whose combined identity is collision-checked from request bytes,
    so Windows workspaces and pytest temp roots stay below the legacy path boundary.
    """

    if not campaign_id or any(char not in "0123456789abcdef" for char in campaign_id):
        raise ValueError("campaign_id must be lowercase hexadecimal")
    if not source_revision or any(char not in "0123456789abcdef" for char in source_revision):
        raise ValueError("source_revision must be lowercase hexadecimal")
    repository_alias = hashlib.sha256(f"{org}/{repo}".encode()).hexdigest()[:16]
    return (
        readme_poc_root()
        / "c"
        / campaign_id[:20]
        / "r"
        / repository_alias
        / "s"
        / source_revision[:12]
    )


def readme_poc_campaign_work_dir(
    campaign_id: str,
    org: str,
    repo: str,
    source_revision: str,
    work_id: str,
) -> Path:
    """Private attempt parent; lanes never write the compatibility view."""

    if not work_id or any(char not in "0123456789abcdef" for char in work_id):
        raise ValueError("work_id must be lowercase hexadecimal")
    return (
        readme_poc_campaign_repository_dir(campaign_id, org, repo, source_revision)
        / "w"
        / work_id[:20]
    )


def readme_poc_portfolio_summary_path() -> Path:
    """Canonical current summary, atomically replaced after each local POC pass."""
    return readme_poc_root() / "portfolio-summary.json"


def registry_heal_marker_path() -> Path:
    """TTL marker for the supervise-time registry self-heal (CORE-034): a
    sequential multi-repo pass reads this to scan GitHub once per interval,
    not once per repo."""
    return runs_dir() / "registry-heal" / "last_heal.json"


def toolchains_dir() -> Path:
    """RPOC-041: cache root for auto-provisioned build JDKs (Eclipse
    Temurin), one `temurin-<version>/` subdirectory per extracted release --
    see `facts/java_toolchain.py`. Deliberately persistent across runs
    (unlike `baseline_dir()`): a ~200MB JDK download is exactly the kind of
    cost this cache exists to avoid paying twice."""
    return runs_dir() / "toolchains"
