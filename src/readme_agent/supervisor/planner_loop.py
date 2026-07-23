"""Run the bounded capability-selection loop after specialist observation."""

import json
from dataclasses import dataclass
from typing import Any

from readme_agent import env
from readme_agent.capabilities import registry
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.capabilities.stop import CAPABILITY_ID as STOP_CAPABILITY_ID
from readme_agent.errors import LLMError
from readme_agent.llm import prompt_registry
from readme_agent.llm.planner_client import LivePlannerClient, PlannerClient
from readme_agent.state.backend import StateBackend
from readme_agent.state.schema import DomainStateV1
from readme_agent.supervisor import dossier
from readme_agent.supervisor.action_dispatch import dispatch_and_record
from readme_agent.supervisor.convergence import (
    ConvergenceOutcome,
    check_repair_exhausted,
    final_status,
)
from readme_agent.supervisor.models import DecisionSummary
from readme_agent.supervisor.task import Task, TaskGraph


@dataclass
class PlannerLoopResult:
    graph: TaskGraph
    decisions: list[DecisionSummary]
    outcome: ConvergenceOutcome


def _default_planner_client() -> LivePlannerClient:
    return LivePlannerClient(
        env.llm_base_url(),
        env.llm_api_key(),
        env.llm_model_for_job("supervisor_planning"),
    )


