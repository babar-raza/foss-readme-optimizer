# L8-VPY-03 closeout-semantics amendment — report

## Outcome

`L8-VPY-03-ALL-PYTHON-VERIFIED-POC`'s `closeout_rules`/`acceptance_checks` are amended, under new
governance decision 102, to require every current Python repository to reach `NO_OP_PROVEN` **or**
an accepted typed external-blocker disposition — instead of an unqualified "every repository ...
no-op-proven". No repository's own state changed. No product-repository write occurred.

## Why

Live `mission evaluate` recovered the expired claim on `L8-VPY-03` and confirmed it still could
not close: 10 of 13 Python repositories are `NO_OP_PROVEN`; the other 3 (HTML, PSD, TeX) carry
genuine, product-owner-reviewed, non-agent-fixable external blockers (see `logs/2026-08-12.md`'s
`master mission cohort external-blocker` and `master governance evidence html decision-101`
entries). `L8-VPY-03`'s own `closeout_rules` read literally required all 13, which none of the
three remaining repositories can ever satisfy without an upstream/product action this project has
no authority to perform (no product-repository write is authorized by this work).

Because `L8-VPY-04-PRODUCTION-TRANSPORT`, `L8-VPY-05-PRODUCTION-ADMISSION`, and every non-Python
task after them (`L8-VNET-01` first) depend on `L8-VPY-03` reaching status `CLOSED` — confirmed by
reading `src/readme_agent/supervisor/mission_control.py` directly: dependency satisfaction is
`_DEPENDENCY_SATISFIED = _TERMINAL_SUCCESS = {"CLOSED"}`, and `closeout_rules` is schema-only
prose the mission controller never parses or evaluates — the literal "all 13" reading permanently
blocks the entire requested non-Python portfolio (.NET, Java, C++, TypeScript, Rust, Go) behind
three repositories this project cannot fix.

Asked the product owner how to proceed. Chosen: amend the graph's closeout semantics via a new
governance decision, rather than pursue the one repairable blocker (HTML) through a separately
authorized product-repo push, or record the conflict and stop without further progress.

## What changed

- **Governance decision 102** (`plans/master.md`, `plans/decisions/catalog.jsonl`): a
  platform-cohort gate task may close, solely to unlock the mission controller's `CLOSED`-only
  dependency check on later tasks, once every repository in its scope is `NO_OP_PROVEN` or carries
  an accepted, human-reviewed typed disposition. It requires an explicit, individual human
  product-owner review of every remaining blocker's disposition before it applies — already
  satisfied here (see `logs/2026-08-12.md`).
- **`L8-VPY-03`'s `acceptance_checks`/`closeout_rules`/`failure_reroute`** amended in place to
  state that disposition-aware bar honestly.
- **Independent, non-authoring review** (see `independently_verified` evidence) found two real,
  narrow gaps and both were fixed: `plans/master.md`'s Decision Ledger header still said "101
  stable decisions" after decision 102 was added (fixed); PSD had no dedicated disposition record
  comparable to HTML's `data/working_condition_exceptions.json` entry or TeX's
  `report/findings/tex/python/upstream-issues.md` (fixed by adding
  `report/findings/psd/python/upstream-issues.md`, per decision 101's own routing rule for a
  repository whose source is missing rather than merely broken).
- **A `GOV-032` backlog row was attempted and reverted** — see "Reverted attempt" in
  `amended-files.md`. Adding a new row to `plans/requirements/catalog.jsonl` broke 5 real tests
  (`TestCompactAuthoritySourceBinding`) because of a genuine, pre-existing asymmetry in
  `scripts/governance/validate_compact_authority.py`: decisions can be appended post-migration
  (filtered out of the source-reconstruction check by ID), requirements currently cannot. Fixing
  that validator is out of scope for this amendment, so the row was reverted rather than shipped
  with a self-caused test regression; the underlying finding is preserved via the new PSD record
  and this note instead of a formal catalog row.

## What did NOT change (explicit scope limits)

- **Decision 101's guarantee is untouched**: a typed-disposition repository (HTML's
  `HUMAN_ACCEPTED_WORKING_CONDITION_EXCEPTION`, PSD's deferred status, TeX's excluded status) is
  never reclassified as `NO_OP_PROVEN` and never counts toward Gate A/B or full-registry closure.
  Decision 102 does not reopen that; it only changes what unlocks the *next task in the dependency
  graph*.
- **No other task's closeout wording changed.** Decision 102 is a general principle (reusable for
  a future platform's own gate task, mirroring how decision 101 was built as a reusable pattern,
  not a one-off), but *applying* it to a specific task requires that task's own wording to be
  edited in place — done here only for `L8-VPY-03`.
- **HTML, PSD, and TeX's own dispositions are unchanged.** Their resume predicates (a corrected
  `pyproject.toml` + PyPI publish for HTML; a corrected commit for TeX; a real source push for
  PSD) are exactly as recorded on 2026-08-12. Each independently returns to the strict lane on its
  own resume predicate, without reopening `L8-VPY-03` or anything that depends on its closure.
- **No product-repository write occurred.** No default branch, PR, or package publish.
- **`L8-VPY-03`'s own status is not asserted as "POC completion."** The amended `failure_reroute`
  clause says so explicitly: closing under decision 102 unlocks downstream sequencing only.

## Verification approach

This amendment touches zero Python source or test files (`plans/`, `logs/`, and generated
`plans/investigations/evidence/` / `plans/investigations/control/` reference-hash refreshes only).
`ruff check`, `ruff format --check`, and `mypy src` all pass clean (see
`static-and-focused-verification.json`), confirming no regression. Because closing `L8-VPY-03` is
itself a declared cohort boundary (decision 94: complete suites and canonical evidence occur at
declared shared/repository/cohort boundaries, not every micro-fix), a fresh complete non-live
pytest run was taken bound to this session's HEAD rather than citing the prior, older-commit
receipt — its exact outcome, including any pre-existing failures, is recorded honestly in
`static-and-focused-verification.json` and is not weakened, hidden, or deleted to force a green
result.

## Truth boundary

Generated is not verified; verified is not human accepted; human accepted is not publication
eligible. This amendment changes only whether `L8-VPY-03` may reach `CLOSED` in the mission
controller's dependency graph. It proves nothing new about any individual repository's README
content, and it authorizes no product effect.
