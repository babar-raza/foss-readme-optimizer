# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: analysis_or_evidence_only
"""Build assurance-separated trusted review, repair, ledger, and no-op evidence."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from trp03_evidence_support import (  # noqa: E402
    blind_accept,
    fidelity_accept,
    fidelity_loss,
    review_clients,
    tool_result,
)

from readme_agent.evidence.writer import (  # noqa: E402
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.facts.trusted_readme_extraction import (  # noqa: E402
    extract_trusted_readme_fact_graph,
)
from readme_agent.gitsafety._git import run_git  # noqa: E402
from readme_agent.llm.analysis_client import FixtureAnalysisClient  # noqa: E402
from readme_agent.llm.call_ledger import (  # noqa: E402
    bind_llm_repository_revision,
    current_llm_accounting_summary,
    current_llm_call_context,
    load_llm_call_records,
    start_llm_call_accounting,
)
from readme_agent.llm.verifier_client import FixtureForcedToolClient  # noqa: E402
from readme_agent.readme.trusted_composition import compose_trusted_readme  # noqa: E402
from readme_agent.registry.loader import load_products  # noqa: E402
from readme_agent.repository_snapshot import capture_repository_snapshot  # noqa: E402
from readme_agent.specialists.trusted_transform_review import (  # noqa: E402
    run_trusted_transform_review,
)
from readme_agent.specialists.trusted_transform_review_repair import (  # noqa: E402
    run_trusted_review_with_repair,
)

ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
SOURCE = "# Widget\n\nA specific package for Python developers.\n"
EVIDENCE_DIR = (
    REPO_ROOT / "plans" / "investigations" / "evidence" / "trp-03-independent-fidelity-review-v1"
)


def _git(root: Path, *args: str) -> None:
    result = run_git(list(args), cwd=root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)


def _write_outputs(output: Path, payloads: dict[str, object]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    expected = {*payloads, "llm-call-ledger.jsonl", "sha256sums.txt"}
    unexpected = {
        path.name for path in output.iterdir() if path.is_file() and path.name not in expected
    }
    if unexpected:
        raise RuntimeError(f"refusing to overwrite evidence with unknown files: {unexpected}")
    context = current_llm_call_context()
    if context is None:
        raise RuntimeError("evidence run lost its LLM accounting context")
    ledger_source = Path(context.ledger_path)
    load_llm_call_records(ledger_source)
    write_redacted_text(
        output / "llm-call-ledger.jsonl",
        ledger_source.read_text(encoding="utf-8"),
    )
    ledger_sha256 = hashlib.sha256((output / "llm-call-ledger.jsonl").read_bytes()).hexdigest()
    for name, payload in payloads.items():
        write_redacted_json(output / name, _bind_ledger_reference(payload, ledger_sha256))
    refresh_sha256sums(output)


def _bind_ledger_reference(value: object, ledger_sha256: str) -> object:
    if isinstance(value, dict):
        return {
            key: (
                "llm-call-ledger.jsonl"
                if key == "ledger_path"
                else (
                    ledger_sha256
                    if key == "ledger_sha256"
                    else _bind_ledger_reference(item, ledger_sha256)
                )
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_bind_ledger_reference(item, ledger_sha256) for item in value]
    return value


def main() -> int:
    run_id = f"trp03-evidence-{uuid.uuid4()}"
    start_llm_call_accounting(ORG_REPO, run_id, stage="TRUSTED_REVIEWING")
    runtime_root = REPO_ROOT / "runs"
    runtime_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="trp03-", dir=runtime_root) as temporary:
        root = Path(temporary) / "source"
        root.mkdir()
        _git(root, "init", "-b", "main")
        _git(root, "config", "user.name", "TRP-03 Evidence")
        _git(root, "config", "user.email", "trp03@example.invalid")
        (root / "README.md").write_text(SOURCE, encoding="utf-8", newline="")
        _git(root, "add", "README.md")
        _git(root, "commit", "-m", "seed")
        entry = next(item for item in load_products() if item.org_repo == ORG_REPO)
        snapshot = capture_repository_snapshot(entry, root)
        graph = extract_trusted_readme_fact_graph(snapshot)
        bind_llm_repository_revision(graph.source_revision, stage="TRUSTED_REVIEWING")

        source_composition = compose_trusted_readme(
            graph,
            SOURCE,
            client=FixtureForcedToolClient(
                [tool_result(graph, SOURCE, "fixture-author")],
                job="trusted_readme_section_transform",
                prompt_id="trusted_readme_section_transform",
            ),
        )
        blind, fidelity = review_clients(
            [blind_accept("A specific package")],
            [fidelity_accept(graph)],
        )
        accepted = run_trusted_transform_review(
            graph,
            SOURCE,
            source_composition,
            blind_client=blind,
            fidelity_client=fidelity,
        )
        no_op = run_trusted_transform_review(
            graph,
            SOURCE,
            source_composition,
            blind_client=FixtureAnalysisClient([]),
            fidelity_client=FixtureAnalysisClient([]),
            cached_review=accepted.review,
        )

        weakened = "# Widget\n\nA package.\n"
        weakened_composition = compose_trusted_readme(
            graph,
            SOURCE,
            client=FixtureForcedToolClient(
                [tool_result(graph, weakened, "fixture-author")],
                job="trusted_readme_section_transform",
                prompt_id="trusted_readme_section_transform",
            ),
        )
        blind, fidelity = review_clients([blind_accept("A package.")], [fidelity_loss(graph)])
        rejected = run_trusted_transform_review(
            graph,
            SOURCE,
            weakened_composition,
            blind_client=blind,
            fidelity_client=fidelity,
        )

        blind, fidelity = review_clients(
            [blind_accept("A package."), blind_accept("A specific package")],
            [fidelity_loss(graph), fidelity_accept(graph)],
        )
        repaired = run_trusted_review_with_repair(
            graph,
            SOURCE,
            weakened_composition,
            blind_client=blind,
            fidelity_client=fidelity,
            repair_client=FixtureForcedToolClient(
                [tool_result(graph, SOURCE, "fixture-repair")],
                job="trusted_readme_section_transform",
                prompt_id="trusted_readme_section_transform",
            ),
        )
        accounting = current_llm_accounting_summary()
        payloads = {
            "accepted-review.json": accepted.model_dump(mode="json"),
            "content-loss-rejection.json": rejected.model_dump(mode="json"),
            "repair-loop.json": repaired.model_dump(mode="json"),
            "no-op-proof.json": no_op.model_dump(mode="json"),
            "scenario-summary.json": {
                "schema_version": 1,
                "task_id": "TRP-03-INDEPENDENT-FIDELITY-REVIEW",
                "content_assurance": "trusted_inherited",
                "factual_truth_verified": False,
                "source_revision": graph.source_revision,
                "accepted_verdict": accepted.review.verdict,
                "content_loss_verdict": rejected.review.verdict,
                "repair_outcome": repaired.outcome,
                "repair_changed_candidate": repaired.repair_history[0].candidate_changed,
                "cache_reused": no_op.cache_reused,
                "cache_provider_call_delta": no_op.new_provider_call_count,
                "accounting": accounting.model_dump(mode="json"),
                "live_route_proof": "deferred_to_TRP-04_canary_qualification",
            },
        }
        _write_outputs(EVIDENCE_DIR, payloads)
    print(f"wrote {EVIDENCE_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
