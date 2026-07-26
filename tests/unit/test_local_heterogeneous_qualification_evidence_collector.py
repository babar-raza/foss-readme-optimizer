"""Qualification evidence collection permits only one campaign writer."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from filelock import FileLock


def _load_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "plans"
        / "investigations"
        / "tools"
        / "collect_local_heterogeneous_qualification_evidence.py"
    )
    spec = importlib.util.spec_from_file_location(
        "local_heterogeneous_qualification_evidence_collector",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_active_campaign_writer_blocks_a_duplicate_session(tmp_path, monkeypatch):
    module = _load_module()
    output = tmp_path / "qualification"
    lock_path = output.parent / f".{output.name}.campaign.lock"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "collector",
            "--output",
            str(output),
            "--session-id",
            "initial-discrimination",
        ],
    )

    with FileLock(lock_path):
        assert module.main() == 2


def test_campaign_allows_documentation_commit_when_hashed_sources_are_unchanged(
    tmp_path, monkeypatch
):
    module = _load_module()
    output = tmp_path / "qualification"
    output.mkdir()
    recorded = {
        "schema_version": 1,
        "source_head": "a" * 40,
        "source_files": {"prompt.yaml": "content-hash"},
    }
    (output / "campaign-source.json").write_text(
        json.dumps(recorded),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        module,
        "_source_snapshot",
        lambda: {
            "schema_version": 1,
            "source_head": "b" * 40,
            "source_files": {"prompt.yaml": "content-hash"},
        },
    )

    assert module._bind_campaign_source(output) == recorded
