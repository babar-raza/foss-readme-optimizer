# Agile Authority Reset Reproduction

The accepted implementation is commit `73fb96db18133194ebc88c35d5997e19f5187f86` with tree
`0f2dba6a132c230d1372f9f2290c83f9d58cbb10`.

From a clean checkout of that commit, use the repository virtual environment and run:

```powershell
.venv/Scripts/python scripts/governance/run_official_checks.py
.venv/Scripts/python scripts/governance/validate_compact_authority.py
.venv/Scripts/python scripts/governance/query_requirement_catalog.py `
  --task-id L8-AGILE-AUTHORITY-RESET
```

Expected results are 3,229 passing non-live tests with no other outcomes or leaked processes;
98 decisions, 475 requirements, seven active tasks, 125 deferred tasks, and one ready task; and an
exact eight-requirement task slice containing `L8-047` through `L8-054`.

The non-authoring V3 verifier additionally reran 288 repaired-boundary public-seam tests, 80 safety
tests, direct cache-invalidation and effect-ledger adversarial probes, actionlint, JSON validation,
and the compact-authority reconstruction. Its source receipt and verdict hashes are recorded in
`verification.json`.
