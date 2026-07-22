"""`ORC-002`/`VER-002`: failure classification and repair-task creation.
`EFF-003`'s actual enforcement point -- whether to even *propose*
dispatching a capability+arguments again -- lives here, not in
`effect_ledger.py` (see `test_effect_ledger.py`'s
`TestDispatchGatedEffectRetryInertness` for why)."""

from readme_agent.capabilities.dispatcher import DispatchResult
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.errors import LLMError
from readme_agent.llm.planner_client import FixturePlannerClient, PlannerTurn
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.supervisor.repair import (
    classify_failure,
    classify_verification,
    create_repair_task,
    select_repair_alternative,
)
from readme_agent.supervisor.task import Task, TaskGraph

_TOOLS = [{"type": "function", "function": {"name": "detect_readme_gaps", "parameters": {}}}]


def _manifest(**overrides) -> CapabilityManifest:
    defaults = dict(
        capability_id="mutate_thing",
        version="1",
        name="Mutate thing",
        purpose="test",
        category="test",
        owner="tests",
        execution_type="gated_effector",
        side_effect_class="local_write",
        required_inputs={"org_repo": "string"},
        idempotency_inputs=["org_repo"],
        retry_policy="idempotent_only",
    )
    return CapabilityManifest(**{**defaults, **overrides})


class TestClassifyFailure:
    def test_rejected_outcomes_classify_as_dispatch_rejected(self):
        for outcome in (
            "rejected_unknown_capability",
            "rejected_permission_denied",
            "rejected_domain_denied",
            "rejected_invalid_arguments",
        ):
            assert classify_failure(DispatchResult(outcome=outcome)) == "dispatch_rejected"

    def test_execution_error_classifies_as_execution_error(self):
        assert classify_failure(DispatchResult(outcome="execution_error")) == "execution_error"


class TestClassifyVerification:
    def test_reject_verdict_classifies_as_verification_rejected(self):
        assert classify_verification({"verdict": "reject", "reason": "stale render"}) == (
            "verification_rejected"
        )


class TestCreateRepairTask:
    def test_execution_error_with_idempotent_only_creates_a_repair_task(self):
        graph = TaskGraph()
        failed = graph.add_task(Task(capability_id="mutate_thing", arguments={"org_repo": "a/b"}))
        graph.mark(failed.task_id, "FAILED")

        repair = create_repair_task(
            graph, failed, "execution_error", _manifest(retry_policy="idempotent_only")
        )

        assert repair is not None
        assert repair.capability_id == "mutate_thing"
        assert repair.arguments == {"org_repo": "a/b"}
        assert repair.depends_on == [failed.task_id]

    def test_execution_error_without_idempotent_only_refuses_to_propose_a_retry(self):
        """The actual EFF-003 enforcement: retry must never be a guess."""
        graph = TaskGraph()
        failed = graph.add_task(Task(capability_id="mutate_thing", arguments={"org_repo": "a/b"}))
        graph.mark(failed.task_id, "FAILED")

        repair = create_repair_task(
            graph, failed, "execution_error", _manifest(retry_policy="manual_only")
        )

        assert repair is None

    def test_dispatch_rejected_is_never_auto_repaired(self):
        """Permission/domain-denied, unknown capability, malformed
        arguments are genuine blockers/gaps, not transient failures a blind
        retry could fix."""
        graph = TaskGraph()
        failed = graph.add_task(Task(capability_id="mutate_thing", arguments={"org_repo": "a/b"}))
        graph.mark(failed.task_id, "FAILED")

        repair = create_repair_task(
            graph, failed, "dispatch_rejected", _manifest(retry_policy="idempotent_only")
        )

        assert repair is None

    def test_no_manifest_is_never_auto_repaired(self):
        graph = TaskGraph()
        failed = graph.add_task(Task(capability_id="unknown_thing"))
        graph.mark(failed.task_id, "FAILED")

        repair = create_repair_task(graph, failed, "execution_error", None)

        assert repair is None

    def test_verification_rejected_is_never_auto_repaired(self):
        """`VER-002`: a rejected verification is a deterministic, reproducible
        verdict against the exact same candidate -- a blind retry would just
        reproduce the identical rejection, exactly the "retry must never be
        a guess" reasoning already established for `dispatch_rejected`/
        `validation_failed`."""
        graph = TaskGraph()
        failed = graph.add_task(Task(capability_id="mutate_thing", arguments={"org_repo": "a/b"}))
        graph.mark(failed.task_id, "FAILED")

        repair = create_repair_task(
            graph, failed, "verification_rejected", _manifest(retry_policy="idempotent_only")
        )

        assert repair is None


class TestSelectRepairAlternative:
    """Wave 8.6 (`VER-006` reversal): a real, model-driven repair choice for
    the classes `create_repair_task()` never auto-repairs. Reuses the same
    unscoped tool menu the main planner sees -- the model can only ever
    propose a `Task`, never execute anything itself."""

    def test_planner_selecting_a_tool_produces_a_repair_task(self):
        graph = TaskGraph()
        failed = graph.add_task(Task(capability_id="mutate_thing", arguments={"org_repo": "a/b"}))
        graph.mark(failed.task_id, "FAILED")
        client = FixturePlannerClient(
            [
                PlannerTurn(
                    tool_call={
                        "id": "call-1",
                        "function": {
                            "name": "detect_readme_gaps",
                            "arguments": '{"org_repo": "a/b"}',
                        },
                    },
                    meta=LLMResponseMeta(),
                )
            ]
        )

        repair = select_repair_alternative(
            graph, failed, "dispatch_rejected", "permission denied", _TOOLS, client
        )

        assert repair is not None
        assert repair.capability_id == "detect_readme_gaps"
        assert repair.arguments == {"org_repo": "a/b"}
        assert repair.depends_on == [failed.task_id]

    def test_planner_stopping_escalates_with_none(self):
        graph = TaskGraph()
        failed = graph.add_task(Task(capability_id="mutate_thing", arguments={"org_repo": "a/b"}))
        graph.mark(failed.task_id, "FAILED")
        client = FixturePlannerClient(
            [PlannerTurn(content="nothing would help", meta=LLMResponseMeta())]
        )

        repair = select_repair_alternative(
            graph, failed, "dispatch_rejected", "permission denied", _TOOLS, client
        )

        assert repair is None

    def test_llm_error_fails_closed_to_escalate(self):
        graph = TaskGraph()
        failed = graph.add_task(Task(capability_id="mutate_thing", arguments={"org_repo": "a/b"}))
        graph.mark(failed.task_id, "FAILED")

        class _RaisingClient:
            def plan(self, messages, tools):
                raise LLMError("gateway unreachable")

        repair = select_repair_alternative(
            graph, failed, "dispatch_rejected", "permission denied", _TOOLS, _RaisingClient()
        )

        assert repair is None

    def test_malformed_arguments_json_fails_closed(self):
        graph = TaskGraph()
        failed = graph.add_task(Task(capability_id="mutate_thing", arguments={"org_repo": "a/b"}))
        graph.mark(failed.task_id, "FAILED")
        client = FixturePlannerClient(
            [
                PlannerTurn(
                    tool_call={
                        "id": "call-1",
                        "function": {"name": "detect_readme_gaps", "arguments": "{not valid json"},
                    },
                    meta=LLMResponseMeta(),
                )
            ]
        )

        repair = select_repair_alternative(
            graph, failed, "dispatch_rejected", "permission denied", _TOOLS, client
        )

        assert repair is None
