"""Aggregate planner and reviewer results into the Level-8 qualification gate."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from typing import Protocol

from readme_agent.golden_set.harness import run_golden_set
from readme_agent.golden_set.review_harness import run_review_golden_set
from readme_agent.golden_set.scenarios import SCENARIOS
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.planner_client import PlannerClient

MINIMUM_EVALUATIONS = 100
MINIMUM_SESSIONS = 3
QUALIFICATION_PASS_RATE_FLOOR = 0.95


class AnalysisClientLike(Protocol):
    def analyze(self, messages: list[dict]) -> AnalysisResult: ...


@dataclass(frozen=True)
class DeterministicQualificationResult:
    total: int
    passed: int
    evidence_refs: list[str]

    def __post_init__(self) -> None:
        if self.total < 1 or self.passed < 0 or self.passed > self.total:
            raise ValueError("deterministic qualification counts are invalid")

    @property
    def complete(self) -> bool:
        return self.passed == self.total


@dataclass(frozen=True)
class QualificationEvaluation:
    session: int | str
    job: str
    scenario_id: str
    category: str
    ecosystem: str | None
    passed: bool
    expected: str
    actual: str | None
    detail: str
    prompt_tokens: int | None
    latency_seconds: float | None


@dataclass(frozen=True)
class QualificationSessionResult:
    session_id: int | str
    planner_results: list[dict]
    reviewer_results: list[dict]

    def as_record(self) -> dict:
        return asdict(self)


def run_qualification_session(
    session_id: int | str,
    planner_client: PlannerClient,
    reviewer_client: AnalysisClientLike,
) -> QualificationSessionResult:
    """Run both real prompt seams once without dispatching a capability."""

    scenario_by_id = {scenario.scenario_id: scenario for scenario in SCENARIOS}
    planner = [
        QualificationEvaluation(
            session=session_id,
            job="supervisor_planning",
            scenario_id=result.scenario_id,
            category=result.category,
            ecosystem=None,
            passed=result.passed,
            expected=(
                scenario_by_id[result.scenario_id].expected_capability_id
                or f"not:{scenario_by_id[result.scenario_id].forbidden_capability_id}"
            ),
            actual=result.actual_capability_id,
            detail=result.detail,
            prompt_tokens=result.prompt_tokens,
            latency_seconds=result.latency_seconds,
        )
        for result in run_golden_set(planner_client)
    ]
    reviewer = [
        QualificationEvaluation(
            session=session_id,
            job="independent_readme_review",
            scenario_id=result.scenario_id,
            category=result.category,
            ecosystem=result.ecosystem,
            passed=result.passed,
            expected=result.expected_verdict,
            actual=result.actual_verdict,
            detail=result.detail,
            prompt_tokens=result.prompt_tokens,
            latency_seconds=result.latency_seconds,
        )
        for result in run_review_golden_set(reviewer_client)
    ]
    return QualificationSessionResult(
        session_id=session_id,
        planner_results=[asdict(record) for record in planner],
        reviewer_results=[asdict(record) for record in reviewer],
    )


def _score(records: list[QualificationEvaluation]) -> dict:
    total = len(records)
    passed = sum(1 for record in records if record.passed)
    by_category: dict[str, dict[str, int]] = {}
    by_ecosystem: dict[str, dict[str, int]] = {}
    for record in records:
        category = by_category.setdefault(record.category, {"total": 0, "passed": 0})
        category["total"] += 1
        category["passed"] += int(record.passed)
        if record.ecosystem is not None:
            ecosystem = by_ecosystem.setdefault(record.ecosystem, {"total": 0, "passed": 0})
            ecosystem["total"] += 1
            ecosystem["passed"] += int(record.passed)
    return {
        "total": total,
        "passed": passed,
        "pass_rate": passed / total if total else None,
        "by_category": by_category,
        "by_ecosystem": by_ecosystem,
    }


def build_qualification_report(
    evaluations: list[QualificationEvaluation],
    *,
    sessions: int,
    deterministic: DeterministicQualificationResult,
) -> dict:
    """Build the volume, deterministic, overall, and per-route acceptance gate."""

    jobs = {
        job: _score([record for record in evaluations if record.job == job])
        for job in ("supervisor_planning", "independent_readme_review")
    }
    total_score = _score(evaluations)
    enough_sessions = sessions >= MINIMUM_SESSIONS
    enough_evaluations = total_score["total"] >= MINIMUM_EVALUATIONS
    overall_pass_rate = bool(
        total_score["pass_rate"] is not None
        and total_score["pass_rate"] >= QUALIFICATION_PASS_RATE_FLOOR
    )
    every_route_pass_rate = all(
        score["pass_rate"] is not None and score["pass_rate"] >= QUALIFICATION_PASS_RATE_FLOOR
        for score in jobs.values()
    )
    acceptance = {
        "minimum_sessions": enough_sessions,
        "minimum_evaluations": enough_evaluations,
        "deterministic_validation_100_percent": deterministic.complete,
        "overall_pass_rate": overall_pass_rate,
        "every_route_pass_rate": every_route_pass_rate,
    }
    return {
        "schema_version": 1,
        "sessions": sessions,
        "session_count": sessions,
        "minimum_sessions": MINIMUM_SESSIONS,
        "total": total_score["total"],
        "total_evaluations": total_score["total"],
        "passed": total_score["passed"],
        "passed_evaluations": total_score["passed"],
        "minimum_evaluations": MINIMUM_EVALUATIONS,
        "pass_rate": total_score["pass_rate"],
        "pass_rate_floor": QUALIFICATION_PASS_RATE_FLOOR,
        "jobs": jobs,
        "routes": jobs,
        "deterministic_validation": {
            "total": deterministic.total,
            "passed": deterministic.passed,
            "complete": deterministic.complete,
            "evidence_refs": deterministic.evidence_refs,
        },
        "acceptance": acceptance,
        "volume_complete": enough_sessions and enough_evaluations,
        "qualified": all(acceptance.values()),
        "evaluations": [asdict(record) for record in evaluations],
    }


def summarize_qualification(
    sessions: Sequence[QualificationSessionResult | dict],
    deterministic: DeterministicQualificationResult,
) -> dict:
    """Rebuild a report from resumable session records."""

    evaluations: list[QualificationEvaluation] = []
    session_ids: set[int | str] = set()
    for session in sessions:
        record = session.as_record() if isinstance(session, QualificationSessionResult) else session
        session_ids.add(record["session_id"])
        evaluations.extend(
            QualificationEvaluation(**result)
            for result in [*record["planner_results"], *record["reviewer_results"]]
        )
    return build_qualification_report(
        evaluations,
        sessions=len(session_ids),
        deterministic=deterministic,
    )


def run_qualification(
    planner_client_factory: Callable[[], PlannerClient],
    reviewer_client_factory: Callable[[], AnalysisClientLike],
    *,
    sessions: int = MINIMUM_SESSIONS,
    deterministic: DeterministicQualificationResult,
) -> dict:
    """Run distinct client instances for each governed session."""

    session_records = [
        run_qualification_session(
            session,
            planner_client_factory(),
            reviewer_client_factory(),
        )
        for session in range(1, sessions + 1)
    ]
    return summarize_qualification(session_records, deterministic)
