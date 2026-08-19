#!/usr/bin/env python3
"""Classify every check in the vendored aspose.org check battery into one of
four buckets and decide which are promotable to blocking acceptance gates.

Method (mechanical + empirical, never hand-guessed):

1. **Severity** comes straight from `validation.aspose_checks.load_check_registry()`
   (`hard_gate` vs `heuristic`, derived from each check's own docstring convention).
2. **Runnable-now** means every parameter the check declares is already inside
   `validation.aspose_checks_bridge._real_kwargs()`'s supplied set
   (`readme_text`, `markdown_text`, `archetype`, `install_info`, `license_file`,
   `enterprise_link`, `family`, `own_family`, `platform`). A check needing any
   other parameter (`dependency_snapshot`, `content_units`, `available_badges`,
   ...) is not yet drivable with real data this repo produces.
3. **Empirical false-positive check**: every runnable `hard_gate` check is run
   against a committed candidate/facts fixture for each of this portfolio's
   three `AGENT_APPROVED`-or-beyond repositories (3D/barcode/cells-Python --
   the only repositories with real accepted output to validate against;
   fixtures live under `data/check_classification_fixtures/`, refreshed
   deliberately via `refresh_check_classification_fixtures.py`, never read
   live from local `runs/` state -- this classification must be
   byte-reproducible from a clean checkout). A check that fires on at least
   one of them is NOT auto-promoted: real inspection during this
   classification's original authoring session found several vendored
   hard-gate checks encode aspose.org's own specific template conventions
   (an exact license sentence, exact Mermaid subgraph ID names, a
   title-case heuristic tuned to aspose.org's own heading shapes) that this
   repo's independently-designed, independently-reviewed template
   legitimately does not match -- promoting those to blocking would regress
   accepted output on a false positive, not catch a real defect. Those get
   `applicable_after_adaptation`, not `applicable_reusable`, until a human
   confirms (or the check/template is aligned) that the finding is genuine.

Buckets:

* `applicable_reusable` -- hard gate, runnable with real data today, and
  fired zero times against the three current accepted candidates. Promoted
  to blocking (`blocking: true`).
* `applicable_after_adaptation` -- hard gate but either (a) needs production
  input this repo does not build yet, or (b) fired against a currently
  accepted candidate and needs template-alignment review before blocking
  promotion is safe. Never blocking.
* `diagnostic_heuristic` -- heuristic per the vendored module's own
  docstring convention. Kept as a reviewer-visible finding only, per this
  repo's own instruction to keep subjective/probabilistic checks
  non-blocking unless a requirement explicitly promotes them.
* `unrelated` -- checks with zero optimizer-workflow relevance (aspose.org
  issue-management/skill-workflow only). None found: every one of the 89
  checks in `readme_refresh_checks.py` is a README-content correctness
  check by construction (confirmed by a full docstring scan for
  process-only vocabulary -- "skill", "issue tracker", "workflow dispatch",
  etc. -- during this classification's original authoring session). The
  bucket is retained for a future vendored-battery refresh that might add one.

Regenerate after any vendored-check-battery change:

    .venv/Scripts/python scripts/data-refresh/classify_aspose_checks.py
"""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.validation.aspose_checks import load_check_registry
from readme_agent.validation.aspose_checks_bridge import run_aspose_checks

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "data" / "aspose_check_classification.json"
# Committed, version-controlled candidate/facts snapshots -- never `runs/`
# (gitignored, absent on a clean checkout). Refreshed deliberately via
# `refresh_check_classification_fixtures.py`, not read live from local runs.
FIXTURES_ROOT = REPO_ROOT / "data" / "check_classification_fixtures"

# The exact parameter names `_real_kwargs()` can ever supply -- mirrored here
# (not imported) so this script's "runnable now" judgment is provably the
# same test the bridge itself applies at runtime, without importing a
# private helper's return value from a live call.
_REAL_PARAM_NAMES = {
    "readme_text",
    "markdown_text",
    "archetype",
    "install_info",
    "license_file",
    "enterprise_link",
    "family",
    "own_family",
    "platform",
    "dependency_snapshot",
}

