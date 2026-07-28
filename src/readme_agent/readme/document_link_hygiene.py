"""Remove unbound Aspose URLs while preserving their visitor-facing text."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.links.allocation import code_sha256, resolve_link_budget
from readme_agent.links.catalog import lookup_verified_target, normalize_target_url
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.registry.models import LinkAllocationPolicyV1

AsposeLinkForm = Literal["image", "markdown", "html", "autolink", "raw"]
_URL = r"https?://(?:[a-z0-9-]+\.)*aspose\.(?:com|org)(?:/[^\s<>)\"']*)?"
_FENCED_CODE = re.compile(
    r"(?ms)^(?P<fence>`{3,}|~{3,})[^\r\n]*\r?\n.*?^(?P=fence)[ \t]*(?:\r?\n|$)"
)
_INLINE_CODE = re.compile(r"`+[^`\r\n]+`+")
_PATTERNS: tuple[tuple[AsposeLinkForm, re.Pattern[str], int | None], ...] = (
    (
        "image",
        re.compile(rf"!\[([^\]\n]*)\]\(({_URL})(?:\s+[\"'][^\"']*[\"'])?\)", re.IGNORECASE),
        1,
    ),
    (
        "markdown",
        re.compile(rf"(?<!!)\[([^\]\n]+)\]\(({_URL})(?:\s+[\"'][^\"']*[\"'])?\)", re.IGNORECASE),
        1,
    ),
    (
        "html",
        re.compile(rf"(?:href|src)\s*=\s*([\"']){_URL}\1", re.IGNORECASE),
        None,
    ),
    ("autolink", re.compile(rf"<{_URL}>", re.IGNORECASE), None),
    ("raw", re.compile(_URL, re.IGNORECASE), None),
)


class AsposeLinkRewriteV1(BaseModel):
    """One exact untrusted-link rewrite in a candidate or source span."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    form: AsposeLinkForm
    character_start: int
    character_end: int
    original: str
    replacement: str


def remove_unbound_aspose_links(markdown: str) -> tuple[str, list[AsposeLinkRewriteV1]]:
    """Unwrap every Aspose target, retaining Markdown labels and image alt text."""

    rewrites: list[AsposeLinkRewriteV1] = []
    occupied: list[tuple[int, int]] = []
    protected = [
        match.span()
        for pattern in (_FENCED_CODE, _INLINE_CODE)
        for match in pattern.finditer(markdown)
    ]
    for form, pattern, label_group in _PATTERNS:
        for match in pattern.finditer(markdown):
            start, end = match.span()
            if any(
                start < protected_end and protected_start < end
                for protected_start, protected_end in protected
            ):
                continue
            if any(
                start < occupied_end and occupied_start < end
                for occupied_start, occupied_end in occupied
            ):
                continue
            replacement = match.group(label_group) if label_group is not None else ""
            rewrites.append(
                AsposeLinkRewriteV1(
                    form=form,
                    character_start=start,
                    character_end=end,
                    original=match.group(0),
                    replacement=replacement,
                )
            )
            occupied.append((start, end))
    rendered = markdown
    for rewrite in sorted(rewrites, key=lambda item: item.character_start, reverse=True):
        rendered = (
            rendered[: rewrite.character_start]
            + rewrite.replacement
            + rendered[rewrite.character_end :]
        )
    return rendered, sorted(rewrites, key=lambda item: item.character_start)


def _overlaps(
    start: int,
    end: int,
    operations: list[ReadmeDocumentOperationV1],
) -> bool:
    return any(
        operation.source_byte_start < end and start < operation.source_byte_end
        for operation in operations
    )


