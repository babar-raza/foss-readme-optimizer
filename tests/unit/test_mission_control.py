"""Offline tests for the supervisor's central mission-taskcard consumer."""

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from readme_agent.errors import ConfigError
from readme_agent.facts.acceptance_contract import current_fact_acceptance_contract
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.registry.loader import load_products
from readme_agent.state.backend import SaveResult
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.mission_goal_schema import MissionContributionEvidenceV1
from readme_agent.state.schema import MissionExecutionStateV1, RunStateV1
from readme_agent.supervisor.mission_control import (
    claim_next_task,
    evaluate_mission,
    has_graph_drift,
    mission_state_key,
    persist_evaluation,
    transition_task,
)
from readme_agent.supervisor.mission_goal_guard import (
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)
from readme_agent.supervisor.mission_graph import load_mission_graph
from readme_agent.supervisor.mission_lifecycle_freshness import (
    evaluate_lifecycle_fact_freshness,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_GRAPH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)


def _load_tool_module(name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _MemoryStateBackend:
    def __init__(self) -> None:
        self.records: dict[str, RunStateV1] = {}

    def load(self, org_repo: str) -> RunStateV1 | None:
        record = self.records.get(org_repo)
        return deepcopy(record) if record is not None else None

    def save(self, org_repo: str, state: RunStateV1, expected_version: int | None) -> SaveResult:
        current = self.records.get(org_repo)
        current_version = current.state_version if current is not None else None
        if expected_version != current_version:
            return SaveResult(outcome="stale", new_version=current_version)
        new_version = (current_version or 0) + 1
        self.records[org_repo] = state.model_copy(
            update={"org_repo": org_repo, "state_version": new_version}
        )
        return SaveResult(outcome="saved", new_version=new_version)


def _write_contribution_evidence(
    tmp_path: Path,
    backend: _MemoryStateBackend,
    task,
) -> Path:
    proof_path = tmp_path / f"{task.task_id}-proof.txt"
    proof_path.write_text("independent task proof", encoding="utf-8")
    scoreboard = derive_lifecycle_scoreboard(backend)
    scoreboard_hash = lifecycle_scoreboard_sha256(scoreboard)
    evidence = MissionContributionEvidenceV1(
        task_id=task.task_id,
        stage_goal_id=task.stage_goal_id,
        campaign_id=task.campaign_id,
        goal_ids=task.goal_ids,
        core_contribution=task.core_contribution,
        acceptance_checks_passed=task.acceptance_checks,
        proof_refs=[str(proof_path)],
        scoreboard_before_sha256=scoreboard_hash,
        scoreboard_after_sha256=scoreboard_hash,
        first_failing_boundary_before=scoreboard.first_failing_boundary,
        first_failing_boundary_after=scoreboard.first_failing_boundary,
        independently_verified=True,
    )
    evidence_path = tmp_path / f"{task.task_id}-contribution.json"
    evidence_path.write_text(evidence.model_dump_json(indent=2), encoding="utf-8")
    return evidence_path


def test_real_level8_graph_is_schema_valid_and_acyclic():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)

    assert graph.mission_authority.mission_id == "LEVEL8-CENTRAL-REPOSITORY-PRESENTATION"
    assert graph.autonomous_execution_contract.mechanism_locked is True
    assert len(graph.taskcards) >= 30
    assert len(graph_hash) == 64
    tasks = {task.task_id: task for task in graph.taskcards}
    assert tasks["L8-TRUTH-01A-FACT-CONTRACT"].goal_ids == ["GOAL-TRUTH"]
    assert tasks["L8-COMPOSE-02-EXISTING-SECTIONS"].goal_ids == ["GOAL-README"]
    assert tasks["L8-WAVE4-PRESENTATION-INTELLIGENCE"].goal_ids == [
        "GOAL-README",
        "GOAL-PROFILE",
    ]
    assert tasks["L8-MISSION-GOAL-GUARD"].goal_ids == ["GOAL-AUTONOMY"]
    assert tasks["L8-WAVE5-VERIFIED-PROPOSAL-LIFECYCLE"].goal_ids == ["GOAL-DELIVERY"]
    assert tasks["L8-WAVE8-NINETY-DAY-SELF-MAINTENANCE"].goal_ids == ["GOAL-MATURITY"]
    assert tasks["L8-VPY-00-GOLDEN-TEMPLATE"].dependencies == [
        "L8-PLAN-RECONCILIATION-ACCELERATION"
    ]
    assert tasks["L8-ACCEL-00-PYTHON-READINESS"].dependencies == ["L8-VPY-00-GOLDEN-TEMPLATE"]
    assert tasks["L8-VPY-01-NOTE-VERIFIED-CANARY"].dependencies == ["L8-ACCEL-00-PYTHON-READINESS"]
    assert tasks["L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES"].dependencies == [
        "L8-ACCEL-00-PYTHON-READINESS"
    ]
    assert tasks["L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES"].dependencies == [
        "L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES"
    ]
    assert tasks["L8-VPY-03-ALL-PYTHON-VERIFIED-POC"].dependencies == [
        "L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES"
    ]
    goals = {goal.goal_id: goal for goal in graph.mission_authority.stage_goal_catalog}
    campaigns = {campaign.campaign_id: campaign for campaign in graph.campaign_catalog}
    assert list(campaigns) == [
        "CAMP-PLAN-FREEZE",
        "CAMP-SHARED-ACCELERATION",
        "CAMP-THREE-SLICES",
        "CAMP-PYTHON-PORTFOLIO",
        "CAMP-GATE-A-PORTFOLIO",
        "CAMP-GATE-B-AND-LATER",
    ]
    assert all(
        task.campaign_id is None
        for task in graph.taskcards
        if task.stage_goal_id.startswith("GOAL-T")
    )
    assert all(
        task.campaign_id is not None
        for task in graph.taskcards
        if not task.stage_goal_id.startswith("GOAL-T")
    )
    assert goals["GOAL-V0-VERIFIED-PYTHON-POC"].execution_required is True
    assert goals["GOAL-TP-TRUSTED-COHORT-POC"].execution_required is False
    assert tasks["TRP-04P-COHORT-FREEZE"].dependencies == ["TRP-03-INDEPENDENT-FIDELITY-REVIEW"]
    assert tasks["TRP-04-CANARY-QUALIFICATION"].dependencies == ["TRP-04P-POC-PRESENTATION"]
    assert tasks["TRP-04-CANARY-QUALIFICATION"].stage_goal_id == (
        "GOAL-T0R-TRUSTED-ADVERSARIAL-QUALIFICATION"
    )
    local_poc_children = {
        task.task_id
        for task in graph.taskcards
        if task.parent_task_id == "L8-LOCAL-README-PROPOSAL-PROOF"
    }
    assert {
        "L8-LOCAL-PORTFOLIO-RUNTIME",
        "L8-LOCAL-PORTFOLIO-PRODUCT-TRUTH",
        "L8-LOCAL-README-ASSESSMENT-COMPOSITION",
        "L8-LOCAL-INDEPENDENT-REVIEW-REPAIR",
        "L8-LOCAL-HETEROGENEOUS-QUALIFICATION",
        "L8-LOCAL-FULL-REGISTRY-GATE-A",
    } <= local_poc_children
    assert tasks["L8-LOCAL-HUMAN-REVIEW-GATE-B"].dependencies == ["L8-LOCAL-FULL-REGISTRY-GATE-A"]
    assert (
        "L8-LOCAL-HUMAN-REVIEW-GATE-B" in tasks["L8-WAVE5-VERIFIED-PROPOSAL-LIFECYCLE"].dependencies
    )
    assert tasks["L8-GATE-C-VERIFIED-JAVA-PROPOSAL-PROOF"].dependencies == [
        "L8-WAVE5-VERIFIED-PROPOSAL-LIFECYCLE"
    ]
    assert tasks["L8-GATE-D-GITHUB-APP-INTEGRATION"].dependencies == [
        "L8-GATE-C-VERIFIED-JAVA-PROPOSAL-PROOF"
    ]
    assert tasks["L8-WAVE6-CONTROLLED-JAVA-PILOT"].dependencies == [
        "L8-GATE-D-GITHUB-APP-INTEGRATION"
    ]
    assert tasks["L8-WAVE7-LEVEL6-AUTONOMOUS-PORTFOLIO"].dependencies == [
        "L8-WAVE6-CONTROLLED-JAVA-PILOT"
    ]
    assert tasks["L8-WAVE7-HETEROGENEOUS-PORTFOLIO"].dependencies == [
        "L8-WAVE7-LEVEL6-AUTONOMOUS-PORTFOLIO"
    ]


