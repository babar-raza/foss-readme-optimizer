"""T3 -- bridge the vendored aspose.org check battery into real candidate
validation, using genuinely real data (candidate text + this repo's own
resolved ProductFactsV2, including the "aspose.*" fields
`facts/provider.py` injects -- T4) rather than the synthetic minimal
fixtures `validation/aspose_checks/__init__.py` uses only to prove
invocability.

A check whose real-data requirements this repo cannot currently satisfy
(e.g. content_units, reference_index -- machinery not yet built/wired for
this pipeline; dependency_snapshot is wired for python/rust as of Gate R6c
but still absent for other registry ecosystems and for repositories whose
manifest this bridge cannot parse) is skipped explicitly and recorded in
`checks_skipped`, never silently treated as passing. A check that raises on
real input (these functions were only ever proven invocable on synthetic
minimal fixtures, never semantically validated against real repositories)
is recorded in `checks_errored`, never allowed to crash the surrounding
candidate validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.validation.aspose_check_inputs import qualified_check_inputs
from readme_agent.validation.aspose_checks import load_check_registry

# data/aspose_check_classification.json (scripts/data-refresh/classify_aspose_checks.py)
# -- the evidence-graded blocking decision per check. Never hand-edited.
_CLASSIFICATION_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "aspose_check_classification.json"
)

# Every fact field provider.py's aspose_fact_records() may inject; used only
# to recover the family/platform this candidate is for (see _real_kwargs).
_ASPOSE_FACT_FIELDS = (
    "aspose.archetype",
    "aspose.install_info",
    "aspose.license_file",
    "aspose.enterprise_link",
    "aspose.seo_keywords",
    "aspose.dev_test_artifacts",
    "aspose.capability_dependencies",
    "aspose.dependency_claims",
)


class AsposeCheckFindingV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    check_name: str
    severity: Literal["critical", "warning"]
    section: str | None
    message: str


class AsposeCheckResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    valid: bool
    checks_run: tuple[str, ...]
    checks_skipped: tuple[str, ...]
    checks_errored: tuple[str, ...]
    findings: tuple[AsposeCheckFindingV1, ...]


def _fact_value(facts: ProductFactsV2 | None, field: str) -> Any:
    if facts is None or field not in facts.selected_fact_ids:
        return None
    return facts.selected_fact(field).value


def _real_kwargs(candidate_text: str, facts: ProductFactsV2 | None) -> dict[str, Any]:
    """Build the real (never synthetic) keyword-argument pool this bridge can
    supply today. A check is only invoked when every parameter it declares
    is a key in this pool -- see run_aspose_checks()."""

    # Deliberately NOT supplying old_readme_text/new_readme_text/
    # old_markdown_text/new_markdown_text: this bridge validates one candidate
    # snapshot, not a before/after diff. Feeding a diff-only check identical
    # old==new text would make it vacuously "pass" every time regardless of
    # the check's real question -- worse than skipping it outright, since a
    # vacuous pass looks like a verified clean result.
    kwargs: dict[str, Any] = {
        "readme_text": candidate_text,
        "markdown_text": candidate_text,
    }
    for field, param in (
        ("aspose.archetype", "archetype"),
        ("aspose.install_info", "install_info"),
        ("aspose.license_file", "license_file"),
        ("aspose.enterprise_link", "enterprise_link"),
        ("aspose.dependency_snapshot", "dependency_snapshot"),
    ):
        value = _fact_value(facts, field)
        if value is not None:
            kwargs[param] = value

    if facts is not None:
        location = None
        for field in _ASPOSE_FACT_FIELDS:
            if field in facts.selected_fact_ids:
                location = facts.selected_fact(field).source.location
                break
        if location and location.startswith("data/imported:"):
            family, _, platform = location.removeprefix("data/imported:").partition("/")
            if family and platform:
                kwargs["family"] = family
                kwargs["own_family"] = family
                kwargs["platform"] = platform

    return kwargs


def _dependency_snapshot_applicable(value: Any) -> bool:
    """`DependencySnapshotV1.applicable` -- `False` means `dependency_
    snapshot.py` already determined this repository/ecosystem has no
    manifest its extraction supports (a real, honest gap, not zero
    dependencies). Defaults to applicable when the shape is unrecognized so
    a genuinely-applicable snapshot is never mistaken for an unsupported one
    just because of a schema drift this function doesn't know about yet."""

    if isinstance(value, dict):
        return value.get("applicable", True) is not False
    return getattr(value, "applicable", True) is not False


def _message_from_finding(raw: Any) -> str:
    if isinstance(raw, dict):
        detail = raw.get("detail") or raw.get("reason") or raw.get("message")
        if detail:
            return str(detail)
        return ", ".join(f"{key}={value!r}" for key, value in raw.items())
    return str(raw)


