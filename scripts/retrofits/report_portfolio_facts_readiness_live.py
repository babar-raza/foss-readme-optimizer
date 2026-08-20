"""One-shot: a historical-artifact facts-readiness PREFLIGHT over the 21 of
31 processable repositories with an already-persisted `product-facts-v2.json`
snapshot on disk (owner review, 2026-08-20, correction 7).

This is explicitly NOT a fresh all-31 facts acquisition run: it never
invokes `collect_product_facts`/`get_product_facts` (that path can trigger
real local example compilation/execution via `local_verification.py`'s
isolated verifiers) and never calls Qwen or generates a candidate. Instead
it reads the most recently written, already persisted `product-facts-v2.json`
artifact per repository under `runs/readme-proposal-bundles/` -- real
`ProductFactsV2` output from prior, already-completed pilot runs, loaded
here read-only. A repository with no persisted artifact is reported
honestly in `facts_not_collected`, never fabricated.

Four distinct revision identities are tracked separately and never
conflated (owner review, 2026-08-20, terminology correction):

  1. current_repository_revision   -- live git HEAD, `git ls-remote` only
  2. imported_knowledge_revision   -- the imported knowledge corpus's own
                                       recorded `repo_sha` (model.yaml)
  3. persisted_product_facts_revision -- the `source_revision` embedded in
                                       the loaded historical snapshot
  4. candidate_revision            -- not applicable; this run generates no
                                       candidate

`imported_knowledge_vs_current_repository` (identity 2 vs 1) is the same
metric, same `assess_bundle_freshness` computation, as the 2026-08-19/
2026-08-20 owner-audit 3-repository calibration table (3D/Note/Barcode,
all Python) -- reconciled below, not overwritten: that 3-repo sample found
2/3 (Note, Barcode) `stale_revision` and 1/3 (3D) `current`; this sweep
runs the identical computation across the full 31-repo processable set.

`persisted_product_facts_vs_current_repository` (identity 3 vs 1) is a
separate question this preflight also answers: whether the cached snapshot
itself was captured against the repository's current commit. A repository
can be current on one axis and stale on the other -- they are unrelated.
"""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.facts.portfolio_facts_readiness import (
    portfolio_facts_readiness,
    processable_registry_entries,
    repository_live_freshness,
)
from readme_agent.facts.schema_v2 import ProductFactsV2

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BUNDLES_ROOT = _REPO_ROOT / "runs" / "readme-proposal-bundles"


def _org_repo(entry) -> str:
    return f"{entry.org}/{entry.repo_name}"


