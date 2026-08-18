"""The bounded LLM-verification fallback acceptance path for claim
accountability (2026-08-18), alongside (never instead of) the mechanical
whole-claim fact-variant coverage check in `source_claim_fact_binding.py`.

Mirrors aspose.org's own proven `content-dispositions.json` reconciliation
model: a claim the mechanical check cannot bind gets one narrow, forced-
tool-call classification (redundant with the already-composed candidate,
verified against real repository source, pure narrative filler, or
unverifiable), and that verdict is never trusted without deterministic
corroboration (`verification/claim_disposition.py`) -- exactly the "who
verifies the verifier" resolution `verification/prose_quality.py` already
established for its own additive LLM signal.

Phase 1 (this module): the mechanism is complete, corroborated, and tested
end-to-end via `build_readme_claim_accountability_map`'s new optional
`llm_disposition_client`/`repository_root` parameters -- entirely inert
(zero behavior change) unless a caller explicitly supplies a client. No
caller in the live candidate-rendering pipeline (`document_renderer.py`,
`supervisor/loop.py`) passes one yet; wiring a real client into that live
chain is the deliberately deferred next step, not attempted in the same
pass that introduced the mechanism itself."""

from __future__ import annotations

import hashlib
from pathlib import Path

from readme_agent.env import llm_api_key, llm_base_url, llm_model_for_job
from readme_agent.llm.verifier_client import ForcedToolClient, LiveForcedToolClient
from readme_agent.readme.claim_accountability_models import ClaimDispositionRecordV1
from readme_agent.verification.claim_disposition import check_claim_disposition

JOB_ID = "claim_disposition_check"


def default_claim_disposition_client() -> ForcedToolClient:
    """The real, live client construction this job routes through --
    mirrors `capabilities/verify_prose_quality.py::execute()`'s own
    `LiveForcedToolClient(..., job=..., prompt_id=...)` pattern exactly."""

    return LiveForcedToolClient(
        llm_base_url(),
        llm_api_key(),
        llm_model_for_job(JOB_ID),
        job=JOB_ID,
        prompt_id=JOB_ID,
    )


def llm_verified_claim_disposition(
    claim_id: str,
    claim_text: str,
    candidate_text: str,
    repository_root: Path,
    client: ForcedToolClient | None,
) -> ClaimDispositionRecordV1 | None:
    """Attempt the fallback for one claim the mechanical check could not
    bind. Returns a corroborated, accepted disposition record, or `None`
    when the claim remains unverifiable (stays blocking, unchanged from
    today's behavior) -- callers only ever gain acceptance, never lose it,
    since this only ever runs after the mechanical path has already
    failed."""

    content_sha256 = hashlib.sha256(claim_text.encode("utf-8")).hexdigest()
    record = check_claim_disposition(
        claim_id, content_sha256, claim_text, candidate_text, repository_root, client
    )
    if record.corroborated and record.classification != "unverifiable":
        return record
    return None