def test_stage_goals_derive_advance_and_reactivate_without_manual_selection():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = {task.task_id: "CLOSED" for task in graph.taskcards}
    statuses["L8-VPY-00-GOLDEN-TEMPLATE"] = "TODO"
    statuses["L8-PLAN-RECONCILIATION-ACCELERATION"] = "CLOSED"
    statuses["L8-INTAKE-02-READONLY-PREFLIGHT-ENROLLMENT"] = "TODO"
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
        active_goal_id="GOAL-V2-VERIFIED-GATE-A",
    )

    qualification = evaluate_mission(graph, state)
    assert qualification.active_goal_id == "GOAL-V0-VERIFIED-PYTHON-POC"
    assert qualification.concurrent_goal_ids == ["GOAL-C0-AUTHORIZED-PORTFOLIO"]
    assert [task.task_id for task in qualification.eligible_tasks[:2]] == [
        "L8-VPY-00-GOLDEN-TEMPLATE",
        "L8-INTAKE-02-READONLY-PREFLIGHT-ENROLLMENT",
    ]
    assert qualification.next_task is not None
    assert qualification.next_task.campaign_id == "CAMP-SHARED-ACCELERATION"

    after_qualification = state.model_copy(
        update={
            "task_statuses": {
                **statuses,
                "L8-VPY-00-GOLDEN-TEMPLATE": "CLOSED",
            }
        }
    )
    intake = evaluate_mission(graph, after_qualification)
    assert intake.active_goal_id == "GOAL-C0-AUTHORIZED-PORTFOLIO"
    assert intake.concurrent_goal_ids == []

    preserved_trusted_statuses = {
        **after_qualification.task_statuses,
        "L8-INTAKE-02-READONLY-PREFLIGHT-ENROLLMENT": "CLOSED",
        "TRP-05-FULL-REGISTRY-TRANSFORM": "TODO",
    }
    preserved_trusted = evaluate_mission(
        graph,
        after_qualification.model_copy(update={"task_statuses": preserved_trusted_statuses}),
    )
    assert preserved_trusted.active_goal_id is None
    assert "TRP-05-FULL-REGISTRY-TRANSFORM" not in preserved_trusted.unresolved_task_ids

    reopened = evaluate_mission(
        graph,
        after_qualification.model_copy(
            update={
                "task_statuses": {
                    **preserved_trusted_statuses,
                    "TRP-01-README-DERIVED-FACTS": "REGRESSED",
                }
            }
        ),
    )
    assert reopened.active_goal_id is None
    assert "TRP-01-README-DERIVED-FACTS" not in reopened.unresolved_task_ids
    tasks = {task.task_id: task for task in graph.taskcards}
    local_wave3 = tasks["L8-WAVE3-LOCAL-PRODUCT-TRUTH-FOUNDATION"]
    assert local_wave3.dependencies == ["L8-WAVE1-CANONICAL-SAFETY-SPINE"]
    assert (
        "L8-WAVE3-LOCAL-PRODUCT-TRUTH-FOUNDATION"
        in tasks["L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP"].dependencies
    )
    local_wave4 = tasks["L8-WAVE4-LOCAL-PRESENTATION-PLAN-FOUNDATION"]
    assert local_wave4.dependencies == ["L8-WAVE3-LOCAL-PRODUCT-TRUTH-FOUNDATION"]
    assert (
        "L8-WAVE4-LOCAL-PRESENTATION-PLAN-FOUNDATION"
        in tasks["L8-WAVE4-PRESENTATION-INTELLIGENCE"].dependencies
    )
    preproduction = tasks["L8-PREPRODUCTION-IDEA-FIDELITY-GATE"]
    assert preproduction.dependencies == ["L8-WAVE4-LOCAL-PRESENTATION-PLAN-FOUNDATION"]
    assert (
        "L8-PREPRODUCTION-IDEA-FIDELITY-GATE"
        in tasks["L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME"].dependencies
    )
    coverage = graph.requirement_coverage
    assert coverage is not None
    coverage_tool = _load_tool_module(
        "build_level8_requirement_taskcard_coverage_contract",
        "scripts/governance/build_level8_requirement_taskcard_coverage.py",
    )
    expected_graph, expected_report = coverage_tool.build_coverage()
    expected_coverage = expected_graph["requirement_coverage"]
    assert coverage.total_requirement_rows == expected_coverage["total_requirement_rows"]
    assert coverage.mandatory_requirement_rows == expected_coverage["mandatory_requirement_rows"]
    assert coverage.reopened_implemented_rows == expected_coverage["reopened_implemented_rows"]
    assert len({mapping.requirement_id for mapping in coverage.mappings}) == len(
        expected_coverage["mappings"]
    )
    assert expected_report["unmapped_requirement_ids"] == []
    l8_mapping = next(
        mapping for mapping in coverage.mappings if mapping.requirement_id == "L8-011"
    )
    assert l8_mapping.task_id == "L8-WAVE8-NINETY-DAY-SELF-MAINTENANCE"
    auth_mapping = next(
        mapping for mapping in coverage.mappings if mapping.requirement_id == "AUTH-008"
    )
    assert auth_mapping.task_id == "TRP-05C-GITHUB-APP-HOSTED-QUALIFICATION"
    finalized_readme_mapping = next(
        mapping for mapping in coverage.mappings if mapping.requirement_id == "RDM-026"
    )
    assert finalized_readme_mapping.task_id == "L8-VPY-03-ALL-PYTHON-VERIFIED-POC"
    hosted_revalidation_mapping = next(
        mapping for mapping in coverage.mappings if mapping.requirement_id == "L8-001"
    )
    assert hosted_revalidation_mapping.task_id == "L8-GATE-D-GITHUB-APP-INTEGRATION"
    preproduction_mapping = next(
        mapping for mapping in coverage.mappings if mapping.requirement_id == "L8-014"
    )
    assert preproduction_mapping.task_id == "L8-PREPRODUCTION-IDEA-FIDELITY-GATE"
    requirements_path = REPO_ROOT / coverage.source_path
    assert coverage.source_sha256 == coverage_tool.canonical_text_sha256(requirements_path)


