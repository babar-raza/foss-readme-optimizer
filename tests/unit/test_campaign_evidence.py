import hashlib
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from readme_agent.supervisor.campaign_evidence import (
    CampaignTaskVerdictV1,
    EvidenceBindingV1,
    accept_campaign_evidence_manifest,
    build_campaign_evidence_manifest,
    validate_campaign_evidence_manifest,
)


def test_closed_task_requires_exact_evidence() -> None:
    with pytest.raises(ValidationError, match="requires exact evidence"):
        CampaignTaskVerdictV1(
            task_id="TASK", requirement_ids=["REQ"], durable_status="CLOSED", verdict="CLOSED"
        )


def test_campaign_manifest_replays_deterministically() -> None:
    task = CampaignTaskVerdictV1(
        task_id="TASK",
        requirement_ids=["REQ"],
        durable_status="CLOSED",
        verdict="CLOSED",
        evidence=[
            EvidenceBindingV1(path="evidence.json", sha256="a" * 64, requirement_ids=["REQ"])
        ],
    )
    first = build_campaign_evidence_manifest(
        campaign_id="CAMP-SHARED-ACCELERATION",
        graph_sha256="b" * 64,
        task_verdicts=[task],
        durable_state_version=1,
        transition_payload={"state_version": 1, "transition": "one"},
    )
    second = build_campaign_evidence_manifest(
        campaign_id="CAMP-SHARED-ACCELERATION",
        graph_sha256="b" * 64,
        task_verdicts=[task],
        durable_state_version=1,
        transition_payload={"state_version": 1, "transition": "one"},
    )
    assert first.replay_id == second.replay_id
    assert first.manifest_sha256 == second.manifest_sha256


def test_campaign_manifest_replays_graph_membership_and_evidence(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.json"
    evidence.write_text("{}\n", encoding="utf-8")
    graph = tmp_path / "graph.yaml"
    graph.write_text(
        yaml.safe_dump(
            {
                "taskcards": [
                    {
                        "task_id": "TASK",
                        "campaign_id": "CAMP-SHARED-ACCELERATION",
                        "requirement_ids": ["REQ"],
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    task = CampaignTaskVerdictV1(
        task_id="TASK",
        requirement_ids=["REQ"],
        durable_status="CLOSED",
        verdict="CLOSED",
        evidence=[
            EvidenceBindingV1(
                path="evidence.json",
                sha256=hashlib.sha256(evidence.read_bytes()).hexdigest(),
                requirement_ids=["REQ"],
            )
        ],
    )
    manifest = build_campaign_evidence_manifest(
        campaign_id="CAMP-SHARED-ACCELERATION",
        graph_sha256=hashlib.sha256(graph.read_bytes()).hexdigest(),
        task_verdicts=[task],
        durable_state_version=1,
        transition_payload={"state_version": 1, "transition": "one"},
    )

    transition = {"state_version": 1, "transition": "one"}
    validate_campaign_evidence_manifest(
        manifest,
        graph_path=graph,
        repository_root=tmp_path,
        durable_transition_payload=transition,
    )
    accepted = accept_campaign_evidence_manifest(
        manifest,
        graph_path=graph,
        repository_root=tmp_path,
        durable_transition_payload=transition,
    )
    assert accepted.replay_result == "ACCEPTED"

    evidence.write_text("corrupt\n", encoding="utf-8")
    with pytest.raises(ValueError, match="evidence hash mismatch"):
        validate_campaign_evidence_manifest(
            manifest,
            graph_path=graph,
            repository_root=tmp_path,
            durable_transition_payload=transition,
        )