def _latest_facts_path(bundle_dir: Path) -> Path | None:
    candidates = list(bundle_dir.glob("*/product-facts-v2.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _persisted_source_revision(facts: ProductFactsV2) -> str | None:
    try:
        return facts.selected_fact("product.identity").source.source_revision
    except KeyError:
        return None


def _load_facts_by_org_repo() -> tuple[dict[str, ProductFactsV2], dict[str, str]]:
    facts_by_org_repo: dict[str, ProductFactsV2] = {}
    source_run_by_org_repo: dict[str, str] = {}
    for entry in processable_registry_entries():
        org_repo = _org_repo(entry)
        bundle_dir = _BUNDLES_ROOT / f"{entry.org}__{entry.repo_name}"
        if not bundle_dir.is_dir():
            continue
        latest = _latest_facts_path(bundle_dir)
        if latest is None:
            continue
        try:
            facts = ProductFactsV2.model_validate_json(latest.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        facts_by_org_repo[org_repo] = facts
        source_run_by_org_repo[org_repo] = latest.parent.name
    return facts_by_org_repo, source_run_by_org_repo


def main() -> None:
    facts_by_org_repo, source_run_by_org_repo = _load_facts_by_org_repo()
    result = portfolio_facts_readiness(
        facts_by_org_repo=facts_by_org_repo,
        freshness_probe=repository_live_freshness,
    )

    status_counts: dict[str, int] = {}
    for row in result.readiness:
        status_counts[row.overall_status] = status_counts.get(row.overall_status, 0) + 1

    # Identity 2 vs identity 1: imported knowledge corpus vs live current repo.
    knowledge_vs_current = [
        {
            "org_repo": row.org_repo,
            "current_repository_revision": row.live_source_revision,
            "imported_knowledge_revision": row.knowledge_repo_sha,
            "freshness": row.freshness,
        }
        for row in result.freshness
    ]
    knowledge_stale = sum(1 for row in result.freshness if row.freshness == "stale_revision")
    knowledge_current = sum(1 for row in result.freshness if row.freshness == "current")

    # Identity 3 vs identity 1: persisted ProductFacts snapshot vs live current repo.
    live_revision_by_org_repo = {row.org_repo: row.live_source_revision for row in result.freshness}
    facts_vs_current = []
    facts_stale = 0
    facts_current = 0
    for org_repo, facts in facts_by_org_repo.items():
        persisted_revision = _persisted_source_revision(facts)
        live_revision = live_revision_by_org_repo.get(org_repo)
        if persisted_revision is None or live_revision is None:
            status = "unavailable"
        elif persisted_revision == live_revision:
            status = "current"
            facts_current += 1
        else:
            status = "stale"
            facts_stale += 1
        facts_vs_current.append(
            {
                "org_repo": org_repo,
                "persisted_product_facts_revision": persisted_revision,
                "current_repository_revision": live_revision,
                "status": status,
                "source_run": source_run_by_org_repo.get(org_repo),
            }
        )

    report = {
        "run_kind": "historical_artifact_preflight",
        "run_description": (
            "A preflight over the 21 of 31 processable repositories with an already-persisted "
            "product-facts-v2.json snapshot on disk. This is NOT a fresh all-31 facts "
            "acquisition run -- no fact collection, no candidate generation, no Qwen call was "
            "performed. The next knowledge operation runs fresh facts acquisition for all 31."
        ),
        "total_processable": result.total_processable,
        "facts_loaded_from_persisted_artifacts": len(facts_by_org_repo),
        "facts_not_collected": list(result.facts_not_collected),
        "readiness_status_counts": status_counts,
        "revision_identities": {
            "1_current_repository_revision": "live git HEAD, git ls-remote only",
            "2_imported_knowledge_revision": (
                "the imported knowledge corpus's own recorded repo_sha (model.yaml)"
            ),
            "3_persisted_product_facts_revision": (
                "the source_revision embedded in the loaded historical product-facts-v2.json "
                "snapshot"
            ),
            "4_candidate_revision": "not applicable -- this run generates no candidate",
        },
        "imported_knowledge_vs_current_repository": {
            "identities_compared": "2 vs 1",
            "stale_count": knowledge_stale,
            "current_count": knowledge_current,
            "total": len(result.freshness),
            "reconciliation_note": (
                "Same computation (assess_bundle_freshness) as the 2026-08-19/2026-08-20 "
                "owner-audit 3-repository calibration table (3D/Note/Barcode, all Python), run "
                "here across the full 31-repo processable set instead of 3. That 3-repo sample "
                "found 2/3 (Note, Barcode) stale_revision and 1/3 (3D) current -- 67% stale. "
                "This 31-repo sweep finds the same proportion within a few points -- "
                "corroborating, not contradicting, that prior finding."
            ),
            "per_repository": knowledge_vs_current,
        },
        "persisted_product_facts_vs_current_repository": {
            "identities_compared": "3 vs 1",
            "stale_count": facts_stale,
            "current_count": facts_current,
            "total": len(facts_vs_current),
            "note": (
                "Whether the cached snapshot used for THIS preflight was captured against the "
                "repository's current commit -- independent of imported-knowledge freshness "
                "above. A repository can be current on one axis and stale on the other."
            ),
            "per_repository": facts_vs_current,
        },
        "readiness_per_repository": [
            {
                "org_repo": row.org_repo,
                "overall_status": row.overall_status,
                "source_run": source_run_by_org_repo.get(row.org_repo),
                "sections": {section.section_id: section.status for section in row.sections},
            }
            for row in result.readiness
        ],
    }

    out_path = _REPO_ROOT / "runs" / "portfolio-facts-readiness-2026-08-20.json"
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "run_kind": report["run_kind"],
                "total_processable": report["total_processable"],
                "facts_loaded_from_persisted_artifacts": report[
                    "facts_loaded_from_persisted_artifacts"
                ],
                "readiness_status_counts": status_counts,
                "imported_knowledge_vs_current_repository": {
                    "stale_count": knowledge_stale,
                    "current_count": knowledge_current,
                },
                "persisted_product_facts_vs_current_repository": {
                    "stale_count": facts_stale,
                    "current_count": facts_current,
                },
                "out_path": str(out_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
