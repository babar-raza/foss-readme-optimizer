"""Agentic drafting of `product_truth` for repositories with no policy-
authored ground truth yet (`RPOC-030`-`033`, sprint charter Part B.2 Phase 2
Lane F, design in Part C.5).

Recon for this taskcard confirmed every one of the 27 non-pilot registry
repos fails the identical validation stage for the identical reason: no
human ever authored a `product_truth` block in that repo's `config/
policies/*.yml`, so `product.audience`/`capabilities`/`formats`/
`limitations`/`example.minimal` all resolve to `missing`. This module closes
that gap without manual authoring, but never by trusting a free-text LLM
response on its own -- every claim it drafts is routed through a real,
already-existing, unmodified deterministic gate before it can become a
`verified` `ProductFactsV2` fact (`capabilities.draft_product_truth.py`
owns that gating/repair-loop orchestration; this module owns exactly one
thing: producing one candidate draft per call).

Only 5 of `schema_v2.REQUIRED_PRODUCT_FIELDS` are genuinely interpretive
(`audience`, `problems_solved`, `capabilities`, `formats`, `limitations`) --
the rest are already mechanically derived by `facts/repository_ingestion.py`/
`facts/provider.py`. `draft_product_truth()` therefore drafts exactly those
5 fields plus `minimal_example` (itself gated separately, by `facts/local_
verification.py`, not by either of the two mechanisms below), and supplies
the REST of `ProductFactsV2` back to the model only as read-only grounding
context to cite -- never as something to redraft.

`DraftProductTruthV1` deliberately reuses this project's own existing
pydantic shapes rather than inventing parallel ones (`GOVERNANCE.md`'s
reuse-required discipline): `audience`/`problems_solved` are `facts/
interpretive_evidence.py::InterpretiveClaimV1` (claim_id + text +
supporting_fact_ids) -- exactly the input shape `groundedness_fact_
candidate()` already consumes, unmodified. `capabilities`/`formats`/
`limitations`/`minimal_example` reuse `registry/models.py`'s existing
`EvidenceBackedProductFact`/`MinimalExamplePolicy` -- exactly the shape a
human already writes by hand in `config/policies/*.yml` (see
`config/policies/aspose-cells-foss.yml`'s own `product_truth:` block), and
exactly what `facts/policy_evidence.py::evidence_fact_candidate()` already
accepts, unmodified. A passed draft is therefore already policy-YAML-shaped
with zero translation.

**LLM client: `llm/verifier_client.py::LiveForcedToolClient`, not free-form
JSON** -- the full-registry Gate-A run proved that a valid JSON response can
still drift from the nested `DraftProductTruthV1` contract. Production forces
one native tool carrying the complete schema; injected fixture analysis
clients retain the same offline test seam.

**Model route**: `env.py::JOB_MODEL_ROUTING["draft_product_truth"]`,
live-characterized in `plans/investigations/evidence/draft-product-truth-
route-characterization-2026-07-25/characterization-and-recommendation.md`
against this exact prompt (RPOC-030), not assumed from the reviewer job's
own, differently-shaped characterization.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from readme_agent import env, paths
from readme_agent.errors import LLMError
from readme_agent.facts.interpretive_evidence import InterpretiveClaimV1
from readme_agent.facts.provider import collect_product_facts
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.inspection import file_inventory
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.generation_prompts import build_draft_product_truth_messages
from readme_agent.llm.verifier_client import LiveForcedToolClient
from readme_agent.registry.loader import require_listed
from readme_agent.registry.models import EvidenceBackedProductFact, MinimalExamplePolicy

_MODEL_ROUTE_JOB = "draft_product_truth"

# RPOC-033: this job's response is meaningfully larger than a single verdict
# object (several claim/evidence arrays plus a full minimal-example code
# block) -- sized generously above `LiveAnalysisClient`'s own
# `DEFAULT_MAX_TOKENS=1000` rather than risking the exact truncated-mid-JSON
# confound `independent-readme-reviewer-route-characterization-2026-07-25/
# characterization-and-recommendation.md` already documented and corrected
# for a smaller, single-verdict response shape (900 -> 1600). Raised again
# from an initial 3000 (sufficient for the route characterization's own
# bounded scenarios) once a real, large repository's own richly-detailed
# capabilities list (24 real entries against aspose-cells-foss) showed this
# job's real completion size scales with how much real evidence the model
# is actually given -- the same reasoning behind `MAX_CONTEXT_CHARS`'s own
# increase just above. The first real full-portfolio sweep then produced
# three independently truncated tool-argument objects at 3.5-5k output
# characters under the 4,000-token setting (Python, C++, and another Python
# repository). Qwen's routed reasoning consumes part of the completion
# budget, so the visible JSON length is not the token budget. Eight thousand
# leaves the same bounded context headroom while allowing the complete
# structured payload to survive; the forced-tool client still retries one
# malformed structured response and fails closed after that.
_MAX_RESPONSE_TOKENS = 8000
_REQUEST_TIMEOUT_SECONDS = 180

# Bounded repo-context budget (RPOC-033): stays well inside qwen3-next's own
# proven-safe ~71k-token context ceiling (`plans/investigations/
# llm-gateway-context-ceiling-corrected.md` L1'), leaving generous headroom
# for the objective-facts JSON, the system/user instruction text, and the
# model's own completion budget. Caps characters, not tokens -- the selector
# runs before any real token count from the gateway is known; ~4-5 real
# chars/token for this kind of source/prose mix is this project's own
# already-measured ratio for similar payloads (see the context-ceiling doc's
# own correction of an earlier 4-chars/token assumption).
#
# Raised from an initial 45_000 (RPOC-033's own first live dry-run pass):
# against a real, large commercial-grade repository
# (aspose-cells-foss/Aspose.Cells-FOSS-for-Java), 45_000 chars covered only a
# small fraction of the real source tree, and the model -- given
# incomplete context but real prior knowledge of well-known Excel/OOXML
# concepts -- cited several plausible-sounding file paths (WorksheetView.java,
# DataValidation.java, ...) that were never actually shown to it, correctly
# BLOCKED by evidence_fact_candidate() (never a false pass), but not the
# useful, mostly-passing draft this capability aims for. 180_000 chars
# (~40k tokens at this ratio) still leaves comfortable headroom under the
# ~71k-token ceiling for the facts JSON/instructions/repair hints alongside
# it -- a real, evidence-driven correction, not a guess, matching this
# project's own precedent of correcting a too-small budget after finding a
# real confound (`independent-readme-reviewer-route-characterization-
# 2026-07-25`'s own 900 -> 1600 correction).
MAX_CONTEXT_CHARS = 180_000
MAX_FILE_EXCERPT_CHARS = 6_000

# Per-ecosystem source-file glob, keyed by `ProductEntry.ecosystem` (the same
# ecosystems `registry/models.py::MinimalExamplePolicy.language` and
# `facts/local_verification.py::_VERIFIERS` already support, RPOC-034/035).
_ECOSYSTEM_SOURCE_GLOBS: dict[str, tuple[str, ...]] = {
    "java": ("*.java",),
    "net": ("*.cs",),
    "dotnet": ("*.cs",),
    "python": ("*.py",),
    "typescript": ("*.ts",),
    "go": ("*.go",),
    "cpp": ("*.h", "*.hpp", "*.cc", "*.cpp"),
    "rust": ("*.rs",),
}
_DOC_GLOBS = ("*.md", "*.rst")
_CONTEXT_PATH_HEADER = re.compile(r"(?m)^--- (?P<path>.+) ---$")

# Always excluded from what this module shows the model as "already-
# established, citable objective facts": product.audience/problems_solved
# would be self-referential (citing your own claim to ground itself), and
# example.minimal is code, not descriptive text worth citing as grounding
# for anything else. product.capabilities/formats/limitations are
# deliberately NOT excluded here (unlike an earlier version of this filter)
# -- `capabilities/draft_product_truth.py::orchestrate_product_truth_draft()`
# resets those three fields to `missing` in the `facts_so_far` it passes in
# before this module's own caller ever sees them (so a repository's
# pre-existing, already-authored product_truth -- e.g. this project's own
# aspose-cells-foss pilot, used as a live dry-run plausibility anchor --
# never leaks into the prompt as ground truth to copy), then re-populates
# them, ONE repair round later, with THIS SAME draft's own freshly-verified
# capabilities/formats/limitations. That is real, legitimate, independently
# re-checkable grounding material for an audience/problems_solved claim
# (mechanically verified against real repository files, not merely
# asserted) -- and, for the 27 repos with no pre-existing product_truth at
# all (this capability's actual target case), it is very often the ONLY
# rich descriptive vocabulary available at all: the purely mechanical
# objective facts (identity/platforms/license/coordinates/...) rarely
# contain the kind of product-shape language ("workbook", "spreadsheet",
# "XLSX") an audience/problems_solved claim needs to achieve full lexical
# coverage against.
_SELF_REFERENTIAL_FIELDS = frozenset(
    {"product.audience", "product.problems_solved", "example.minimal"}
)


def _draft_language(ecosystem: str | None) -> str:
    """Translate registry ecosystem keys to the typed example-language contract."""
    return "dotnet" if ecosystem == "net" else (ecosystem or "unknown")


class DraftProductTruthV1(BaseModel):
    """See this module's own docstring for why each field type is reused,
    not reinvented, from `facts/interpretive_evidence.py`/`registry/
    models.py`. `extra="forbid"` -- an LLM response carrying an unexpected
    extra key is a schema drift worth failing loudly on, matching
    `specialists/independent_readme_review.py::
    IndependentReadmeReviewResultV1`'s own precedent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    audience: list[InterpretiveClaimV1] = Field(min_length=1, max_length=1)
    problems_solved: list[InterpretiveClaimV1] = Field(min_length=1, max_length=4)
    capabilities: list[EvidenceBackedProductFact] = Field(min_length=1, max_length=8)
    formats: list[EvidenceBackedProductFact] = Field(min_length=1, max_length=8)
    limitations: list[EvidenceBackedProductFact] = Field(default_factory=list, max_length=4)
    minimal_example: MinimalExamplePolicy