def test_preserved_trusted_goals_cannot_regain_execution_authority():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = {task.task_id: "CLOSED" for task in graph.taskcards}
    statuses["TRP-04P-COHORT-FREEZE"] = "TODO"
    statuses["TRP-04-CANARY-QUALIFICATION"] = "TODO"
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    evaluation = evaluate_mission(graph, state)
    assert evaluation.active_goal_id is None
    assert evaluation.next_task is None
    assert "TRP-04P-COHORT-FREEZE" not in evaluation.unresolved_task_ids
    assert "TRP-04-CANARY-QUALIFICATION" not in evaluation.unresolved_task_ids


def test_verified_python_goal_is_the_first_executable_goal_after_assurance():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = {task.task_id: "CLOSED" for task in graph.taskcards}
    statuses["L8-VPY-00-GOLDEN-TEMPLATE"] = "TODO"
    statuses["TRP-04P-COHORT-FREEZE"] = "TODO"
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    evaluation = evaluate_mission(graph, state)

    assert evaluation.active_goal_id == "GOAL-V0-VERIFIED-PYTHON-POC"
    assert evaluation.next_task is not None
    assert evaluation.next_task.task_id == "L8-VPY-00-GOLDEN-TEMPLATE"


def test_terminal_exception_stage_does_not_starve_later_ready_work():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = {task.task_id: "CLOSED" for task in graph.taskcards}
    statuses.update(
        {
            "L8-WAVE0-PLAN-TRUTH-RECONCILIATION": "REROUTED",
            "L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME": "BLOCKED_EXTERNAL",
            "L8-PREPRODUCTION-IDEA-FIDELITY-GATE": "REROUTED",
            "TRP-04P-COHORT-FREEZE": "TODO",
        }
    )
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    evaluation = evaluate_mission(graph, state)

    assert evaluation.active_goal_id is None
    assert evaluation.next_task is None
    assert "L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME" in evaluation.blocked_external_task_ids
    assert evaluation.mission_complete is False


