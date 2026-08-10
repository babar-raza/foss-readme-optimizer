"""Recognize exact inherited shells governed by deterministic omission policy."""

from __future__ import annotations

import ast
import hashlib
import re
from collections.abc import Iterable
from pathlib import PurePosixPath

from markdown_it import MarkdownIt

from readme_agent.facts.curated_python_fixture_inventory import SnapshotFixtureInventoryV1
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    SourceClaimResolutionV1,
)
from readme_agent.readme.presentation_lint_text import strip_emoji_decorations
from readme_agent.readme.source_claim_capability_binding import public_api_feature_is_anchored
from readme_agent.readme.source_claim_risk import SourceClaimRiskV1


def exact_authorized_claim_ids(
    source_text: str,
    claims: list[ReadmeMaterialClaimAssessmentV1],
    ranges: Iterable[tuple[int, int]],
    *,
    authority: str,
) -> frozenset[str]:
    """Bind an authority range only when it equals one complete assessed claim."""

    supplied = list(ranges)
    if len(supplied) != len(set(supplied)):
        raise ValueError(f"{authority} claim ranges contain duplicates")
    claims_by_range: dict[tuple[int, int], frozenset[str]] = {
        (claim.source_byte_start, claim.source_byte_end): frozenset({claim.claim_id})
        for claim in claims
    }
    unknown = sorted(set(supplied) - claims_by_range.keys())
    if unknown:
        raise ValueError(f"{authority} claim range is partial, spoofed, or stale: {unknown[0]}")
    return frozenset(claim_id for item in supplied for claim_id in claims_by_range[item])


def deferred_withheld_source_resolution(
    claim: ReadmeMaterialClaimAssessmentV1,
    claim_text: str,
    candidate_bytes: bytes,
    risk: SourceClaimRiskV1,
    *,
    correction_candidate_claim_ids: frozenset[str],
    extra_evidence: Iterable[str] = (),
) -> SourceClaimResolutionV1 | None:
    """Return an exact deferred disposition only for an authorized optional claim."""

    if (
        claim.claim_id not in correction_candidate_claim_ids
        or risk.risk_class != "optional_explicit_deferral"
    ):
        return None
    claim_hash = hashlib.sha256(claim_text.encode("utf-8")).hexdigest()
    if claim_hash != claim.content_sha256:
        raise ValueError("withheld source claim bytes do not match the assessed claim hash")
    candidate_hash = hashlib.sha256(candidate_bytes).hexdigest()
    return SourceClaimResolutionV1(
        claim_id=claim.claim_id,
        source_byte_start=claim.source_byte_start,
        source_byte_end=claim.source_byte_end,
        content_sha256=claim.content_sha256,
        resolution="deferred_verification",
        evidence=[
            f"source-claim:{claim.claim_id}",
            f"source-content-sha256:{claim.content_sha256}",
            f"candidate-content-sha256:{candidate_hash}",
            "authority:verified-source-assurance:correction-candidate",
            "risk-policy:optional-inherited-detail-deferred-v1",
            *extra_evidence,
        ],
        rationale=risk.rationale,
    )


def deferred_unverified_obligation_detail_resolution(
    claim: ReadmeMaterialClaimAssessmentV1,
    claim_text: str,
    candidate_bytes: bytes,
    risk: SourceClaimRiskV1,
    facts: ProductFactsV2,
    *,
    correction_candidate_claim_ids: frozenset[str],
    candidate_core_present: bool,
) -> SourceClaimResolutionV1 | None:
    """Defer unsupported source detail only after the verified core slot exists."""

    if (
        claim.claim_id not in correction_candidate_claim_ids
        or risk.risk_class != "mandatory_fact_resolution"
        or risk.obligation_id
        not in {"api_public_surface", "major_capabilities", "product_overview"}
        or not candidate_core_present
    ):
        return None
    if risk.obligation_id == "major_capabilities" and not _capability_anchor_matches(
        claim_text, facts
    ):
        return None
    if hashlib.sha256(claim_text.encode("utf-8")).hexdigest() != claim.content_sha256:
        raise ValueError("deferred source detail bytes do not match the assessed claim hash")
    return SourceClaimResolutionV1(
        claim_id=claim.claim_id,
        source_byte_start=claim.source_byte_start,
        source_byte_end=claim.source_byte_end,
        content_sha256=claim.content_sha256,
        resolution="deferred_verification",
        evidence=[
            f"source-claim:{claim.claim_id}",
            f"source-content-sha256:{claim.content_sha256}",
            f"candidate-content-sha256:{hashlib.sha256(candidate_bytes).hexdigest()}",
            f"unverified-source-detail-for:{risk.obligation_id}",
            "candidate-core-validated-separately",
            "disposition:withheld-pending-repository-verification-v1",
        ],
        rationale=(
            "Withhold this exact inherited detail because repository evidence does not yet "
            "prove its complete wording. The candidate independently satisfies the required "
            f"{risk.obligation_id} slot with accepted facts; this source claim remains visible "
            "as deferred evidence and is not treated as false or verified."
        ),
    )