# The three repositories currently AGENT_APPROVED-or-beyond in this
# portfolio -- the only ones with a real accepted candidate to validate
# non-regression against. Each repo's candidate + facts are a committed
# snapshot under `FIXTURES_ROOT` (see `_latest_candidate`), not disposable
# `runs/` state -- classification must be byte-reproducible from a clean
# checkout, not silently degrade to "validated against nothing" whenever
# `runs/` (gitignored) happens to be absent, which would flip any hard-gate
# check that only avoided `blocking: true` because it fired against a real
# candidate to blocking on the next regeneration, with no audit trail.
# Refresh a fixture deliberately (`scripts/data-refresh/
# refresh_check_classification_fixtures.py`) when a repository's own
# accepted candidate changes; never point this back at `runs/`.
# `load_check_registry()`'s severity classifier reads only `inspect.getdoc()`
# (real docstrings) -- it cannot see a `#`-comment-only severity note.
# `check_no_leaked_docstring_artifacts` has no docstring at all; its own
# leading comment says "Heuristic, non-blocking (2026-08-09, MT027) -- same
# two-tier posture as check_process_narration_smells" (confirmed by direct
# source read during this classification's original authoring session,
# 2026-08-19). The mechanical classifier's own documented fail-closed
# default (unmarked -> hard_gate) then makes it look promotable although its
# real author intent was heuristic. This is the one confirmed instance found
# this session; it is listed explicitly, with the evidence above, rather
# than silently patched -- a future vendored-battery refresh should recheck
# every comment-only (docstring-less) check the same way.
_SEVERITY_OVERRIDES: dict[str, str] = {
    "check_no_leaked_docstring_artifacts": "heuristic",
}

# Checks that passed the three-repository empirical validation above but were
# then proven, by running this repo's own full relevant unit-test suite
# (`tests/unit/test_readme_document_plan.py`,
# `test_readme_existing_section_regressions.py`, `test_agentic_readme_
# composition.py`, `test_readme_assessment.py`, `test_readme_section_
# journey.py`, `test_readme_factuality.py` -- 2026-08-19), to false-positive
# against this repo's own legitimate, real generated content:
#
# * `check_process_narration_smells` flags "The coordinate was verified
#   against Maven Central" as leaked internal process narration. That
#   sentence is this repo's own deliberate, factual visitor-facing content
#   (a verified installation fact), not aspose.org's internal assurance
#   narration (source revisions, isolated-build conditions, provider calls --
#   see docs/architecture.md's "Internal assurance narration" rule) the check
#   was actually written to catch. A blanket "was verified" phrase match is
#   too broad for this repo's own install-verification prose convention.
# * `check_scope_limitations_format` requires the Scope and Limitations
#   section to close with a specific Enterprise Edition prose paragraph --
#   this repo's own template places that relationship prose differently
#   (see `readme/presentation_contract.py`), so the check's structural
#   assumption does not match this repo's current, independently-designed
#   contract.
#
# Three real repositories were not a large enough validation sample; this
# repo's own test suite is the stronger, broader signal. Both stay
# `applicable_after_adaptation` rather than `applicable_reusable` until
# either the check is narrowed (process narration) or this repo's template
# is deliberately aligned with the exact closing-paragraph convention
# (scope/limitations).
_BLOCKING_OVERRIDES: dict[str, str] = {
    "check_process_narration_smells": (
        'false-positives on this repo\'s own legitimate "was verified against <registry>" '
        "install-verification prose -- confirmed via a full relevant-suite regression run, "
        "not merely the 3-repository empirical pass above"
    ),
    "check_scope_limitations_format": (
        "requires an exact Enterprise Edition closing-paragraph convention this repo's own "
        "template does not currently produce -- confirmed via a full relevant-suite "
        "regression run, not merely the 3-repository empirical pass above"
    ),
}

# `check_no_excluded_domain_links` was previously overridden to nonblocking
# here: it fired against a real captured-evidence NET fixture
# (tests/unit/test_readme_existing_section_regressions.py) whose original
# README carries a forum.aspose.com/products.aspose.app link. Root-caused
# 2026-08-19 (Gate R4): `document_link_hygiene.py`'s `_URL` pattern only
# recognized `aspose.com`/`aspose.org`, never `aspose.app`, so a
# `products.aspose.app` link survived every strip-then-restore pass
# unrecognized (confirmed: `forum.aspose.com` was already being stripped
# correctly, since `.com` was covered). Fixed by adding `aspose.app` to
# `_URL`; the fixture test was updated to wire in the real link catalogs it
# had been omitting (matching what every real `readme-agent poc` run always
# supplies), and now produces zero findings for this check with both links
# genuinely stripped. No override remains -- this check is now empirically
# clean like every other `applicable_reusable` check.

_VALIDATION_REPOS = {
    "aspose-3d-foss/Aspose.3D-FOSS-for-Python": "aspose-3d-foss__Aspose.3D-FOSS-for-Python",
    "aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python": (
        "aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python"
    ),
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Python": (
        "aspose-cells-foss__Aspose.Cells-FOSS-for-Python"
    ),
}


def _latest_candidate(repo_dir_name: str) -> tuple[str, ProductFactsV2 | None] | None:
    """The committed candidate/facts fixture for one validation repository.
    `None` only when a repository genuinely has no fixture yet (never a
    silent `runs/`-absence degradation) -- callers must be able to tell "not
    validated against this repo yet" apart from "validated, found nothing.\""""

    base = FIXTURES_ROOT / repo_dir_name
    readme_path = base / "candidate" / "README.md"
    if not readme_path.is_file():
        return None
    text = readme_path.read_text(encoding="utf-8")
    facts_path = base / "facts" / "product-facts.json"
    facts: ProductFactsV2 | None = None
    if facts_path.is_file():
        try:
            raw_facts = json.loads(facts_path.read_text(encoding="utf-8"))
            facts = ProductFactsV2.model_validate(raw_facts)
        except Exception:  # noqa: BLE001 -- best-effort empirical input, never fatal
            facts = None
    return text, facts


