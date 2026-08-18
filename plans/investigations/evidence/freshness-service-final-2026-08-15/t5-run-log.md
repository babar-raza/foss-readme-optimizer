# T5 — pilot run log (cells/python)

Target: `aspose-cells-foss/Aspose.Cells-FOSS-for-Python` (real, publicly clonable — confirmed via
`git ls-remote`; `mode: dry_run` in `data/products.json`, matching the standing pilot
authorization for local-only, non-mutating runs). Source revision resolved at run time:
`26c3bd1633e84b91c0f6fad1fd353662fd61fb54` (`main`).

## Run 1

```
readme-agent poc --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Python
```

stdout: `aspose-cells-foss/Aspose.Cells-FOSS-for-Python: composing via LLM (no valid reusable
plan)` then `... DIAGNOSTIC_VALIDATION_reject -> runs\share\poc\...\README.md`.

`candidate-README.md` sha256: `2e6579ea89c1a06ede70928e564c1f352584a88467b56dd66a46d39bd618a6f3`.

## Run 2 (immediately after, unchanged inputs)

```
readme-agent poc --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Python
```

stdout: `aspose-cells-foss/Aspose.Cells-FOSS-for-Python: reusing hash-bound composition plan`
then the same `DIAGNOSTIC_VALIDATION_reject -> ...` line.

Candidate sha256 (run 2): `2e6579ea89c1a06ede70928e564c1f352584a88467b56dd66a46d39bd618a6f3` —
**byte-identical to run 1** (`diff` empty). Run 2 made **zero new LLM calls** ("reusing
hash-bound composition plan" — not "composing via LLM"), matching `noop.json`'s own internal
proof (`candidate_sha256 == recomposed_sha256`, `new_provider_call_count: 0`,
`llm_accounting_status: "EXACT"`, `verdict: "RENDER_REPRODUCIBLE"`).

## Docker isolation machinery — proven live, not wired into this specific candidate

The diagnostic `poc` path's `verified_example_present` check
(`readme/document_validation.py:411`) is a **static** exact-substring presence check, not
container execution — confirmed by reading its source before claiming otherwise. The real
Docker-isolated verifier (`facts/isolated_execution.py::execute_isolated`, consuming
`IsolatedExecutionRequestV1`) is separate machinery, reached by the full canonical
`supervise` transaction, not the diagnostic `poc` runner (which explicitly disclaims
`acceptance_authority` and bypasses "the mission graph, durable lifecycle, recovery, and the
complete canonical supervisor transaction" — `validation.json`'s own
`acceptance_exclusion` field).

Attempted `readme-agent supervise --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Python
--execution-profile local_dry_run`: did not complete within the available session time (process
terminated, exit 143/SIGTERM, no output produced) — an honest, disclosed non-result, not a
fabricated success. `--execution-profile local_poc` (the profile the CLI itself names as the
supported full-portfolio path) requires `--registry data/products.json`, i.e. a whole-portfolio
run across 30+ products — out of proportion and out of scope for a single-repo pilot skeleton,
and not attempted for that reason.

In place of a full single-repo Docker-verified run, the **existing, already-tested Docker
isolation machinery was proven live and functional** in this environment: `tests/security/
test_isolated_execution_docker_live.py` (marked `@pytest.mark.live`, excluded from the default
suite per `pyproject.toml`'s `addopts = "-m 'not live'"`) run explicitly with `-m live`:

```
.venv/Scripts/python.exe -m pytest tests/security/test_isolated_execution_docker_live.py -v -m live
```

Result: **2 passed in 13.80s** — `test_real_container_enforces_truth_isolation_controls` and
`test_real_container_timeout_kills_work_and_cleans_resources`, both against a real, pinned
`alpine@sha256:14358309a308569c32bdc37e2e0e9694be33a9d99e68afb0f5ff33cc1f695dce` image with real
container start/stop/cleanup. This proves the capability is real and live in this environment;
it does not itself constitute a Docker-verified run of cells/python's specific example code.