def test_requirement_coverage_source_hash_is_line_ending_independent(tmp_path: Path):
    coverage_tool = _load_tool_module(
        "build_level8_requirement_taskcard_coverage_line_endings",
        "scripts/governance/build_level8_requirement_taskcard_coverage.py",
    )
    lf_path = tmp_path / "requirements-lf.md"
    crlf_path = tmp_path / "requirements-crlf.md"
    lf_path.write_bytes(b"# Requirements\n\n| ID | Status |\n")
    crlf_path.write_bytes(b"# Requirements\r\n\r\n| ID | Status |\r\n")

    assert coverage_tool.canonical_text_sha256(lf_path) == coverage_tool.canonical_text_sha256(
        crlf_path
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda task: task.pop("goal_ids"), "invalid mission task graph"),
        (
            lambda task: task.update(goal_ids=["GOAL-NARRATIVE-ONLY"]),
            "invalid mission task graph",
        ),
        (
            lambda task: task["core_contribution"].update(
                summary="complete the task and support the mission"
            ),
            "vague core contribution",
        ),
    ],
)
def test_graph_rejects_missing_unknown_or_vague_goal_bindings(tmp_path, mutation, message):
    raw = yaml.safe_load(REAL_GRAPH.read_text(encoding="utf-8"))
    mutation(raw["taskcards"][0])
    invalid = tmp_path / "invalid-goal-binding.yaml"
    invalid.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_mission_graph(invalid)


def test_dynamic_scoreboard_counts_durable_lifecycle_progress(tmp_path):
    products = list(load_products())[:6]
    products_path = tmp_path / "products.json"
    source_products = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    selected_org_repos = {entry.org_repo for entry in products}
    products_path.write_text(
        json.dumps(
            [
                item
                for item in source_products
                if f"{item['repo_url'].split('/')[3]}/{item['repo_name']}" in selected_org_repos
            ]
        ),
        encoding="utf-8",
    )
    backend = _MemoryStateBackend()
    statuses = (
        "FACTS_READY",
        "CANDIDATE_GENERATED",
        "DETERMINISTIC_VALIDATED",
        "AGENT_APPROVED",
        "NO_OP_PROVEN",
        "HUMAN_ACCEPTED",
    )
    for entry, status in zip(products, statuses, strict=True):
        backend.records[entry.org_repo] = RunStateV1(
            org_repo=entry.org_repo,
            readme_poc_lifecycle=ReadmePocLifecycleStateV2(status=status),
        )

    scoreboard = derive_lifecycle_scoreboard(
        backend,
        products_path=products_path,
        verify_acceptance_freshness=False,
    )

    assert scoreboard.denominator == 6
    assert (
        scoreboard.facts_ready,
        scoreboard.candidate_generated,
        scoreboard.deterministic_validated,
        scoreboard.agent_approved,
        scoreboard.no_op_proven,
        scoreboard.human_accepted,
    ) == (6, 5, 4, 3, 2, 1)
    assert scoreboard.first_failing_boundary == "CANDIDATE_GENERATED"


