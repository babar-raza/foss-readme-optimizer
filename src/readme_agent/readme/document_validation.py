"""Independently reconstruct and validate a complete README document candidate."""

from __future__ import annotations

import hashlib
import re

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field

from readme_agent.facts.example_quality import source_contains_comments
from readme_agent.facts.protected_content import (
    fingerprint_protected_content,
    protected_fragment_ids_overlapping_byte_span,
    validate_protected_content,
)
from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1
from readme_agent.links.contextual_validation import validate_contextual_link_candidate
from readme_agent.links.terminology import find_enterprise_terminology_findings
from readme_agent.readme.claim_accountability_validation import (
    validate_claim_accountability_map,
)
from readme_agent.readme.document_plan import ReadmeDocumentPlanV1
from readme_agent.readme.document_renderer import (
    apply_document_operations,
    document_template_hash,
)
from readme_agent.readme.document_structure import introduced_duplicate_headings
from readme_agent.readme.document_terminology import enterprise_product_name
from readme_agent.readme.example_assurance_validation import (
    unsupported_example_assurance_claims,
)
from readme_agent.readme.header_visual_validation import validate_readme_header_visual
from readme_agent.readme.limitation_validation import verified_limitations_are_represented
from readme_agent.readme.markers import find_presentation_span
from readme_agent.readme.presentation_lint import lint_readme_presentation
from readme_agent.readme.presentation_lint_models import PresentationLintFindingV1

_ACCEPTED_STATES = {"verified", "policy_approved"}
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


class DocumentCandidateValidationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    valid: bool
    checks: dict[str, bool]
    errors: list[str] = Field(default_factory=list)
    authorized_protected_corrections: list[str] = Field(default_factory=list)
    deferred_source_claim_ids: list[str] = Field(default_factory=list)
    presentation_findings: list[PresentationLintFindingV1] = Field(default_factory=list)


def _sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _text_value(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item).rstrip(".") + "." for item in value)
    return str(value)


def _text_fragments(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).rstrip(".") for item in value if str(item).strip()]
    text = str(value).rstrip(".")
    return [text] if text else []


def _accepted(facts: ProductFactsV2, field_name: str):
    fact = facts.selected_fact(field_name)
    if fact.verification_state not in _ACCEPTED_STATES or fact.has_unresolved_conflict:
        return None
    return fact


def accepted_fact_is_represented(
    fact: FactRecordV2 | None,
    candidate_text: str,
    represented_fact_ids: set[str],
) -> bool:
    """Accept exact prose or an explicitly recorded supporting-fact representation."""

    if fact is None:
        return True
    evidence_ids = {fact.fact_id, *fact.supporting_fact_ids}
    return bool(evidence_ids & represented_fact_ids) or any(
        fragment in candidate_text for fragment in _text_fragments(fact.value)
    )


def _comment_failures(candidate_text: str) -> list[str]:
    failures = ["README contains an HTML comment"] if _HTML_COMMENT.search(candidate_text) else []
    for token in MarkdownIt("commonmark").parse(candidate_text):
        if token.type != "fence":
            continue
        language = token.info.strip().split(maxsplit=1)[0]
        if (
            language
            and language.casefold() != "mermaid"
            and source_contains_comments(language, token.content)
        ):
            line = token.map[0] + 1 if token.map is not None else "unknown"
            failures.append(
                f"README contains a source comment in the {language} fence at line {line}"
            )
    return failures


