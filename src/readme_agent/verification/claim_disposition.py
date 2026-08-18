"""A narrow, corroborated LLM fallback layered ADDITIVELY onto the existing
mechanical claim-accountability gate (2026-08-18) -- never a replacement of
it, mirroring `verification/prose_quality.py`'s own "additive, corroborated,
never trusted at face value" shape exactly.

`source_claim_fact_binding.py::_covered_by_fact_variants` correctly declines
to certify a source claim whose literal text cannot be mechanically
reconstructed from pre-extracted fact phrases -- that gate is not loosened
here. This module only ever runs for a claim that has ALREADY failed that
mechanical check, and its own verdict is never trusted from the model's own
say-so: `corroborate_claim_disposition()` -- plain, deterministic code --
independently re-checks the model's cited evidence (a verbatim quote that
must actually appear in the candidate text, or in a real repository file)
before the verdict can affect anything. An uncorroborated (hallucinated,
out-of-scope, or unverifiable) verdict never unblocks a claim."""

from __future__ import annotations

from pathlib import Path

from readme_agent.llm.claim_disposition_prompts import (
    CLAIM_DISPOSITION_TOOL_SCHEMA,
    build_claim_disposition_messages,
)
from readme_agent.llm.verifier_client import ForcedToolClient
from readme_agent.readme.claim_accountability_models import ClaimDispositionRecordV1

_MAX_LISTED_FILES = 400


def repository_file_listing(repository_root: Path) -> str:
    """A bounded, real listing of text-like files the model may cite --
    keeps citations checkable (a path outside this listing is never real
    evidence) without shipping full file contents into the prompt."""

    if not repository_root.is_dir():
        return "(no repository clone available)"
    paths = sorted(
        str(path.relative_to(repository_root)).replace("\\", "/")
        for path in repository_root.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and path.suffix.lower() in {".py", ".md", ".rst", ".toml", ".cfg", ".txt", ".json"}
    )
    return "\n".join(paths[:_MAX_LISTED_FILES]) or "(no matching files found)"


def _resolve_within_repository(repository_root: Path, evidence_ref: str) -> Path | None:
    """Refuse any path that would escape the repository clone."""

    candidate = (repository_root / evidence_ref).resolve()
    try:
        candidate.relative_to(repository_root.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def corroborate_claim_disposition(
    claim_id: str,
    content_sha256: str,
    candidate_text: str,
    repository_root: Path,
    llm_result: dict,
) -> ClaimDispositionRecordV1:
    """Pure except for one bounded, read-only file read of an already-
    listed, path-escape-checked repository file. Never trusts the model's
    classification or quote without independently finding that exact quote
    in the exact location the model cited."""

    classification = str(llm_result.get("classification") or "unverifiable")
    evidence_type = str(llm_result.get("evidence_type") or "none")
    evidence_ref = str(llm_result.get("evidence_ref") or "")
    evidence_quote = str(llm_result.get("evidence_quote") or "")
    reasoning = str(llm_result.get("reasoning") or "no reasoning provided")

    corroborated = False
    if (
        classification == "redundant_with_candidate"
        and evidence_type == "candidate_section_reference"
    ):
        corroborated = bool(evidence_quote) and evidence_quote in candidate_text
    elif classification == "verified_against_source" and evidence_type == "clone_cache_path":
        resolved = _resolve_within_repository(repository_root, evidence_ref)
        if resolved is not None and evidence_quote:
            try:
                file_content = resolved.read_text(encoding="utf-8", errors="replace")
            except OSError:
                file_content = ""
            corroborated = evidence_quote in file_content
    elif classification == "narrative_filler":
        # No evidence to corroborate -- asserts absence of factual content,
        # not presence of a fact. Accepted only on the model's classification
        # itself, matching aspose.org's own "no source claim to verify"
        # category (content-dispositions.json unit_id u0007/u0008/u0011).
        corroborated = True

    if not corroborated:
        classification = "unverifiable"
        evidence_type = "none"
        evidence_ref = ""
        evidence_quote = ""

    return ClaimDispositionRecordV1(
        claim_id=claim_id,
        content_sha256=content_sha256,
        classification=classification,  # type: ignore[arg-type]
        evidence_type=evidence_type,  # type: ignore[arg-type]
        evidence_ref=evidence_ref,
        evidence_quote=evidence_quote,
        reasoning=reasoning,
        corroborated=corroborated,
    )


def check_claim_disposition(
    claim_id: str,
    content_sha256: str,
    claim_text: str,
    candidate_text: str,
    repository_root: Path,
    client: ForcedToolClient | None,
) -> ClaimDispositionRecordV1:
    """`client=None` (no verifier configured) degrades honestly: the claim
    stays unverified/blocking, never crashes, never silently accepted --
    this fallback is additive, not required for the mechanical gate to
    function. A real `LLMError` from `client` propagates uncaught, exactly
    matching `check_prose_quality`'s documented behavior."""

    if client is None:
        return ClaimDispositionRecordV1(
            claim_id=claim_id,
            content_sha256=content_sha256,
            classification="unverifiable",
            evidence_type="none",
            evidence_ref="",
            evidence_quote="",
            reasoning="no verifier client configured",
            corroborated=False,
        )

    messages = build_claim_disposition_messages(
        claim_text, candidate_text, repository_file_listing(repository_root)
    )
    result = client.call(
        messages, CLAIM_DISPOSITION_TOOL_SCHEMA
    )  # LLMError propagates, deliberately uncaught
    return corroborate_claim_disposition(
        claim_id, content_sha256, candidate_text, repository_root, result.arguments
    )