def test_dynamic_scoreboard_builds_fact_contract_per_registry_entry(tmp_path, monkeypatch):
    source_products = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    selected = [
        item
        for item in source_products
        if item["ecosystem"] == "python" and item["family"] in {"3d", "barcode"}
    ]
    products_path = tmp_path / "products.json"
    products_path.write_text(json.dumps(selected), encoding="utf-8")
    observed: list[tuple[str | None, str | None]] = []

    def contract(ecosystem=None, family=None):
        observed.append((ecosystem, family))
        return object()

    monkeypatch.setattr(
        "readme_agent.supervisor.mission_goal_guard.current_fact_acceptance_contract",
        contract,
    )

    scoreboard = derive_lifecycle_scoreboard(_MemoryStateBackend(), products_path=products_path)

    assert scoreboard.denominator == 2
    assert observed == [("python", "3d"), ("python", "barcode")]


def test_dynamic_scoreboard_reports_raw_but_excludes_stale_acceptance(
    tmp_path,
    monkeypatch,
):
    entry = load_products()[0]
    products_path = tmp_path / "products.json"
    source_products = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    products_path.write_text(
        json.dumps(
            [
                item
                for item in source_products
                if f"{item['repo_url'].split('/')[3]}/{item['repo_name']}" == entry.org_repo
            ]
        ),
        encoding="utf-8",
    )
    backend = _MemoryStateBackend()
    backend.records[entry.org_repo] = RunStateV1(
        org_repo=entry.org_repo,
        readme_poc_lifecycle=ReadmePocLifecycleStateV2(
            status="NO_OP_PROVEN",
            source_revision="a" * 40,
        ),
    )
    monkeypatch.setattr(
        "readme_agent.supervisor.mission_goal_guard.evaluate_lifecycle_fact_freshness",
        lambda *args, **kwargs: type(
            "Decision",
            (),
            {"reusable": True, "mismatch_reasons": []},
        )(),
    )
    monkeypatch.setattr(
        "readme_agent.supervisor.local_poc_cache.evaluate_completed_local_poc_cache",
        lambda *args, **kwargs: type(
            "Decision",
            (),
            {
                "reusable": False,
                "mismatch_reasons": ["current_template_hash_mismatch"],
            },
        )(),
    )

    scoreboard = derive_lifecycle_scoreboard(backend, products_path=products_path)

    assert scoreboard.raw_agent_approved == 1
    assert scoreboard.raw_no_op_proven == 1
    assert scoreboard.agent_approved == 0
    assert scoreboard.no_op_proven == 0
    assert scoreboard.stale_acceptance_repositories == {
        entry.org_repo: ["current_template_hash_mismatch"]
    }
    assert scoreboard.first_failing_boundary == "AGENT_APPROVED"


def test_dynamic_scoreboard_reports_raw_but_excludes_stale_fact_contract(
    tmp_path,
    monkeypatch,
):
    entry = load_products()[0]
    products_path = tmp_path / "products.json"
    source_products = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    products_path.write_text(
        json.dumps(
            [
                item
                for item in source_products
                if f"{item['repo_url'].split('/')[3]}/{item['repo_name']}" == entry.org_repo
            ]
        ),
        encoding="utf-8",
    )
    backend = _MemoryStateBackend()
    backend.records[entry.org_repo] = RunStateV1(
        org_repo=entry.org_repo,
        readme_poc_lifecycle=ReadmePocLifecycleStateV2(
            status="DETERMINISTIC_VALIDATED",
            source_revision="a" * 40,
        ),
    )
    monkeypatch.setattr(
        "readme_agent.supervisor.mission_goal_guard.evaluate_lifecycle_fact_freshness",
        lambda *args, **kwargs: type(
            "Decision",
            (),
            {
                "reusable": False,
                "mismatch_reasons": ["fact_acceptance_contract_hash_changed"],
            },
        )(),
    )

    scoreboard = derive_lifecycle_scoreboard(backend, products_path=products_path)

    assert (
        scoreboard.raw_facts_ready,
        scoreboard.raw_candidate_generated,
        scoreboard.raw_deterministic_validated,
    ) == (1, 1, 1)
    assert (
        scoreboard.facts_ready,
        scoreboard.candidate_generated,
        scoreboard.deterministic_validated,
    ) == (0, 0, 0)
    assert scoreboard.stale_fact_contract_repositories == {
        entry.org_repo: ["fact_acceptance_contract_hash_changed"]
    }
    assert scoreboard.first_failing_boundary == "FACTS_READY"


