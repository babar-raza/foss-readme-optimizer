"""Wave 13.5 (`OPS-012`): the durable-state enforcement action `OPS-011`'s
own measurement side (`harness.py`/`aggregation.py`) already made possible
but never automated -- durably flips a job's `ModelRouteStatusV1` to
`disabled` when a real golden-set run's pass rate for that job crosses a
documented floor, so a degrading route stops silently substituting a
possibly-degraded model before a human happens to notice, matching
`state/schema.py::ModelRouteStatusV1`'s own docstring ("never a silent
model substitution -- disabled blocks the run outright"). Never auto-
re-enables and never overwrites an already-disabled record with a fresh
reason -- re-enabling stays exclusively `readme-agent model-route-enable`'s
job (`commands.py::cmd_model_route_enable`), an explicit, human-authored
act, per `OPS-011`'s own extension decision."""

from datetime import UTC, datetime

from readme_agent.golden_set.harness import ScenarioResult, summarize
from readme_agent.state.backend import StateBackend
from readme_agent.state.schema import ModelRouteStatusV1

# Below this pass rate, a job's route is durably disabled rather than left
# silently degraded. Not a guess: `LLM-018`'s own live characterization
# found gpt-oss's freeform-JSON validity swings 0.4-0.8 run-to-run for a
# job that is NOT routed anywhere today precisely because it's unreliable;
# by contrast every model actually routed via `JOB_MODEL_ROUTING` has
# scored 5/5 in every probe run so far (`llm-gateway-characterization.md`).
# 0.5 sits below even gpt-oss's worst measured swing, so it only fires for
# a real, unambiguous regression in an already-trusted route, never
# ordinary single-run sampling noise.
PASS_RATE_FLOOR = 0.5


def evaluate_and_disable(
    job: str,
    results: list[ScenarioResult],
    backend: StateBackend,
    *,
    evidence_ref: str | None = None,
) -> ModelRouteStatusV1 | None:
    """Returns the newly-written `disabled` status if this run's pass rate
    crossed `PASS_RATE_FLOOR`, else `None` -- covering both "this run was
    fine" and "a human already disabled this route, we're not touching
    their record again" (an idempotent, side-effect-free no-op in the
    second case, not a silent overwrite of their own recorded reason)."""
    summary = summarize(results)
    pass_rate = summary["pass_rate"]
    if pass_rate is None or pass_rate >= PASS_RATE_FLOOR:
        return None

    existing = backend.load_model_route_status(job)
    if existing is not None and existing.status == "disabled":
        return None

    status = ModelRouteStatusV1(
        job=job,
        status="disabled",
        reason=f"golden-set pass_rate {pass_rate:.2f} crossed floor {PASS_RATE_FLOOR}",
        disabled_at=datetime.now(UTC).isoformat(),
        evidence_ref=evidence_ref,
    )
    backend.save_model_route_status(status)
    return status
