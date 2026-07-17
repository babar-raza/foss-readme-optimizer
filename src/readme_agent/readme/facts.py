"""Canonical facts -> sha256, computed *before* any LLM call.

sha256_text is adopted verbatim (CRLF-normalized before hashing) from
aspose.org's cleanroom_manifest.py -- the proven fix for the cross-platform
(Windows dev / Linux CI) hash-determinism concern.

RepositoryFacts is also the *sole* permitted input to llm/prompts.py's
build_prompt() (Consistency & Determinism Tier 1 SS2) -- the coupling is
mechanically enforced there, not just by convention here.
"""

import hashlib
import json

from pydantic import BaseModel, Field

from readme_agent.readme.gap_detector import GapReport

# Bumped whenever prompts.py or renderer.py's owned-span contract changes --
# included in the facts hash so a renderer/prompt change forces regeneration
# even when nothing about the repo itself changed.
GENERATION_SCHEMA_VERSION = "2"


def sha256_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class GapReportFacts(BaseModel):
    """Only the decision-relevant fields of GapReport -- evidence excerpts are
    for human debugging, not part of what generation depends on."""

    license_mentioned: bool
    products_org_link: bool
    products_com_link: bool
    relationship_explained: bool

    @classmethod
    def from_gap_report(cls, report: GapReport) -> "GapReportFacts":
        return cls(
            license_mentioned=report.license_mentioned,
            products_org_link=report.products_org_link,
            products_com_link=report.products_com_link,
            relationship_explained=report.relationship_explained,
        )


class RepositoryFacts(BaseModel):
    org_repo: str
    commit_sha: str | None
    manifest: dict[str, str] = Field(default_factory=dict)
    detected_license: str | None
    gap_report: GapReportFacts
    policy_content_hash: str
    generation_schema_version: str = GENERATION_SCHEMA_VERSION


# Deliberately excludes gap_report: it's *derived from* README content this
# tool itself rewrites, so it's an output of rendering, not an independent
# input fact -- hashing it makes the hash unable to ever match itself once a
# render closes a gap (a real bug caught by the orchestrator's idempotency
# test, not a hypothetical). Everything else here is independent of our own
# writes: repo metadata, detected license, and policy content.
_HASH_FIELDS = (
    "org_repo",
    "commit_sha",
    "manifest",
    "detected_license",
    "policy_content_hash",
    "generation_schema_version",
)


def compute_facts_hash(facts: RepositoryFacts) -> str:
    dumped = facts.model_dump(mode="json")
    canonical_input = {k: dumped[k] for k in _HASH_FIELDS}
    canonical = json.dumps(canonical_input, sort_keys=True, separators=(",", ":"))
    return sha256_text(canonical)