_CAPABILITY_GENERIC_WORDS = {
    "and",
    "aspose",
    "based",
    "content",
    "for",
    "format",
    "from",
    "future",
    "including",
    "like",
    "on",
    "the",
    "unverified",
    "via",
    "with",
}


def _capability_words(value: str) -> set[str]:
    visible_text = re.sub(r"\]\([^)]+\)", "]", strip_emoji_decorations(value))
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", visible_text)
    return {
        word[:-1] if word.endswith("s") and len(word) > 4 else word
        for word in re.findall(r"[A-Za-z0-9]+", expanded.casefold())
        if word not in _CAPABILITY_GENERIC_WORDS
    }


def _capability_anchor_matches(claim_text: str, facts: ProductFactsV2) -> bool:
    if public_api_feature_is_anchored(claim_text, facts):
        return True
    fact_id = facts.selected_fact_ids.get("product.capabilities")
    if fact_id is None:
        return False
    fact = facts.fact_by_id(fact_id)
    if (
        fact.verification_state not in {"verified", "policy_approved"}
        or fact.has_unresolved_conflict
        or not isinstance(fact.value, list)
    ):
        return False
    claim_words = _capability_words(claim_text)
    claim_numbers = {word for word in claim_words if word.isdigit()}
    capability_word_sets = [_capability_words(str(value)) for value in fact.value]
    if (
        re.search(r"(?m)^\s*\|.*\|\s*$", claim_text)
        and sum(
            bool(
                (claim_words - claim_numbers).intersection(
                    words - {word for word in words if word.isdigit()}
                )
            )
            for words in capability_word_sets
        )
        >= 2
    ):
        # A multi-row table commonly carries unverified per-row qualifiers and
        # numbers. Two independently accepted capability anchors are enough to
        # classify the exact table as related detail for explicit deferral;
        # they do not verify or publish the table itself.
        return True
    normalized_claim = " ".join(
        re.findall(r"[a-z]+", strip_emoji_decorations(claim_text).casefold())
    ).removeprefix("content ")
    generic_content_group = normalized_claim == "extraction"
    for value, fact_words in zip(fact.value, capability_word_sets, strict=True):
        if generic_content_group and "content" in str(value).casefold():
            return True
        if claim_numbers - fact_words:
            continue
        if claim_words.intersection(fact_words):
            return True
    return False


_INPUT_METHODS = frozenset({"from_file", "import_file", "load", "load_from", "open", "read"})


def _python_fence_content(claim_text: str) -> str | None:
    tokens = MarkdownIt("commonmark").parse(claim_text)
    material = [
        token for token in tokens if token.type not in {"paragraph_open", "paragraph_close"}
    ]
    if len(material) != 1 or material[0].type != "fence":
        return None
    token = material[0]
    if token.info.strip().casefold() not in {"py", "python"}:
        return None
    return token.content.rstrip()


def _literal_input_assets(code: str) -> tuple[str, ...]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ()
    references: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        method: str | None = None
        if isinstance(node.func, ast.Attribute):
            method = node.func.attr
        elif isinstance(node.func, ast.Name):
            method = node.func.id
        if method not in _INPUT_METHODS:
            continue
        argument = node.args[0]
        if not isinstance(argument, ast.Constant) or not isinstance(argument.value, str):
            continue
        if method == "open" and isinstance(node.func, ast.Name) and len(node.args) > 1:
            mode = node.args[1]
            if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
                if any(flag in mode.value for flag in "wax+"):
                    continue
        reference = argument.value.replace("\\", "/").removeprefix("./")
        path = PurePosixPath(reference)
        if not reference or path.is_absolute() or ".." in path.parts or "://" in reference:
            continue
        references.add(reference)
    return tuple(sorted(references))


