"""Choose measured repository-lane capacity without weakening isolation."""

from __future__ import annotations

from readme_agent.state.agile_execution_schema import (
    ParallelismControlStateV1,
    ParallelismDecisionV1,
)

MINIMUM_SPEEDUP = 1.5
MAXIMUM_COORDINATION_OVERHEAD_RATIO = 0.25


def decide_parallelism(state: ParallelismControlStateV1) -> ParallelismDecisionV1:
    """Start serial, admit two lanes after isolation, and earn or lose lane three."""

    if state.calibration_active:
        return ParallelismDecisionV1(
            max_repository_lanes=1,
            reason="calibration is serial",
        )
    if state.shared_repair_active:
        return ParallelismDecisionV1(
            max_repository_lanes=1,
            reason="shared repair is serial",
        )
    if not state.transaction_isolation_proven:
        return ParallelismDecisionV1(
            max_repository_lanes=1,
            reason="repository transaction isolation is not proven",
        )
    if not state.observations:
        return ParallelismDecisionV1(
            max_repository_lanes=2,
            reason="isolation proof admits the measured two-lane trial",
        )
    latest = state.observations[-1]
    acceptable = (
        latest.isolation_proven
        and not latest.duplicate_work_detected
        and latest.speedup >= MINIMUM_SPEEDUP
        and latest.coordination_overhead_ratio <= MAXIMUM_COORDINATION_OVERHEAD_RATIO
    )
    if latest.lane_count == 2:
        lanes = 3 if acceptable else 1
        reason = (
            "two-lane evidence earns the third lane"
            if acceptable
            else "two-lane evidence failed the gain or coordination threshold; scale down"
        )
    else:
        lanes = 3 if acceptable else 2
        reason = (
            "three-lane evidence retains the third lane"
            if acceptable
            else "three-lane evidence regressed; scale down to the isolated two-lane boundary"
        )
    return ParallelismDecisionV1(
        max_repository_lanes=lanes,
        reason=reason,
        latest_speedup=latest.speedup,
        latest_coordination_overhead_ratio=latest.coordination_overhead_ratio,
    )
