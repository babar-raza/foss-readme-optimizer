import pytest
from pydantic import ValidationError

from readme_agent.supervisor.campaign_packets import (
    ActiveCampaignBriefV1,
    RepositoryWorkPacketV1,
    WorkerStageReceiptV1,
    build_repository_work_packet,
    read_packet_input,
)
from readme_agent.supervisor.stage_dependencies import (
    SelectedDependencyV1,
    build_stage_dependency_manifest,
)


def test_work_packet_forbids_product_effects() -> None:
    with pytest.raises(ValidationError):
        RepositoryWorkPacketV1(
            campaign_id="campaign",
            task_id="task",
            repository="org/repo",
            source_revision="a" * 40,
            target_stage="FACTS",
            stage_dependency_key="b" * 64,
            pipeline_snapshot_id="c" * 64,
            pipeline_snapshot_root="runs/snapshot",
            input_paths=["facts.json"],
            output_root="runs/output",
            focused_checks=["pytest focused"],
            product_effects_allowed=True,
        )


def test_worker_receipt_forbids_nonzero_effect_count() -> None:
    with pytest.raises(ValidationError):
        WorkerStageReceiptV1(
            campaign_id="campaign",
            task_id="task",
            repository="org/repo",
            source_revision="a" * 40,
            target_stage="FACTS",
            stage_dependency_key="b" * 64,
            pipeline_snapshot_id="c" * 64,
            output_hashes={"facts.json": "d" * 64},
            focused_check_results={"focused": "PASSED"},
            verdict="PASSED",
            product_effect_count=1,
        )


def test_work_packet_consumes_exact_stage_dependency_key(tmp_path) -> None:
    manifest = build_stage_dependency_manifest(
        repository="org/repo",
        source_revision="a" * 40,
        stage="FACTS",
        ecosystem="python",
        dependencies=[
            SelectedDependencyV1(dependency_id="ecosystem/python", files={"python.py": "b" * 64})
        ],
    )
    brief = ActiveCampaignBriefV1(
        campaign_id="CAMP-SHARED-ACCELERATION",
        primary_task_id="TASK",
        objective="Prove one selected repository stage safely.",
        pipeline_snapshot_id="c" * 64,
        pipeline_snapshot_root=str(tmp_path),
        graph_sha256="d" * 64,
        allowed_effects=["read_only_local"],
        stop_conditions=["first failing boundary"],
    )
    packet = build_repository_work_packet(
        brief=brief,
        task_id="TASK",
        dependency_manifest=manifest,
        input_paths=["files/facts.json"],
        output_root="runs/output",
        focused_checks=["pytest focused"],
    )
    assert packet.stage_dependency_key == manifest.stage_key
    assert packet.pipeline_snapshot_id == brief.pipeline_snapshot_id
    source = tmp_path / "files/facts.json"
    source.parent.mkdir()
    source.write_bytes(b"sealed")
    assert read_packet_input(packet, "files/facts.json") == b"sealed"