def deferred_unverified_source_example_resolution(
    claim: ReadmeMaterialClaimAssessmentV1,
    claim_text: str,
    source_text: str,
    candidate_bytes: bytes,
    risk: SourceClaimRiskV1,
    facts: ProductFactsV2,
    accepted_primary: tuple[list[CandidateContentProvenanceV1], list[str]] | None,
    *,
    correction_candidate_claim_ids: frozenset[str],
) -> SourceClaimResolutionV1 | None:
    """Defer one static-only inherited example when its exact input asset is absent."""

    if (
        claim.claim_id not in correction_candidate_claim_ids
        or risk.risk_class != "mandatory_fact_resolution"
        or risk.obligation_id != "primary_example"
        or accepted_primary is None
    ):
        return None
    claim_hash = hashlib.sha256(claim_text.encode("utf-8")).hexdigest()
    if claim_hash != claim.content_sha256:
        raise ValueError("source example bytes do not match the assessed claim hash")
    code = _python_fence_content(claim_text)
    if code is None or code.encode("utf-8") in candidate_bytes:
        return None
    examples_id = facts.selected_fact_ids.get("repository.examples")
    minimal_id = facts.selected_fact_ids.get("example.minimal")
    if examples_id is None or minimal_id is None:
        return None
    examples = facts.fact_by_id(examples_id)
    minimal = facts.fact_by_id(minimal_id)
    if (
        examples.verification_state != "verified"
        or examples.has_unresolved_conflict
        or examples.source.source_revision is None
        or not isinstance(examples.value, dict)
        or minimal.verification_state not in {"verified", "policy_approved"}
        or minimal.has_unresolved_conflict
        or not isinstance(minimal.value, dict)
        or minimal.value.get("verification_outcome")
        not in {"SOURCE_BUILD_VERIFIED", "SOURCE_TREE_VERIFIED"}
    ):
        return None
    source_readme_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    if examples.value.get("readme_sha256") != source_readme_hash:
        return None
    inline_examples = examples.value.get("inline_examples")
    withheld_examples = examples.value.get("withheld_inline_examples")
    if not isinstance(inline_examples, list) or not isinstance(withheld_examples, list):
        return None
    exact = [
        item
        for item in [*inline_examples, *withheld_examples]
        if isinstance(item, dict) and item.get("code") == code
    ]
    if len(exact) != 1:
        return None
    example = exact[0]
    static_decision_recorded = example.get("static_api_verified") is True or (
        example.get("static_api_verified") is False
        and isinstance(example.get("validation_reason"), str)
        and bool(str(example["validation_reason"]).strip())
    )
    if not static_decision_recorded or example.get("execution_verified") is not False:
        return None
    raw_inventory = examples.value.get("fixture_inventory")
    try:
        inventory = SnapshotFixtureInventoryV1.model_validate(raw_inventory)
    except (TypeError, ValueError):
        return None
    if (
        inventory.scan_status != "complete"
        or inventory.source_revision != examples.source.source_revision
        or inventory.inventory_sha256 is None
        or inventory.tree_id is None
    ):
        return None
    references = _literal_input_assets(code)
    recognized = set(inventory.recognized_extensions)
    if not references or any(
        PurePosixPath(item).suffix.casefold() not in recognized for item in references
    ):
        return None
    if any(inventory.matching_paths(reference) for reference in references):
        return None
    bindings, replacement_fact_ids = accepted_primary
    if minimal_id not in replacement_fact_ids:
        return None
    replacement_ids = sorted(binding.provenance_id for binding in bindings)
    candidate_hash = hashlib.sha256(candidate_bytes).hexdigest()
    fact_ids = sorted({examples_id, *replacement_fact_ids})
    return SourceClaimResolutionV1(
        claim_id=claim.claim_id,
        source_byte_start=claim.source_byte_start,
        source_byte_end=claim.source_byte_end,
        content_sha256=claim.content_sha256,
        resolution="verified_omission",
        obligation_id="primary_example",
        fact_ids=fact_ids,
        replacement_provenance_ids=replacement_ids,
        evidence=[
            f"source-claim:{claim.claim_id}",
            f"source-content-sha256:{claim.content_sha256}",
            f"source-readme-sha256:{source_readme_hash}",
            f"candidate-content-sha256:{candidate_hash}",
            f"snapshot-revision:{inventory.source_revision}",
            f"snapshot-tree:{inventory.tree_id}",
            f"snapshot-inventory-sha256:{inventory.inventory_sha256}",
            *(f"absent-input-fixture:{item}" for item in references),
            *(f"accepted-fact:{item}" for item in fact_ids),
            *(f"candidate-provenance:{item}" for item in replacement_ids),
            "disposition:static-only-source-example-deferred-v1",
        ],
        rationale=(
            "The exact inherited Python example has a recorded static validation decision but "
            "is not execution-verified, and its literal input fixture is absent from the "
            "complete immutable Git "
            "tree. It is deferred without claiming falsity or execution; the candidate primary "
            "example is independently source-build verified."
        ),
    )


