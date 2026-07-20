from readme_agent.readme.facts import (
    GapReportFacts,
    RepositoryFacts,
    compute_facts_hash,
    compute_tracked_content_hash,
    sha256_text,
)
from readme_agent.readme.gap_detector import GapReport


class TestSha256Text:
    def test_crlf_and_lf_produce_the_same_hash(self):
        lf = "line1\nline2\nline3\n"
        crlf = "line1\r\nline2\r\nline3\r\n"
        assert sha256_text(lf) == sha256_text(crlf)

    def test_different_content_hashes_differently(self):
        assert sha256_text("a") != sha256_text("b")


def _facts(**overrides) -> RepositoryFacts:
    defaults = dict(
        org_repo="aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
        commit_sha="abc123",
        manifest={"artifact_id": "aspose-cells-foss", "name": "Aspose.Cells FOSS"},
        detected_license="MIT",
        gap_report=GapReportFacts.from_gap_report(
            GapReport(
                license_mentioned=True,
                products_org_link=False,
                products_com_link=False,
                relationship_explained=False,
            )
        ),
        policy_content_hash="policyhash123",
        prompt_content_hash="prompthash123",
    )
    defaults.update(overrides)
    return RepositoryFacts(**defaults)


class TestComputeFactsHash:
    def test_identical_facts_hash_identically(self):
        assert compute_facts_hash(_facts()) == compute_facts_hash(_facts())

    def test_different_commit_sha_changes_the_hash(self):
        assert compute_facts_hash(_facts()) != compute_facts_hash(_facts(commit_sha="different"))

    def test_gap_report_does_not_affect_the_hash(self):
        """Deliberate, not an oversight: gap_report is *derived from* README
        content this tool itself rewrites, so it's an output of rendering,
        not an independent input fact. Hashing it made the hash structurally
        unable to ever match itself once a render closed a gap -- a real bug
        the orchestrator's idempotency test caught, not a hypothetical one."""
        changed = GapReportFacts.from_gap_report(
            GapReport(
                license_mentioned=True,
                products_org_link=True,
                products_com_link=False,
                relationship_explained=False,
            )
        )
        assert compute_facts_hash(_facts()) == compute_facts_hash(_facts(gap_report=changed))

    def test_different_policy_content_hash_changes_the_hash(self):
        assert compute_facts_hash(_facts()) != compute_facts_hash(
            _facts(policy_content_hash="other")
        )

    def test_different_prompt_content_hash_changes_the_hash(self):
        assert compute_facts_hash(_facts()) != compute_facts_hash(
            _facts(prompt_content_hash="other")
        )


class TestComputeTrackedContentHash:
    """Decision #38: the single, canonical content-level fingerprint both
    `orchestrator.py`'s durable-skip gate and (Wave 6's) readme_reconciliation
    specialist compare against -- never reimplemented a second time."""

    def test_identical_content_hashes_identically(self, tmp_path):
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")
        (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
        assert compute_tracked_content_hash(tmp_path) == compute_tracked_content_hash(tmp_path)

    def test_edited_readme_changes_the_hash(self, tmp_path):
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")
        before = compute_tracked_content_hash(tmp_path)
        (tmp_path / "README.md").write_text("hello world", encoding="utf-8")
        after = compute_tracked_content_hash(tmp_path)
        assert before != after

    def test_missing_files_produce_a_deterministic_sentinel_not_a_crash(self, tmp_path):
        result = compute_tracked_content_hash(tmp_path)
        assert isinstance(result, str)
        assert result == compute_tracked_content_hash(tmp_path)

    def test_adding_a_community_file_changes_the_hash(self, tmp_path):
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")
        before = compute_tracked_content_hash(tmp_path)
        (tmp_path / "CONTRIBUTING.md").write_text("please contribute", encoding="utf-8")
        after = compute_tracked_content_hash(tmp_path)
        assert before != after

    def test_unrelated_file_does_not_affect_the_hash(self, tmp_path):
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")
        before = compute_tracked_content_hash(tmp_path)
        (tmp_path / "some_other_file.txt").write_text("irrelevant", encoding="utf-8")
        after = compute_tracked_content_hash(tmp_path)
        assert before == after