def run_aspose_checks(candidate_text: str, facts: ProductFactsV2 | None) -> AsposeCheckResultV1:
    """Run every vendored aspose.org check this repo can currently drive with
    real data. Hard-gate checks are severity "critical" (block acceptance,
    matching aspose.org's own quality bar); heuristic checks are "warning"
    (visible, non-blocking)."""

    registry = load_check_registry()
    available = _real_kwargs(candidate_text, facts)
    findings: list[AsposeCheckFindingV1] = []
    checks_run: list[str] = []
    checks_skipped: list[str] = []
    checks_errored: list[str] = []

    for name, descriptor in sorted(registry.items()):
        check_inputs = qualified_check_inputs(name, available)
        if not set(descriptor.required_parameters) <= set(check_inputs):
            checks_skipped.append(name)
            continue
        if "dependency_snapshot" in descriptor.parameters and not _dependency_snapshot_applicable(
            check_inputs["dependency_snapshot"]
        ):
            # This ecosystem/repository has no manifest this bridge's
            # extraction supports at all (dependency_snapshot.py already
            # recorded applicable=False with a real reason) -- invoking the
            # check body anyway would silently return [] for most of these
            # checks (nothing to complain about vs. an empty required-deps
            # list), recorded as a clean "pass" indistinguishable from a
            # real one. Extraction-unsupported must never appear as a
            # passing dependency check: skip explicitly instead.
            checks_skipped.append(name)
            continue
        kwargs = {
            param: check_inputs[param] for param in descriptor.parameters if param in check_inputs
        }
        try:
            raw_findings = descriptor.invoke(**kwargs)
        except Exception:  # noqa: BLE001 -- isolate one unvalidated check from the rest
            checks_errored.append(name)
            continue
        if not isinstance(raw_findings, list):
            # This bridge's normalization only understands the documented
            # list[...]-of-findings convention (empty = pass). A check
            # returning something else (observed: bool, dict) is not
            # semantically interpretable here -- recorded as errored, never
            # guessed at.
            checks_errored.append(name)
            continue
        checks_run.append(name)
        if not raw_findings:
            continue
        severity: Literal["critical", "warning"] = (
            "critical" if descriptor.severity == "hard_gate" else "warning"
        )
        for raw in raw_findings:
            findings.append(
                AsposeCheckFindingV1(
                    check_name=name,
                    severity=severity,
                    section=descriptor.section,
                    message=_message_from_finding(raw),
                )
            )

    return AsposeCheckResultV1(
        valid=not any(finding.severity == "critical" for finding in findings),
        checks_run=tuple(checks_run),
        checks_skipped=tuple(checks_skipped),
        checks_errored=tuple(checks_errored),
        findings=tuple(findings),
    )


def load_blocking_check_names() -> frozenset[str]:
    """Fail closed: a missing, unreadable, or malformed classification file
    is a corpus-integrity defect, not a benign "nothing is blocking yet"
    state -- silently returning an empty set here would make acceptance
    gating pass every candidate regardless of real hard-gate findings,
    exactly the kind of "unit test passes without governed production
    proof" gap this repo's own completion standard rejects. Raise instead;
    the committed `data/aspose_check_classification.json` must always be
    present and well-formed on any checkout that reaches acceptance gating."""

    if not _CLASSIFICATION_PATH.is_file():
        raise RuntimeError(
            f"aspose check classification file missing: {_CLASSIFICATION_PATH} -- "
            "acceptance gating cannot determine which checks are blocking; regenerate via "
            "scripts/data-refresh/classify_aspose_checks.py, never proceed without it"
        )
    try:
        raw = json.loads(_CLASSIFICATION_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(
            f"aspose check classification file unreadable/corrupt: {_CLASSIFICATION_PATH} "
            f"({type(exc).__name__}: {exc}) -- regenerate via "
            "scripts/data-refresh/classify_aspose_checks.py, never proceed without it"
        ) from exc
    checks = raw.get("checks")
    if not isinstance(checks, list):
        raise RuntimeError(
            f"aspose check classification file has no 'checks' list: {_CLASSIFICATION_PATH} -- "
            "regenerate via scripts/data-refresh/classify_aspose_checks.py"
        )
    return frozenset(
        entry["check_name"] for entry in checks if isinstance(entry, dict) and entry.get("blocking")
    )


def blocking_aspose_check_findings(result: AsposeCheckResultV1) -> list[AsposeCheckFindingV1]:
    """The subset of `result.findings` whose check is classified `blocking:
    true` in `data/aspose_check_classification.json` -- checks proven, by
    real empirical validation against currently accepted candidates, not to
    false-positive on this repo's own (independently-designed) template. See
    `scripts/data-refresh/classify_aspose_checks.py`'s module docstring for
    the exact classification method. Every other aspose_checks finding
    remains visible via `AsposeCheckResultV1.findings` but never blocks
    acceptance. Fails closed (raises) when the classification file itself
    is missing or malformed -- see `load_blocking_check_names`."""

    blocking_names = load_blocking_check_names()
    return [finding for finding in result.findings if finding.check_name in blocking_names]


def blocking_aspose_check_gaps(result: AsposeCheckResultV1) -> list[AsposeCheckFindingV1]:
    """Stage 3B: a classified-blocking check that was *skipped* (its real-data
    parameters weren't available) or *errored* (raised, or returned a shape
    this bridge can't interpret) never produced a real finding at all --
    `blocking_aspose_check_findings` above, which only ever inspects
    `result.findings`, cannot see it, so it was previously silently
    indistinguishable from "ran cleanly and passed". This synthesizes one
    critical, clearly-labeled finding per such gap, carrying its actual
    reason (skip vs. error), so acceptance gating sees the true state
    instead of promoting a candidate no blocking check actually verified."""

    blocking_names = load_blocking_check_names()
    gaps: list[AsposeCheckFindingV1] = []
    for name in sorted(blocking_names & set(result.checks_skipped)):
        gaps.append(
            AsposeCheckFindingV1(
                check_name=name,
                severity="critical",
                section=None,
                message=(
                    f"blocking check {name} was skipped this run (its required real-data "
                    "parameters were not available) -- cannot be treated as passing"
                ),
            )
        )
    for name in sorted(blocking_names & set(result.checks_errored)):
        gaps.append(
            AsposeCheckFindingV1(
                check_name=name,
                severity="critical",
                section=None,
                message=(
                    f"blocking check {name} raised or returned an unexpected result this run "
                    "-- cannot be treated as passing"
                ),
            )
        )
    return gaps
