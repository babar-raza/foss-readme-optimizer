"""Build replay-accepted Campaign 2/3 evidence from graph and durable mission state."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import yaml

from readme_agent.supervisor.campaign_evidence import (
    CampaignTaskVerdictV1,
    EvidenceBindingV1,
    accept_campaign_evidence_manifest,
    build_campaign_evidence_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GRAPH_PATH = REPO_ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
OUTPUT_ROOT = REPO_ROOT / "plans/investigations/evidence/final-throughput-correction-v1"
STATE_REF = "refs/readme-agent-inspect/current-level8"
CAMPAIGNS = ("CAMP-SHARED-ACCELERATION", "CAMP-THREE-SLICES")


def _read_state() -> dict:
    payload = subprocess.check_output(["git", "show", f"{STATE_REF}:state.json"], cwd=REPO_ROOT)
    return json.loads(payload)


def _local_evidence(refs: list[str], requirement_ids: list[str]) -> list[EvidenceBindingV1]:
    bindings: list[EvidenceBindingV1] = []
    remaining = list(requirement_ids)
    for reference in refs:
        relative = reference.split("#", 1)[0]
        if relative.startswith("commit:"):
            continue
        path = REPO_ROOT / relative
        if not path.is_file():
            continue
        bindings.append(
            EvidenceBindingV1(
                path=relative.replace("\\", "/"),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                requirement_ids=remaining,
            )
        )
        remaining = []
    return bindings if not remaining else []


def _latest_closure_refs(state: dict, task_id: str) -> list[str]:
    transitions = state["mission_execution"]["transition_history"]
    for transition in reversed(transitions):
        if transition["task_id"] == task_id and transition["to_status"] == "CLOSED":
            return transition.get("evidence_refs", [])
    return []


def _task_verdicts(graph: dict, state: dict, campaign_id: str) -> list[CampaignTaskVerdictV1]:
    statuses = state["mission_execution"]["task_statuses"]
    verdicts: list[CampaignTaskVerdictV1] = []
    for task in graph["taskcards"]:
        if task.get("campaign_id") != campaign_id:
            continue
        task_id = task["task_id"]
        requirement_ids = sorted(task.get("requirement_ids", []))
        durable_status = statuses.get(task_id, "UNKNOWN")
        evidence = (
            _local_evidence(_latest_closure_refs(state, task_id), requirement_ids)
            if durable_status == "CLOSED"
            else []
        )
        if durable_status == "CLOSED" and (evidence or not requirement_ids):
            verdict = "CLOSED"
        elif durable_status in {"BLOCKED", "BLOCKED_EXTERNAL"}:
            verdict = "BLOCKED_EXTERNAL" if durable_status == "BLOCKED_EXTERNAL" else "PARTIAL"
        elif durable_status in {"TODO", "READY"}:
            verdict = "OPEN"
        else:
            verdict = "PARTIAL"
        verdicts.append(
            CampaignTaskVerdictV1(
                task_id=task_id,
                requirement_ids=requirement_ids,
                durable_status=durable_status,
                verdict=verdict,
                evidence=evidence,
            )
        )
    return verdicts


def main() -> int:
    graph_bytes = GRAPH_PATH.read_bytes()
    graph = yaml.safe_load(graph_bytes)
    state = _read_state()
    transition = dict(state["mission_execution"]["transition_history"][-1])
    transition["state_version"] = state["state_version"]
    for campaign_id in CAMPAIGNS:
        pending = build_campaign_evidence_manifest(
            campaign_id=campaign_id,
            graph_sha256=hashlib.sha256(graph_bytes).hexdigest(),
            task_verdicts=_task_verdicts(graph, state, campaign_id),
            durable_state_version=state["state_version"],
            transition_payload=transition,
        )
        accepted = accept_campaign_evidence_manifest(
            pending,
            graph_path=GRAPH_PATH,
            repository_root=REPO_ROOT,
            durable_transition_payload=transition,
        )
        suffix = campaign_id.removeprefix("CAMP-").lower().replace("-", "_")
        path = OUTPUT_ROOT / f"campaign-evidence-{suffix}-v1.json"
        path.write_text(
            json.dumps(accepted.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"{campaign_id}: {len(accepted.task_verdicts)} tasks -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
