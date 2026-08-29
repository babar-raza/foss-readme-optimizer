"""Additive-only governance-growth-vs-delivery visibility: never blocks, never
raises, degrades to "unknown" per-field rather than hiding the others."""

from __future__ import annotations

import json

from readme_agent.supervisor import growth_ceiling as gc


def test_format_renders_unknown_for_missing_fields():
    ceiling = gc.GrowthCeilingV1(
        window_days=7, requirements_added=None, decisions_added=None, no_op_proven_delta=None
    )
    rendered = gc.format_growth_ceiling(ceiling)
    assert "requirements_added=unknown" in rendered
    assert "decisions_added=unknown" in rendered
    assert "no_op_proven_delta=unknown" in rendered
    assert "growth_ceiling_7d" in rendered


def test_format_renders_real_values():
    ceiling = gc.GrowthCeilingV1(
        window_days=7, requirements_added=5, decisions_added=2, no_op_proven_delta=1
    )
    rendered = gc.format_growth_ceiling(ceiling)
    assert "requirements_added=5" in rendered
    assert "decisions_added=2" in rendered
    assert "no_op_proven_delta=1" in rendered


def test_record_and_delta_reads_back_a_written_observation(tmp_path, monkeypatch):
    history = tmp_path / "no-op-proven-history.jsonl"
    monkeypatch.setattr(gc, "NO_OP_PROVEN_HISTORY_PATH", history)

    from datetime import UTC, datetime, timedelta

    old_entry = {
        "observed_at": (datetime.now(UTC) - timedelta(days=10)).isoformat(),
        "no_op_proven": 1,
    }
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_text(json.dumps(old_entry) + "\n", encoding="utf-8")

    delta = gc._no_op_proven_delta(current=4, days=7)
    assert delta == 3


def test_delta_is_none_without_history_old_enough_to_compare(tmp_path, monkeypatch):
    history = tmp_path / "no-op-proven-history.jsonl"
    monkeypatch.setattr(gc, "NO_OP_PROVEN_HISTORY_PATH", history)

    assert gc._no_op_proven_delta(current=4, days=7) is None

    from datetime import UTC, datetime

    recent_entry = {"observed_at": datetime.now(UTC).isoformat(), "no_op_proven": 1}
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_text(json.dumps(recent_entry) + "\n", encoding="utf-8")
    # Only an observation from today exists -- nothing old enough to diff against.
    assert gc._no_op_proven_delta(current=4, days=7) is None


def test_record_no_op_proven_observation_appends_one_line(tmp_path, monkeypatch):
    history = tmp_path / "sub" / "no-op-proven-history.jsonl"
    monkeypatch.setattr(gc, "NO_OP_PROVEN_HISTORY_PATH", history)

    gc.record_no_op_proven_observation(2)
    gc.record_no_op_proven_observation(3)

    lines = history.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[-1])["no_op_proven"] == 3


def test_compute_growth_ceiling_never_raises_when_git_is_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(gc, "REPO_ROOT", tmp_path / "not-a-real-repo")
    monkeypatch.setattr(gc, "NO_OP_PROVEN_HISTORY_PATH", tmp_path / "history.jsonl")

    ceiling = gc.compute_growth_ceiling(no_op_proven=1, window_days=7)

    assert ceiling.requirements_added is None
    assert ceiling.decisions_added is None