def _draft_product_truth_tool_schema(
    *,
    accepted_fact_ids: list[str],
    evidence_paths: list[str],
    language: str,
) -> dict:
    """Bind model identifiers to the exact facts and files supplied in this turn."""

    fact_id_items: dict = {"type": "string", "minLength": 1}
    if accepted_fact_ids:
        fact_id_items["enum"] = accepted_fact_ids
    evidence_path_items: dict = {"type": "string", "minLength": 1}
    if evidence_paths:
        evidence_path_items["enum"] = evidence_paths
    interpretive_claim_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "claim_id": {"type": "string", "minLength": 1},
            "text": {"type": "string", "minLength": 1, "maxLength": 300},
            "supporting_fact_ids": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": fact_id_items,
            },
        },
        "required": ["claim_id", "text", "supporting_fact_ids"],
    }

    def evidence_backed_fact_schema(*, one_anchor: bool = False) -> dict:
        required_symbols: dict = {
            "type": "array",
            "minItems": 1,
            "maxItems": 1 if one_anchor else 4,
            "items": {"type": "string", "minLength": 1},
        }
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "value": {"type": "string", "minLength": 1, "maxLength": 200},
                "evidence_paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 4,
                    "items": evidence_path_items,
                },
                "required_symbols": required_symbols,
            },
            "required": ["value", "evidence_paths", "required_symbols"],
        }

    return {
        "type": "function",
        "function": {
            "name": "submit_product_truth_draft",
            "description": (
                "Submit one repository-grounded product-truth draft for deterministic verification."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "audience": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 1,
                        "items": interpretive_claim_schema,
                    },
                    "problems_solved": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 4,
                        "items": interpretive_claim_schema,
                    },
                    "capabilities": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 8,
                        "items": evidence_backed_fact_schema(one_anchor=True),
                    },
                    "formats": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 8,
                        "items": evidence_backed_fact_schema(),
                    },
                    "limitations": {
                        "type": "array",
                        "maxItems": 4,
                        "items": evidence_backed_fact_schema(),
                    },
                    "minimal_example": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "language": {"type": "string", "enum": [language]},
                            "class_name": {"type": "string", "minLength": 1},
                            "code": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 600,
                            },
                            "evidence_paths": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 4,
                                "items": evidence_path_items,
                            },
                            "required_symbols": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 4,
                                "items": {"type": "string", "minLength": 1},
                            },
                        },
                        "required": [
                            "language",
                            "class_name",
                            "code",
                            "evidence_paths",
                            "required_symbols",
                        ],
                    },
                },
                "required": [
                    "audience",
                    "problems_solved",
                    "capabilities",
                    "formats",
                    "limitations",
                    "minimal_example",
                ],
            },
        },
    }


