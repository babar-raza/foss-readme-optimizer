# README validation contract (vendored aspose.org check battery)

T3 (freshness-service plan): this document is the drift-test target for the vendored
89-check battery (`src/readme_agent/validation/aspose_checks/`). It states what the
registry itself already derives mechanically -- the numbers below are asserted against
the live registry by `tests/unit/test_readme_process_drift.py`, never hand-maintained as
a source of truth.

## Where the checks come from

Vendored, with explicit authorization (`plans/investigations/evidence/imported-corpus-v1/
licensing-resolution-state.md`), from aspose.org's `readme_refresh_checks.py`
(`src/readme_agent/vendored_asposeorg/scripts/pipeline/commands/foss/`). Loaded and
classified by `readme_agent.validation.aspose_checks.load_check_registry()`.

## Check inventory (derived, not a binding constant)

As of the registry's last derivation: **89** checks. Never hardcode this number anywhere
outside a comment explaining it changes -- see resolution 7 of this plan ("check
inventory is derived, never a binding constant"). The registry's own `load_check_registry()`
re-derives it by introspection on the vendored module every time it's called.

## Classification

Each check carries two independently derived properties:

- **Severity** (`hard_gate` | `heuristic`): parsed from the vendored function's own
  docstring convention ("Hard gate" / "Heuristic, non-blocking..."). A check whose status
  was explicitly *changed* (e.g. "downgraded from an originally-planned hard gate")
  classifies by whichever term appears first in its docstring -- current status, not
  history. A check with no marker at all fails closed to `hard_gate`.
- **Scope** (`section` | `document_global`): derived from the check's name prefix. Checks
  scoped to a single README section (`check_diagram_*` → "At a Glance",
  `check_license_*` → "License", etc.) invalidate only that section on a content change;
  document-global checks (disposition/duplicate/reconciliation checks, narration/casing
  rules) invalidate the whole document.

## Fail-closed fixture coverage

Every one of the 89 checks is proven genuinely invocable, on a real (not mocked) call,
with a minimal but contract-realistic README fixture, returning a correctly-typed result
(`list[dict]`, `dict`, or `bool` per the check's own return annotation) --
`tests/unit/test_aspose_checks_fixture_coverage.py`. This is systematic coverage of every
check's basic operability and type contract, not 89 individually hand-crafted semantic
test cases (each check's exact business logic would need its own deep-dive to test that
thoroughly; that remains future work -- see the T3 closeout evidence for what's not yet
done).

## What is NOT yet part of this contract

- Individual semantic fixtures per check (positive AND negative cases proving each
  check's specific rule, not just that it runs) -- only a representative few checks have
  this today (see `test_aspose_checks_registry.py`'s 5 real end-to-end invocations, and
  `test_hard_gate_checks_correctly_flag_a_deliberately_incomplete_minimal_fixture`'s 6).
- Wiring the registry into an actual composition/validation pipeline (T14, T5 onward).
- The remaining ~40% of the vendored `readme_refresh_run.py` orchestration's factpack
  detectors not yet adapted (T4's own closeout evidence lists exactly which).