def verified_paired_example_intro_resolution(
    claim: ReadmeMaterialClaimAssessmentV1,
    claim_text: str,
    paired_claim: ReadmeMaterialClaimAssessmentV1 | None,
    paired_claim_text: str | None,
    source_text: str,
    risk: SourceClaimRiskV1,
    facts: ProductFactsV2,
    accepted_primary: tuple[list[CandidateContentProvenanceV1], list[str]] | None,
    paired_resolution: SourceClaimResolutionV1 | None,
    *,
    correction_candidate_claim_ids: frozenset[str],
) -> SourceClaimResolutionV1 | None:
    """Omit one exact example intro only when its adjacent example remains fact-bound."""

    if (
        claim.claim_id not in correction_candidate_claim_ids
        or risk.risk_class != "mandatory_fact_resolution"
        or risk.obligation_id != "primary_example"
        or accepted_primary is None
        or paired_claim is None
        or paired_claim_text is None
        or paired_resolution is None
        or paired_resolution.resolution not in {"verified_equivalence", "verified_omission"}
    ):
        return None
    if hashlib.sha256(claim_text.encode("utf-8")).hexdigest() != claim.content_sha256:
        raise ValueError("source example intro bytes do not match the assessed claim hash")
    tokens = MarkdownIt("commonmark").parse(claim_text)
    if (
        [token.type for token in tokens] != ["paragraph_open", "inline", "paragraph_close"]
        or not claim_text.rstrip().endswith(":")
        or _python_fence_content(paired_claim_text) is None
    ):
        return None
    source_bytes = source_text.encode("utf-8")
    if (
        paired_claim.source_byte_start < claim.source_byte_end
        or source_bytes[claim.source_byte_end : paired_claim.source_byte_start].strip()
    ):
        return None
    examples_id = facts.selected_fact_ids.get("repository.examples")
    minimal_id = facts.selected_fact_ids.get("example.minimal")
    if examples_id is None or minimal_id is None or examples_id not in paired_resolution.fact_ids:
        return None
    bindings, replacement_fact_ids = accepted_primary
    if minimal_id not in replacement_fact_ids:
        return None
    replacement_ids = sorted(binding.provenance_id for binding in bindings)
    fact_ids = sorted(replacement_fact_ids)
    return SourceClaimResolutionV1(
        claim_id=claim.claim_id,
        source_byte_start=claim.source_byte_start,
        source_byte_end=claim.source_byte_end,
        content_sha256=claim.content_sha256,
        resolution="verified_omission",
        obligation_id="primary_example",
        fact_ids=fact_ids,
        replacement_provenance_ids=replacement_ids,
        evidence=[
            f"source-claim:{claim.claim_id}",
            f"source-content-sha256:{claim.content_sha256}",
            f"paired-source-claim:{paired_claim.claim_id}",
            f"paired-candidate-claim:{paired_resolution.candidate_claim_id}",
            f"paired-accepted-fact:{examples_id}",
            *(f"accepted-fact:{item}" for item in fact_ids),
            *(f"candidate-provenance:{item}" for item in replacement_ids),
            "disposition:paired-example-intro-superseded-v1",
        ],
        rationale=(
            "The exact inherited sentence only introduces the immediately adjacent Python "
            "example. That example remains independently fact-bound in the candidate, while the "
            "primary quick start is source-build verified; omitting the redundant intro loses no "
            "product claim."
        ),
    )


def governed_source_omission(claim_text: str) -> tuple[str, str] | None:
    """Return the evidence kind and rationale for one governed legacy shell."""

    folded = claim_text.strip().casefold()
    if re.search(r"official\s+aspose\s+project|100\s*%\s+free", folded):
        return (
            "presentation-policy-correction",
            "Omit this exact promotional source unit under the product-first presentation "
            "contract; replacement content is separately fact-bound.",
        )
    if folded.startswith("quick links:"):
        return (
            "redundant-navigation-shell",
            "Omit this exact quick-link shell because the compiled candidate contains one "
            "complete list-based Navigation section.",
        )
    if folded.startswith("[![ci]"):
        return (
            "superseded-badge-shell",
            "Replace this exact inherited badge shell with the one-row fact-bound badge set.",
        )
    if folded.startswith("pypi release page (maintainers):"):
        return (
            "maintainer-only-link",
            "Omit this exact maintainer-only release-management URL.",
        )
    return None


__all__ = [
    "deferred_unverified_obligation_detail_resolution",
    "deferred_unverified_source_example_resolution",
    "deferred_withheld_source_resolution",
    "exact_authorized_claim_ids",
    "governed_source_omission",
    "verified_paired_example_intro_resolution",
]
