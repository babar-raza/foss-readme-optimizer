"""Frozen visitor-facing defect corpus for deterministic README presentation lint."""

import hashlib
import json
import re
from pathlib import Path

_ROOT = Path(__file__).parents[2]
_CORPUS_PATH = _ROOT / "tests/fixtures/presentation_defects/corpus.json"
_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9.-]+$")


def _corpus() -> dict:
    return json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))


def test_corpus_sources_are_immutable_and_every_expected_span_is_exact() -> None:
    corpus = _corpus()
    assert corpus["schema_version"] == 1

    for case in corpus["cases"]:
        source = _ROOT / case["source_path"]
        assert source.is_file(), case["case_id"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == case["source_sha256"]
        text = source.read_text(encoding="utf-8")

        for finding in case["findings"]:
            assert len(finding["exact_spans"]) == len(finding["expected_occurrences"])
            for span, expected_count in zip(
                finding["exact_spans"],
                finding["expected_occurrences"],
                strict=True,
            ):
                assert span
                assert text.count(span) == expected_count, finding["finding_id"]


def test_corpus_ids_are_stable_unique_and_defect_specific() -> None:
    corpus = _corpus()
    case_ids = [case["case_id"] for case in corpus["cases"]]
    finding_ids = [
        finding["finding_id"] for case in corpus["cases"] for finding in case["findings"]
    ]

    assert len(case_ids) == len(set(case_ids))
    assert len(finding_ids) == len(set(finding_ids))
    assert all(_STABLE_ID.fullmatch(item) for item in case_ids + finding_ids)
    assert all(item.startswith("presentation.") for item in finding_ids)
    assert all(
        finding["rule_id"] and finding["rationale"]
        for case in corpus["cases"]
        for finding in case["findings"]
    )


def test_corpus_covers_every_known_critical_visitor_defect_and_control() -> None:
    corpus = _corpus()
    rule_ids = {finding["rule_id"] for case in corpus["cases"] for finding in case["findings"]}
    origins = {case["origin"] for case in corpus["cases"]}
    real_platforms = {
        case["platform"] for case in corpus["cases"] if case["origin"] == "real_candidate"
    }

    assert {
        "raw_internal_token",
        "semantic_duplicate",
        "competing_primary_examples",
        "visitor_fragment",
        "cross_product_leakage",
        "malformed_navigation",
        "prompt_injection_residue",
        "promotional_imbalance",
    } <= rule_ids
    assert origins == {"real_candidate", "synthetic_negative", "synthetic_positive"}
    assert real_platforms == {"java", "python"}


def test_expected_verdicts_fail_closed_without_turning_positive_content_into_a_template() -> None:
    corpus = _corpus()
    positives = [case for case in corpus["cases"] if case["expected_verdict"] == "ACCEPT"]
    negatives = [case for case in corpus["cases"] if case["expected_verdict"] == "REJECT"]

    assert [case["case_id"] for case in positives] == ["synthetic.strong-existing-content"]
    assert positives[0]["findings"] == []
    assert negatives
    assert all(case["findings"] for case in negatives)
    assert all(
        finding["severity"] == "critical" for case in negatives for finding in case["findings"]
    )
    assert "Aspose" not in (_ROOT / positives[0]["source_path"]).read_text(encoding="utf-8")


def test_cross_product_control_is_repository_bound_not_a_universal_template_allowlist() -> None:
    corpus = _corpus()
    case = next(
        item for item in corpus["cases"] if item["case_id"] == "synthetic.cross-product-leakage"
    )
    text = (_ROOT / case["source_path"]).read_text(encoding="utf-8")

    own_product = (
        case["repository"].split("/", maxsplit=1)[1].replace("-for-Python", "").replace("-", " ")
    )
    foreign_span = case["findings"][0]["exact_spans"][0]
    assert own_product in text
    assert own_product not in foreign_span
    assert "Aspose.Cells FOSS" in foreign_span