def _retained_product_spans(
    context: DocumentRenderContext,
    rewrites: list[AsposeLinkRewriteV1],
    existing_operations: list[ReadmeDocumentOperationV1],
    catalogs: AsposeLinkCatalogSetV1,
    policy: LinkAllocationPolicyV1,
) -> set[tuple[int, int]]:
    """Keep only distinct, verified product targets that fit the reserved budget."""

    example = context.facts.selected_fact("example.minimal")
    value = example.value if isinstance(example.value, dict) else {}
    code = str(value.get("code") or "").strip()
    budget = resolve_link_budget(
        policy,
        context.inner_text,
        verified_code_sha256s={code_sha256(code)} if code else set(),
    )
    identity = context.facts.selected_fact("product.identity")
    identity_value = identity.value if isinstance(identity.value, dict) else {}
    platform = str(
        identity_value.get("platform") or identity_value.get("ecosystem") or ""
    ).casefold()
    first_h2 = next((heading for heading in context.headings if heading.level == 2), None)
    first_h2_start = first_h2.start if first_h2 is not None else len(context.inner_text)
    resources = context.h2("Resources")
    candidates: list[tuple[tuple, AsposeLinkRewriteV1, str, str]] = []
    for index, rewrite in enumerate(rewrites):
        target_match = re.search(_URL, rewrite.original, re.IGNORECASE)
        if target_match is None or rewrite.character_start < first_h2_start:
            continue
        start = context.byte_offset(rewrite.character_start)
        end = context.byte_offset(rewrite.character_end)
        if _overlaps(start, end, existing_operations):
            continue
        target = target_match.group(0)
        record = lookup_verified_target(catalogs, target)
        if record is None or not record.linkable or record.surface != "products":
            continue
        in_resources = bool(
            resources is not None
            and resources.heading_end <= rewrite.character_start < resources.section_end
        )
        candidates.append(
            (
                (
                    1 if in_resources else 0,
                    0 if platform in record.platforms else 1,
                    0 if record.parent_domain == "aspose.org" else 1,
                    index,
                ),
                rewrite,
                normalize_target_url(target),
                record.parent_domain,
            )
        )
    total_limit = max(0, budget.max_total - (1 if budget.max_total else 0))
    domain_limits = {
        "aspose.org": max(
            0,
            budget.domain_maxima["aspose.org"] - (1 if budget.domain_maxima["aspose.org"] else 0),
        ),
        "aspose.com": budget.domain_maxima["aspose.com"],
    }
    retained: set[tuple[int, int]] = set()
    targets: set[str] = set()
    domains = {"aspose.org": 0, "aspose.com": 0}
    for _, rewrite, target, parent in sorted(candidates):
        if (
            len(retained) >= total_limit
            or len(retained) >= budget.surface_maxima["products"]
            or domains[parent] >= domain_limits[parent]
            or target in targets
        ):
            continue
        retained.add((rewrite.character_start, rewrite.character_end))
        targets.add(target)
        domains[parent] += 1
    return retained


def build_source_link_hygiene_operations(
    context: DocumentRenderContext,
    existing_operations: list[ReadmeDocumentOperationV1],
    catalogs: AsposeLinkCatalogSetV1,
    policy: LinkAllocationPolicyV1,
) -> list[ReadmeDocumentOperationV1]:
    """Unwrap unsupported links while retaining bounded verified product targets."""

    identity = context.facts.selected_fact("product.identity")
    _, rewrites = remove_unbound_aspose_links(context.inner_text)
    retained = _retained_product_spans(
        context,
        rewrites,
        existing_operations,
        catalogs,
        policy,
    )
    operations: list[ReadmeDocumentOperationV1] = []
    for index, rewrite in enumerate(rewrites, start=1):
        if (rewrite.character_start, rewrite.character_end) in retained:
            continue
        start = context.byte_offset(rewrite.character_start)
        end = context.byte_offset(rewrite.character_end)
        if _overlaps(start, end, existing_operations):
            continue
        operations.append(
            build_operation(
                operation_id=f"readme.links.unwrap-unbound:{index}",
                operation="replace",
                source=context.source,
                start=start,
                end=end,
                replacement=rewrite.replacement,
                fact_ids=[identity.fact_id],
                treatment="presentation_policy_correction",
                rationale=(
                    "Preserve maintainer-authored visitor text while removing an Aspose target "
                    "that has no current catalog-backed context binding."
                ),
            )
        )
    return operations
