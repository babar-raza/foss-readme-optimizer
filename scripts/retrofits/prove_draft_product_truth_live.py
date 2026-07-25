"""RPOC-033 live dry-run proof: the taskcard's own single most important
verification -- a real, unmocked run of `capabilities/draft_product_truth.py::
execute()` (which itself calls the real, live-characterized
`facts/agentic_drafting.py::draft_product_truth()`, routed to `qwen3-next`
via `env.py::JOB_MODEL_ROUTING["draft_product_truth"]`) against a real
registry repository that ALREADY has a real, hand-authored `product_truth` in
its policy YAML (`config/policies/aspose-cells-foss.yml`) -- used here as a
plausibility anchor, never as ground truth this draft is forced to match.

Runs the SAME real, imported (never reimplemented) production entry point
`capabilities/draft_product_truth.py::execute()`, under a real
`repository_snapshot_scope(..., allow_local_fact_verification=True)` -- the
exact condition the `local_dry_run` execution profile sets -- so
`example.minimal` is really compiled against a real disposable Maven build,
never skipped.

Reports: whether the drafted output passed its own mechanical/groundedness/
local-verification gates, and a qualitative side-by-side against the real
hand-authored `product_truth` (same product, recognizably describing the
same real capabilities/audience, not wildly divergent).

Writes nothing to `config/policies/*.yml` -- `execute()` itself has no write
path (see its own docstring). This script only reads and reports.

Kept after use as the executable record of this verification -- see
plans/GOVERNANCE.md, "Repository layout", placement rule 5.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


from readme_agent import paths  # noqa: E402
from readme_agent.capabilities import draft_product_truth  # noqa: E402
from readme_agent.gitsafety.clone import clone_baseline  # noqa: E402
from readme_agent.registry.loader import load_policy, require_listed  # noqa: E402
from readme_agent.repository_snapshot import (  # noqa: E402
    capture_repository_snapshot,
    repository_snapshot_scope,
)

ORG_REPO = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"

OUT_DIR = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "draft-product-truth-live-proof-2026-07-25"
)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Repo: {ORG_REPO}")

    entry = require_listed(ORG_REPO)
    baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
    print(f"Cloning/reusing baseline at: {baseline_path}")
    clone_baseline(entry, baseline_path)
    snapshot = capture_repository_snapshot(entry, baseline_path)
    print(f"Snapshot source_revision: {snapshot.source_revision}")

    with repository_snapshot_scope(snapshot, allow_local_fact_verification=True):
        result = draft_product_truth.execute(ORG_REPO)

    real_policy = load_policy(entry.policy_profile)
    real_truth = real_policy.product_truth
    assert real_truth is not None, "expected aspose-cells-foss.yml to already have product_truth"

    drafted = result["proposed_product_truth"]
    facts = result["product_facts_v2"]
    selected = facts["selected_fact_ids"]
    by_id = {f["fact_id"]: f for f in facts["facts"]}
    gated_field_states = {
        field: by_id[selected[field]]["verification_state"]
        for field in (
            "product.audience",
            "product.problems_solved",
            "product.capabilities",
            "product.formats",
            "product.limitations",
            "example.minimal",
        )
    }

    report = {
        "org_repo": ORG_REPO,
        "source_revision": snapshot.source_revision,
        "repair_attempts": result["repair_attempts"],
        "findings": result["findings"],
        "gated_field_verification_states": gated_field_states,
        "drafted_product_truth": drafted,
        "real_hand_authored_product_truth": real_truth.model_dump(mode="json"),
    }
    out_path = OUT_DIR / "live-proof-result.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print("\n=== GATE OUTCOME PER FIELD ===")
    for field, state in gated_field_states.items():
        print(f"  {field}: {state}")

    print(f"\nrepair_attempts: {result['repair_attempts']}")
    print(f"findings: {json.dumps(result['findings'], indent=2)}")

    print("\n=== DRAFTED vs REAL HAND-AUTHORED (qualitative anchor) ===")
    print("-- audience --")
    print("  drafted:", drafted["audience"])
    print("  real   :", real_truth.audience)
    print("-- problems_solved --")
    print("  drafted:", drafted["problems_solved"])
    print("  real   :", real_truth.problems_solved)
    print("-- capabilities (values only) --")
    print("  drafted:", [c["value"] for c in drafted["capabilities"]])
    print("  real   :", [c.value for c in real_truth.capabilities])
    print("-- formats (values only) --")
    print("  drafted:", [c["value"] for c in drafted["formats"]])
    print("  real   :", [c.value for c in real_truth.formats])
    print("-- limitations (values only) --")
    print("  drafted:", [c["value"] for c in drafted["limitations"]])
    print("  real   :", [c.value for c in real_truth.limitations])
    print("-- minimal_example.language --")
    print("  drafted:", drafted["minimal_example"]["language"])
    print("  real   :", real_truth.minimal_example.language)

    print(f"\nwrote: {out_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
