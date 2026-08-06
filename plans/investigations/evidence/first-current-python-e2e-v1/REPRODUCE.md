# First Current Python README E2E Proof

This evidence closes only `L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E`. It proves the
first finalized repository-verified README and partial portfolio progress. It
does not claim the complete Python POC or verified Gate A.

## Reproduce the complete non-live gate

Create a clean detached worktree at commit
`92bc1df6cfd7d9da1d4131e752781aa9cd0e32b0`, point `PYTHONPATH` at that
worktree's `src` directory, and run:

```powershell
.venv\Scripts\python.exe scripts\governance\run_full_pytest.py
```

The checked-in receipt records 3,376 passing tests, a clean and unchanged tree,
the dependency-lock hash, the exact test-inventory hash, and no leaked
descendant processes.

## Reconstruct the promoted artifact

With the accepted runtime bundle present under
`runs/readme-poc/aspose-3d-foss__Aspose.3D-FOSS-for-Python/62fb89f3ca76dc0afa9b2dfb983b9a1fa3f74fba/`,
run:

```powershell
.venv\Scripts\python.exe scripts\governance\promote_finalized_verified_readmes.py
```

Then verify every entry in
`plans/investigations/evidence/finalized-repository-readmes-v1/sha256sums.txt`
with SHA-256. The promoted README and runtime candidate must both hash to
`6340b6512071b72de09154a9b3f2ecbf59ceaf5635f64b1641e546026c20278c`.

The unchanged runtime proof is
`review/no-op-proof.json`: it records `NO_OP_PROVEN`, no patch, no duplicate
bundle, zero new provider calls, and one accepted-cache reuse. No product
remote, target branch, or pull request was written.
