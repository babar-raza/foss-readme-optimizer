# Registry eligibility, verified-throughput, and multi-agent integration evidence

This evidence package records the 2026-08-02 control-repository integration slice at base HEAD
`dd0fd06d6c0701050afcb645479ea6d801a1ca98` on `main`. It is evidence for the integrated dirty
candidate tree, not a claim that `L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP`, Gate A, or the Level-8 mission
is closed.

## Outcomes proved

- The execution registry contains 31 entries. Every admitted name satisfies the case-insensitive
  `Aspose[.-]{Family}-FOSS-for-{Platform}` contract with one terminal platform token.
- Only `aspose-html-foss/CSSForge` and
  `aspose-pdf-foss/Aspose-PDF-FOSS-for-Go-MCP` were removed relative to the base commit.
  `aspose-pdf-foss/Aspose-PDF-FOSS-for-Go` remains admitted.
- The current platform denominator is Python 12, .NET 6, Java 4, C++ 4, TypeScript 2, Go 2,
  and Rust 1.
- Discovery, loading, and reconciliation share one naming implementation. Stable provider
  identity and a configured override cannot admit a nonconforming name. A conforming but
  ambiguous identity remains in the prior registry state without refresh; it is not silently
  deleted.
- The product-truth forced-tool contract transports minimal examples as bounded physical source
  lines. Deterministic normalization preserves indentation and rejects scalar, malformed,
  embedded-newline, and oversized payloads without an ecosystem-specific production branch.
- Raw lifecycle acceptance is now separated from currently reusable acceptance. The current
  durable scoreboard reports 2 raw approvals/no-op proofs but 0 current approvals/no-op proofs,
  with Slides Python and Words Python explicitly stale.
- Invalidated candidates are copied to immutable, shortened-path superseded evidence with their
  full SHA-256 identity retained in `superseded.json`.
- The sole mission graph now contains a machine-readable coordinator-led worker-wave contract.
  Every claimed task must disposition Repair, Advancement, Validator/Evidence,
  Documentation/State-Sync, and Independent Verification, assign disjoint leases to active lanes,
  serialize integration/state/commits, and pass independent verification before human review.
- Independent review found that the Documentation/State-Sync worker had directly authored an
  uncommitted shared-file proposal. The coordinator reviewed and integrated that proposal, then
  repaired the durable contract: future documentation/state workers are proposal-only under
  `runs/multi-agent/`, and only the coordinator may apply changes to authority/shared files.

## Verification performed

- Registry, lifecycle, facts, prompt, safety, and integration matrix: 288 passed in 102.95 seconds.
- Legacy fixture repair group: 139 passed and 2 precise residual failures; both residual controls
  were repaired and then passed. The final remaining specialist fixtures passed 47/47.
- Complete non-live inventory: 2,639 passed in 259.95 seconds using four workers, work-steal
  distribution, zero worker restarts, and zero leaked repository processes. The machine-readable
  receipt is `runs/verification/pytest-full-latest.json`.
- Ruff check, Ruff format check, mypy over 490 source files, plan structure, verifier wiring,
  prompt hygiene, 459-row requirement/task coverage, semantic traceability, actionlint, and
  `git diff --check` passed after the complete suite. Actionlint was invoked through the pinned
  absolute path `C:/Users/prora/go/bin/actionlint.EXE` because it is not present on `PATH`.

## Honest limitations

- `CORE-023`, `L8-036`, and `L8-038` remain `PARTIAL`. This slice does not provide the required
  fresh authenticated all-visibility GitHub enumeration and current `RegistryRevisionV1` proof.
- The durable mission state is version 676 and reports graph drift until this coherent graph is
  committed and reconciled through `evaluate`.
- The portfolio is not agent-approved: 17/31 are `FACTS_READY`, 9/31 have candidates and
  deterministic validation, and 0/31 have current agent approval or no-op proof.
- Aspose.TeX FOSS for Python remains blocked at the source/product boundary: 102 of 119 Python
  files observed by the repair lane are syntax-invalid, and no verified PyPI acquisition path was
  found. This is not converted into guessed product truth.
- No product repository, branch, pull request, setting, package, release, or default branch was
  changed by this slice.

## Reproduction

The 288-test integration matrix used this exact command:

```powershell
.venv/Scripts/python -m pytest -q `
  tests/unit/test_registry_discovery.py `
  tests/unit/test_registry_loader.py `
  tests/unit/test_registry_reconciliation.py `
  tests/unit/test_registry_revision.py `
  tests/unit/test_registry_self_heal.py `
  tests/unit/test_registry_intake.py `
  tests/unit/test_readme_poc_intake.py `
  tests/unit/test_supervisor_intake.py `
  tests/unit/test_commands_lifecycle.py `
  tests/integration/test_readonly_intake_portfolio.py `
  tests/unit/test_mission_control.py `
  tests/unit/test_content_assurance.py `
  tests/unit/test_local_poc_cache.py `
  tests/unit/test_local_poc_evidence.py `
  tests/unit/test_agentic_drafting.py `
  tests/unit/test_draft_product_truth_capability.py `
  tests/unit/test_llm_call_ledger.py `
  tests/unit/test_prompt_hygiene.py `
  tests/unit/test_gitsafety.py `
  tests/security/test_no_secrets_in_evidence.py
```

The complete and governance checks used:

```powershell
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m ruff format --check .
.venv/Scripts/python -m mypy src
.venv/Scripts/python scripts/governance/run_full_pytest.py
.venv/Scripts/python scripts/governance/validate_plan_structure.py
.venv/Scripts/python scripts/governance/check_verifiers_are_wired.py --check
.venv/Scripts/python scripts/governance/check_prompt_hygiene.py
.venv/Scripts/python scripts/governance/build_level8_requirement_taskcard_coverage.py --check
.venv/Scripts/python plans/investigations/tools/traceability_matrix.py --check
& 'C:/Users/prora/go/bin/actionlint.EXE' `
  (Get-ChildItem .github/workflows/*.yml | ForEach-Object FullName)
git diff --check
```
