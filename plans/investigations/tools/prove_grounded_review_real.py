"""Run the production separated reviewer on one sealed real README bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from readme_agent.errors import LLMError
from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.llm.call_ledger import (
    bind_llm_repository_revision,
    current_llm_accounting_summary,
    current_llm_call_context,
    start_llm_call_accounting,
)
from readme_agent.llm.verification_prompts import separated_reviewer_standard_hash
from readme_agent.specialists.separated_readme_review import run_separated_readme_review

ORG_REPO = "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp"


def _load_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    bundle = args.bundle.resolve()
    output = args.output.resolve()
    manifest = _load_object(bundle / "manifest.json")
    if manifest.get("org_repo") != ORG_REPO:
        raise RuntimeError("bundle repository does not match governed Cells C++ representative")
    if manifest.get("lifecycle_status") != "DETERMINISTIC_VALIDATED":
        raise RuntimeError("real review prerequisite is not deterministically validated")
    source_revision = str(manifest["source_revision"])
    candidate = (bundle / "candidate" / "README.md").read_text(encoding="utf-8")
    source = (bundle / "source" / "README.md").read_text(encoding="utf-8")
    facts = _load_object(bundle / "facts" / "product-facts.json")
    plan = {
        "repository_presentation_plan": _load_object(
            bundle / "planning" / "presentation-plan.json"
        ),
        "readme_document_plan": _load_object(bundle / "planning" / "readme-document-plan.json"),
    }
    control_snapshot = {
        "branch": _git("branch", "--show-current"),
        "head": _git("rev-parse", "HEAD"),
        "tree_clean": not bool(_git("status", "--porcelain=v1")),
    }
    run_id = "L8-REVIEW-01A-CELLS-CPP"
    start_llm_call_accounting(
        ORG_REPO,
        run_id,
        campaign_id=run_id,
        stage="AGENT_REVIEWING",
    )
    bind_llm_repository_revision(source_revision, stage="AGENT_REVIEWING")
    review = None
    review_error = None
    try:
        review = run_separated_readme_review(
            ORG_REPO,
            source,
            candidate,
            plan,
            facts,
        )
    except LLMError as exc:
        review_error = {
            "error_class": type(exc).__name__,
            "message": str(exc),
            "classified_verdict": "SYSTEM_FAILURE",
            "candidate_retained": True,
        }
    accounting = current_llm_accounting_summary()
    if accounting.status != "EXACT" or accounting.provider_call_count < 1:
        raise RuntimeError("real separated review did not record its provider calls")

    output.mkdir(parents=True, exist_ok=True)
    context = current_llm_call_context()
    assert context is not None
    shutil.copyfile(context.ledger_path, output / "llm-call-ledger.jsonl")
    write_redacted_json(
        output / "cells-cpp-grounded-review.json",
        {
            "schema_version": 1,
            "org_repo": ORG_REPO,
            "source_revision": source_revision,
            "source_bundle": str(bundle),
            "candidate_sha256": hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
            "reviewer_standard_sha256": separated_reviewer_standard_hash(),
            "control_branch": control_snapshot["branch"],
            "control_head": control_snapshot["head"],
            "control_tree_clean": control_snapshot["tree_clean"],
            "review": review.model_dump(mode="json") if review is not None else None,
            "review_error": review_error,
            "llm_accounting": accounting.model_dump(mode="json"),
            "remote_write_attempted": False,
        },
    )
    refresh_sha256sums(output)
    verdict = review.verdict if review is not None else "SYSTEM_FAILURE"
    print(json.dumps({"output": str(output), "verdict": verdict}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
