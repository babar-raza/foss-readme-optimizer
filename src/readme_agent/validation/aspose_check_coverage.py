"""Build the per-run check-coverage report: for every one of the 89+
vendored aspose.org checks, exactly one outcome (`pass`/`fail`/`skip`/
`error`/`not_applicable`) with a real reason -- Gate R7 of the 2026-08-19
knowledge-to-output pipeline course-correction review.

`run_aspose_checks()` (`aspose_checks_bridge.py`) already computes
`checks_run`/`checks_skipped`/`checks_errored`/`findings` for every real
candidate, but discards everything except `.valid` and `.findings` once a
caller reads them -- there was no durable evidence artifact recording,
for one real run, which checks executed, which were skipped and why,
which errored, and which of the ones that ran actually passed versus
found something. This module builds that record and never invents an
outcome: every one of the 89+ checks in the live registry gets exactly one
entry, sourced entirely from the same `AsposeCheckResultV1` and
`data/aspose_check_classification.json` every other consumer already
trusts.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.validation.aspose_checks import load_check_registry
from readme_agent.validation.aspose_checks_bridge import (
    AsposeCheckResultV1,
    load_blocking_check_names,
)

CheckOutcome = Literal["pass", "fail", "skip", "error", "not_applicable"]


class CheckCoverageEntryV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    check_name: str
    outcome: CheckOutcome
    severity: Literal["hard_gate", "heuristic"]
    classification: str
    blocking: bool
    reason: str


class CheckCoverageReportV1(BaseModel):
    """Every check in the live registry, accounted for exactly once."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    check_count: int
    pass_count: int
    fail_count: int
    skip_count: int
    error_count: int
    not_applicable_count: int
    entries: tuple[CheckCoverageEntryV1, ...]


def build_check_coverage_report(
    result: AsposeCheckResultV1, classification: dict
) -> CheckCoverageReportV1:
    """`classification` is the parsed `data/aspose_check_classification.json`
    document (its own real, versioned identity -- callers already load and
    fail-closed-validate it elsewhere; this function trusts a caller-parsed
    dict rather than re-reading the file itself, so it composes cleanly
    with `load_blocking_check_names()`'s own fail-closed contract)."""

    registry = load_check_registry()
    by_name = {entry["check_name"]: entry for entry in classification.get("checks", [])}
    findings_by_check: dict[str, int] = {}
    for finding in result.findings:
        findings_by_check[finding.check_name] = findings_by_check.get(finding.check_name, 0) + 1
    blocking_names = load_blocking_check_names()

    entries: list[CheckCoverageEntryV1] = []
    for name in sorted(registry):
        descriptor = registry[name]
        classified = by_name.get(name)
        classification_bucket = classified["classification"] if classified else "unclassified"
        reason = classified["reason"] if classified else "no classification entry for this check"

        if classification_bucket == "unrelated":
            outcome: CheckOutcome = "not_applicable"
        elif name in result.checks_errored:
            outcome = "error"
        elif name in result.checks_skipped:
            outcome = "skip"
        elif name in result.checks_run:
            outcome = "fail" if findings_by_check.get(name) else "pass"
        else:
            # Registered but this run never even attempted it (e.g. the
            # classification itself is stale relative to the live
            # registry) -- never silently absent from the report.
            outcome = "skip"
            reason = f"{reason} (not attempted by this run)"

        entries.append(
            CheckCoverageEntryV1(
                check_name=name,
                outcome=outcome,
                severity=descriptor.severity,
                classification=classification_bucket,
                blocking=name in blocking_names,
                reason=reason,
            )
        )

    counts: dict[CheckOutcome, int] = {
        "pass": 0,
        "fail": 0,
        "skip": 0,
        "error": 0,
        "not_applicable": 0,
    }
    for entry in entries:
        counts[entry.outcome] += 1

    return CheckCoverageReportV1(
        check_count=len(entries),
        pass_count=counts["pass"],
        fail_count=counts["fail"],
        skip_count=counts["skip"],
        error_count=counts["error"],
        not_applicable_count=counts["not_applicable"],
        entries=tuple(entries),
    )


__all__ = ["CheckCoverageEntryV1", "CheckCoverageReportV1", "build_check_coverage_report"]
