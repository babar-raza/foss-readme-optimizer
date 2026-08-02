# Wave 3 Page and PDF Python facts evidence

Verdict: `ACCEPTED_FOR_PAGE_PDF_FACTS_SLICE_ONLY`.

This record proves current-contract, repository-verified `FACTS_READY` results for Aspose.Page
FOSS for Python and Aspose.PDF FOSS for Python. It does not prove a README candidate, independent
README quality approval, no-op candidate acceptance, Wave 3 closure, verified Python POC closure,
Gate A, or any product effect.

Both repositories were recollected through the canonical bounded `local_poc` supervisor. Each
first run made exactly one `draft_product_truth` provider call. Each identical rerun made zero
provider calls and zero effects, executed no later stage, and preserved its revision-addressed
bundle. Independent verification accepted the four terminal manifests and current durable facts.

The first Page attempt failed closed because Docker Desktop's Linux engine was stopped. The
coordinator started the installed engine, verified Docker Desktop 4.47.0, Engine 28.4.0, and the
exact pinned Python image, then reran the unchanged command successfully. Isolation was not
weakened and no implementation change was made.

## Reproduction

```powershell
.venv/Scripts/readme-agent supervise --repo aspose-page-foss/Aspose.Page-FOSS-for-Python --execution-profile local_poc --bounded-verified-canary --max-readme-poc-stage FACTS_READY
.venv/Scripts/readme-agent supervise --repo aspose-pdf-foss/Aspose-PDF-FOSS-for-Python --execution-profile local_poc --bounded-verified-canary --max-readme-poc-stage FACTS_READY
.venv/Scripts/python -m pytest -q tests/unit/test_fact_acceptance_contract.py tests/unit/test_local_poc_cache.py tests/unit/test_local_poc_evidence.py tests/unit/test_product_truth_ingestion.py tests/unit/test_repository_snapshot.py tests/unit/test_stage_limit.py tests/unit/test_supervisor_product_truth.py tests/unit/test_python_dependency_acquisition.py tests/unit/test_python_public_api.py
.venv/Scripts/python -m pytest -q tests/unit/test_gitsafety.py tests/unit/test_registry_loader.py tests/security/test_no_secrets_in_evidence.py
```

The open `EVID-005` limitation is explicit: all four terminal manifests have a null top-level
`facts_hash`, while their durable lifecycle and revision-bundle manifests bind the current non-null
hash. This prevents broader terminal-manifest closure but does not invalidate the bounded facts
result.
