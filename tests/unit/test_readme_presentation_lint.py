"""Deterministic pre-review README presentation lint qualification."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.presentation_lint import lint_readme_presentation

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = PROJECT_ROOT / "tests/fixtures/presentation_defects/corpus.json"
FACTS_PROOF = (
    PROJECT_ROOT
    / "plans/investigations/evidence"
    / "level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24"
    / "immutable-snapshot-and-product-facts-proof.json"
)


def _facts(org_repo: str) -> ProductFactsV2:
    proof = json.loads(FACTS_PROOF.read_text(encoding="utf-8"))
    pilot = next(item for item in proof["current_pilots"] if item["org_repo"] == org_repo)
    return ProductFactsV2.model_validate(pilot["product_facts_v2"])


def _facts_for_case(case: dict) -> ProductFactsV2 | None:
    if case["origin"] == "synthetic_positive":
        return None
    if "cells" in case["repository"].casefold():
        return _facts("aspose-cells-foss/Aspose.Cells-FOSS-for-Java")
    return _facts("aspose-3d-foss/Aspose.3D-FOSS-for-Java")


def test_complete_corpus_has_expected_verdicts_rules_and_exact_spans() -> None:
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    for case in corpus["cases"]:
        candidate = (PROJECT_ROOT / case["source_path"]).read_text(encoding="utf-8")
        result = lint_readme_presentation(candidate, _facts_for_case(case))

        assert result.valid is (case["expected_verdict"] == "ACCEPT"), case["case_id"]
        for expectation in case["findings"]:
            actual_spans = {
                span.text
                for finding in result.findings
                if finding.rule_id == expectation["rule_id"]
                for span in finding.spans
            }
            assert set(expectation["exact_spans"]) <= actual_spans, expectation["finding_id"]


def test_finding_ids_and_spans_are_stable_across_identical_runs() -> None:
    case = next(
        item
        for item in json.loads(CORPUS_PATH.read_text(encoding="utf-8"))["cases"]
        if item["case_id"] == "real.cells-java.visitor-defects"
    )
    candidate = (PROJECT_ROOT / case["source_path"]).read_text(encoding="utf-8")
    facts = _facts_for_case(case)

    first = lint_readme_presentation(candidate, facts)
    second = lint_readme_presentation(candidate, facts)

    assert first == second
    assert len({finding.finding_id for finding in first.findings}) == len(first.findings)
    assert all(
        candidate[span.start : span.end] == span.text
        for finding in first.findings
        for span in finding.spans
    )


def test_code_tokens_and_a_product_specific_strong_readme_are_not_template_gated() -> None:
    candidate = """# Mesh Toolkit

Mesh Toolkit is a Rust library for validating meshes and exporting geometry to OBJ files.

## Example

```rust
let internal_value = Mesh::triangle();
```

## License

MIT
"""
    result = lint_readme_presentation(candidate, None)

    assert result.valid
    assert not result.findings


def test_rule_inventory_is_complete_and_deterministically_ordered() -> None:
    candidate = PROJECT_ROOT / "tests/fixtures/presentation_defects/strong-existing-content.md"
    result = lint_readme_presentation(candidate.read_text(encoding="utf-8"), None)

    assert result.rules_run == [
        "competing_primary_examples",
        "cross_product_leakage",
        "malformed_navigation",
        "promotional_imbalance",
        "prompt_injection_residue",
        "raw_internal_token",
        "semantic_duplicate",
        "visitor_fragment",
    ]
