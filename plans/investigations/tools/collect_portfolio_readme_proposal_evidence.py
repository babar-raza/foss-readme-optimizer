# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: full-portfolio (non-Java-pilot) local README proposal evidence producer
"""Generalizes collect_local_readme_proposal_evidence.py's 3-Java-pilot pipeline to every
other registered products.json entry -- Level-5/idea.md's "no repo left untouched" scope:
every entry gets a real local proposal + independent verification; only the two Java
`full`-mode entries ever attempt a live PR, and that stays entirely out of this tool's
scope (open_presentation_pr is a separately authorized, separately gated effect).

Unlike the 3-pilot tool, facts are collected FRESH per repo here (no pre-existing immutable-
snapshot proof to read from) -- same clone -> snapshot -> collect_product_facts() sequence
`collect_local_immutable_snapshot_and_product_facts_evidence.py::_pilot_proof()` already
uses, feeding the same deterministic candidate-rendering + independent-verification pipeline
`collect_local_readme_proposal_evidence.py::_pilot_bundle()` already uses. Reuses both
patterns rather than inventing a third (GOVERNANCE.md rule 8).

Per-repo failures are recorded, never let one repo's clone/build/verify problem abort the
whole portfolio run (GOV-003/017 spirit: a partial, honest result beats an all-or-nothing
script that loses every already-completed repo's evidence to one later failure).

RPOC-071 (sprint charter Part B.2 Phase 5 Lane S / Part C.7) extends the manifest this tool
writes with charter-required portfolio aggregate fields -- status/ecosystem/missing-
capability distributions and `ReadmePocStatusV1`-aware counts, layered additively onto the
pre-existing `results[]` shape, never replacing it (see `compute_portfolio_summary_
aggregates()`) -- plus a `--reaggregate-only` mode that recomputes those fields against an
already-collected evidence dir's `portfolio-proof-manifest.json` without repeating the
expensive per-repo clone/build/verify pass."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import traceback
from argparse import ArgumentParser
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent import paths  # noqa: E402
from readme_agent.capabilities.dispatcher import dispatch_tool_call  # noqa: E402
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION  # noqa: E402
from readme_agent.facts.provider import collect_product_facts  # noqa: E402
from readme_agent.facts.schema_v2 import ProductFactsV2  # noqa: E402
from readme_agent.gitsafety.clone import clone_baseline  # noqa: E402
from readme_agent.presentation.document_planner import (  # noqa: E402
    build_document_repository_presentation_plan,
)
from readme_agent.readme.document_renderer import (  # noqa: E402
    build_readme_document_candidate,
)
from readme_agent.registry.loader import find_entry, load_policy, load_products  # noqa: E402
from readme_agent.repository_snapshot import (  # noqa: E402
    capture_repository_snapshot,
    repository_snapshot_scope,
)
from readme_agent.state.lifecycle_schema import ReadmePocStatusV1  # noqa: E402

# RPOC-052: this tool no longer imports `verification.readme_proposal_bundle`'s two
# `verify_*` functions directly -- both are now real, registered capabilities
# (`capabilities/verify_readme_proposal_bundle.py`/`capabilities/verify_cross_pilot_
# specificity.py`), dispatched below via `dispatch_tool_call()` exactly like every other
# capability in this project, closing `check_verifiers_are_wired.py`'s own finding that
# these two functions were reachable only from a test or a standalone script like this one.
_VERIFIER_PERMISSIONS = {"read_only_local", "read_only_network"}


def _dispatch_verify_readme_proposal_bundle(bundle_dir: Path) -> dict:
    dispatch = dispatch_tool_call(
        {
            "function": {
                "name": "verify_readme_proposal_bundle",
                "arguments": json.dumps({"bundle_dir": str(bundle_dir)}),
            }
        },
        _VERIFIER_PERMISSIONS,
        # verify_readme_proposal_bundle is domain-scoped to INDEPENDENT_VERIFICATION
        # (capabilities/domains.py) -- this tool acts as that domain's caller here, the
        # same authority the in-graph review node (specialists/readme_presentation.py)
        # exercises for a single repo, generalized to this tool's own portfolio batch.
        caller_domain=INDEPENDENT_VERIFICATION,
    )
    if dispatch.outcome != "executed" or dispatch.result is None:
        raise RuntimeError(f"verify_readme_proposal_bundle:{dispatch.outcome}:{dispatch.error}")
    return dispatch.result


def _dispatch_verify_cross_pilot_specificity(pilots: list[tuple[str, str]]) -> dict:
    arguments = {"pilots": [[org_repo, text] for org_repo, text in pilots]}
    dispatch = dispatch_tool_call(
        {
            "function": {
                "name": "verify_cross_pilot_specificity",
                "arguments": json.dumps(arguments),
            }
        },
        _VERIFIER_PERMISSIONS,
    )
    if dispatch.outcome != "executed" or dispatch.result is None:
        raise RuntimeError(f"verify_cross_pilot_specificity:{dispatch.outcome}:{dispatch.error}")
    return dispatch.result


# The 3 Java pilots already have dedicated, checksum-complete evidence
# (collect_local_readme_proposal_evidence.py) -- excluded here to avoid duplicate work,
# not because they're out of this program's scope.
EXCLUDED_ORG_REPOS = {
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
    "aspose-3d-foss/Aspose.3D-FOSS-for-Java",
    "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java",
}

DEFAULT_EVIDENCE_DIR = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-portfolio-readme-proposals-2026-07-25"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def _json(path: Path, value: object) -> None:
    _write(path, json.dumps(value, indent=2) + "\n")


def _slug(org_repo: str) -> str:
    return org_repo.split("/", 1)[1].lower().replace(".", "-").replace("_", "-")


def _control_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _refresh_checksums(bundle: Path) -> None:
    _json(
        bundle / "artifact-sha256.json",
        {
            path.name: _sha256(path)
            for path in sorted(bundle.iterdir())
            if path.is_file() and path.name != "artifact-sha256.json"
        },
    )


def _repo_bundle(output: Path, org_repo: str) -> dict:
    slug = _slug(org_repo)
    bundle = output / slug
    bundle.mkdir()

    entry = find_entry(org_repo)
    if entry is None or entry.policy_profile is None:
        raise RuntimeError(f"{org_repo}: policy profile is unavailable")

    baseline = clone_baseline(entry, paths.baseline_dir(entry.org, entry.repo_name))
    snapshot = capture_repository_snapshot(entry, baseline)
    readme_source = (
        (snapshot.root_path / snapshot.readme_path).read_text(encoding="utf-8", errors="replace")
        if snapshot.readme_path is not None
        else ""
    )

    with repository_snapshot_scope(snapshot, allow_local_fact_verification=True):
        facts_result = collect_product_facts(org_repo)

    facts = ProductFactsV2.model_validate(facts_result["product_facts_v2"])
    candidate, document_plan = build_readme_document_candidate(
        org_repo, readme_source, facts, base_revision=snapshot.source_revision
    )
    ownership = load_policy(entry.policy_profile).surface_ownership
    repository_plan, patch, _executable, records = build_document_repository_presentation_plan(
        org_repo,
        readme_source,
        readme_source,
        candidate,
        facts,
        ownership,
        base_revision=snapshot.source_revision,
    )
    rerendered, rerun_plan = build_readme_document_candidate(
        org_repo, candidate, facts, base_revision=snapshot.source_revision
    )
    identical_rerun_noop = rerendered == candidate and not rerun_plan.operations

    _write(bundle / "original-readme.md", readme_source)
    _write(bundle / "candidate-readme.md", candidate)
    _write(bundle / "proposal.patch", patch["patch"])
    _json(bundle / "product-facts-v2.json", facts.model_dump(mode="json"))
    _json(bundle / "readme-document-plan-v1.json", document_plan.model_dump(mode="json"))
    _json(
        bundle / "repository-presentation-plan-v1.json",
        repository_plan.model_dump(mode="json"),
    )
    _json(bundle / "document-validation.json", records["document_validation"])
    _refresh_checksums(bundle)

    verdict = _dispatch_verify_readme_proposal_bundle(bundle)
    _json(bundle / "independent-review.json", verdict)
    _refresh_checksums(bundle)

    return {
        "org_repo": org_repo,
        "slug": slug,
        "status": "ok",
        "verified": verdict["verified"],
        "failures": verdict["failures"],
        "identical_rerun_noop": identical_rerun_noop,
        "candidate": candidate,
    }


def _collect_results(evidence_dir: Path, only: list[str] | None) -> tuple[list[dict], dict | None]:
    """Runs the real per-repo clone/build/verify pass for every eligible
    `data/products.json` entry (minus the 3 already-covered Java pilots and
    any `disabled` entry), returning the raw `results[]` list plus the
    cross-portfolio-specificity verdict (`None` if fewer than 2 candidates
    were produced to compare). Split out of `main()` so `--reaggregate-only`
    can skip this expensive part entirely while reusing everything else."""
    entries = [
        e for e in load_products() if e.mode != "disabled" and e.org_repo not in EXCLUDED_ORG_REPOS
    ]
    if only:
        entries = [e for e in entries if e.org_repo in set(only)]

    results: list[dict] = []
    candidates_for_cross_check: list[tuple[str, str]] = []
    for entry in entries:
        print(f"=== {entry.org_repo} ===", flush=True)
        try:
            result = _repo_bundle(evidence_dir, entry.org_repo)
            print(f"  verified={result['verified']} failures={result['failures']}", flush=True)
            candidates_for_cross_check.append((result["org_repo"], result["candidate"]))
            del result["candidate"]  # not JSON-summary-worthy; the bundle itself has it
            results.append(result)
        except Exception as exc:  # noqa: BLE001 -- one repo's failure must not lose the rest
            print(f"  ERROR: {exc}", flush=True)
            results.append(
                {
                    "org_repo": entry.org_repo,
                    "slug": _slug(entry.org_repo),
                    "status": "error",
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )

    cross_pilot = None
    if len(candidates_for_cross_check) >= 2:
        cross_pilot = _dispatch_verify_cross_pilot_specificity(candidates_for_cross_check)
        _json(evidence_dir / "cross-portfolio-specificity.json", cross_pilot)
    return results, cross_pilot


def _enrich_results_with_registry_metadata(results: list[dict]) -> None:
    """Backfills registry-derived `ecosystem` (an existing `data/products.json`
    field, RPOC-071) and normalizes `readme_poc_status` to an explicit key
    (defaulting to `None`) on every result dict, in place -- so both a freshly
    collected run and a `--reaggregate-only` reload of an older manifest that
    predates both fields end up with the same shape before `compute_portfolio_
    summary_aggregates()` sees them. Keeping the registry lookup here (not
    inside `compute_portfolio_summary_aggregates()`) is what keeps that
    function pure/I-O-free and directly testable against synthetic fixtures
    that don't correspond to any real registry entry."""
    for result in results:
        if "ecosystem" not in result:
            entry = find_entry(result["org_repo"])
            result["ecosystem"] = entry.ecosystem if entry is not None else None
        result.setdefault("readme_poc_status", None)


