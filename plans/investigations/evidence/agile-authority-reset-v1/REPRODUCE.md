# Agile Authority Reset Reproduction

The accepted implementation is commit `73fb96db18133194ebc88c35d5997e19f5187f86` with tree
`0f2dba6a132c230d1372f9f2290c83f9d58cbb10`. The committed closeout and requirement-evidence
reconciliation is commit `489c8dca227c5fbb54a38fdb3eb9ae6db79dd547` with tree
`bdba91d38c61db822ccd3c2eed0b99278b95b53b`.

From a clean checkout of that commit, use the repository virtual environment and run:

```powershell
.venv/Scripts/python scripts/governance/run_official_checks.py
.venv/Scripts/python scripts/governance/validate_compact_authority.py
.venv/Scripts/python scripts/governance/query_requirement_catalog.py `
  --task-id L8-AGILE-AUTHORITY-RESET
```

The implementation tree produced 3,229 passing non-live tests. The closeout tree produced 3,230
passing non-live tests. Both receipts record no other outcomes, leaked processes, or tree mutation;
the latter is SHA-256 `b31b797dd52b27ebc167fbe832043049608ee3704b58bd1218bd8fd6db162001`.
The compact catalog contains 98 decisions, 475 requirements, seven active tasks, 125 deferred tasks,
and an exact eight-requirement reset slice containing `L8-047` through `L8-054`.

The non-authoring V3 verifier additionally reran 288 repaired-boundary public-seam tests, 80 safety
tests, direct cache-invalidation and effect-ledger adversarial probes, actionlint, JSON validation,
and the compact-authority reconstruction. Its source receipt and verdict hashes are recorded in
`verification.json`.

The durable reset closed at state version 765 with graph hash
`6bfe0443c80dfd1c622271ab57d04d4ef3717d93b5c460c352dc9059803410bc`. The same controller then
claimed `L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E` at state version 766 with no graph drift.
