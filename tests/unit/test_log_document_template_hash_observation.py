"""T1 instrumentation: additive-only, correctly detects flips, correctly attributes them
to actually-changed contributing files, and never mutates production state."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.governance import log_document_template_hash_observation as observer


def test_contributing_files_is_non_empty_and_includes_a_known_template() -> None:
    files = observer._contributing_files()
    assert files
    assert "src/readme_agent/readme/document_renderer.py" in files


def test_first_observation_is_never_a_flip(tmp_path: Path, monkeypatch) -> None:
    history = tmp_path / "history.jsonl"
    monkeypatch.setattr(observer, "HISTORY_PATH", history)
    monkeypatch.setattr(
        "readme_agent.readme.document_templates.document_template_hash", lambda: "hash-a"
    )
    monkeypatch.setattr(observer, "_git_head", lambda: "head-1")

    entry = observer.observe()

    assert entry["flipped"] is False
    assert entry["template_hash"] == "hash-a"
    recorded = [json.loads(line) for line in history.read_text(encoding="utf-8").splitlines()]
    assert len(recorded) == 1


def test_identical_hash_is_not_a_flip(tmp_path: Path, monkeypatch) -> None:
    history = tmp_path / "history.jsonl"
    monkeypatch.setattr(observer, "HISTORY_PATH", history)
    monkeypatch.setattr(observer, "_git_head", lambda: "head-1")
    monkeypatch.setattr(
        "readme_agent.readme.document_templates.document_template_hash", lambda: "hash-a"
    )
    observer.observe()

    monkeypatch.setattr(observer, "_git_head", lambda: "head-2")
    second = observer.observe()

    assert second["flipped"] is False


def test_changed_hash_is_a_flip_and_attributes_changed_files(tmp_path: Path, monkeypatch) -> None:
    history = tmp_path / "history.jsonl"
    monkeypatch.setattr(observer, "HISTORY_PATH", history)
    monkeypatch.setattr(observer, "_git_head", lambda: "head-1")
    monkeypatch.setattr(
        "readme_agent.readme.document_templates.document_template_hash", lambda: "hash-a"
    )
    observer.observe()

    monkeypatch.setattr(observer, "_git_head", lambda: "head-2")
    monkeypatch.setattr(
        "readme_agent.readme.document_templates.document_template_hash", lambda: "hash-b"
    )
    monkeypatch.setattr(
        observer, "_changed_contributing_files", lambda prev, curr: ["templates/readme/x.md"]
    )
    second = observer.observe()

    assert second["flipped"] is True
    assert second["changed_contributing_files"] == ["templates/readme/x.md"]


def test_report_counts_observations_distinct_hashes_and_flips(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    history = tmp_path / "history.jsonl"
    entries = [
        {"observed_at": "t1", "template_hash": "a", "git_head": "h1", "flipped": False},
        {
            "observed_at": "t2",
            "template_hash": "b",
            "git_head": "h2",
            "flipped": True,
            "changed_contributing_files": ["templates/readme/x.md"],
        },
        {"observed_at": "t3", "template_hash": "b", "git_head": "h3", "flipped": False},
    ]
    history.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")
    monkeypatch.setattr(observer, "HISTORY_PATH", history)

    observer.report()

    out = capsys.readouterr().out
    assert "observations: 3" in out
    assert "distinct template_hash values: 2" in out
    assert "flips: 1" in out
    assert "templates/readme/x.md" in out


def test_report_with_no_history_does_not_crash(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(observer, "HISTORY_PATH", tmp_path / "absent.jsonl")
    observer.report()
    assert "no observations recorded yet" in capsys.readouterr().out
