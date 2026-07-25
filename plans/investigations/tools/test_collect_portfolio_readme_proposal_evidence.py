# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: unit tests for RPOC-071's portfolio-summary aggregation logic
"""Unit tests for `collect_portfolio_readme_proposal_evidence.py::
compute_portfolio_summary_aggregates()` (RPOC-071, sprint charter Part B.2
Phase 5 Lane S / Part C.7).

Exercises the aggregation function in isolation with synthetic per-repo
result-dict fixtures -- one repo per `ReadmePocStatusV1` value, plus several
with `readme_poc_status` missing/`None` (the real portfolio run's actual
current shape, since RPOC-070's lifecycle field is brand new and nothing
populates it in production yet) -- so every count is proven correct
independent of whatever the live evidence run currently contains, and the
"handle `None`/missing status gracefully, not crash" requirement is a real
assertion, not just an absence of exceptions.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import get_args

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import collect_portfolio_readme_proposal_evidence as portfolio_tool  # noqa: E402

from readme_agent.state.lifecycle_schema import ReadmePocStatusV1  # noqa: E402

compute_portfolio_summary_aggregates = portfolio_tool.compute_portfolio_summary_aggregates
_missing_capability_tags = portfolio_tool._missing_capability_tags


def _ok_result(
    org_repo: str,
    *,
    verified: bool,
    failures: list[str] | None = None,
    ecosystem: str | None = "python",
    readme_poc_status: str | None = None,
    identical_rerun_noop: bool = False,
) -> dict:
    return {
        "org_repo": org_repo,
        "slug": org_repo.split("/", 1)[1].lower(),
        "status": "ok",
        "verified": verified,
        "failures": failures or [],
        "identical_rerun_noop": identical_rerun_noop,
        "ecosystem": ecosystem,
        "readme_poc_status": readme_poc_status,
    }


def _error_result(org_repo: str, *, ecosystem: str | None = "cpp") -> dict:
    return {
        "org_repo": org_repo,
        "slug": org_repo.split("/", 1)[1].lower(),
        "status": "error",
        "error": "boom",
        "traceback": "Traceback (most recent call last): ...",
        "ecosystem": ecosystem,
        "readme_poc_status": None,
    }


def test_processed_and_total_repositories_counts_pass_through():
    results = [_ok_result("org/a", verified=True), _ok_result("org/b", verified=False)]
    summary = compute_portfolio_summary_aggregates(results, total_repositories=31)
    assert summary["total_repositories"] == 31
    assert summary["processed_count"] == 2


def test_candidates_generated_reviewer_and_system_failure_counts():
    results = [
        _ok_result("org/a", verified=True),
        _ok_result("org/b", verified=False, failures=["something else went wrong"]),
        _error_result("org/c"),
    ]
    summary = compute_portfolio_summary_aggregates(results, total_repositories=3)
    assert summary["candidates_generated_count"] == 2  # both "ok" repos got a candidate
    assert summary["reviewer_accepted_count"] == 1
    assert summary["reviewer_rejected_count"] == 1
    assert summary["system_failures_count"] == 1


def test_blocked_facts_count_uses_missing_failure_text_only_among_ok_results():
    results = [
        _ok_result("org/a", verified=False, failures=["product.audience:missing is missing"]),
        _ok_result("org/b", verified=False, failures=["independent verification tampered"]),
        _error_result("org/c"),  # an error repo never reaches "is missing" territory
    ]
    summary = compute_portfolio_summary_aggregates(results, total_repositories=3)
    assert summary["blocked_facts_count"] == 1


def test_no_op_rerun_count():
    results = [
        _ok_result("org/a", verified=True, identical_rerun_noop=True),
        _ok_result("org/b", verified=True, identical_rerun_noop=False),
    ]
    summary = compute_portfolio_summary_aggregates(results, total_repositories=2)
    assert summary["no_op_rerun_count"] == 1


def test_status_distribution_covers_every_readme_poc_status_value_and_not_set():
    statuses = get_args(ReadmePocStatusV1)
    results = [
        _ok_result(f"org/repo-{i}", verified=True, readme_poc_status=status)
        for i, status in enumerate(statuses)
    ]
    # Several repos with no lifecycle record yet -- the real, expected shape today.
    results.append(_ok_result("org/untracked-1", verified=True, readme_poc_status=None))
    results.append(_error_result("org/untracked-2"))

    summary = compute_portfolio_summary_aggregates(results, total_repositories=len(results))

    distribution = summary["status_distribution"]
    assert set(distribution) == set(statuses) | {"not_set"}
    for status in statuses:
        assert distribution[status] == 1
    assert distribution["not_set"] == 2
    assert sum(distribution.values()) == len(results)


def test_status_distribution_handles_missing_key_not_just_none_value():
    result_without_key = {
        "org_repo": "org/legacy",
        "slug": "legacy",
        "status": "ok",
        "verified": True,
        "failures": [],
        "identical_rerun_noop": True,
        "ecosystem": "python",
        # no "readme_poc_status" key at all -- an older manifest's shape.
    }
    summary = compute_portfolio_summary_aggregates([result_without_key], total_repositories=1)
    assert summary["status_distribution"]["not_set"] == 1


def test_ecosystem_distribution_groups_by_existing_ecosystem_field():
    results = [
        _ok_result("org/a", verified=True, ecosystem="python"),
        _ok_result("org/b", verified=True, ecosystem="python"),
        _ok_result("org/c", verified=True, ecosystem="net"),
        _ok_result("org/d", verified=True, ecosystem=None),
    ]
    summary = compute_portfolio_summary_aggregates(results, total_repositories=4)
    assert summary["ecosystem_distribution"] == {"python": 2, "net": 1, "unknown": 1}


def test_missing_capability_distribution_counts_distinct_repos_per_tag():
    results = [
        _ok_result(
            "org/a",
            verified=False,
            failures=[
                "org/a: an operation cites an unaccepted fact",
                "org/a: independent validation failed: "
                "['x: product.audience:missing is missing', "
                "'x: product.audience:missing is missing']",  # repeated within one repo
            ],
        ),
        _ok_result(
            "org/b",
            verified=False,
            failures=[
                "org/b: independent validation failed: "
                "['x: product.audience:missing is missing', "
                "'x: installation.verified_acquisition:disposable-source-build is blocked', "
                "'selected verified minimal example is absent']"
            ],
        ),
    ]
    summary = compute_portfolio_summary_aggregates(results, total_repositories=2)
    distribution = summary["missing_capability_distribution"]
    assert distribution["product.audience:missing"] == 2  # recurs across both repos
    assert distribution["operation:unaccepted_fact_citation"] == 1
    assert distribution["installation.verified_acquisition:blocked"] == 1
    assert distribution["installation:verified_minimal_example_absent"] == 1


def test_missing_capability_tags_deduplicates_within_one_repo():
    tags = _missing_capability_tags(
        [
            "x: product.audience:missing is missing",
            "x: product.audience:missing is missing",
        ]
    )
    assert tags == {"product.audience:missing"}


def test_empty_results_produce_zeroed_aggregates_not_a_crash():
    summary = compute_portfolio_summary_aggregates([], total_repositories=31)
    assert summary["total_repositories"] == 31
    assert summary["processed_count"] == 0
    assert summary["candidates_generated_count"] == 0
    assert summary["reviewer_accepted_count"] == 0
    assert summary["reviewer_rejected_count"] == 0
    assert summary["blocked_facts_count"] == 0
    assert summary["system_failures_count"] == 0
    assert summary["no_op_rerun_count"] == 0
    assert sum(summary["status_distribution"].values()) == 0
    assert summary["ecosystem_distribution"] == {}
    assert summary["missing_capability_distribution"] == {}