def run_planner_loop(
    *,
    org_repo: str,
    specialist_results: dict[str, DomainStateV1],
    initial_decisions: list[DecisionSummary],
    state_backend: StateBackend | None,
    planner_client: PlannerClient | None,
    repair_planner_client: PlannerClient | None,
    allowed_permission_classes: set[PermissionClass] | None,
    max_turns: int,
    no_progress_turn_limit: int,
    dossier_token_budget: int,
) -> PlannerLoopResult:
    """Select and dispatch capabilities until a deterministic terminal result."""

    graph = TaskGraph()
    decisions = list(initial_decisions)
    applied_any_effect = False

    bootstrap = graph.add_task(
        Task(capability_id="inspect_repository", arguments={"org_repo": org_repo})
    )
    bootstrap = dispatch_and_record(
        graph,
        bootstrap,
        backend=state_backend,
        org_repo=org_repo,
        decisions=decisions,
        turn=0,
        repair_planner_client=repair_planner_client,
        tools=registry.all_tool_schemas(),
        allowed_permission_classes=allowed_permission_classes,
    )
    decisions.append(
        DecisionSummary(
            turn=0,
            kind="capability_selected",
            detail="inspect_repository (bootstrap)",
        )
    )

    client = planner_client or _default_planner_client()
    supervisor_prompt = prompt_registry.get("supervisor_turn")
    assert supervisor_prompt is not None, "prompts/planning/supervisor_turn.yaml missing"
    initial_dossier = dossier.build_initial_dossier(specialist_results)
    tried_capability_ids: list[str] = []
    bootstrap_result = bootstrap.result or {}
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": supervisor_prompt.system},
        {
            "role": "user",
            "content": dossier.render_turn_context(
                supervisor_prompt,
                org_repo=org_repo,
                turn_number=1,
                max_turns=max_turns,
                tried_capability_ids=tried_capability_ids,
                bootstrap_result=bootstrap_result,
                dossier=initial_dossier,
            ),
        },
    ]

    turn = 0
    outcome: ConvergenceOutcome | None = None
    consecutive_no_progress_turns = 0
    while outcome is None:
        turn += 1
        exhausted = check_repair_exhausted(turns_taken=turn, max_turns=max_turns)
        if exhausted is not None:
            classified = final_status(
                graph,
                applied_any_effect=applied_any_effect,
                specialist_results=specialist_results,
            )
            # Exhaustion is only the fallback reason. A known task or
            # specialist failure is more specific and must remain the
            # terminal classification; a converged-looking graph is not
            # enough because the planner never emitted a stop.
            outcome = classified if classified.status == "BLOCKED" else exhausted
            break
        messages[1]["content"] = dossier.render_turn_context(
            supervisor_prompt,
            org_repo=org_repo,
            turn_number=turn,
            max_turns=max_turns,
            tried_capability_ids=tried_capability_ids,
            bootstrap_result=bootstrap_result,
            dossier=initial_dossier,
        )
        try:
            plan = client.plan(messages, registry.all_tool_schemas())
        except LLMError as exc:
            decisions.append(
                DecisionSummary(turn=turn, kind="stop", detail=f"planner_llm_failure: {exc}")
            )
            outcome = ConvergenceOutcome(
                status="BLOCKED",
                blocked_reason=f"planner_llm_failure: {exc}",
            )
            break

        if plan.tool_call is None:
            decisions.append(
                DecisionSummary(turn=turn, kind="stop", detail=plan.content or "planner stopped")
            )
            outcome = final_status(
                graph,
                applied_any_effect=applied_any_effect,
                specialist_results=specialist_results,
            )
            break

        function = plan.tool_call.get("function", {})
        capability_id = function.get("name")
        if capability_id == STOP_CAPABILITY_ID:
            try:
                stop_arguments = json.loads(function.get("arguments") or "{}")
            except json.JSONDecodeError:
                stop_arguments = {}
            decisions.append(
                DecisionSummary(
                    turn=turn,
                    kind="stop",
                    detail=f"stop capability called: {stop_arguments.get('reason', '')}",
                )
            )
            outcome = final_status(
                graph,
                applied_any_effect=applied_any_effect,
                specialist_results=specialist_results,
            )
            break

        try:
            arguments = json.loads(function.get("arguments") or "{}")
        except json.JSONDecodeError:
            arguments = {}
        arguments["org_repo"] = org_repo
        tried_capability_ids.append(capability_id or "")
        new_task = graph.add_task(Task(capability_id=capability_id, arguments=arguments))
        decisions.append(
            DecisionSummary(
                turn=turn,
                kind="capability_selected",
                detail=capability_id or "",
            )
        )
        if new_task.state == "SUPERSEDED":
            consecutive_no_progress_turns += 1
            if consecutive_no_progress_turns >= no_progress_turn_limit:
                decisions.append(
                    DecisionSummary(
                        turn=turn,
                        kind="stop",
                        detail=(
                            "deterministic termination backstop: "
                            f"{consecutive_no_progress_turns} consecutive turns with no forward "
                            "progress (repeated/duplicate capability calls)"
                        ),
                    )
                )
                outcome = final_status(
                    graph,
                    applied_any_effect=applied_any_effect,
                    specialist_results=specialist_results,
                )
                break
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"{capability_id} with these arguments was already answered this run: "
                        f"{json.dumps(new_task.result)}. Choose something else, or stop."
                    ),
                }
            )
            continue

        extra_kwargs = (
            {"state_backend": state_backend} if capability_id == "get_domain_findings" else None
        )
        resolved = dispatch_and_record(
            graph,
            new_task,
            backend=state_backend,
            org_repo=org_repo,
            decisions=decisions,
            turn=turn,
            extra_kwargs=extra_kwargs,
            repair_planner_client=repair_planner_client,
            tools=registry.all_tool_schemas(),
            allowed_permission_classes=allowed_permission_classes,
        )
        if resolved.state == "PASSED":
            consecutive_no_progress_turns = 0
            resolved_manifest = (
                registry.get(resolved.capability_id) if resolved.capability_id else None
            )
            if resolved_manifest is not None and resolved_manifest.side_effect_class in (
                "local_write",
                "remote_write",
            ):
                applied_any_effect = True
        else:
            consecutive_no_progress_turns += 1
        messages.extend(
            [
                {
                    "role": "assistant",
                    "content": plan.content,
                    "tool_calls": [plan.tool_call],
                },
                {
                    "role": "tool",
                    "tool_call_id": plan.tool_call.get("id", ""),
                    "content": json.dumps(
                        {
                            "state": resolved.state,
                            "result": resolved.result,
                            "error": resolved.blocked_reason,
                        }
                    ),
                },
            ]
        )
        if consecutive_no_progress_turns >= no_progress_turn_limit:
            decisions.append(
                DecisionSummary(
                    turn=turn,
                    kind="stop",
                    detail=(
                        "deterministic termination backstop: "
                        f"{consecutive_no_progress_turns} consecutive turns with no forward "
                        "progress (rejected/failed dispatches)"
                    ),
                )
            )
            outcome = final_status(
                graph,
                applied_any_effect=applied_any_effect,
                specialist_results=specialist_results,
            )
            break

        usage = plan.meta.usage
        if (
            usage is not None
            and usage.prompt_tokens is not None
            and usage.prompt_tokens > dossier_token_budget
        ):
            decisions.append(
                DecisionSummary(
                    turn=turn,
                    kind="token_budget_exceeded",
                    detail=f"prompt_tokens={usage.prompt_tokens}",
                )
            )
            outcome = ConvergenceOutcome(
                status="BLOCKED",
                blocked_reason=f"dossier_token_budget_exceeded:{usage.prompt_tokens}",
            )

    assert outcome is not None
    return PlannerLoopResult(graph=graph, decisions=decisions, outcome=outcome)