class _AnalysisClientLike(Protocol):
    def analyze(self, messages: list[dict]) -> AnalysisResult: ...


def _citable_objective_facts(facts_so_far: ProductFactsV2) -> dict:
    """The read-only grounding context shown to the model: every currently-
    selected fact in an accepted verification state (`verified`/
    `policy_approved`), excluding the self-referential fields (see
    `_SELF_REFERENTIAL_FIELDS`'s own docstring). A `missing`/`blocked`/
    `conflicting` fact is deliberately never offered as something to cite --
    citing it would fail `groundedness_fact_candidate()`'s own citation-
    resolution check anyway (`facts/interpretive_evidence.py::
    _resolve_cited_fact()` requires an accepted state), so excluding it here
    saves a wasted attempt rather than relying on the gate to catch it after
    the fact."""
    citable = []
    for field_name in sorted(facts_so_far.selected_fact_ids):
        if field_name in _SELF_REFERENTIAL_FIELDS:
            continue
        fact = facts_so_far.selected_fact(field_name)
        if fact.verification_state not in {"verified", "policy_approved"}:
            continue
        citable.append({"fact_id": fact.fact_id, "field": fact.field, "value": fact.value})
    return {"org_repo": facts_so_far.org_repo, "facts": citable}


def _format_repair_hints(repair_hints: dict[str, list[str]] | None) -> str:
    """Formats `capabilities/draft_product_truth.py`'s own per-field gate-
    failure reasons into the `$repair_hints_section` slot `prompts/
    generation/draft_product_truth.yaml`'s `user_template` declares. Empty
    string (not a section header with nothing under it) when there is
    nothing to repair -- a first attempt should not see a stray "repair
    hints" heading with no content."""
    if not repair_hints:
        return ""
    lines = [
        "\nRepair hints from a prior blocked draft attempt -- fix exactly these "
        "issues, do not repeat them; do not change fields not listed here:"
    ]
    for field_name in sorted(repair_hints):
        lines.append(f"- {field_name}:")
        lines.extend(f"    - {reason}" for reason in repair_hints[field_name])
    return "\n".join(lines) + "\n"


