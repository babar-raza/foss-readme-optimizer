"""Bind concrete current pytest nodes to implemented knowledge requirements."""

from __future__ import annotations

import json
from pathlib import Path

PATH = Path("plans/requirements/catalog.jsonl")
EVIDENCE = {
    "KNOW-001": (
        "tests/unit/test_aspose_knowledge_claims.py::"
        "test_load_knowledge_claims_real_corpus_returns_typed_claims; "
        "tests/unit/test_aspose_knowledge_claims.py::"
        "test_load_knowledge_claims_covers_every_documented_kind_somewhere_in_the_corpus"
    ),
    "KNOW-002": (
        "tests/unit/test_aspose_knowledge_selection.py::"
        "test_select_knowledge_claims_bounded_selection_never_exceeds_cap; "
        "tests/unit/test_aspose_knowledge_selection.py::"
        "test_select_knowledge_claims_readme_overlap_frees_cap_slot_for_new_information; "
        "tests/unit/test_aspose_knowledge_selection.py::"
        "test_select_knowledge_claims_search_intent_keyword_outranks_equal_confidence_claim"
    ),
    "KNOW-003": (
        "tests/unit/test_aspose_knowledge_selection.py::"
        "test_select_knowledge_claims_uncorroborated_stale_claims_are_never_output_eligible; "
        "tests/unit/test_aspose_knowledge_selection.py::"
        "test_select_knowledge_claims_current_repo_evidence_wins_on_real_license_conflict; "
        "tests/unit/test_aspose_knowledge_selection.py::"
        "test_select_knowledge_claims_fbx_positive_claim_conflicts_with_stub_implementation"
    ),
    "KNOW-012": (
        "tests/unit/test_aspose_checks_registry.py::"
        "test_check_no_excluded_domain_links_real_invocation_flags_forum_link; "
        "tests/unit/test_readme_existing_section_regressions.py::"
        "test_real_net_partial_sections_preserve_maintainer_content_without_fact_duplication"
    ),
}


def main() -> None:
    records = [json.loads(line) for line in PATH.read_text(encoding="utf-8").splitlines() if line]
    found: set[str] = set()
    for record in records:
        requirement_id = record["requirement_id"]
        nodes = EVIDENCE.get(requirement_id)
        if nodes is None:
            continue
        found.add(requirement_id)
        existing = record["acceptance_evidence"].split(" Current focused proof:", maxsplit=1)[0]
        cited_nodes = "; ".join(f"`{node}`" for node in nodes.split("; "))
        record["acceptance_evidence"] = (
            f"{existing.rstrip('.')}. Current focused proof: {cited_nodes}."
        )
    missing = sorted(set(EVIDENCE) - found)
    if missing:
        raise ValueError(f"missing requirement rows: {', '.join(missing)}")
    PATH.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
