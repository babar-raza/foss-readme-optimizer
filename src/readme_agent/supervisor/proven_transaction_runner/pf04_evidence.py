"""Execute the current PF04 receipt matrix and sealed canary through registered actions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from readme_agent import paths
from readme_agent.cli import main as cli_main
from readme_agent.llm.call_ledger import current_llm_accounting_summary
from readme_agent.supervisor.mission_graph import load_mission_graph
from readme_agent.supervisor.proven_transaction_runner.contracts import (
    ProvenTransactionContextV1,
    canonical_sha256,
)
from readme_agent.supervisor.proven_transaction_runner.pf04_handlers import (
    ExternalFactReplayCaseV1,
    build_pf04_handlers,
)
from readme_agent.supervisor.proven_transaction_runner.runner import run_proven_transaction

TASK_ID: Literal["L8-PF-04-MINIMAL-GRAPH-RUNNER"] = "L8-PF-04-MINIMAL-GRAPH-RUNNER"
SEALED_REPOSITORY = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
SEALED_REVISION = "ee05c1ba9153ef5916b7a108406c794f2e464d01"
MISSION_GRAPH = Path("plans/investigations/control/level8-autonomous-mission-task-graph.yaml")
CASES = (
    ExternalFactReplayCaseV1(
        org_repo="aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript",
        source_revision="fc186507e5b7124f4664aa6035f25cfd3112367d",
        expected_surfaces=("example.minimal", "installation.verified_acquisition"),
    ),
    ExternalFactReplayCaseV1(
        org_repo="aspose-email-foss/Aspose.Email-FOSS-for-.Net",
        source_revision="59125b4732df0eedbc4d4c2ab978698ed4348eb7",
        expected_surfaces=("example.minimal",),
    ),
    ExternalFactReplayCaseV1(
        org_repo="aspose-email-foss/Aspose.Email-FOSS-for-Cpp",
        source_revision="fef9c934c3ad7a207c97cc24546176e678f577af",
        expected_surfaces=("example.minimal", "installation.verified_acquisition"),
    ),
    ExternalFactReplayCaseV1(
        org_repo="aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp",
        source_revision="ecc2baf8cc3e3e4a6ee36cbfb992ec4fa6dd7765",
        expected_surfaces=("example.minimal", "installation.verified_acquisition"),
    ),
    ExternalFactReplayCaseV1(
        org_repo="aspose-tex-foss/Aspose.TeX-FOSS-for-Python",
        source_revision="2f4bfab3863e66ef32868f5464685eb4c2d36911",
        expected_surfaces=("example.minimal", "installation.verified_acquisition"),
    ),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sealed_bundle() -> Path:
    org, repo = SEALED_REPOSITORY.split("/", maxsplit=1)
    return paths.readme_poc_repository_dir(org, repo, SEALED_REVISION)


def _sealed_replay() -> dict:
    bundle = _sealed_bundle()
    candidate_path = bundle / "candidate" / "README.md"
    candidate_hash_path = bundle / "candidate" / "candidate-hash.txt"
    before_candidate_sha256 = _sha256(candidate_path)
    expected_candidate_hash = candidate_hash_path.read_text(encoding="utf-8").strip()
    argv = [
        "supervise",
        "--repo",
        SEALED_REPOSITORY,
        "--execution-profile",
        "local_poc",
        "--bounded-verified-canary",
        "--no-registry-heal",
        "--mission-task-id",
        TASK_ID,
        "--mission-observer",
        "codex",
    ]
    first_exit_code = cli_main(argv)
    first_accounting = current_llm_accounting_summary()
    if first_exit_code != 0:
        raise RuntimeError(f"sealed canonical supervisor promotion exited {first_exit_code}")
    if first_accounting.status != "EXACT":
        raise RuntimeError("sealed canonical supervisor promotion has inexact call accounting")

    from readme_agent.state.local_poc_backend import default_local_poc_state_backend
    from readme_agent.supervisor.portfolio_proof_engine.rubric import evaluate_repository

    acceptance = evaluate_repository(SEALED_REPOSITORY, default_local_poc_state_backend())
    if not acceptance.accepted or acceptance.score != 30:
        raise RuntimeError("sealed canonical transaction did not reach 30/30 acceptance")
    if acceptance.hard_disqualifier_count != 0:
        raise RuntimeError("sealed canonical transaction has a hard disqualifier")
    if not acceptance.benchmark_acceptance_proven:
        raise RuntimeError("sealed canonical transaction lacks benchmark acceptance")
    if not acceptance.replay_attestation_proven:
        raise RuntimeError("sealed canonical transaction lacks replay attestation")

    second_exit_code = cli_main(argv)
    no_op_accounting = current_llm_accounting_summary()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    no_op = json.loads((bundle / "review" / "no-op-proof.json").read_text(encoding="utf-8"))
    rubric = json.loads((bundle / "review" / "rubric-evaluation.json").read_text(encoding="utf-8"))[
        "outcome"
    ]
    after_candidate_sha256 = _sha256(candidate_path)
    observed_candidate_hash = candidate_hash_path.read_text(encoding="utf-8").strip()
    if second_exit_code != 0:
        raise RuntimeError(f"sealed canonical supervisor replay exited {second_exit_code}")
    if no_op_accounting.status != "EXACT" or no_op_accounting.provider_call_count != 0:
        raise RuntimeError(
            "sealed canonical supervisor replay did not prove exact zero provider calls"
        )
    if before_candidate_sha256 != after_candidate_sha256:
        raise RuntimeError("sealed canonical supervisor replay changed candidate bytes")
    if observed_candidate_hash != expected_candidate_hash:
        raise RuntimeError("sealed canonical supervisor replay changed candidate identity")
    if manifest.get("lifecycle_status") != "NO_OP_PROVEN":
        raise RuntimeError("sealed canonical supervisor replay did not remain NO_OP_PROVEN")
    if no_op.get("new_provider_call_count") != 0 or no_op.get("patch_created"):
        raise RuntimeError("sealed canonical supervisor no-op receipt is not effect- and call-free")
    if not rubric.get("accepted") or rubric.get("score") != 30:
        raise RuntimeError("sealed canonical supervisor replay lost 30/30 acceptance")
    if rubric.get("hard_disqualifier_count") != 0:
        raise RuntimeError("sealed canonical supervisor replay has a hard disqualifier")
    return {
        "org_repo": SEALED_REPOSITORY,
        "source_revision": SEALED_REVISION,
        "candidate_hash": observed_candidate_hash,
        "candidate_sha256": after_candidate_sha256,
        "lifecycle_status": manifest["lifecycle_status"],
        "rubric_score": rubric["score"],
        "hard_disqualifier_count": rubric["hard_disqualifier_count"],
        "first_provider_call_count": first_accounting.provider_call_count,
        "no_op_provider_call_count": no_op_accounting.provider_call_count,
        "no_op_fixture_call_count": no_op_accounting.fixture_call_count,
        "benchmark_acceptance_proven": rubric["benchmark_acceptance_proven"],
        "replay_attestation_proven": rubric["replay_attestation_proven"],
        "patch_created": no_op["patch_created"],
        "duplicate_bundle_created": no_op["duplicate_bundle_created"],
        "no_op_receipt_sha256": _sha256(bundle / "review" / "no-op-proof.json"),
    }


def main() -> int:
    """Run or resume the checksum-bound PF04 transaction."""

    _graph, graph_sha256 = load_mission_graph(MISSION_GRAPH)
    bundle = _sealed_bundle()
    dependencies = {
        "external_case_matrix": canonical_sha256([case.model_dump(mode="json") for case in CASES]),
        "sealed_candidate": (bundle / "candidate" / "candidate-hash.txt")
        .read_text(encoding="utf-8")
        .strip(),
        "sealed_final_verdict": _sha256(bundle / "review" / "final-verdict.json"),
        "resolver_adapter": _sha256(Path("src/readme_agent/facts/external_fact_block_adapters.py")),
        "runner": _sha256(Path("src/readme_agent/supervisor/proven_transaction_runner/runner.py")),
        "pf04_handlers": _sha256(
            Path("src/readme_agent/supervisor/proven_transaction_runner/pf04_handlers.py")
        ),
        "pf04_evidence": _sha256(Path(__file__)),
    }
    context = ProvenTransactionContextV1(
        task_id=TASK_ID,
        org_repo=SEALED_REPOSITORY,
        source_revision=SEALED_REVISION,
        graph_sha256=graph_sha256,
        dependency_hashes=dependencies,
    )
    output_root = paths.runs_dir() / "pf04-proven-transaction"
    receipt = run_proven_transaction(
        context,
        handlers=build_pf04_handlers(
            CASES, runs_root=paths.runs_dir(), sealed_replay=_sealed_replay
        ),
        output_root=output_root,
    )
    print(output_root / receipt.transaction_id / "receipt.json")
    return 0 if receipt.terminal_status == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