def test_fact_freshness_reuses_public_truth_contract_without_state_mutation(tmp_path):
    org_repo = "org/repo"
    source_revision = "a" * 40
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://org/repo",
        source_revision=source_revision,
    )
    renderable_values = {
        "product.audience": ["Developers using Python"],
        "product.problems_solved": ["Process note files"],
        "product.capabilities": ["Create and inspect notes"],
        "product.formats": ["ONE"],
    }
    records = [
        FactRecordV2(
            fact_id=descriptive_fact_id(field, "mission-freshness-fixture"),
            field=field,
            value=renderable_values.get(field, {"field": field}),
            source=source,
            verification_state="verified",
            authoritative_owner="repository-owner",
            confidence=1.0,
            affected_surfaces=["readme"],
        )
        for field in REQUIRED_PRODUCT_FIELDS
    ]
    facts = ProductFactsV2(
        org_repo=org_repo,
        facts=records,
        selected_fact_ids={fact.field: fact.fact_id for fact in records},
    )
    contract = current_fact_acceptance_contract()
    verification_hash = "b" * 64
    lifecycle = ReadmePocLifecycleStateV2(
        status="FACTS_READY",
        source_revision=source_revision,
        facts_hash=facts.canonical_hash(),
        fact_acceptance_contract_hash=contract.canonical_hash(),
        fact_acceptance_component_hashes=contract.component_hashes,
    )
    state = RunStateV1(org_repo=org_repo, readme_poc_lifecycle=lifecycle)
    bundle_dir = tmp_path / "bundle"
    (bundle_dir / "facts").mkdir(parents=True)
    (bundle_dir / "facts" / "product-facts.json").write_text(
        facts.model_dump_json(), encoding="utf-8"
    )
    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                "org_repo": org_repo,
                "source_revision": source_revision,
                "facts_hash": facts.canonical_hash(),
                "content_assurance": "repository_verified",
                "fact_acceptance_contract_hash": contract.canonical_hash(),
                "fact_acceptance_component_hashes": contract.component_hashes,
                "local_verification_contract_hash": verification_hash,
            }
        ),
        encoding="utf-8",
    )
    state_before = state.model_dump(mode="json")

    decision = evaluate_lifecycle_fact_freshness(
        state,
        bundle_dir,
        current_contract=contract,
        current_local_verification_hash=verification_hash,
    )

    assert decision.reusable is True
    assert decision.mismatch_reasons == []
    assert state.model_dump(mode="json") == state_before

    lifecycle.fact_acceptance_contract_hash = "0" * 64
    classification_only_change = evaluate_lifecycle_fact_freshness(
        state,
        bundle_dir,
        current_contract=contract,
        current_local_verification_hash=verification_hash,
    )
    assert classification_only_change.reusable is True

    lifecycle.fact_acceptance_component_hashes = {
        **contract.component_hashes,
        "fact_schema": "0" * 64,
    }
    recollection_change = evaluate_lifecycle_fact_freshness(
        state,
        bundle_dir,
        current_contract=contract,
        current_local_verification_hash=verification_hash,
    )
    assert recollection_change.reusable is False
    assert recollection_change.mismatch_reasons == [
        "fact_acceptance_recollection_component_changed"
    ]

    lifecycle.fact_acceptance_contract_hash = contract.canonical_hash()
    lifecycle.fact_acceptance_component_hashes = contract.component_hashes
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("content_assurance")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    missing_assurance = evaluate_lifecycle_fact_freshness(
        state,
        bundle_dir,
        current_contract=contract,
        current_local_verification_hash=verification_hash,
    )
    assert missing_assurance.reusable is False
    assert missing_assurance.mismatch_reasons == ["manifest_content_assurance_mismatch"]

    manifest["content_assurance"] = "repository_verified"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (bundle_dir / "facts" / "proposed-product-truth.json").write_text("{}", encoding="utf-8")
    lifecycle.prompt_hash = "0" * 64
    stale_prompt = evaluate_lifecycle_fact_freshness(
        state,
        bundle_dir,
        current_contract=contract,
        current_local_verification_hash=verification_hash,
    )
    assert stale_prompt.reusable is False
    assert stale_prompt.mismatch_reasons == ["draft_product_truth_prompt_hash_changed"]


