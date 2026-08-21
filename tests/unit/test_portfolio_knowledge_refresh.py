"""Tests for isolated portfolio knowledge refresh accounting."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from readme_agent.facts import portfolio_knowledge_refresh as refresh


def test_refresh_rejects_a_repository_outside_the_allow_list(monkeypatch) -> None:
    monkeypatch.setattr(refresh, "load_products", lambda: ())

    with pytest.raises(ValueError, match="not in data/products.json"):
        refresh.refresh_repository_knowledge_cohort(("outside/repository",))


def test_refresh_records_typed_psd_non_processability_without_cloning(monkeypatch) -> None:
    entry = SimpleNamespace(
        org_repo="aspose-psd-foss/Aspose.PSD-FOSS-for-Python",
        family="psd",
        platform="python",
    )
    monkeypatch.setattr(refresh, "load_products", lambda: (entry,))
    monkeypatch.setattr(
        refresh,
        "current_repository_knowledge_generator_sha256",
        lambda: "a" * 64,
    )
    monkeypatch.setattr(
        refresh,
        "clone_baseline",
        lambda *args, **kwargs: pytest.fail("PSD disposition must not clone"),
    )

    report = refresh.refresh_repository_knowledge_cohort((entry.org_repo,))

    assert report.entries[0].status == "non_processable_no_implementation"
    assert report.entries[0].source_revision is None
