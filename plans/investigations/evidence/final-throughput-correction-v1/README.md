# Final throughput execution freeze

This directory supersedes the historical, non-operative
`plan-reconciliation-acceleration-2026-08-02/campaign-freeze-v1.json`. That earlier manifest
recorded mutable dirty-worktree hashes and remained `CREATED`; it is retained only as evidence of
the rejected boundary.

The operative split is:

- `plan-freeze-v1.json`: `SEALED` committed authority/control bytes at control commit
  `2dff75805e85d24c72477f2e46179e5b0897c3e0`;
- `pipeline-contract-snapshot-v1.json`: `SEALED` exact raw bytes for 85 selected dirty pipeline
  implementation/test files, materialized below the content-addressed runtime root under `runs/`;
- `freeze-acceptance-receipt-v1.json`: `ACCEPTED` replay binding both manifests and the canonical
  `data/aspose_org_links.json` catalog.
- `campaign-evidence-shared_acceleration-v1.json` and
  `campaign-evidence-three_slices-v1.json`: replay-accepted graph/durable-state snapshots. Their
  per-task verdicts remain truthful (`OPEN`/`PARTIAL` where work is unfinished); acceptance of the
  aggregate manifest is not campaign closure.

Reproduce from the repository root:

```powershell
.venv/Scripts/python scripts/governance/seal_final_throughput_contracts.py replay
```

The replay reads worker inputs only from the immutable snapshot. It does not authorize product
repository writes or claim any README lifecycle closure.
