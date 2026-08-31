"""Tests for scripts/governance/heal_log_coverage.py -- the one script in scripts/governance/
that's deliberately write- and push-capable outside a human `git commit`. `find_gaps` and the
git/validate tail (`_validate_commit_and_push`) are both monkeypatched out here so these tests
exercise the real skeleton-generation and orchestration logic (circuit breaker, dry-run) without
ever shelling out to git or running validate_plan_structure.py as a subprocess."""

from governance.heal_log_coverage import MAX_AUTO_HEAL_DATES, _skeleton_for_gap, heal


def _commit(sha="abc123def456", author="Someone", subject="a change", files=None):
    return {
        "sha": sha,
        "date": "2026-08-01",
        "author": author,
        "subject": subject,
        "files": files if files is not None else ["plans/master.md"],
    }


def _gap(date="2026-08-01", commits=None):
    return {"date": date, "commits": commits if commits is not None else [_commit()]}


class TestSkeletonForGap:
    def test_single_commit_uses_its_subject_as_title(self):
        gap = _gap(commits=[_commit(subject="fix(facts): provision dotnet 10 SDK")])

        skeleton = _skeleton_for_gap(gap)

        assert skeleton["title"] == "fix(facts): provision dotnet 10 SDK"
        assert skeleton["date"] == "2026-08-01"

    def test_multiple_commits_use_a_count_title(self):
        gap = _gap(commits=[_commit(sha="111"), _commit(sha="222"), _commit(sha="333")])

        skeleton = _skeleton_for_gap(gap)

        assert skeleton["title"] == "3 commits landed without a logs/ entry."

    def test_body_lists_every_commit_with_its_sha_author_subject_and_files(self):
        gap = _gap(
            commits=[
                _commit(
                    sha="abc123def456",
                    author="Codex",
                    subject="feat(registry): gate portfolios",
                    files=["plans/decisions/catalog.jsonl", "plans/master.md"],
                )
            ]
        )

        skeleton = _skeleton_for_gap(gap)

        assert "abc123def" in skeleton["body"]  # short sha
        assert "Codex" in skeleton["body"]
        assert "feat(registry): gate portfolios" in skeleton["body"]
        assert "plans/decisions/catalog.jsonl" in skeleton["body"]

    def test_a_file_outside_the_governed_set_does_not_crash_tag_inference(self):
        """audit_log_coverage.py's git pathspec should only ever put governed paths in `files`,
        but this is exactly the wrong place to let an unrecognized value raise inside an
        unattended CI job -- it must fall back gracefully instead."""
        gap = _gap(commits=[_commit(files=["data/products.json"])])

        skeleton = _skeleton_for_gap(gap)

        assert skeleton["tags"] == ["master", "auto-skeleton"]
        assert "data/products.json" in skeleton["body"]

    def test_tags_include_auto_skeleton_and_the_document_a_governed_file_belongs_to(self):
        gap = _gap(
            commits=[
                _commit(files=["plans/GOVERNANCE.md"]),
                _commit(sha="222", files=["plans/requirements/catalog.jsonl"]),
            ]
        )

        skeleton = _skeleton_for_gap(gap)

        assert "auto-skeleton" in skeleton["tags"]
        assert "governance" in skeleton["tags"]
        assert "requirements" in skeleton["tags"]
        assert "master" not in skeleton["tags"]

    def test_decisions_and_requirements_are_left_blank_for_a_human_enrichment_pass(self):
        skeleton = _skeleton_for_gap(_gap())

        assert skeleton["decisions"] == []
        assert skeleton["requirements"] == []
        assert skeleton["wave_phase"] == []


class TestHeal:
    def _set_logs_dir(self, tmp_path, monkeypatch):
        """`write_entry` (used by the real, non-dry-run path) reads/writes
        `log_shard_writer.LOGS_DIR`/`INDEX_FILE` at call time, so both need monkeypatching to a
        tmp_path fixture with a valid shard-directory table already present."""
        import governance.log_shard_writer as lsw

        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        index = logs_dir / "README.md"
        index.write_text(
            "# Project log\n\n## Shard directory\n\n| Date | File | Entries |\n|---|---|---:|\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(lsw, "LOGS_DIR", logs_dir)
        monkeypatch.setattr(lsw, "INDEX_FILE", index)
        return logs_dir

    def test_no_gaps_is_a_clean_noop(self, monkeypatch):
        import governance.heal_log_coverage as hlc

        monkeypatch.setattr(hlc, "find_gaps", lambda rev_range: [])
        finalize_calls = []
        monkeypatch.setattr(
            hlc, "_validate_commit_and_push", lambda dates: finalize_calls.append(dates)
        )

        exit_code = heal(None, dry_run=False)

        assert exit_code == 0
        assert finalize_calls == []

    def test_circuit_breaker_refuses_a_batch_over_the_threshold_without_writing(
        self, tmp_path, monkeypatch
    ):
        import governance.heal_log_coverage as hlc

        logs_dir = self._set_logs_dir(tmp_path, monkeypatch)
        too_many = [_gap(date=f"2026-08-{i:02d}") for i in range(1, MAX_AUTO_HEAL_DATES + 2)]
        monkeypatch.setattr(hlc, "find_gaps", lambda rev_range: too_many)
        finalize_calls = []
        monkeypatch.setattr(
            hlc, "_validate_commit_and_push", lambda dates: finalize_calls.append(dates)
        )

        exit_code = heal(None, dry_run=False)

        assert exit_code == 2
        assert finalize_calls == []
        assert list(logs_dir.glob("2026-*.md")) == []  # nothing written

    def test_dry_run_writes_nothing_and_never_calls_finalize(self, tmp_path, monkeypatch):
        import governance.heal_log_coverage as hlc

        logs_dir = self._set_logs_dir(tmp_path, monkeypatch)
        monkeypatch.setattr(hlc, "find_gaps", lambda rev_range: [_gap()])
        finalize_calls = []
        monkeypatch.setattr(
            hlc, "_validate_commit_and_push", lambda dates: finalize_calls.append(dates)
        )

        exit_code = heal(None, dry_run=True)

        assert exit_code == 0
        assert finalize_calls == []
        assert list(logs_dir.glob("2026-*.md")) == []

    def test_real_gap_writes_a_skeleton_shard_and_hands_off_to_finalize(
        self, tmp_path, monkeypatch
    ):
        import governance.heal_log_coverage as hlc

        logs_dir = self._set_logs_dir(tmp_path, monkeypatch)
        monkeypatch.setattr(hlc, "find_gaps", lambda rev_range: [_gap(date="2026-08-01")])
        finalize_calls = []
        monkeypatch.setattr(
            hlc,
            "_validate_commit_and_push",
            lambda dates: finalize_calls.append(dates) or 0,
        )

        exit_code = heal(None, dry_run=False)

        assert exit_code == 0
        assert finalize_calls == [["2026-08-01"]]
        shard = logs_dir / "2026-08-01.md"
        assert shard.exists()
        assert "auto-skeleton" in shard.read_text(encoding="utf-8")

    def test_finalize_failure_propagates_as_the_overall_exit_code(self, tmp_path, monkeypatch):
        import governance.heal_log_coverage as hlc

        self._set_logs_dir(tmp_path, monkeypatch)
        monkeypatch.setattr(hlc, "find_gaps", lambda rev_range: [_gap(date="2026-08-01")])
        monkeypatch.setattr(hlc, "_validate_commit_and_push", lambda dates: 1)

        exit_code = heal(None, dry_run=False)

        assert exit_code == 1
