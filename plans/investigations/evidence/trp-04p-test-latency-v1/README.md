# TRP-04P Test-Latency Proof

This package proves a correctness-preserving reduction in the complete non-live pytest campaign.
It does not deselect tests, replace the closure suite with focused tests, or claim that hosted
workflow bootstrap is fully optimized.

## Result

- Current serial reference: 2,348 passed, 41 live tests deselected by repository policy, 1,049.01
  seconds.
- Repeated bounded benchmarks after test isolation: 2,349 passed in 270.85 and 283.41 seconds.
- Final clean committed closure run after the runner and its five additive controls: 2,353 passed
  in 236.63 pytest seconds (237.854 wrapper seconds).
- Accepted command: `.venv/Scripts/python scripts/governance/run_full_pytest.py`.
- Bounds: four workers, `worksteal`, zero permitted worker restarts, a short xdist temp root on
  Windows, and post-run descendant detection.
- Inventory: the closure receipt records 2,353 selected nodes and SHA-256
  `21425a5464f0cf6eff1a7a778eef7b22a94fa3c358f81a73326e23743d8183f8`.

The five nodes added by the optimization slice were also run serially. Together with the serial
2,348-node reference, they cover the exact 2,353-node closure inventory. The optimized closure run
then passed that same current inventory without retries or omissions.

## First-boundary repairs

The first xdist experiment was rejected. It exposed inherited interactive Git credential helpers
and Windows path-length failures; five tests failed. Offline tests now hide system/global Git
configuration and disable interactive prompting, and the closure runner uses a deliberately short
temporary root. A later hosted CI attempt was also rejected before pytest because CI resolved
unlocked Ruff 0.16.0 instead of committed Ruff 0.15.22. CI now installs `requirements-lock.txt`
before the editable package. Linux mypy then exposed a Windows-only subprocess constant in Linux
stubs; the platform guard is now explicitly annotated without changing process cleanup.

The first descendant check also counted unrelated Python processes from another repository as
leaks. The accepted check binds a process to this repository by command line and has a negative
control for simultaneous unrelated repository activity. These are environment-boundary defects,
not test assertions edited to manufacture a pass.

## Verification tiers

- Editing: touched-file Ruff plus the smallest owning contract tests.
- Coherent seam: process cleanup, Git safety, workflow, state, authorization, and evidence/security
  regressions selected by the affected public contract.
- Closure: the complete non-live inventory through the bounded runner, with a checksum-bound
  receipt.
- Reuse: allowed only when commit, dependency lock, Python/runtime, test inventory, and required
  gate hashes match. A changed commit invalidates the receipt.

Workflow dependency caching is implemented with the lock as its cache key. A cache-miss run and an
identical primary-key cache-hit rerun both passed; restoring the cache did not materially remove
the 11-16 second locked install. A wheel/minimal-runtime split therefore remains a measured hosted
App qualification opportunity, not a hidden prerequisite for this proof.

## Reproduction

```powershell
.venv/Scripts/python scripts/governance/run_full_pytest.py `
  --receipt runs/verification/trp-04p-test-latency-clean.json
```

The raw serial run, collection inventory, rejected first benchmark, repeated accepted benchmarks,
closure receipt, verification record, independent verdict, and SHA-256 inventory are preserved
beside this file.