def _is_noise_path(root: Path, path: Path) -> bool:
    return any(part in file_inventory.NOISE_DIRS for part in path.relative_to(root).parts)


def _select_bounded_repo_context(root: Path, ecosystem: str | None) -> str:
    """Simple, deterministic "most relevant files" selector (RPOC-033's own
    scope: "keep this simple, e.g. prioritize files already cited as
    evidence_paths-worthy candidates by file type/location heuristics,
    don't over-engineer"). Prioritizes, in order: the README, the detected
    manifest(s), then real source/doc files matching this repository's
    ecosystem, shallowest-path-first (a top-level public API surface is
    more likely evidence-worthy than a deeply nested internal one) --
    bounded by `MAX_CONTEXT_CHARS` total and `MAX_FILE_EXCERPT_CHARS` per
    file, so one huge file cannot consume the whole budget."""
    inventory = file_inventory.scan(root)
    sections: list[str] = []
    budget = MAX_CONTEXT_CHARS

    def _add(rel_path: str, text: str) -> bool:
        nonlocal budget
        excerpt = text[:MAX_FILE_EXCERPT_CHARS]
        block = f"--- {rel_path} ---\n{excerpt}\n"
        if len(block) > budget:
            return False
        sections.append(block)
        budget -= len(block)
        return True

    def _read(path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            return None

    if inventory.readme_path is not None:
        text = _read(inventory.readme_path)
        if text is not None:
            _add(inventory.readme_path.relative_to(root).as_posix(), text)

    for _ecosystem_name, manifest_path in sorted(inventory.manifest_paths.items()):
        text = _read(manifest_path)
        if text is not None:
            _add(manifest_path.relative_to(root).as_posix(), text)

    candidates: set[Path] = set()
    for pattern in _ECOSYSTEM_SOURCE_GLOBS.get(ecosystem or "", ()):
        candidates.update(root.rglob(pattern))
    for pattern in _DOC_GLOBS:
        candidates.update(root.rglob(pattern))

    already_shown = {inventory.readme_path, *inventory.manifest_paths.values()}
    ordered = sorted(
        (
            path
            for path in candidates
            if path.is_file() and path not in already_shown and not _is_noise_path(root, path)
        ),
        key=lambda path: (len(path.relative_to(root).parts), str(path)),
    )
    for path in ordered:
        if budget <= 0:
            break
        text = _read(path)
        if text is None:
            continue
        _add(path.relative_to(root).as_posix(), text)

    return "".join(sections) if sections else "(no repository context could be read)"


def draft_product_truth(
    org_repo: str,
    *,
    facts_so_far: ProductFactsV2 | None = None,
    repair_hints: dict[str, list[str]] | None = None,
    client: _AnalysisClientLike | None = None,
) -> DraftProductTruthV1:
    """One candidate `product_truth` draft. `facts_so_far`: defaults to a
    fresh `collect_product_facts()` call (this module assembling its own
    objective facts, per this taskcard's own literal instruction) when the
    caller does not already have one; `capabilities/draft_product_truth.py`
    passes its own already-fetched `ProductFactsV2` instead, since it also
    needs the identical object for gating and `collect_product_facts()` can
    trigger a real local build (`facts/local_verification.py`) when a
    policy's `product_truth.minimal_example` already exists -- calling it
    twice per orchestration pass (once per repair attempt) would be
    genuinely wasteful, not just architecturally impure."""
    entry = require_listed(org_repo)
    if facts_so_far is None:
        facts_result = collect_product_facts(org_repo)
        facts_so_far = ProductFactsV2.model_validate(facts_result["product_facts_v2"])

    baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
    clone_baseline(entry, baseline_path)
    repository_context = _select_bounded_repo_context(baseline_path, entry.ecosystem)
    citable_facts = _citable_objective_facts(facts_so_far)
    objective_facts_json = json.dumps(citable_facts, sort_keys=True, default=str)
    draft_language = _draft_language(entry.ecosystem)

    messages = build_draft_product_truth_messages(
        org_repo,
        draft_language,
        objective_facts_json,
        repository_context,
        _format_repair_hints(repair_hints),
    )
    if client is not None:
        result: AnalysisResult = client.analyze(messages)
    else:
        forced_result = LiveForcedToolClient(
            env.llm_base_url(),
            env.llm_api_key(),
            env.llm_model_for_job(_MODEL_ROUTE_JOB),
            timeout=_REQUEST_TIMEOUT_SECONDS,
            max_tokens=_MAX_RESPONSE_TOKENS,
            job=_MODEL_ROUTE_JOB,
            prompt_id="draft_product_truth",
        ).call(
            messages,
            _draft_product_truth_tool_schema(
                accepted_fact_ids=[str(fact["fact_id"]) for fact in citable_facts["facts"]],
                evidence_paths=sorted(
                    match.group("path")
                    for match in _CONTEXT_PATH_HEADER.finditer(repository_context)
                ),
                language=draft_language,
            ),
        )
        result = AnalysisResult(parsed=forced_result.arguments, meta=forced_result.meta)
    try:
        return DraftProductTruthV1.model_validate(result.parsed)
    except ValidationError as exc:
        raise LLMError(
            f"draft_product_truth response for {org_repo} did not match the required "
            f"DraftProductTruthV1 schema: {exc}"
        ) from exc
