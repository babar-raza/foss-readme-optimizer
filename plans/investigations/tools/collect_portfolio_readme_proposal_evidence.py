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
script that loses every already-completed repo's evidence to one later failure)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import traceback
from argparse import ArgumentParser
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent import paths  # noqa: E402
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
from readme_agent.verification.readme_proposal_bundle import (  # noqa: E402
    verify_cross_pilot_specificity,
    verify_readme_proposal_bundle,
)

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

    verdict = verify_readme_proposal_bundle(bundle)
    _json(bundle / "independent-review.json", verdict.model_dump(mode="json"))
    _refresh_checksums(bundle)

    return {
        "org_repo": org_repo,
        "slug": slug,
        "status": "ok",
        "verified": verdict.verified,
        "failures": verdict.failures,
        "identical_rerun_noop": identical_rerun_noop,
        "candidate": candidate,
    }


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--only", nargs="*", default=None, help="org_repo values to restrict to")
    args = parser.parse_args()
    evidence_dir = args.evidence_dir.resolve()
    evidence_dir.mkdir(parents=True, exist_ok=False)

    entries = [
        e for e in load_products() if e.mode != "disabled" and e.org_repo not in EXCLUDED_ORG_REPOS
    ]
    if args.only:
        entries = [e for e in entries if e.org_repo in set(args.only)]

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
        cross_pilot = verify_cross_pilot_specificity(candidates_for_cross_check).model_dump(
            mode="json"
        )
        _json(evidence_dir / "cross-portfolio-specificity.json", cross_pilot)

    summary = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "control_revision": _control_revision(),
        "task_id": "L8-LOCAL-README-PROPOSAL-PROOF",
        "scope": "full portfolio minus the 3 Java pilots (see EXCLUDED_ORG_REPOS)",
        "total_entries": len(entries),
        "ok_count": sum(1 for r in results if r["status"] == "ok"),
        "verified_count": sum(1 for r in results if r["status"] == "ok" and r["verified"]),
        "error_count": sum(1 for r in results if r["status"] == "error"),
        "cross_portfolio_specificity_verified": (
            cross_pilot["verified"] if cross_pilot is not None else None
        ),
        "results": results,
    }
    _json(evidence_dir / "portfolio-proof-manifest.json", summary)
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
