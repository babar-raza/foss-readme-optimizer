# Independent Review Start

Review this package as a plan/control-plane release, not as proof that the README portfolio is
complete.

## Start here

1. Read `AGENTS.md` for repository governance and safety.
2. Read `plans/idea.md`, `plans/master.md`, `plans/requirements.md`, and
   `plans/GOVERNANCE.md` in their subject-specific authority roles.
3. Inspect `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` as the sole
   executable graph and `plans/status.md` as the generated snapshot. Durable supervisor state,
   not this ZIP, owns live task status after packaging.
4. Read `plan-reconciliation-report.md`, `contradiction-matrix.md`,
   `independent-verification-history.md`, and `freeze-validation-history.md`.
5. Reproduce `campaign-freeze-v1.json` before trusting cached or dirty contract bytes.
6. Inspect the canonical independent report under
   `runs/multi-agent/PLAN-RECONCILIATION-ACCELERATION-2026-08-02/independent-verification/`.

## Required verdict boundary

The plan gate may be accepted only if authority, trusted-history exclusion, canonical order,
campaign membership, mission migration, current 31-repository status, reviewer design, suite
economy, and freeze hashes agree. Current product truth remains 1/31 accepted and 0/31 no-op. Do
not infer product readiness, Gate A, Gate B, Gate C, or maturity from this plan package.

## Safety

No product repository write is authorized. The package contains no secrets. The control commit is
`83d43102582c4cf7d74250529927b2256e30f718`; content-addressed dirty contract inputs are disclosed
in `campaign-freeze-v1.json` and must be invalidated on mismatch.
