"""Tests for bounded portfolio source-access preflight reuse."""

from argparse import Namespace

import pytest

from readme_agent.supervisor.portfolio_preflight_policy import (
    bounded_portfolio_facts_preflight_satisfied,
)


def _args(**updates) -> Namespace:
    values = {
        "_portfolio_member": True,
        "_portfolio_source_revision": "a" * 40,
        "execution_profile": "local_poc",
        "max_readme_poc_stage": "FACTS_READY",
    }
    values.update(updates)
    return Namespace(**values)


def test_registry_bound_facts_reuse_live_remote_head_proof() -> None:
    assert bounded_portfolio_facts_preflight_satisfied(_args())


@pytest.mark.parametrize(
    "updates",
    [
        {"_portfolio_member": False},
        {"_portfolio_source_revision": None},
        {"_portfolio_source_revision": "not-a-git-sha"},
        {"execution_profile": "local_inspect"},
        {"max_readme_poc_stage": "CANDIDATE_GENERATED"},
        {"max_readme_poc_stage": None},
    ],
)
def test_every_other_path_retains_normal_preflight(updates: dict[str, object]) -> None:
    assert not bounded_portfolio_facts_preflight_satisfied(_args(**updates))
