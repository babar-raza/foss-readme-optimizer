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

Live since 2026-08-18 (`543943038` wired the client through
`capabilities/build_presentation_plan.py` -> `document_planner.py`/
`document_renderer.py` -> `verified_template_document.py`; `928421b65` made
the dropped-claim case reachable). Still additive and opt-in at every
signature: a caller that omits `llm_disposition_client`/`repository_root`
(and now `ratchet_path`) gets the exact pre-existing mechanical-only
behavior."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from readme_agent import paths
from readme_agent.env import llm_api_key, llm_base_url, llm_model_for_job
from readme_agent.llm.verifier_client import ForcedToolClient, LiveForcedToolClient
from readme_agent.readme.claim_accountability_models import ClaimDispositionRecordV1
from readme_agent.verification.claim_disposition import (
    check_claim_disposition,
    corroborate_claim_disposition,
)

JOB_ID = "claim_disposition_check"

# Ratchet (2026-08-18 Gate A recovery): an LLM verdict that was accepted once
# -- i.e. deterministically corroborated against the real candidate/source --
# is persisted per claim-content hash and replayed on later runs through the
# SAME deterministic corroboration (quote must still be found verbatim in the
# current candidate or cited file) with zero provider calls. Only claims with
# no replayable accepted verdict reach the model. This converts the observed
# per-run corroboration nondeterminism ("claim counts fluctuated between
# passes with unchanged inputs") into monotone convergence: an accepted claim
# can only regress if the candidate/source genuinely stops containing its
# evidence, never because a re-rolled model call answered differently.
# Rejected/uncorroborated verdicts are deliberately NOT persisted -- a negative
# is retried live only when the repository is re-executed at all (which the
# blocked-decision cache already restricts to genuine dependency changes).
RATCHET_SCHEMA_VERSION = 1


def claim_disposition_ratchet_path(org_repo: str) -> Path:
    """Repo-level accepted-verdict store, sibling of blocked-decision.json."""

    org, repo = org_repo.split("/", maxsplit=1)
    return paths.readme_poc_root() / f"{org}__{repo}" / "claim-disposition-ratchet.json"


def shared_claim_disposition_ratchet_path() -> Path:
    """Portfolio-level read-through store (E5 design principle 5): identical
    claim text recurs verbatim across repos (page/note share content hash
    7ff54c1da64deecb), so accepted verdicts are also shared portfolio-wide,
    keyed purely by claim-content hash. Sharing is safe by construction: a
    verdict replayed from this store must still pass the full deterministic
    corroboration against the CURRENT repo's candidate/clone before it is
    accepted -- the store only saves provider calls, never re-verification."""

    return paths.readme_poc_root() / "shared-claim-disposition-ratchet.json"


def _load_ratchet(path: Path) -> dict[str, dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != RATCHET_SCHEMA_VERSION
        or not isinstance(payload.get("accepted"), dict)
    ):
        return {}
    return {key: value for key, value in payload["accepted"].items() if isinstance(value, dict)}


