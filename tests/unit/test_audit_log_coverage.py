"""Tests for scripts/governance/audit_log_coverage.py -- the read-only detector that found the 10
real missing logs/ shards this project's coverage-enforcement layers exist because of. Uses the
injectable `commits` seam so these never shell out to git or touch the real repo, same pattern as
validate_plan_structure.py's `_USE_GIT`/`_USE_GIT_TEXTS`."""

from governance.audit_log_coverage import find_gaps


def _commit(sha="abc123def", date="2026-08-01", author="Someone", subject="a change", files=None):
    return {
        "sha": sha,
        "date": date,
        "author": author,
        "subject": subject,
        "files": files if files is not None else ["plans/master.md"],
    }


class TestFindGaps:
    def test_date_with_no_matching_shard_is_a_gap(self, tmp_path, monkeypatch):
        import governance.audit_log_coverage as alc

        monkeypatch.setattr(alc, "LOGS_DIR", tmp_path)  # empty -- no shard for any date

        gaps = find_gaps(commits=[_commit(date="2026-08-01")])

        assert [g["date"] for g in gaps] == ["2026-08-01"]
        assert gaps[0]["commits"][0]["sha"] == "abc123def"

    def test_date_with_an_existing_shard_is_not_a_gap(self, tmp_path, monkeypatch):
        import governance.audit_log_coverage as alc

        monkeypatch.setattr(alc, "LOGS_DIR", tmp_path)
        (tmp_path / "2026-08-01.md").write_text("already covered", encoding="utf-8")

        gaps = find_gaps(commits=[_commit(date="2026-08-01")])

        assert gaps == []

    def test_no_commits_at_all_means_no_gaps(self, tmp_path, monkeypatch):
        import governance.audit_log_coverage as alc

        monkeypatch.setattr(alc, "LOGS_DIR", tmp_path)

        assert find_gaps(commits=[]) == []

    def test_multiple_commits_on_the_same_date_are_grouped_into_one_gap(
        self, tmp_path, monkeypatch
    ):
        import governance.audit_log_coverage as alc

        monkeypatch.setattr(alc, "LOGS_DIR", tmp_path)
        commits = [
            _commit(sha="111", date="2026-08-01", subject="first change"),
            _commit(sha="222", date="2026-08-01", subject="second change"),
        ]

        gaps = find_gaps(commits=commits)

        assert len(gaps) == 1
        assert gaps[0]["date"] == "2026-08-01"
        assert [c["sha"] for c in gaps[0]["commits"]] == ["111", "222"]

    def test_gap_dates_are_returned_oldest_first(self, tmp_path, monkeypatch):
        import governance.audit_log_coverage as alc

        monkeypatch.setattr(alc, "LOGS_DIR", tmp_path)
        commits = [
            _commit(sha="333", date="2026-08-25"),
            _commit(sha="111", date="2026-08-01"),
            _commit(sha="222", date="2026-08-08"),
        ]

        gaps = find_gaps(commits=commits)

        assert [g["date"] for g in gaps] == ["2026-08-01", "2026-08-08", "2026-08-25"]

    def test_a_covered_date_and_a_gap_date_are_both_correctly_classified(
        self, tmp_path, monkeypatch
    ):
        import governance.audit_log_coverage as alc

        monkeypatch.setattr(alc, "LOGS_DIR", tmp_path)
        (tmp_path / "2026-08-08.md").write_text("covered", encoding="utf-8")
        commits = [_commit(sha="111", date="2026-08-01"), _commit(sha="222", date="2026-08-08")]

        gaps = find_gaps(commits=commits)

        assert [g["date"] for g in gaps] == ["2026-08-01"]
