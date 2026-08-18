# Phase-14 GitHub-runner readiness audit (2026-08-18)

Fourteen-point audit of `.github/workflows/readme-agent-production.yml` (807 lines) + CI +
profiles. The four purely mechanical gaps found were fixed the same session (commit
`b0298737a`): job `timeout-minutes` (nothing inherits the 6-hour default), `retention-days: 30`
on all six artifact uploads, a concurrency group on `stage-proposal` (the only writing job —
every read job was already grouped), and a `$GITHUB_STEP_SUMMARY` health digest.

## Standing findings (not yet fixed — each needs its own deliberate pass)

1. **Lock is pinned but not hash-pinned, and marker-less.** `requirements-lock.txt` is a
   Windows/Python-3.13 `pip freeze`; CI runs it on ubuntu 3.11/3.12/3.13 and production
   hardcodes 3.12 — the production interpreter matches neither dev (3.13) nor the lock's
   generating interpreter. The 3.11/3.12 legs resolve wheels the lock never saw: the prime
   mechanical suspect for hosted CI red-since-2026-08-02.
2. **`LLM_BASE_URL` does not fail closed**: `env.py` silently falls back to
   `GPT_OSS_ENDPOINT` and then the hardcoded default; it is also absent from
   `env.secret_values()` so it is never redacted. Decide fail-closed vs documented-default.
3. **No candidate upload**: `runs/readme-poc/**` bundles are never uploaded as artifacts, and
   `github_observe` produces no candidate at all (no `local_write`). A human cannot retrieve a
   runner-produced candidate today.
4. **No self re-trigger**: an incomplete slice waits for the next cron; the local slice-budget
   resume loop has no hosted counterpart.
5. **No failure-signature concept in code** (`failure_signature` greps empty) — the health
   report aggregates counts, not signatures; wire the S1..S10 ledger taxonomy in.
6. **One gitignored-state test dependency survives** in the non-live suite:
   `test_source_claim_structured_matching_exact.py` skips (not fails) without
   `runs/baseline/…Note…` — a silent coverage loss on clean checkouts.

## What a fresh clone actually does (verified)

- `runs/local-poc-state/state.git` auto-initializes → clean checkout = cold full portfolio,
  never a resume (all lifecycle state is gitignored).
- `runs/baseline/**` absence blocks nothing in the default gate (`-m 'not live'` excludes the
  docker-live consumers); the TB-05 Note fixture + TB-02 manifest resolver (imported this
  session, commit `c90f72202`) removed the hosted runner-environment failures.
- `.state/` is inert scratch.
- `run_full_pytest.py` is stricter on a pristine tree (fails on any untracked byte appearing
  during the run, and on leaked descendants).

## Clean-checkout local simulation recipe (the defined Phase-14 integration gate)

1. `git clone` to a short path (e.g. `C:\ra`) at the target HEAD; copy nothing gitignored.
2. venv with **3.13**, then exactly CI's install: `pip install -r requirements-lock.txt` +
   `pip install -e . --no-deps` (never `.[dev]` — unpinned resolve).
3. Run the five gates in CI order (`ruff check`, `ruff format --check`, `mypy src`,
   `run_full_pytest.py`, `validate_plan_structure.py`); capture exit codes unmasked.
4. Diff failures against the current 5-failure baseline; expect exactly one skip
   (finding 6 above). Anything else new is a real clean-checkout defect.
5. Repeat under 3.11 and 3.12 (the legs dev never runs — see finding 1).
6. Then the runner-equivalent ACT proof inside the fresh clone
   (`act workflow_dispatch --bind -W .github/workflows/readme-agent-production.yml`
   with `proof_mode=act_qualified_cohort` per
   `plans/investigations/evidence/trp-04p-act-workflow-parity-v1/REPRODUCE.md`) — the
   `restore-qualified-cohort` step rebuilds `runs/readme-poc/**` from committed checksummed
   inputs, so no gitignored state is needed; expect `healthy: true`, zero LLM calls, zero
   effects.

## Finding #1 CLOSED (2026-08-18): hash-pinned lockfile landed

`requirements-lock.txt` is now generated via `pip-compile --extra=dev --generate-hashes`
against `pyproject.toml`'s real dependency declarations (was a plain, unpinned `pip freeze`).
Conflict-free resolution; every entry carries sha256 hashes; verified twice via independent
fresh-venv installs (`pip install --require-hashes -r requirements-lock.txt` → `pip install -e .
--no-deps` → `import readme_agent` → collect-only), including once by this coordinator
independently of the implementing agent. 20 packages moved forward (time-driven `>=`
resolution), `marko`/`mistune` correctly dropped as genuinely unused (grep-verified) leftover
freeze artifacts, package count 75→73. No workflow YAML change needed — neither CI nor
production passes `--require-hashes` today, and a hash-pinned file installs cleanly without it;
adding the flag to enforce hashes in CI is a reasonable, deliberately separate follow-up.

**Deliberate non-action**: this session's own active `.venv` (used throughout for every gate)
was NOT rebuilt against the new lock — it remains on its already-verified package set. Rebasing
the dev environment onto newer tool versions (ruff/mypy bumps) this late risks introducing
unrelated lint/type noise with no mission benefit; the lockfile's job is fresh/CI installs,
which is now correct and independently verified.