# Cheap, derived-not-collected missing-capability signal (RPOC-071): parses the
# verification-failure strings `verify_readme_proposal_bundle()` already produces for the
# recurring "<field>:<value> is missing/blocked" shape citation/acquisition checks emit,
# plus two fixed-text gaps that don't carry a field name. No new data collection -- every
# string matched here already lives in each repo's own `failures` list.
_MISSING_OR_BLOCKED_FIELD_RE = re.compile(r"([A-Za-z][\w.]*):[\w-]+ is (missing|blocked)")
_UNACCEPTED_FACT_MARKER = "cites an unaccepted fact"
_MISSING_MINIMAL_EXAMPLE_MARKER = "selected verified minimal example is absent"


def _missing_capability_tags(failures: list[str]) -> set[str]:
    """One repo's distinct set of missing-capability tags found in its
    `failures` strings -- deduplicated per repo so `missing_capability_
    distribution` counts *how many repos* hit a given gap, not how many times
    the same gap's text happened to repeat within one repo's failure list."""
    text = " ".join(failures)
    tags = {f"{field}:{state}" for field, state in _MISSING_OR_BLOCKED_FIELD_RE.findall(text)}
    if _UNACCEPTED_FACT_MARKER in text:
        tags.add("operation:unaccepted_fact_citation")
    if _MISSING_MINIMAL_EXAMPLE_MARKER in text:
        tags.add("installation:verified_minimal_example_absent")
    return tags


