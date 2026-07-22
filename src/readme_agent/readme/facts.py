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
from pathlib import Path

from pydantic import BaseModel, Field

from readme_agent.inspection import file_inventory
from readme_agent.readme.gap_detector import GapReport
from readme_agent.validation.registry import VALIDATION_RULESET_VERSION

# Bumped whenever build_prompt()'s logic or renderer.py's owned-span contract
# changes -- included in the facts hash so a change forces regeneration even
# when nothing about the repo itself changed. Prompt *wording* changes are now
# covered automatically by prompt_content_hash instead (prompts/README.md rule
# 3); this version is for logic/contract changes the file hash can't see.
# Bumped to "3" for Phase 21 (decision #9 as corrected): renderer.py merges
# what were two owned spans (callout, resources) into one -- a real
# owned-span contract change, not cosmetic. Bumped to "4" for the prompts/
# migration (`GOV-016`): build_prompt()'s implementation changed from
# embedded f-strings to loading+substituting prompts/relationship_explained/.
# Bumped to "5" for the categorical prompt registry migration (`GOV-024`,
# Wave 8.5): build_prompt()'s implementation changed again, from loading two
# `.txt` files to loading a schema-validated YAML manifest via
# llm/prompt_registry.py -- same string.Template substitution semantics,
# same generated content, but the file-hash tripwire this version guards
# can't see "same semantics," only "file changed."
GENERATION_SCHEMA_VERSION = "5"


def sha256_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def compute_tracked_content_hash(repo_path: Path) -> str:
    """Content-level fingerprint of the repository-file-managed control-class
    surfaces (decision #19's class 1: README, LICENSE, community files) --
    independent from and finer-grained than `SupervisorStateV1.
    last_observed_upstream_revision`'s whole-repo commit SHA, which keeps its
    own, different, coarser purpose (supervisor loop-cost avoidance).

    This is the single, canonical implementation: `orchestrator.py`'s
    durable-skip gate and the readme_reconciliation specialist both compare
    against this function's output, never a second, independently-computed
    hash -- the fragmentation of "did anything change" signals across waves
    is exactly what previously let a real drift-detection gap go unnoticed
    (decision #38).
    """
    inventory = file_inventory.scan(repo_path)
    tracked: list[tuple[str, Path | None]] = [
        ("README", inventory.readme_path),
        ("LICENSE", inventory.license_path),
    ]
    tracked.extend(sorted(inventory.community_paths.items()))

    parts = []
    for name, path in tracked:
        if path is not None and path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")
            parts.append(f"{name}:{sha256_text(content)}")
        else:
            parts.append(f"{name}:MISSING")
    return sha256_text("|".join(parts))


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
    prompt_content_hash: str
    generation_schema_version: str = GENERATION_SCHEMA_VERSION
    # VER-004: closes durable_skip's blindness to a validation *rule-code*
    # change (policy_content_hash only covers the policy YAML, never the
    # rule modules in validation/registry.py::RULES) -- same manually-bumped
    # convention as generation_schema_version, folded into the same hash so
    # bumping it forces exactly one honest re-validation on next touch.
    validation_ruleset_version: str = VALIDATION_RULESET_VERSION


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
    "prompt_content_hash",
    "generation_schema_version",
    "validation_ruleset_version",
)


def compute_facts_hash(facts: RepositoryFacts) -> str:
    dumped = facts.model_dump(mode="json")
    canonical_input = {k: dumped[k] for k in _HASH_FIELDS}
    canonical = json.dumps(canonical_input, sort_keys=True, separators=(",", ":"))
    return sha256_text(canonical)
