"""Current-contract safeguards for the working-condition-presentation exception lane."""

from types import SimpleNamespace

import pytest
from governance import promote_working_condition_exceptions as promotion

from readme_agent.errors import NotAllowlistedError

REPOSITORY = "aspose-html-foss/Aspose.HTML-FOSS-for-Python"
SOURCE_REVISION = "c2356ec872fd7d64c14a0ae8cc043eea1a03847e"
ENTRY = {
    "repository": REPOSITORY,
    "platform": "python",
    "family": "html",
    "accepted_date": "2026-08-12",
    "accepted_by": "product owner",
    "acceptance_basis": "accepted in chat",
    "blocking_defect_summary": "broken build backend, no PyPI release",
    "resume_predicate": "upstream fixes the build backend and publishes to PyPI",
}


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(__import__("json").dumps(value), encoding="utf-8")


def _valid_bundle(bundle_dir):
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "README.md").write_text("# Aspose.HTML FOSS for Python\n", encoding="utf-8")
    (bundle_dir / "UPSTREAM-DEFECTS.md").write_text("- installation blocked\n", encoding="utf-8")
    _write_json(
        bundle_dir / "validation.json",
        {
            "org_repo": REPOSITORY,
            "source_revision": SOURCE_REVISION,
            "deterministic_verdict": "accept",
            "independent_review_verdict": "ACCEPT",
            "review_open": False,
            "disposition_ledger_valid": True,
            "disposition_ledger_errors": [],
        },
    )


def _setup(tmp_path, monkeypatch, registry_entries):
    repo_root = tmp_path / "repo"
    monkeypatch.setattr(promotion, "REPO_ROOT", repo_root)
    monkeypatch.setattr(
        promotion, "REGISTRY_PATH", repo_root / "data/working_condition_exceptions.json"
    )
    monkeypatch.setattr(promotion, "POC_SHARE_ROOT", repo_root / "runs/share/poc")
    _write_json(promotion.REGISTRY_PATH, registry_entries)
    monkeypatch.setattr(
        promotion,
        "require_listed",
        lambda repository: SimpleNamespace(platform="python"),
    )
    return repo_root / "evidence"


def test_promotes_a_single_accepted_exception(tmp_path, monkeypatch):
    output_root = _setup(tmp_path, monkeypatch, [ENTRY])
    _valid_bundle(promotion.POC_SHARE_ROOT / REPOSITORY.replace("/", "__"))

    manifest = promotion.promote(output_root)

    assert manifest["exception_count"] == 1
    assert manifest["promotion_exclusions"] == []
    row = manifest["repositories"][0]
    assert row["repository"] == REPOSITORY
    assert row["verdict"] == "HUMAN_ACCEPTED_WORKING_CONDITION_EXCEPTION"
    destination = promotion.REPO_ROOT / row["committed_readme"]
    assert destination.is_file()
    assert (destination.parent / "ACCEPTANCE-RECORD.json").is_file()
    assert promotion.verify_sha256sums(output_root) is True


def test_rerun_is_byte_identical(tmp_path, monkeypatch):
    output_root = _setup(tmp_path, monkeypatch, [ENTRY])
    _valid_bundle(promotion.POC_SHARE_ROOT / REPOSITORY.replace("/", "__"))

    first = promotion.promote(output_root)
    first_bytes = {
        path.relative_to(output_root).as_posix(): path.read_bytes()
        for path in output_root.rglob("*")
        if path.is_file()
    }
    second = promotion.promote(output_root)
    second_bytes = {
        path.relative_to(output_root).as_posix(): path.read_bytes()
        for path in output_root.rglob("*")
        if path.is_file()
    }

    assert first == second
    assert first_bytes == second_bytes


def test_unaccepted_verdict_is_excluded_not_fatal(tmp_path, monkeypatch):
    output_root = _setup(tmp_path, monkeypatch, [ENTRY])
    bundle_dir = promotion.POC_SHARE_ROOT / REPOSITORY.replace("/", "__")
    _valid_bundle(bundle_dir)
    validation = __import__("json").loads((bundle_dir / "validation.json").read_text())
    validation["deterministic_verdict"] = "reject"
    _write_json(bundle_dir / "validation.json", validation)

    manifest = promotion.promote(output_root)

    assert manifest["exception_count"] == 0
    assert len(manifest["promotion_exclusions"]) == 1
    assert manifest["promotion_exclusions"][0]["repository"] == REPOSITORY


def test_missing_poc_bundle_is_excluded_not_fatal(tmp_path, monkeypatch):
    output_root = _setup(tmp_path, monkeypatch, [ENTRY])

    manifest = promotion.promote(output_root)

    assert manifest["exception_count"] == 0
    assert manifest["promotion_exclusions"][0]["reason"].startswith(REPOSITORY)


def test_repository_missing_from_products_registry_is_rejected(tmp_path, monkeypatch):
    output_root = _setup(tmp_path, monkeypatch, [ENTRY])
    _valid_bundle(promotion.POC_SHARE_ROOT / REPOSITORY.replace("/", "__"))
    monkeypatch.setattr(
        promotion,
        "require_listed",
        lambda repository: (_ for _ in ()).throw(NotAllowlistedError(repository)),
    )

    with pytest.raises(NotAllowlistedError):
        promotion.promote(output_root)


def test_platform_mismatch_between_registry_and_products_is_rejected(tmp_path, monkeypatch):
    output_root = _setup(tmp_path, monkeypatch, [ENTRY])
    _valid_bundle(promotion.POC_SHARE_ROOT / REPOSITORY.replace("/", "__"))
    monkeypatch.setattr(
        promotion,
        "require_listed",
        lambda repository: SimpleNamespace(platform="net"),
    )

    with pytest.raises(ValueError, match="does not match"):
        promotion.promote(output_root)


def test_rejects_symlink_in_output_root(tmp_path, monkeypatch):
    output_root = _setup(tmp_path, monkeypatch, [ENTRY])
    output_root.mkdir(parents=True)
    target = tmp_path / "target.txt"
    target.write_text("x", encoding="utf-8")
    (output_root / "link.txt").symlink_to(target)

    with pytest.raises(ValueError, match="unsupported symlink"):
        promotion.promote(output_root)


def test_empty_registry_produces_a_zero_exception_checksum_valid_tree(tmp_path, monkeypatch):
    output_root = _setup(tmp_path, monkeypatch, [])

    manifest = promotion.promote(output_root)

    assert manifest["exception_count"] == 0
    assert manifest["registry_denominator"] == 0
    assert promotion.verify_sha256sums(output_root) is True
