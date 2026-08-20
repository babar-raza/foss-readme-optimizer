"""Deterministic fact-to-cluster grouping, bounded at MAX_ACCEPTED_FACTS per cluster."""

from readme_agent.readme.section_cluster_planner import plan_section_clusters
from readme_agent.specialists.section_authoring_contracts import MAX_ACCEPTED_FACTS


def test_empty_fact_ids_yields_no_clusters():
    assert plan_section_clusters(section_id="overview", fact_ids=()) == ()


def test_under_cap_yields_one_cluster_with_bare_section_id():
    plans = plan_section_clusters(section_id="overview", fact_ids=["F.1", "F.2", "F.3"])

    assert len(plans) == 1
    assert plans[0].target_section_id == "overview"
    assert plans[0].accepted_fact_ids == ("F.1", "F.2", "F.3")


def test_exactly_at_cap_yields_one_cluster():
    fact_ids = [f"F.{i}" for i in range(MAX_ACCEPTED_FACTS)]

    plans = plan_section_clusters(section_id="limitations", fact_ids=fact_ids)

    assert len(plans) == 1
    assert plans[0].accepted_fact_ids == tuple(fact_ids)


def test_five_facts_split_into_two_clusters_each_under_cap():
    fact_ids = [f"F.{i}" for i in range(5)]

    plans = plan_section_clusters(section_id="limitations", fact_ids=fact_ids)

    assert len(plans) == 2
    assert [plan.target_section_id for plan in plans] == ["limitations-1", "limitations-2"]
    assert all(len(plan.accepted_fact_ids) <= MAX_ACCEPTED_FACTS for plan in plans)
    assert plans[0].accepted_fact_ids == ("F.0", "F.1", "F.2", "F.3")
    assert plans[1].accepted_fact_ids == ("F.4",)
    # every fact appears in exactly one cluster
    reassembled = [fact_id for plan in plans for fact_id in plan.accepted_fact_ids]
    assert reassembled == fact_ids


def test_duplicate_fact_ids_are_deduplicated_deterministically():
    plans = plan_section_clusters(section_id="overview", fact_ids=["F.1", "F.2", "F.1"])

    assert len(plans) == 1
    assert plans[0].accepted_fact_ids == ("F.1", "F.2")


def test_replanning_the_same_fact_ids_is_stable():
    fact_ids = [f"F.{i}" for i in range(9)]

    first = plan_section_clusters(section_id="capabilities", fact_ids=fact_ids)
    second = plan_section_clusters(section_id="capabilities", fact_ids=fact_ids)

    assert first == second
    assert len(first) == 3
    assert [plan.target_section_id for plan in first] == [
        "capabilities-1",
        "capabilities-2",
        "capabilities-3",
    ]


def test_invalid_max_facts_per_cluster_rejected():
    import pytest

    with pytest.raises(ValueError, match="at least 1"):
        plan_section_clusters(section_id="overview", fact_ids=["F.1"], max_facts_per_cluster=0)