def test_lifecycle_scoreboard_registry_hash_is_line_ending_independent(tmp_path: Path):
    source = (REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8")
    canonical = source.replace("\r\n", "\n").replace("\r", "\n")
    products_path = tmp_path / "products.json"
    backend = _MemoryStateBackend()

    products_path.write_bytes(canonical.encode("utf-8"))
    lf_scoreboard = derive_lifecycle_scoreboard(backend, products_path=products_path)
    products_path.write_bytes(canonical.replace("\n", "\r\n").encode("utf-8"))
    crlf_scoreboard = derive_lifecycle_scoreboard(backend, products_path=products_path)

    assert lf_scoreboard.registry_sha256 == crlf_scoreboard.registry_sha256
    assert lifecycle_scoreboard_sha256(lf_scoreboard) == lifecycle_scoreboard_sha256(
        crlf_scoreboard
    )


def test_requirement_coverage_classifier_handles_every_extractor_status():
    extractor = _load_tool_module(
        "extract_requirements_for_status_contract",
        "plans/investigations/tools/extract_requirements.py",
    )
    classifier = _load_tool_module(
        "coverage_classify_for_status_contract",
        "plans/investigations/tools/coverage_classify.py",
    )

    assert set(classifier.STATUS_DEFAULT) == extractor.VALID_STATUSES


def test_evaluate_initializes_and_preserves_the_bootstrap_claim():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()

    first = persist_evaluation(backend, graph, graph_hash)
    second = persist_evaluation(backend, graph, graph_hash)

    assert first.state_version == 1
    assert second.state_version == 2
    state = second.mission_execution
    assert state is not None
    assert state.active_task_id == "L8-MISSION-CONTROL-CONSUMER"
    assert state.task_statuses[state.active_task_id] == "IN_PROGRESS"
    evaluation = evaluate_mission(graph, state)
    assert evaluation.mission_complete is False
    assert state.lifecycle_scoreboard is not None
    assert state.lifecycle_scoreboard.denominator == len(load_products())
    assert state.next_task is not None
    assert state.next_task.task_id == state.active_task_id
    assert evaluation.core_goal_active is True


def test_read_only_evaluation_accepts_a_new_graph_task_before_state_reconciliation():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = {task.task_id: task.status for task in graph.taskcards}
    statuses.pop("L8-PREPRODUCTION-IDEA-FIDELITY-GATE")
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    evaluation = evaluate_mission(graph, state)

    assert "L8-PREPRODUCTION-IDEA-FIDELITY-GATE" in evaluation.unresolved_task_ids
    assert evaluation.mission_complete is False


def test_claim_is_idempotent_while_a_task_is_already_active():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    persist_evaluation(backend, graph, graph_hash)

    first = claim_next_task(backend, graph, graph_hash, claimed_by="test-worker")
    second = claim_next_task(backend, graph, graph_hash, claimed_by="other-worker")

    assert first.mission_execution is not None
    assert second.mission_execution is not None
    assert first.mission_execution.active_task_id == second.mission_execution.active_task_id
    assert first.mission_execution.claim_id is not None
    assert second.mission_execution.claim_id == first.mission_execution.claim_id
    assert second.mission_execution.claimed_by == first.mission_execution.claimed_by
    assert second.state_version == first.state_version


def test_closeout_ladder_then_claims_exactly_one_dependency_ready_task(tmp_path):
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    persist_evaluation(backend, graph, graph_hash)
    task_id = "L8-MISSION-CONTROL-CONSUMER"
    task = next(task for task in graph.taskcards if task.task_id == task_id)
    contribution_evidence = _write_contribution_evidence(tmp_path, backend, task)

    for status in ("IMPLEMENTED", "VERIFIED", "SCORED", "CLOSED"):
        record = transition_task(
            backend,
            graph,
            graph_hash,
            task_id=task_id,
            to_status=status,
            observed_by="test-verifier",
            reason=f"test transition to {status}",
            evidence_refs=(
                [str(contribution_evidence)]
                if status == "CLOSED"
                else [f"evidence/{status.lower()}.json"]
            ),
        )

    state = record.mission_execution
    assert state is not None
    evaluation = evaluate_mission(graph, state)
    assert [task.task_id for task in evaluation.eligible_tasks] == [
        "L8-MISSION-GOAL-GUARD",
        "L8-PLAN-RECONCILIATION-ACCELERATION",
        "L8-REQUIREMENT-TO-TASKCARD-COVERAGE",
    ]

    claimed = claim_next_task(backend, graph, graph_hash, claimed_by="test-worker")
    assert claimed.mission_execution is not None
    assert claimed.mission_execution.active_task_id == "L8-MISSION-GOAL-GUARD"


def test_rerouted_parent_does_not_unlock_dependent_tasks():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = {task.task_id: task.status for task in graph.taskcards}
    statuses.update(
        {
            "L8-MISSION-CONTROL-CONSUMER": "CLOSED",
            "L8-REQUIREMENT-TO-TASKCARD-COVERAGE": "CLOSED",
            "L8-WAVE0-PLAN-TRUTH-RECONCILIATION": "REROUTED",
        }
    )
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    eligible = [task.task_id for task in evaluate_mission(graph, state).eligible_tasks]

    assert eligible == [
        "L8-MISSION-GOAL-GUARD",
        "L8-PLAN-RECONCILIATION-ACCELERATION",
    ]
    assert "L8-WAVE1-CANONICAL-SAFETY-SPINE" not in eligible


def test_graph_drift_is_visible_to_read_only_status():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256="0" * 64,
        task_statuses={task.task_id: task.status for task in graph.taskcards},
    )

    assert has_graph_drift(state, graph_hash) is True


def test_expired_claim_is_recovered_before_the_next_claim():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    record = persist_evaluation(backend, graph, graph_hash)
    assert record.mission_execution is not None
    expired = record.mission_execution.model_copy(
        update={
            "claim_id": "expired-claim",
            "claimed_by": "lost-worker",
            "claimed_at": "2020-01-01T00:00:00+00:00",
            "claim_expires_at": "2020-01-01T00:30:00+00:00",
        }
    )
    backend.records[mission_state_key(graph.mission_authority.mission_id)] = record.model_copy(
        update={"mission_execution": expired}
    )

    claimed = claim_next_task(backend, graph, graph_hash, claimed_by="recovery-worker")

    assert claimed.mission_execution is not None
    assert claimed.mission_execution.active_task_id == "L8-MISSION-CONTROL-CONSUMER"
    assert claimed.mission_execution.claimed_by == "recovery-worker"
    assert any(
        transition.to_status == "REGRESSED"
        for transition in claimed.mission_execution.transition_history
    )