def compute_portfolio_summary_aggregates(results: list[dict], total_repositories: int) -> dict:
    """RPOC-071 (sprint charter Part B.2 Phase 5 Lane S / Part C.7):
    charter-required aggregate fields layered additively onto the existing
    portfolio-proof-manifest shape -- never replaces `results[]`, matching
    RPOC-070's own additive-field convention on `RunManifestV3` (`readme_poc_
    status`/`readme_poc_transitions` added beside every pre-existing field,
    nothing removed or renamed).

    Pure function over already-collected per-repo result dicts -- no I/O --
    so it is directly unit-testable with synthetic fixtures and reusable
    against any results source (this tool's own run, a `--reaggregate-only`
    reload, or eventually a real production manifest sweep once `readme_poc_
    status` is actually driven by `state/readme_poc_lifecycle.py::
    transition_readme_poc_status()`).

    `readme_poc_status` is read per-result, default `None` -- every repo this
    tool processes today runs through the standalone local-evidence pipeline,
    not the CAS-backed state machine that drives real lifecycle transitions,
    so `None`/missing across the whole current portfolio is the correct,
    expected value until a later taskcard wires production transitions --
    never faked as an already-tracked status. Handled gracefully here (folded
    into `status_distribution["not_set"]`), never a crash.

    The individual counts (`candidates_generated_count`, `reviewer_accepted_
    count`, ...) are diagnostic categories, not a partition -- e.g. a repo
    counted in `blocked_facts_count` is also counted in `reviewer_rejected_
    count`, since a fact gap is one reason a candidate gets rejected, not a
    separate, mutually-exclusive outcome."""
    processed_count = len(results)
    candidates_generated_count = sum(1 for r in results if r.get("status") == "ok")
    reviewer_accepted_count = sum(
        1 for r in results if r.get("status") == "ok" and r.get("verified") is True
    )
    reviewer_rejected_count = sum(
        1 for r in results if r.get("status") == "ok" and r.get("verified") is False
    )
    blocked_facts_count = sum(
        1
        for r in results
        if r.get("status") == "ok" and any("is missing" in f for f in r.get("failures") or [])
    )
    system_failures_count = sum(1 for r in results if r.get("status") == "error")
    no_op_rerun_count = sum(1 for r in results if r.get("identical_rerun_noop") is True)

    status_distribution: dict[str, int] = {status: 0 for status in get_args(ReadmePocStatusV1)}
    status_distribution["not_set"] = 0
    for r in results:
        status = r.get("readme_poc_status")
        if status in status_distribution:
            status_distribution[status] += 1
        else:
            status_distribution["not_set"] += 1

    ecosystem_distribution: dict[str, int] = {}
    for r in results:
        ecosystem = r.get("ecosystem") or "unknown"
        ecosystem_distribution[ecosystem] = ecosystem_distribution.get(ecosystem, 0) + 1

    missing_capability_distribution: dict[str, int] = {}
    for r in results:
        for tag in _missing_capability_tags(r.get("failures") or []):
            missing_capability_distribution[tag] = missing_capability_distribution.get(tag, 0) + 1

    return {
        "total_repositories": total_repositories,
        "processed_count": processed_count,
        "candidates_generated_count": candidates_generated_count,
        "reviewer_accepted_count": reviewer_accepted_count,
        "reviewer_rejected_count": reviewer_rejected_count,
        "blocked_facts_count": blocked_facts_count,
        "system_failures_count": system_failures_count,
        "no_op_rerun_count": no_op_rerun_count,
        "status_distribution": status_distribution,
        "ecosystem_distribution": ecosystem_distribution,
        "missing_capability_distribution": missing_capability_distribution,
    }


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--only", nargs="*", default=None, help="org_repo values to restrict to")
    parser.add_argument(
        "--reaggregate-only",
        action="store_true",
        help=(
            "Skip cloning/building/verifying; reload results[] from an existing "
            "--evidence-dir's portfolio-proof-manifest.json and only recompute the "
            "RPOC-071 summary aggregate fields against that already-collected data "
            "(e.g. to prove/refresh the aggregation logic without repeating an "
            "expensive full portfolio collection)."
        ),
    )
    args = parser.parse_args()
    evidence_dir = args.evidence_dir.resolve()
    manifest_path = evidence_dir / "portfolio-proof-manifest.json"

    if args.reaggregate_only:
        summary = json.loads(manifest_path.read_text(encoding="utf-8"))
        results: list[dict] = summary["results"]
    else:
        evidence_dir.mkdir(parents=True, exist_ok=False)
        results, cross_pilot = _collect_results(evidence_dir, args.only)
        summary = {
            "schema_version": 1,
            "generated_at": datetime.now(UTC).isoformat(),
            "control_revision": _control_revision(),
            "task_id": "L8-LOCAL-README-PROPOSAL-PROOF",
            "scope": "full portfolio minus the 3 Java pilots (see EXCLUDED_ORG_REPOS)",
            "total_entries": len(results),
            "ok_count": sum(1 for r in results if r["status"] == "ok"),
            "verified_count": sum(1 for r in results if r["status"] == "ok" and r["verified"]),
            "error_count": sum(1 for r in results if r["status"] == "error"),
            "cross_portfolio_specificity_verified": (
                cross_pilot["verified"] if cross_pilot is not None else None
            ),
        }

    _enrich_results_with_registry_metadata(results)
    aggregates = compute_portfolio_summary_aggregates(
        results, total_repositories=len(load_products())
    )
    summary.update(aggregates)
    summary["results"] = results
    _json(manifest_path, summary)
    try:
        evidence_dir_display = str(evidence_dir.relative_to(REPO_ROOT))
    except ValueError:
        evidence_dir_display = str(evidence_dir)
    _write(
        evidence_dir / "reproduction-command.txt",
        ".venv/Scripts/python "
        "plans/investigations/tools/collect_portfolio_readme_proposal_evidence.py "
        f"--evidence-dir {evidence_dir_display}\n",
    )
    lines = [
        f"{_sha256(path)}  {path.name}"
        for path in sorted(evidence_dir.rglob("*"))
        if path.is_file() and path.name != "sha256sums.txt"
    ]
    _write(evidence_dir / "sha256sums.txt", "\n".join(lines) + "\n")

    print(
        f"\n{summary['ok_count']}/{summary['total_entries']} produced a bundle, "
        f"{summary['verified_count']} independently verified, "
        f"{summary['error_count']} errored.",
        flush=True,
    )
    return 0 if summary["error_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