def _observed_critical_findings() -> tuple[set[str], set[str], list[str]]:
    """Returns (fired, genuinely_run, validated_against).

    `genuinely_run` is the set of checks `run_aspose_checks()` actually
    invoked against at least one real fixture -- distinct from merely
    "not in `fired`", which a check that was *skipped* everywhere (every
    fixture is missing one of its declared parameters) also satisfies
    vacuously. A check no fixture's `ProductFactsV2` can currently supply
    real data for must never read as "empirically validated clean" --
    confirmed as a real defect found running this classification after
    Gate R6c added `dependency_snapshot`: none of the three committed
    fixtures predate that fact, so every `dependency_snapshot`-needing
    check was skipped at every fixture, yet the old (name not in fired)
    check alone would have promoted them to `applicable_reusable` with a
    reason text falsely claiming "zero false positives observed"."""

    fired: set[str] = set()
    genuinely_run: set[str] = set()
    validated_against: list[str] = []
    for org_repo, dir_name in _VALIDATION_REPOS.items():
        found = _latest_candidate(dir_name)
        if found is None:
            continue
        text, facts = found
        result = run_aspose_checks(text, facts)
        fired |= {
            finding.check_name for finding in result.findings if finding.severity == "critical"
        }
        genuinely_run |= set(result.checks_run)
        validated_against.append(org_repo)
    return fired, genuinely_run, validated_against


def build_classification() -> dict:
    registry = load_check_registry()
    fired_critical, genuinely_run, validated_against = _observed_critical_findings()

    entries = []
    for name, descriptor in sorted(registry.items()):
        missing_params = sorted(set(descriptor.parameters) - _REAL_PARAM_NAMES)
        runnable_now = not missing_params
        severity = _SEVERITY_OVERRIDES.get(name, descriptor.severity)

        if not runnable_now:
            classification = "applicable_after_adaptation"
            blocking = False
            reason = f"blocked on missing production input(s): {', '.join(missing_params)}"
        elif severity == "heuristic":
            classification = "diagnostic_heuristic"
            blocking = False
            reason = "heuristic per vendored docstring convention; reviewer-visible finding only"
        elif name in fired_critical:
            classification = "applicable_after_adaptation"
            blocking = False
            reason = (
                "hard gate; fired against a currently accepted candidate during this "
                "classification's empirical validation pass -- needs template-alignment "
                "review before blocking promotion is safe"
            )
        elif name not in genuinely_run:
            classification = "applicable_after_adaptation"
            blocking = False
            reason = (
                "hard gate; the parameter this check declares is theoretically suppliable "
                "(runnable_now=true) but no committed fixture's ProductFactsV2 currently "
                "carries real data for it, so the check was skipped at every fixture during "
                "this classification's empirical pass -- never genuinely exercised, so never "
                "auto-promoted on the strength of a vacuous absence from fired_critical; "
                "refresh the fixtures (refresh_check_classification_fixtures.py) once a real "
                "candidate carries this input before reconsidering"
            )
        elif name in _BLOCKING_OVERRIDES:
            classification = "applicable_after_adaptation"
            blocking = False
            reason = _BLOCKING_OVERRIDES[name]
        else:
            classification = "applicable_reusable"
            blocking = True
            reason = (
                "hard gate; runnable with real data; zero false positives observed against "
                "the current accepted candidates or this repo's own relevant unit-test suite"
            )

        if name in _SEVERITY_OVERRIDES:
            reason += (
                f" (severity manually overridden from mechanically-derived "
                f"'{descriptor.severity}' to '{severity}' -- see _SEVERITY_OVERRIDES)"
            )

        entries.append(
            {
                "check_name": name,
                "severity": severity,
                "mechanically_derived_severity": descriptor.severity,
                "scope": descriptor.scope,
                "section": descriptor.section,
                "runnable_now": runnable_now,
                "classification": classification,
                "blocking": blocking,
                "reason": reason,
            }
        )

    return {
        "schema_version": 1,
        "generator": "scripts/data-refresh/classify_aspose_checks.py",
        "check_count": len(entries),
        "blocking_count": sum(1 for e in entries if e["blocking"]),
        "empirically_validated_against": validated_against,
        "checks": entries,
    }


def main() -> None:
    classification = build_classification()
    OUTPUT_PATH.write_text(
        json.dumps(classification, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()}: "
        f"{classification['check_count']} checks, {classification['blocking_count']} blocking, "
        f"validated against {classification['empirically_validated_against']}"
    )


if __name__ == "__main__":
    main()