def test_direct_close_and_closure_without_evidence_fail_closed():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    persist_evaluation(backend, graph, graph_hash)

    with pytest.raises(ConfigError, match="invalid mission transition"):
        transition_task(
            backend,
            graph,
            graph_hash,
            task_id="L8-MISSION-CONTROL-CONSUMER",
            to_status="CLOSED",
            observed_by="test",
            reason="skip every verification stage",
            evidence_refs=["not-enough.json"],
        )

    with pytest.raises(ConfigError, match="requires at least one evidence"):
        transition_task(
            backend,
            graph,
            graph_hash,
            task_id="L8-MISSION-CONTROL-CONSUMER",
            to_status="IMPLEMENTED",
            observed_by="test",
            reason="no evidence",
            evidence_refs=[],
        )

    for status in ("IMPLEMENTED", "VERIFIED", "SCORED"):
        transition_task(
            backend,
            graph,
            graph_hash,
            task_id="L8-MISSION-CONTROL-CONSUMER",
            to_status=status,
            observed_by="test",
            reason=f"reach {status} for closure guard",
            evidence_refs=[f"evidence/{status.lower()}.json"],
        )
    with pytest.raises(ConfigError, match="valid contribution evidence"):
        transition_task(
            backend,
            graph,
            graph_hash,
            task_id="L8-MISSION-CONTROL-CONSUMER",
            to_status="CLOSED",
            observed_by="test",
            reason="ordinary report cannot close the task",
            evidence_refs=["evidence/report.json"],
        )


def test_cycle_and_alternative_controller_fail_closed(tmp_path):
    raw = yaml.safe_load(REAL_GRAPH.read_text(encoding="utf-8"))
    raw["taskcards"][0]["dependencies"] = [raw["taskcards"][1]["task_id"]]
    raw["taskcards"][1]["dependencies"] = [raw["taskcards"][0]["task_id"]]
    cyclic = tmp_path / "cyclic-mission.yaml"
    cyclic.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigError, match="cycle detected"):
        load_mission_graph(cyclic)

    raw["taskcards"][0]["dependencies"] = []
    raw["taskcards"][1]["dependencies"] = [raw["taskcards"][0]["task_id"]]
    raw["autonomous_execution_contract"]["mechanism_type"] = "autonomous_cycle"
    alternative = tmp_path / "alternative-controller.yaml"
    alternative.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigError, match="locked to autonomous_supervision"):
        load_mission_graph(alternative)


def test_semantically_unsupported_implemented_requirement_cannot_be_preserved(tmp_path):
    raw = yaml.safe_load(REAL_GRAPH.read_text(encoding="utf-8"))
    mapping = next(
        item
        for item in raw["requirement_coverage"]["mappings"]
        if item["requirement_status"] == "IMPLEMENTED"
        and item["disposition"] == "preserved_verified"
    )
    mapping["semantic_findings"] = ["synthetic missing semantic proof"]
    invalid = tmp_path / "invalid-closure-mission.yaml"
    invalid.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigError, match="has semantic findings but was not reopened"):
        load_mission_graph(invalid)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda task: task.update(blocker_attempts=task["blocker_attempts"][:2]), "three attempts"),
        (
            lambda task: task["blocker_attempts"][2].update(attempt_number=2),
            "non-sequential attempts",
        ),
        (
            lambda task: task["blocker_attempts"][2].update(
                hypothesis=task["blocker_attempts"][1]["hypothesis"]
            ),
            "not materially distinct",
        ),
        (lambda task: task.update(exact_external_action=None), "exact external action"),
    ],
)
def test_external_blocker_requires_three_distinct_attempts_and_resume_contract(
    tmp_path, mutation, message
):
    raw = yaml.safe_load(REAL_GRAPH.read_text(encoding="utf-8"))
    task = raw["taskcards"][0]
    task.update(
        status="BLOCKED_EXTERNAL",
        blocker_attempts=[
            {
                "blocker_id": "SYNTHETIC-EXTERNAL",
                "attempt_number": attempt,
                "hypothesis": f"Distinct external-unblock hypothesis {attempt}",
                "first_failing_boundary": f"External boundary {attempt}",
                "evidence_considered": [f"Evidence {attempt}"],
                "action_taken": f"Safe attempt {attempt}",
                "verification_run": [f"Verification {attempt}"],
                "result": f"External dependency remains after attempt {attempt}",
                "new_information": f"New external fact {attempt}",
                "reason_for_next_attempt": f"Try distinct path {attempt + 1}",
            }
            for attempt in range(1, 4)
        ],
        exact_external_action="External owner grants the missing authority.",
        exact_resume_condition="The authority record is locally observable.",
    )
    mutation(task)
    invalid = tmp_path / "invalid-external-blocker.yaml"
    invalid.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_mission_graph(invalid)


def test_state_key_is_separate_from_every_product_repository():
    assert mission_state_key("LEVEL8-CENTRAL-REPOSITORY-PRESENTATION") == (
        "mission/LEVEL8-CENTRAL-REPOSITORY-PRESENTATION"
    )
