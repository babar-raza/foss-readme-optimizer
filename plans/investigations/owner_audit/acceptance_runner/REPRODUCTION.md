# Reproduction notes

## Scope and safety

This was a read-only audit. No source repository, GitHub ref, issue, workflow, state ref, or product
repository was modified. No live LLM, product build, Docker verification, or full portfolio run was
started. The local optimizer checkout is detached at `56a5f09c`; conclusions about current main
use GitHub file/commit reads pinned to `6d112bbf88bc54f7ef3367b16ef8e9b769bdfb51`.

## Repository authority

```text
GitHub commit:
https://github.com/babar-raza/foss-readme-optimizer/commit/6d112bbf88bc54f7ef3367b16ef8e9b769bdfb51
```

The GitHub commit read initially showed exactly one commit after `1c6fbd495`: `6d112bbf`.
That commit changes `composer_factpack.py` and `test_knowledge_fact_determinism.py` to remove
`target_map_stale` from enterprise-link verification. Its own recorded full-suite result is
5 failed / 4194 passed / 1 xfailed.

Before audit close, main advanced to `685246a7a4dc014adcdcd3da5be8ca49498ee2ed`.
That commit changes control-repository governance/hook scripts and tests only; it does not change
the acceptance/runtime files audited at `6d112bbf`.

## Read-only inventory commands

Run from the extracted Aspose bundle:

```bash
rg '^def check_' files/scripts/pipeline/commands/foss/readme_refresh_checks.py | wc -l
find files/reports/repo-presenter-regen-full -type f -iname readme.md | wc -l
find files/knowledge -type d -name merged | wc -l
find files/reports/readme_refresh_runs -type f -name manifest.json | wc -l
```

Observed: 103 checks, 31 canonical candidates, 8 selective knowledge bundles, 11 run manifests.

Run from the optimizer checkout:

```bash
rg '^def check_' \
  src/readme_agent/vendored_asposeorg/scripts/pipeline/commands/foss/readme_refresh_checks.py \
  | wc -l
find data/imported/knowledge -type d -name merged | wc -l
jq -r 'group_by(.ecosystem)[] | [.[0].ecosystem,length] | @tsv' data/products.json
```

Observed: 89 checks, 31 imported knowledge bundles, 33 registry entries across seven ecosystems.

To reproduce the missing-name set:

```bash
comm -23 \
  <(sed -nE 's/^def (check_[^(]+).*/\1/p' \
      BUNDLE/files/scripts/pipeline/commands/foss/readme_refresh_checks.py | sort) \
  <(sed -nE 's/^def (check_[^(]+).*/\1/p' \
      OPTIMIZER/src/readme_agent/vendored_asposeorg/scripts/pipeline/commands/foss/readme_refresh_checks.py | sort)
```

## Required acceptance replay after repairs

1. Checkout one final optimizer SHA at or after `685246a7` with a clean worktree and use only its
   repository `.venv`. Before committing, verify the post-commit hook's `origin` is exactly the
   intended control repository; never install/use it in a target product checkout.
2. Pin immutable target inputs separately:
   pre-refresh README commit, current default-branch commit, imported knowledge `repo_sha`, and
   canonical Aspose candidate hash. Do not use a refreshed current README as the original.
3. Run official gates:

```bash
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m ruff format --check .
.venv/Scripts/python -m mypy src
.venv/Scripts/python scripts/governance/run_full_pytest.py
```

4. Run one bounded verified canary for each of: pre-refresh 3D/Python, pre-refresh Note/Python,
   pre-refresh Barcode/Python, one genuinely unrefreshed repository, and one README-only fixture.
5. For each run require:
   - candidate and source hashes;
   - item-level knowledge disposition coverage;
   - byte-complete source reconciliation;
   - content/structure/code/badge disposition coverage;
   - 103-check inventory with no unclassified entry, no execution error, and no skipped applicable
     hard gate;
   - deterministic acceptance, independent review, bounded repair history, final approval;
   - an immediate second run with identical candidate/artifact hashes and zero provider calls.
6. Repeat with one repository from .NET, Java, C++, TypeScript, Rust, and Go.
7. Reproduce `.github/workflows/readme-agent-production.yml` with `act` using the same verified
   profile and restored bundle cache, then run a manually dispatched hosted read-only proof.
8. Only after the representatives pass, execute the dynamic `data/products.json` denominator and
   reconstruct the aggregate from persisted artifacts. Expected denominator is 33.

## Document identity warning

At audit start these tips already contained refreshed documents:

- 3D/Python `ee05c1ba9153ef5916b7a108406c794f2e464d01`;
- Note/Python `41de2e8ab478b5aeff3663f7f7cbf83b19fdf676`;
- Barcode/Python `06eca5c01e13ed6d59a640f1cf330c1c5a57d151`.

Results against those current README bytes are preservation/no-op evidence only unless the test
explicitly restores and binds a pre-refresh source document.
