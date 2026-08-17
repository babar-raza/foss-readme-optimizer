"""T3 -- bridge the vendored aspose.org check battery into real candidate
validation, using genuinely real data (candidate text + this repo's own
resolved ProductFactsV2, including the "aspose.*" fields
`facts/provider.py` injects -- T4) rather than the synthetic minimal
fixtures `validation/aspose_checks/__init__.py` uses only to prove
invocability.

A check whose real-data requirements this repo cannot currently satisfy
(e.g. content_units, dependency_snapshot, reference_index -- machinery not
yet built/wired for this pipeline) is skipped explicitly and recorded in
`checks_skipped`, never silently treated as passing. A check that raises on
real input (these functions were only ever proven invocable on synthetic
minimal fixtures, never semantically validated against real repositories)
is recorded in `checks_errored`, never allowed to crash the surrounding
candidate validation.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.validation.aspose_checks import load_check_registry

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
        if not set(descriptor.parameters) <= set(available):
            checks_skipped.append(name)
            continue
        kwargs = {param: available[param] for param in descriptor.parameters}
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
