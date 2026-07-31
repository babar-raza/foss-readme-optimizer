"""Finalize complete README navigation inside its owning bounded operation."""

from __future__ import annotations

from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_operations import apply_document_operations
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_structure import (
    normalize_navigation_targets,
    parse_headings,
    rebuild_navigation_for_labels,
)


def finalize_navigation_operations(
    source: bytes,
    operations: list[ReadmeDocumentOperationV1],
) -> list[ReadmeDocumentOperationV1]:
    """Bind Navigation to every final H2 without creating an overlapping edit."""

    preliminary = apply_document_operations(source, operations).decode("utf-8")
    normalized = normalize_navigation_targets(preliminary)
    if normalized == preliminary:
        return operations
    labels = [
        heading.title
        for heading in parse_headings(preliminary)
        if heading.level == 2 and heading.title.casefold() != "navigation"
    ]
    owners = [
        index
        for index, operation in enumerate(operations)
        if any(
            heading.level == 2 and heading.title.casefold() == "navigation"
            for heading in parse_headings(operation.replacement_text)
        )
    ]
    if len(owners) != 1:
        raise ValueError(
            "README Navigation needs normalization but is not owned by exactly one operation"
        )
    owner_index = owners[0]
    owner = operations[owner_index]
    replacement = rebuild_navigation_for_labels(owner.replacement_text, labels)
    if replacement == owner.replacement_text:
        raise ValueError("README Navigation owner could not be normalized")
    updated = list(operations)
    updated[owner_index] = owner.model_copy(
        update={
            "replacement_text": replacement,
            "replacement_sha256": sha256_hex(replacement.encode("utf-8")),
        }
    )
    final_candidate = apply_document_operations(source, updated).decode("utf-8")
    if normalize_navigation_targets(final_candidate) != final_candidate:
        raise ValueError("README Navigation remains incomplete after normalization")
    return updated
