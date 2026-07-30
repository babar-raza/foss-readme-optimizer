# TRP-04P Test-Latency Proof

This package proves a correctness-preserving reduction in the complete non-live pytest campaign.
It does not deselect tests, replace the closure suite with focused tests, or claim that hosted
workflow bootstrap is fully optimized.

## Result

- Current serial reference: 2,348 passed, 41 live tests deselected by repository policy, 1,049.01
  seconds.
- Repeated bounded benchmarks after test isolation: 2,349 passed in 270.85 and 283.41 seconds.
- Clean committed closure run after the runner and its four additive controls: 2,352 passed in
  206.19 pytest seconds (207.526 wrapper seconds).
- Accepted command: `.venv/Scripts/python scripts/governance/run_full_pytest.py`.
- Bounds: four workers, `worksteal`, zero permitted worker restarts, a short xdist temp root on
  Windows, and post-run descendant detection.
- Inventory: the closure receipt records 2,352 selected nodes and SHA-256
  `01a0f5dfdba057a894c9ae06eade77cf917a0009719aa209114d0aba4173d7d9`.

The four nodes added by the optimization slice were also run serially. Together with the serial
2,348-node reference, they cover the exact 2,352-node closure inventory. The optimized closure run
then passed that same current inventory without retries or omissions.

## First-boundary repairs

The first xdist experiment was rejected. It exposed inherited interactive Git credential helpers
and Windows path-length failures; five tests failed. Offline tests now hide system/global Git
configuration and disable interactive prompting, and the closure runner uses a deliberately short
temporary root. A later hosted CI attempt was also rejected before pytest because CI resolved
unlocked Ruff 0.16.0 instead of committed Ruff 0.15.22. CI now installs `requirements-lock.txt`
before the editable package. Linux mypy then exposed a Windows-only subprocess constant in Linux
stubs; the platform guard is now explicitly annotated without changing process cleanup.

These are environment-boundary defects, not test assertions edited to manufacture a pass.

## Verification tiers

- Editing: touched-file Ruff plus the smallest owning contract tests.
- Coherent seam: process cleanup, Git safety, workflow, state, authorization, and evidence/security
  regressions selected by the affected public contract.
- Closure: the complete non-live inventory through the bounded runner, with a checksum-bound
  receipt.
- Reuse: allowed only when commit, dependency lock, Python/runtime, test inventory, and required
  gate hashes match. A changed commit invalidates the receipt.

Workflow dependency caching is implemented with the lock as its cache key. Cold/warm hosted
bootstrap measurement and any wheel/minimal-runtime split remain part of hosted App qualification;
they are not represented as completed by this package.

## Reproduction

```powershell
.venv/Scripts/python scripts/governance/run_full_pytest.py `
  --receipt runs/verification/trp-04p-test-latency-clean.json
```

The raw serial run, collection inventory, rejected first benchmark, repeated accepted benchmarks,
closure receipt, verification record, independent verdict, and SHA-256 inventory are preserved
beside this file.
