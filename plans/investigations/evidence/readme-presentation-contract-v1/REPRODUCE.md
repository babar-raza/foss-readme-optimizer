# Reproduce the repository-presentation contract proof

Start from commit `5f463e753c634d625547e97d3bafae0dff254cf0` in the repository-root
virtual environment.

```powershell
.venv/Scripts/python -m pytest -q tests/unit/test_repository_presentation_template.py

.venv/Scripts/python -m pytest -q `
  tests/unit/test_repository_presentation_template.py `
  tests/unit/test_readme_header_visual.py `
  tests/unit/test_readme_presentation_lint.py `
  tests/unit/test_readme_document_plan.py `
  tests/unit/test_readme_existing_section_regressions.py `
  tests/unit/test_readme_operation_regressions.py `
  tests/unit/test_independent_readme_review.py `
  tests/unit/test_supervise_readme_proposal_review_integration.py `
  tests/security/test_no_secrets_in_evidence.py `
  tests/unit/test_gitsafety.py `
  tests/unit/test_registry_loader.py

.venv/Scripts/python scripts/governance/run_full_pytest.py `
  --workers 4 `
  --receipt runs/verification/pytest-full-latest.json

.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m ruff format --check .
.venv/Scripts/python -m mypy src
.venv/Scripts/python scripts/governance/validate_plan_structure.py
.venv/Scripts/python scripts/governance/build_level8_requirement_taskcard_coverage.py --check
.venv/Scripts/python plans/investigations/tools/traceability_matrix.py --check
git diff --check
```

The focused proof must reconstruct
`aspose-note-foss-python-golden.md` byte-for-byte, compile the distinct ProductFactsV2 fixture,
reject every negative control, and report no validation errors for either accepted positive case.
