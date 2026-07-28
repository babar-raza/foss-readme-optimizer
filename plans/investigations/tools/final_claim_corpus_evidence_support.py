"""Reusable helpers for complete README claim-corpus evidence."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from collections import Counter
from pathlib import Path

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.git_patch import (
    BoundedSourcePatchV1,
    SourceSpanEditV1,
    create_git_patch_proof,
    sha256_text,
)
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.claim_accountability import (
    build_readme_claim_accountability_map,
)
from readme_agent.readme.claim_accountability_models import (
    ReadmeClaimAccountabilityMapV1,
)
from readme_agent.readme.claim_map import ReadmeClaimMapV1, build_readme_claim_map
from readme_agent.readme.document_renderer import build_readme_document_candidate

REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "L8-COMPOSE-02B-FINAL-CLAIM-CORPUS"
GRAPH_PATH = REPO_ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
INPUT_ROOT = REPO_ROOT / "plans/investigations/evidence/level8-contextual-linking/representatives"
OUTPUT_ROOT = REPO_ROOT / "plans/investigations/evidence/level8-final-readme-claim-corpus"
PLATFORMS = ("java", "python", "typescript")
FOCUSED_TEST_COMMAND = (
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_readme_final_claim_corpus.py",
    "tests/unit/test_readme_assessment.py",
    "tests/unit/test_readme_fact_grounding.py",
    "tests/unit/test_protected_content.py",
    "tests/unit/test_readme_document_plan.py",
    "tests/unit/test_readme_proposal_bundle_verifier.py",
    "tests/unit/test_local_poc_evidence.py",
)


def git_output(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def run_focused_tests() -> dict:
    result = subprocess.run(
        FOCUSED_TEST_COMMAND,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "command": subprocess.list2cmdline(FOCUSED_TEST_COMMAND),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _native_patch(source: str, candidate: str):
    edit = SourceSpanEditV1(
        path="README.md",
        byte_start=0,
        byte_end=len(source.encode("utf-8")),
        expected_sha256=sha256_text(source),
        replacement=candidate,
        purpose="record the claim-corpus candidate without applying a remote effect",
    )
    return create_git_patch_proof(
        source,
        candidate,
        BoundedSourcePatchV1(
            path="README.md",
            source_sha256=sha256_text(source),
            edits=[edit],
        ),
    )


def build_case(platform: str) -> dict:
    root = INPUT_ROOT / platform
    source = (root / "original-readme.md").read_text(encoding="utf-8")
    facts = ProductFactsV2.model_validate_json(
        (root / "product-facts-v2.json").read_text(encoding="utf-8")
    )
    revision = next(
        fact.source.source_revision
        for fact in facts.facts
        if fact.source.source_revision is not None
    )
    candidate, plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    claim_map = build_readme_claim_map(
        plan,
        facts,
        source_text=source,
        candidate_text=candidate,
    )
    accountability = build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=source,
        candidate_text=candidate,
        facts=facts,
        generated_claim_map=claim_map,
    )
    return {
        "platform": platform,
        "source": source,
        "candidate": candidate,
        "facts": facts,
        "revision": revision,
        "plan": plan,
        "claim_map": claim_map,
        "accountability": accountability,
        "patch": _native_patch(source, candidate),
    }


def build_negative_control(facts: ProductFactsV2) -> dict:
    source = "# Product\n\nMaintainer performance parity statement.\n"
    candidate = "# Product\n\nGenerated fastest-in-class statement.\n"
    empty_claim_map = ReadmeClaimMapV1(
        org_repo=facts.org_repo,
        facts_hash=facts.canonical_hash(),
        candidate_sha256=hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
        claims=[],
    )
    accountability = build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=source,
        candidate_text=candidate,
        facts=facts,
        generated_claim_map=empty_claim_map,
    )
    return {
        "source": source,
        "candidate": candidate,
        "accountability": accountability,
    }


def record_containing(case: dict, stage: str, needle: str):
    document = case["source"] if stage == "source" else case["candidate"]
    document_bytes = document.encode("utf-8")
    matches = [
        record
        for record in case["accountability"].claims
        if record.stage == stage
        and needle
        in document_bytes[record.source_byte_start : record.source_byte_end].decode("utf-8")
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {stage} claim containing {needle!r}; got {len(matches)}")
    return matches[0]


def summarize(case: dict) -> dict:
    accountability: ReadmeClaimAccountabilityMapV1 = case["accountability"]
    return {
        "platform": case["platform"],
        "org_repo": case["facts"].org_repo,
        "source_revision": case["revision"],
        "source_claims": sum(record.stage == "source" for record in accountability.claims),
        "candidate_claims": sum(record.stage == "candidate" for record in accountability.claims),
        "expected_dispositions": dict(
            sorted(Counter(record.expected_disposition for record in accountability.claims).items())
        ),
        "currently_accountable": sum(
            record.currently_accountable for record in accountability.claims
        ),
        "missing_accountability": sum(
            not record.currently_accountable for record in accountability.claims
        ),
        "accountability_sha256": accountability.canonical_hash(),
    }


def inventory_is_exact(case: dict) -> bool:
    source_claims = assess_material_claims(case["source"])
    candidate_claims = assess_material_claims(case["candidate"])
    records = case["accountability"].claims
    return (
        sum(record.stage == "source" for record in records) == len(source_claims)
        and sum(record.stage == "candidate" for record in records) == len(candidate_claims)
        and len({record.claim_id for record in records}) == len(records)
    )


def spans_are_exact(case: dict) -> bool:
    for stage in ("source", "candidate"):
        document = case[stage].encode("utf-8")
        for record in (item for item in case["accountability"].claims if item.stage == stage):
            content = document[record.source_byte_start : record.source_byte_end]
            if hashlib.sha256(content).hexdigest() != record.content_sha256:
                return False
    return True


def verify_inventory() -> bool:
    for line in (OUTPUT_ROOT / "sha256sums.txt").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        if hashlib.sha256((OUTPUT_ROOT / relative).read_bytes()).hexdigest() != expected:
            return False
    return True