def _persist_ratchet_entry(path: Path, content_sha256: str, verdict: dict) -> None:
    accepted = _load_ratchet(path)
    accepted[content_sha256] = verdict
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_suffix(".json.tmp")
    staging.write_text(
        json.dumps(
            {"schema_version": RATCHET_SCHEMA_VERSION, "accepted": accepted},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    staging.replace(path)


# `LiveForcedToolClient`'s own DEFAULT_MAX_TOKENS=300 fits a short verdict
# like `prose_quality_check`'s, but this job's `evidence_quote` field must
# hold a verbatim excerpt from a real README sentence or source file --
# routinely longer than 300 tokens once `reasoning`/`evidence_ref` are also
# counted. Confirmed live (2026-08-18, aspose-font-foss): the 300-token
# default truncated mid-JSON (`finish_reason='length'`), raising an
# uncaught LLMError. 1600 matches the exact calibration already documented
# for this failure class on a same-shape "single-verdict" response
# (facts/agentic_drafting.py's own DEFAULT_MAX_TOKENS journey, corrected
# 900 -> 1600 for the identical truncated-mid-JSON confound).
_MAX_TOKENS = 1600


def default_claim_disposition_client() -> ForcedToolClient:
    """The real, live client construction this job routes through --
    mirrors `capabilities/verify_prose_quality.py::execute()`'s own
    `LiveForcedToolClient(..., job=..., prompt_id=...)` pattern, sized for
    this job's longer verbatim-quote response shape (see `_MAX_TOKENS`)."""

    return LiveForcedToolClient(
        llm_base_url(),
        llm_api_key(),
        llm_model_for_job(JOB_ID),
        max_tokens=_MAX_TOKENS,
        job=JOB_ID,
        prompt_id=JOB_ID,
    )


def llm_verified_claim_disposition(
    claim_id: str,
    claim_text: str,
    candidate_text: str,
    repository_root: Path,
    client: ForcedToolClient | None,
    *,
    ratchet_path: Path | None = None,
    known_api_member_names: frozenset[str] | None = None,
) -> ClaimDispositionRecordV1 | None:
    """Attempt the fallback for one claim the mechanical check could not
    bind. Returns a corroborated, accepted disposition record, or `None`
    when the claim remains unverifiable (stays blocking, unchanged from
    today's behavior) -- callers only ever gain acceptance, never lose it,
    since this only ever runs after the mechanical path has already
    failed.

    `known_api_member_names` (2026-08-19, second aspose.org lesson): the
    real public-API bare-name set threaded through to
    `corroborate_claim_disposition()`'s `api_surface_member` evidence path,
    both for a fresh model call and for ratchet replay below -- omitted
    (`None`), every existing caller keeps today's exact behavior.

    With `ratchet_path` (opt-in, live wiring only), a previously accepted
    verdict for the same claim content is replayed through the same
    deterministic corroboration first -- the per-repo store is consulted,
    then the portfolio-shared read-through store
    (`shared_claim_disposition_ratchet_path()`); an entry from either that
    still corroborates against the CURRENT candidate/source is accepted
    with zero provider calls. The model is consulted only when no
    replayable verdict holds, and a freshly accepted verdict is persisted
    to BOTH stores for the next run (of any repo, for the shared store)."""

    content_sha256 = hashlib.sha256(claim_text.encode("utf-8")).hexdigest()
    if ratchet_path is not None:
        # Read-through: the per-repo store first, then the portfolio-shared
        # store. A verdict from EITHER is accepted only after passing the
        # same deterministic corroboration against the CURRENT candidate and
        # repository clone -- sharing never weakens per-repo verification.
        for store_path in (ratchet_path, shared_claim_disposition_ratchet_path()):
            stored_verdict = _load_ratchet(store_path).get(content_sha256)
            if stored_verdict is None:
                continue
            replayed = corroborate_claim_disposition(
                claim_id,
                content_sha256,
                candidate_text,
                repository_root,
                stored_verdict,
                claim_text=claim_text,
                known_api_member_names=known_api_member_names,
            )
            if replayed.corroborated and replayed.classification != "unverifiable":
                from readme_agent.llm.call_ledger import record_non_provider_call

                record_non_provider_call(
                    job=JOB_ID,
                    prompt_id=JOB_ID,
                    prompt_sha256=None,
                    model="cache",
                    disposition="cache_reuse",
                    request={
                        "claim_id": claim_id,
                        "content_sha256": content_sha256,
                        "classification": replayed.classification,
                        "replayed_from": str(store_path),
                    },
                )
                return replayed
    record = check_claim_disposition(
        claim_id,
        content_sha256,
        claim_text,
        candidate_text,
        repository_root,
        client,
        known_api_member_names=known_api_member_names,
    )
    if record.corroborated and record.classification != "unverifiable":
        if ratchet_path is not None:
            accepted_verdict = {
                "classification": record.classification,
                "evidence_type": record.evidence_type,
                "evidence_ref": record.evidence_ref,
                "evidence_quote": record.evidence_quote,
                "reasoning": record.reasoning,
            }
            _persist_ratchet_entry(ratchet_path, content_sha256, accepted_verdict)
            _persist_ratchet_entry(
                shared_claim_disposition_ratchet_path(), content_sha256, accepted_verdict
            )
        return record
    return None
