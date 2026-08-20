"""Load the raw, already-written candidate-bound evidence a rubric evaluation needs.

Every field here is read from the *canonical* `local_poc` compatibility bundle
(`paths.readme_poc_repository_dir()`), never `runs/share/poc/` (the diagnostic straight-line
runner's own separate, non-lifecycle-bound output the task explicitly says must never be
authoritative). Reads are best-effort and defensive: a missing or malformed artifact leaves its
field `None` rather than raising, so a rubric criterion that depends on it fails closed to "not
proven" instead of crashing the whole evaluation -- exactly the fail-closed contract the 30-point
rubric requires.

Field-to-file mapping is grounded in the producers confirmed during this task's research
(`supervisor/local_poc_evidence.py`, `supervisor/local_poc_review_evidence.py`,
`readme/document_validation.py::DocumentCandidateValidationV1`,
`facts/knowledge_application_evidence.py::KnowledgeApplicationV1`,
`specialists/readme_review_roles.py::FactualPlanReviewResultV1`/`BlindQualityReviewResultV1`).
Where this task could not independently confirm an exact nested key inside a real generated
artifact (never having run the live pipeline, per the task's own instruction not to), the readers
below check the most likely key paths rather than assuming one -- `rubric.py`'s criteria treat an
absent value as unproven, never as a guess. Recalibrate the key paths here against one real
generated bundle before the first live rubric run.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from readme_agent import paths


class EvidenceBundleV1(BaseModel):
    """Raw (loosely-typed) evidence for one candidate-bound rubric evaluation."""

    model_config = ConfigDict(extra="forbid")

    org_repo: str
    source_revision: str | None
    candidate_hash: str | None
    bundle_dir: str | None

    manifest: dict | None = None
    deterministic_validation: dict | None = None
    knowledge_application: dict | None = None
    factual_review: dict | None = None
    visitor_review: dict | None = None
    combined_review: dict | None = None
    claim_map: dict | None = None
    reconciliation: dict | None = None
    no_op_proof: dict | None = None
    check_coverage: dict | None = None
    facts: dict | None = None


def _read_json(path: Path) -> dict | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def load_evidence_bundle(
    org_repo: str,
    source_revision: str | None,
    *,
    candidate_hash: str | None = None,
) -> EvidenceBundleV1:
    if not source_revision:
        return EvidenceBundleV1(
            org_repo=org_repo,
            source_revision=None,
            candidate_hash=candidate_hash,
            bundle_dir=None,
        )
    org, repo = org_repo.split("/", maxsplit=1)
    bundle_dir = paths.readme_poc_repository_dir(org, repo, source_revision)
    return EvidenceBundleV1(
        org_repo=org_repo,
        source_revision=source_revision,
        candidate_hash=candidate_hash,
        bundle_dir=str(bundle_dir),
        manifest=_read_json(bundle_dir / "manifest.json"),
        deterministic_validation=_read_json(
            bundle_dir / "review" / "deterministic-validation.json"
        ),
        knowledge_application=_read_json(bundle_dir / "knowledge-application.json"),
        factual_review=_read_json(bundle_dir / "review" / "factual-plan-review.json"),
        visitor_review=_read_json(bundle_dir / "review" / "blind-quality-review.json"),
        combined_review=_read_json(bundle_dir / "review" / "combined-review.json"),
        claim_map=_read_json(bundle_dir / "candidate" / "claim-map.json"),
        reconciliation=_read_json(bundle_dir / "candidate" / "readme-reconciliation.json"),
        no_op_proof=_read_json(bundle_dir / "review" / "no-op-proof.json"),
        check_coverage=_read_json(bundle_dir / "candidate" / "check-coverage.json"),
        facts=_read_json(bundle_dir / "facts" / "product-facts.json"),
    )