def validate_readme_document_candidate(
    original_text: str,
    candidate_text: str,
    plan: ReadmeDocumentPlanV1,
    facts: ProductFactsV2,
    *,
    link_catalogs: AsposeLinkCatalogSetV1 | None = None,
) -> DocumentCandidateValidationV1:
    """Reject stale spans, uncited corrections, reconstruction drift, and protected loss."""

    errors: list[str] = []
    checks: dict[str, bool] = {}
    source_span = find_presentation_span(original_text)
    source_inner = source_span.content if source_span is not None else original_text
    source = source_inner.encode("utf-8")
    candidate_span = find_presentation_span(candidate_text)
    candidate_inner = candidate_span.content if candidate_span is not None else candidate_text
    candidate_inner_bytes = candidate_inner.encode("utf-8")
    source_fingerprint = fingerprint_protected_content(source_inner)

    checks["source_document_hash"] = _sha256(original_text) == plan.source_sha256
    checks["adoption_preserved_source"] = (
        _sha256(source) == plan.adoption.source_inner_sha256
        and len(source) == plan.adoption.source_inner_bytes
    )
    checks["candidate_is_marker_free"] = (
        "<!-- readme-agent:" not in candidate_text and "readme-agent" not in candidate_text
    )
    comment_failures = _comment_failures(candidate_text)
    checks["candidate_has_no_comments"] = not comment_failures
    checks["facts_hash_matches"] = plan.facts_hash == facts.canonical_hash()
    checks["template_hash_matches"] = plan.template_sha256 == document_template_hash()
    checks["candidate_hash_matches"] = _sha256(candidate_text) == plan.candidate_sha256

    for name, passed in checks.items():
        if not passed:
            errors.append(f"{name} failed")
    errors.extend(comment_failures)

    citations_valid = True
    span_hashes_valid = True
    authorized_fragment_ids: set[str] = set()
    source_operations = [
        operation
        for operation in plan.operations
        if operation.coordinate_space == "presentation_inner_utf8"
    ]
    preliminary_candidate = apply_document_operations(source, source_operations)
    for operation in plan.operations:
        coordinate_document = (
            source
            if operation.coordinate_space == "presentation_inner_utf8"
            else preliminary_candidate
        )
        selected = coordinate_document[operation.source_byte_start : operation.source_byte_end]
        if _sha256(selected) != operation.expected_sha256:
            span_hashes_valid = False
            errors.append(f"{operation.operation_id}: source span hash changed")
        if _sha256(operation.replacement_text) != operation.replacement_sha256:
            span_hashes_valid = False
            errors.append(f"{operation.operation_id}: replacement hash changed")
        for fact_id in operation.fact_ids:
            try:
                fact = facts.fact_by_id(fact_id)
            except KeyError:
                citations_valid = False
                errors.append(f"{operation.operation_id}: unknown fact {fact_id}")
                continue
            if facts.selected_fact_ids.get(fact.field) != fact_id:
                citations_valid = False
                errors.append(f"{operation.operation_id}: {fact_id} is not selected")
            if fact.verification_state not in _ACCEPTED_STATES or fact.has_unresolved_conflict:
                citations_valid = False
                errors.append(f"{operation.operation_id}: {fact_id} is {fact.verification_state}")
        if (
            operation.coordinate_space == "presentation_inner_utf8"
            and operation.protected_content_treatment == "authoritative_fact_correction"
        ):
            authorized_fragment_ids.update(
                protected_fragment_ids_overlapping_byte_span(
                    source_inner,
                    operation.source_byte_start,
                    operation.source_byte_end,
                )
            )
        if (
            operation.coordinate_space == "presentation_inner_utf8"
            and operation.protected_content_treatment == "presentation_policy_correction"
            and operation.replacement_text.lstrip().startswith("#")
        ):
            overlapping = protected_fragment_ids_overlapping_byte_span(
                source_inner,
                operation.source_byte_start,
                operation.source_byte_end,
            )
            authorized_fragment_ids.update(
                fragment.fragment_id
                for fragment in source_fingerprint.fragments
                if fragment.fragment_id in overlapping
                and fragment.source_descriptor.startswith("markdown:heading:")
            )
        if (
            operation.coordinate_space == "presentation_inner_utf8"
            and operation.protected_content_treatment == "presentation_policy_correction"
            and operation.operation_id.startswith("readme.comments.remove-")
            and not operation.replacement_text
        ):
            authorized_fragment_ids.update(
                protected_fragment_ids_overlapping_byte_span(
                    source_inner,
                    operation.source_byte_start,
                    operation.source_byte_end,
                )
            )

    for resolution in plan.source_claim_resolutions:
        authorized_fragment_ids.update(
            protected_fragment_ids_overlapping_byte_span(
                source_inner,
                resolution.source_byte_start,
                resolution.source_byte_end,
            )
        )

    checks["source_span_hashes"] = span_hashes_valid
    checks["fact_citations"] = citations_valid

    reconstructed = apply_document_operations(source, plan.operations)
    checks["document_reconstruction"] = reconstructed == candidate_inner_bytes
    if not checks["document_reconstruction"]:
        errors.append("candidate inner bytes do not reconstruct from the document plan")

    protected = validate_protected_content(
        source_fingerprint,
        fingerprint_protected_content(candidate_inner),
        require_maintainer_region_unchanged=False,
    )
    unauthorized_losses = [
        loss for loss in protected.losses if loss.fragment_id not in authorized_fragment_ids
    ]
    checks["protected_content"] = not unauthorized_losses
    errors.extend(
        f"unauthorized protected-content loss: {loss.fragment_id}" for loss in unauthorized_losses
    )

    selected_example = facts.selected_fact("example.minimal")
    example = _accepted(facts, "example.minimal")
    example_value = selected_example.value if isinstance(selected_example.value, dict) else {}
    exact_example = str(example_value.get("code", "")).rstrip()
    example_is_present = bool(exact_example and exact_example in candidate_inner)
    # A narrowly blocked example may be omitted while unrelated README work
    # continues. It may never be rendered, though: its code is still untrusted
    # even when a candidate operation did not cite the blocked fact ID.
    checks["verified_example_present"] = (
        example_is_present if example is not None and exact_example else not example_is_present
    )
    if not checks["verified_example_present"]:
        errors.append(
            "selected verified minimal example is absent"
            if example is not None
            else "selected unverified minimal example is present"
        )
    audience_view = visitor_fact_render_view(facts, "product.audience")
    audience = _accepted(facts, "product.audience")
    problem = _accepted(facts, "product.problems_solved")
    represented_fact_ids = set(
        plan.header_visuals.diagram_fact_ids if plan.header_visuals is not None else []
    )
    represented_fact_ids.update(
        fact_id for binding in plan.candidate_content_provenance for fact_id in binding.fact_ids
    )
    audience_present = (
        audience_view is None
        or any(phrase.rstrip(".") in candidate_inner for phrase in audience_view.phrases)
        or accepted_fact_is_represented(
            audience,
            candidate_inner,
            represented_fact_ids,
        )
    )
    problem_present = accepted_fact_is_represented(
        problem,
        candidate_inner,
        represented_fact_ids,
    )
    checks["verified_overview_present"] = audience_present and problem_present
    if not checks["verified_overview_present"]:
        errors.append("fact-backed audience/problem overview is absent")

    checks["verified_limitations_present"] = verified_limitations_are_represented(
        facts,
        candidate_inner,
    )
    if not checks["verified_limitations_present"]:
        errors.append("selected verified limitations are absent")

    unsupported_assurances = unsupported_example_assurance_claims(
        candidate_inner,
        facts,
        plan.candidate_content_provenance,
    )
    checks["example_assurance_claims_supported"] = not unsupported_assurances
    errors.extend(
        f"unsupported example assurance claim: {claim_id}" for claim_id in unsupported_assurances
    )

    duplicate_headings = introduced_duplicate_headings(source_inner, candidate_inner)
    checks["no_introduced_duplicate_headings"] = not duplicate_headings
    if duplicate_headings:
        errors.append(f"candidate introduced duplicate headings: {duplicate_headings}")

    if plan.header_visuals is not None:
        header_visuals = validate_readme_header_visual(
            plan.header_visuals,
            facts,
            candidate_text=candidate_text,
        )
        checks["header_visuals"] = (
            header_visuals.valid
            and plan.header_visuals.mermaid_markdown in candidate_text
            and candidate_text.count(plan.header_visuals.mermaid_markdown) == 1
        )
        errors.extend(header_visuals.errors)
        if not checks["header_visuals"]:
            errors.append("fact-backed README header or Mermaid diagram is absent")
    else:
        checks["header_visuals"] = False
        errors.append("fact-backed README header and Mermaid plan is absent")

    product_name = enterprise_product_name(facts)
    terminology_findings = (
        find_enterprise_terminology_findings(
            candidate_inner,
            enterprise_product_name=product_name,
        )
        if product_name is not None
        else []
    )
    checks["enterprise_edition_terminology"] = not terminology_findings
    errors.extend(
        f"prohibited Enterprise terminology: {finding.excerpt}" for finding in terminology_findings
    )
    if plan.contextual_links is not None:
        if link_catalogs is None:
            checks["contextual_links"] = False
            errors.append("contextual-link plan cannot be verified without its catalogs")
        else:
            contextual = validate_contextual_link_candidate(
                plan.contextual_links,
                link_catalogs,
                candidate_inner,
                facts,
            )
            checks["contextual_links"] = contextual.valid
            errors.extend(contextual.errors)
    else:
        checks["contextual_links"] = True

    if plan.claim_accountability is None:
        checks["claim_accountability_complete"] = False
        errors.append("complete inherited/generated claim-accountability map is absent")
    else:
        accountability = validate_claim_accountability_map(
            plan.claim_accountability,
            source_text=source_inner,
            candidate_text=candidate_inner,
            facts=facts,
            operations=plan.operations,
            candidate_content_provenance=plan.candidate_content_provenance,
            source_claim_resolutions=plan.source_claim_resolutions,
        )
        checks["claim_accountability_complete"] = accountability.approval_eligible
        checks["claim_accountability_gaps_visible"] = accountability.approval_eligible or bool(
            accountability.blocking_claim_ids
        )
        errors.extend(accountability.errors)
        if accountability.blocking_claim_ids:
            preview = ", ".join(accountability.blocking_claim_ids[:10])
            errors.append(
                "claim accountability has "
                f"{len(accountability.blocking_claim_ids)} blocking claim(s): {preview}"
            )

    presentation_lint = lint_readme_presentation(candidate_inner, facts)
    checks["presentation_lint"] = presentation_lint.valid
    errors.extend(
        f"{finding.finding_id}: {finding.message}" for finding in presentation_lint.findings
    )

    return DocumentCandidateValidationV1(
        valid=not errors,
        checks=checks,
        errors=errors,
        authorized_protected_corrections=sorted(authorized_fragment_ids),
        deferred_source_claim_ids=sorted(
            resolution.claim_id
            for resolution in plan.source_claim_resolutions
            if resolution.resolution == "deferred_verification"
        ),
        presentation_findings=presentation_lint.findings,
    )
