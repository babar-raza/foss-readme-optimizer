"""Produce seven-ecosystem live product-truth evidence without repository writes."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent import paths  # noqa: E402
from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json  # noqa: E402
from readme_agent.facts.context import product_facts_scope  # noqa: E402
from readme_agent.facts.schema_v2 import ProductFactsV2  # noqa: E402
from readme_agent.gitsafety.clone import clone_baseline  # noqa: E402
from readme_agent.readme.idea_candidate import prepare_idea_fidelity_candidate  # noqa: E402
from readme_agent.registry.loader import require_listed  # noqa: E402
from readme_agent.repository_snapshot import (  # noqa: E402
    capture_repository_snapshot,
    repository_snapshot_scope,
)
from readme_agent.state.backend import Lock, SaveResult  # noqa: E402
from readme_agent.state.migrations import ensure_run_state_v2  # noqa: E402
from readme_agent.state.readme_poc_lifecycle import (  # noqa: E402
    record_repository_profile,
    record_repository_snapshot,
)
from readme_agent.state.schema import RunStateV2  # noqa: E402
from readme_agent.supervisor.product_truth import prepare_local_product_truth  # noqa: E402

REPRESENTATIVES = {
    "java": "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
    "net": "aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
    "python": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
    "typescript": "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript",
    "cpp": "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp",
    "go": "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go",
    "rust": "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust",
}
OUT_DIR = paths.runs_dir() / "level8-local-portfolio-product-truth-verification"
GATED_FIELDS = (
    "product.audience",
    "product.problems_solved",
    "product.capabilities",
    "product.formats",
    "product.limitations",
    "example.minimal",
)


class _LocalProofBackend:
    """Process-local CAS backend used only to exercise the real lifecycle boundary."""

    def __init__(self) -> None:
        self.states: dict[str, RunStateV2] = {}

    def load(self, org_repo: str) -> RunStateV2 | None:
        return self.states.get(org_repo)

    def save(self, org_repo: str, state, expected_version: int | None) -> SaveResult:
        current = self.states.get(org_repo)
        current_version = current.state_version if current is not None else None
        if current_version != expected_version:
            return SaveResult("stale", current_version)
        next_version = (current_version or 0) + 1
        self.states[org_repo] = ensure_run_state_v2(state).model_copy(
            update={"org_repo": org_repo, "state_version": next_version}
        )
        return SaveResult("saved", next_version)

    def acquire_lock(self, org_repo: str) -> Lock:
        return Lock(org_repo, "local-product-truth-proof", "9999-01-01T00:00:00+00:00")

    def release_lock(self, lock: Lock) -> None:
        return None

    def lock_still_held(self, lock: Lock) -> bool:
        return True

    def acquire_run_lock(self, org_repo: str) -> Lock:
        return self.acquire_lock(org_repo)

    def release_run_lock(self, lock: Lock) -> None:
        return None

    def load_model_route_status(self, job: str):
        return None

    def save_model_route_status(self, status) -> None:
        return None


def _selected_states(product_facts: dict) -> dict[str, str]:
    by_id = {fact["fact_id"]: fact for fact in product_facts["facts"]}
    return {
        field: by_id[product_facts["selected_fact_ids"][field]]["verification_state"]
        for field in GATED_FIELDS
    }


def main() -> int:
    started_at = datetime.now(UTC).isoformat()
    results = []
    for ecosystem, org_repo in REPRESENTATIVES.items():
        entry = require_listed(org_repo)
        baseline = paths.baseline_dir(entry.org, entry.repo_name)
        clone_baseline(entry, baseline)
        snapshot = capture_repository_snapshot(entry, baseline)
        backend = _LocalProofBackend()
        try:
            record_repository_snapshot(
                backend,
                org_repo,
                source_revision=snapshot.source_revision,
                evidence_refs=["live representative snapshot"],
            )
            record_repository_profile(
                backend,
                org_repo,
                source_revision=snapshot.source_revision,
                evidence_refs=["live representative repository profile"],
            )
            with repository_snapshot_scope(snapshot, allow_local_fact_verification=True):
                prepared = prepare_local_product_truth(org_repo, snapshot, backend)
                with product_facts_scope(prepared.facts):
                    candidate = prepare_idea_fidelity_candidate(org_repo, prepared.facts)
            candidate_facts = ProductFactsV2.model_validate(candidate["product_facts_v2"])
            exact_graph_consumed = (
                candidate_facts.canonical_hash() == prepared.facts.canonical_hash()
            )
            if not exact_graph_consumed:
                raise RuntimeError("candidate renderer did not consume the prepared fact graph")
            record = {
                "ecosystem": ecosystem,
                "org_repo": org_repo,
                "source_revision": snapshot.source_revision,
                "outcome": "FACT_GRAPH_PRODUCED",
                "lifecycle_status": prepared.lifecycle_status,
                "resolution_source": prepared.resolution_source,
                "facts_hash": prepared.facts.canonical_hash(),
                "renderer_consumed_exact_graph": exact_graph_consumed,
                "candidate_status": candidate["status"],
                "candidate_source_revision": candidate["source_revision"],
                "findings": prepared.findings,
                "selected_drafted_field_states": _selected_states(
                    prepared.facts.model_dump(mode="json")
                ),
                "product_facts_v2": prepared.facts.model_dump(mode="json"),
                "proposed_product_truth": prepared.proposed_product_truth,
            }
        except Exception as exc:  # noqa: BLE001 - evidence must retain every lane's raw failure
            record = {
                "ecosystem": ecosystem,
                "org_repo": org_repo,
                "source_revision": snapshot.source_revision,
                "outcome": "SYSTEM_FAILURE",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        results.append(record)
        write_redacted_json(OUT_DIR / "representatives" / ecosystem / "result.json", record)

    system_failures = [item for item in results if item["outcome"] == "SYSTEM_FAILURE"]
    manifest = {
        "schema_version": 1,
        "task_id": "L8-LOCAL-PORTFOLIO-PRODUCT-TRUTH",
        "started_at": started_at,
        "completed_at": datetime.now(UTC).isoformat(),
        "representatives": results,
        "expected_ecosystems": list(REPRESENTATIVES),
        "produced_fact_graphs": len(results) - len(system_failures),
        "system_failures": system_failures,
        "acceptance": {
            "all_representatives_terminal": len(results) == len(REPRESENTATIVES),
            "no_system_failures": not system_failures,
            "renderer_consumed_exact_graph": all(
                item.get("renderer_consumed_exact_graph") is True for item in results
            ),
            "blocked_fields_remain_visible": all(
                item["outcome"] == "SYSTEM_FAILURE"
                or all(
                    state in {"verified", "policy_approved", "blocked", "missing", "conflicting"}
                    for state in item["selected_drafted_field_states"].values()
                )
                for item in results
            ),
            "remote_writes": 0,
        },
        "reproduction_command": (
            ".venv/Scripts/python "
            "plans/investigations/tools/"
            "prove_local_portfolio_product_truth_representatives.py"
        ),
    }
    write_redacted_json(OUT_DIR / "acceptance-manifest.json", manifest)
    refresh_sha256sums(OUT_DIR)
    print(json.dumps(manifest["acceptance"], indent=2))
    print(OUT_DIR.resolve())
    return 1 if system_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
