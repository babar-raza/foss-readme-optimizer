"""Deterministic, case/whitespace-normalized heading identity for the source
disposition ledger's candidate-destination lookup.

Causal fix for `commands_poc.py::build_source_disposition_ledger`'s own
`compiled_blocks.get(heading)` lookup (an exact, case-sensitive string
comparison of the source README's literal heading spelling against the
template contract's canonical slot title -- the two are independently
authored and legitimately differ in case/wording, e.g. source `"## Key
capabilities"` vs. contract `"Key Capabilities"`). This module owns exactly
one responsibility: given one ledger unit's full ancestor heading path and
the compiler's own slot -> compiled-block-text map, decide its candidate
destination, or refuse (return `""`) when the mapping is genuinely ambiguous
or unresolved -- fail closed, never guessed.
"""

from __future__ import annotations


def canonical_heading_key(text: str) -> str:
    """Case/whitespace/harmless-punctuation-insensitive identity for one
    heading's own text. Casefolds, collapses internal whitespace, and strips
    a small set of trailing punctuation real contract/source headings differ
    on (":", "."). Never a semantic rewrite: "Docs & Resources" and "Docs and
    Resources" are deliberately left distinct -- unifying conjunction wording
    would risk merging two genuinely different headings, which fail-closed
    behavior must never do silently."""

    collapsed = " ".join(text.split())
    return collapsed.strip(" :.").casefold()


def _canonical_slot_index(compiled_blocks: dict[str, str]) -> dict[str, str] | None:
    """Canonical key -> original contract slot key. `None` (refuse to resolve
    anything against this map) when two distinct slot titles collide under
    canonicalization -- a template-contract inconsistency, never silently
    picked between."""

    index: dict[str, str] = {}
    for slot_key in compiled_blocks:
        canonical = canonical_heading_key(slot_key)
        existing = index.get(canonical)
        if existing is not None and existing != slot_key:
            return None
        index[canonical] = slot_key
    return index


def resolve_disposition_target(
    heading_path: tuple[str, ...],
    compiled_blocks: dict[str, str],
    raw_candidate_text: str,
    *,
    content_snippets: tuple[str, ...] = (),
) -> str:
    """Resolve one ledger unit's candidate destination.

    `heading_path` is the unit's full ancestor chain, leaf last (e.g.
    `("Dependencies", "Native and System Requirements")` for an H3 nested
    under an H2 slot) -- exactly `InheritedReadmeFactV1.heading_path`.
    `compiled_blocks` is `template_compiler.py::compiled_slot_blocks()`'s own
    output: contract-canonical top-level slot title -> its exact compiled
    "## Heading\\n\\nBody" text.

    Walks from the leaf upward (never sideways/downward), so a duplicate leaf
    heading name under two different parents resolves independently by its
    own real ancestor chain, never by leaf-name alone. The first ancestor
    (starting from the leaf itself) whose canonicalized text matches a
    contract slot wins; a nested unit additionally requires its own leaf text
    to appear verbatim inside that slot's compiled block -- proof the
    compiler actually placed this specific sub-heading's content there, not
    merely that some ancestor matched.

    When no ancestor resolves by name at all, falls back to a bounded
    content-based match: if a long-enough (>=24 normalized characters, to
    avoid an accidental short-string collision) snippet from
    `content_snippets` (the unit's own block text, never its heading label
    alone) appears verbatim in exactly one compiled slot's block -- content
    genuinely relocated under a differently-titled heading -- that slot is
    the target. Landing in zero or multiple slots is ambiguous and fails
    closed.

    Returns "" when nothing resolves, the ancestor match is ambiguous
    (colliding canonical slot titles), or a nested unit's own text cannot be
    found inside its matched ancestor's block.
    """

    index = _canonical_slot_index(compiled_blocks)
    if index is not None and heading_path:
        leaf = heading_path[-1]
        for depth in range(len(heading_path), 0, -1):
            ancestor = heading_path[depth - 1]
            slot_key = index.get(canonical_heading_key(ancestor))
            if slot_key is None:
                continue
            block_text = compiled_blocks.get(slot_key, "")
            if not block_text or block_text not in raw_candidate_text:
                return ""
            if depth == len(heading_path):
                # The unit's own heading IS the slot -- already proven present.
                return slot_key
            # A nested unit: additionally require its own leaf heading text to
            # appear inside the ancestor's compiled block -- never credit a
            # sibling sub-heading's presence to this one.
            return slot_key if leaf and leaf in block_text else ""

    candidates = {
        slot_key
        for slot_key, block_text in compiled_blocks.items()
        for snippet in content_snippets
        if len(snippet) >= 24 and snippet in block_text
    }
    return next(iter(candidates)) if len(candidates) == 1 else ""


__all__ = ["canonical_heading_key", "resolve_disposition_target"]
