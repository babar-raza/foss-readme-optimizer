"""Gate R2: fail-closed corpus accountability. Every raw claims.json entry
and every corpus-loading failure mode must produce exactly one accountable
outcome (a valid claim, or a typed `KnowledgeLoadFindingV1`) -- nothing may
disappear via a silent `continue`."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.facts.aspose_knowledge_claims import (
    load_knowledge_claims,
    load_knowledge_claims_with_findings,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REAL_DATA_ROOT = _REPO_ROOT / "data" / "imported"


def _write_registry(data_root: Path, pairs: list[tuple[str, str]]) -> None:
    registry_path = data_root / "data" / "products.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps([{"family": f, "platform": p} for f, p in pairs]), encoding="utf-8"
    )


def test_real_corpus_valid_product_has_zero_findings():
    result = load_knowledge_claims_with_findings("3d", "python", data_root=_REAL_DATA_ROOT)

    assert len(result.claims) > 1000
    assert result.findings == ()


def test_imported_corpus_root_missing_is_agent_fixable(tmp_path):
    missing_root = tmp_path / "does-not-exist"

    result = load_knowledge_claims_with_findings("cells", "python", data_root=missing_root)

    assert result.claims == ()
    assert len(result.findings) == 1
    assert result.findings[0].finding_type == "imported_corpus_root_missing"
    assert result.findings[0].agent_fixable is True


def test_product_platform_absent_from_registry_is_never_agent_fixable(tmp_path):
    _write_registry(tmp_path, [("cells", "python")])

    result = load_knowledge_claims_with_findings("psd", "python", data_root=tmp_path)

    assert result.claims == ()
    assert len(result.findings) == 1
    assert result.findings[0].finding_type == "product_platform_not_in_imported_corpus"
    assert result.findings[0].agent_fixable is False


def test_expected_bundle_missing_is_agent_fixable(tmp_path):
    _write_registry(tmp_path, [("cells", "python")])
    # No knowledge/cells/python/merged/ directory created at all.

    result = load_knowledge_claims_with_findings("cells", "python", data_root=tmp_path)

    assert result.claims == ()
    assert len(result.findings) == 1
    assert result.findings[0].finding_type == "expected_bundle_missing"
    assert result.findings[0].agent_fixable is True


def test_claims_file_missing_is_agent_fixable(tmp_path):
    _write_registry(tmp_path, [("cells", "python")])
    bundle = tmp_path / "knowledge" / "cells" / "python" / "merged"
    bundle.mkdir(parents=True)
    # Bundle directory exists but claims.json itself is absent.

    result = load_knowledge_claims_with_findings("cells", "python", data_root=tmp_path)

    assert result.claims == ()
    assert len(result.findings) == 1
    assert result.findings[0].finding_type == "claims_file_missing"
    assert result.findings[0].agent_fixable is True


def test_json_parse_error_is_agent_fixable(tmp_path):
    _write_registry(tmp_path, [("cells", "python")])
    bundle = tmp_path / "knowledge" / "cells" / "python" / "merged"
    bundle.mkdir(parents=True)
    (bundle / "claims.json").write_text("{not valid json", encoding="utf-8")

    result = load_knowledge_claims_with_findings("cells", "python", data_root=tmp_path)

    assert result.claims == ()
    assert len(result.findings) == 1
    assert result.findings[0].finding_type == "json_parse_error"
    assert result.findings[0].agent_fixable is True


def test_wrong_top_level_shape_is_agent_fixable(tmp_path):
    _write_registry(tmp_path, [("cells", "python")])
    bundle = tmp_path / "knowledge" / "cells" / "python" / "merged"
    bundle.mkdir(parents=True)
    (bundle / "claims.json").write_text('{"not": "a list"}', encoding="utf-8")

    result = load_knowledge_claims_with_findings("cells", "python", data_root=tmp_path)

    assert result.claims == ()
    assert len(result.findings) == 1
    assert result.findings[0].finding_type == "wrong_top_level_shape"
    assert result.findings[0].agent_fixable is True


def test_invalid_individual_records_are_each_accounted_for(tmp_path):
    _write_registry(tmp_path, [("cells", "python")])
    bundle = tmp_path / "knowledge" / "cells" / "python" / "merged"
    bundle.mkdir(parents=True)
    raw = [
        {"claim_id": "CLM-1", "kind": "feature", "text": "real claim"},  # valid
        "not a dict",  # invalid_record: wrong type
        {"kind": "feature", "text": "missing id"},  # invalid_record: no claim_id
        {"claim_id": "CLM-2", "kind": "not_a_real_kind", "text": "x"},  # invalid_record: bad kind
        {"claim_id": "CLM-3", "kind": "feature"},  # invalid_record: missing text
    ]
    (bundle / "claims.json").write_text(json.dumps(raw), encoding="utf-8")

    result = load_knowledge_claims_with_findings("cells", "python", data_root=tmp_path)

    assert len(result.claims) == 1
    assert result.claims[0].claim_id == "CLM-1"
    invalid_findings = [f for f in result.findings if f.finding_type == "invalid_record"]
    assert len(invalid_findings) == 4
    assert {f.raw_index for f in invalid_findings} == {1, 2, 3, 4}
    assert all(f.agent_fixable for f in invalid_findings)
    # Every raw record is accounted for exactly once: 1 valid + 4 findings == 5 raw entries.
    assert len(result.claims) + len(invalid_findings) == len(raw)


def test_empty_valid_collection_is_not_agent_fixable(tmp_path):
    _write_registry(tmp_path, [("cells", "python")])
    bundle = tmp_path / "knowledge" / "cells" / "python" / "merged"
    bundle.mkdir(parents=True)
    (bundle / "claims.json").write_text("[]", encoding="utf-8")

    result = load_knowledge_claims_with_findings("cells", "python", data_root=tmp_path)

    assert result.claims == ()
    assert len(result.findings) == 1
    assert result.findings[0].finding_type == "empty_valid_collection"
    assert result.findings[0].agent_fixable is False


def test_no_registry_available_degrades_to_attempting_the_load_anyway(tmp_path):
    """When the expectation registry itself is unavailable, the loader
    cannot classify absence as intentional -- it falls through to the
    concrete bundle/file checks rather than silently returning nothing."""

    bundle = tmp_path / "knowledge" / "cells" / "python" / "merged"
    bundle.mkdir(parents=True)
    (bundle / "claims.json").write_text(
        '[{"claim_id": "CLM-1", "kind": "feature", "text": "x"}]', encoding="utf-8"
    )

    result = load_knowledge_claims_with_findings("cells", "python", data_root=tmp_path)

    assert len(result.claims) == 1
    assert result.findings == ()


def test_backward_compatible_wrapper_returns_only_claims():
    claims = load_knowledge_claims("3d", "python", data_root=_REAL_DATA_ROOT)

    assert len(claims) > 1000
    assert isinstance(claims, tuple)
