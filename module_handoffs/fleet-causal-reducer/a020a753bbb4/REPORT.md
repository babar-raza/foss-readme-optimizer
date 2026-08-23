# OPT-STANDALONE-FLEET-CAUSAL-REDUCER — handoff report

## 1-2. Base and current upstream SHA / drift

- Base SHA: `a020a753bbb408fbef7675c8562cf677e14cbab4`
- Current upstream `main` SHA at handoff time: `d6fbed567aa7d99dd0e065944e3694cb6ebd5ced`
- Drift: 1 commit (`fix(evidence): resume long-path supersession`), unrelated to this module.
  Recorded in `BASE_AND_DRIFT.json`, never fetched into or merged onto this lane's branch.

## 3-4. Branch and commits

- Branch: `claude/standalone-fleet-causal-reducer-a020a753bbb4`
- Commits (see `COMMITS.txt`):
  1. `test(portfolio-proof): add fleet causal reducer contracts and red tests`
  2. `feat(portfolio-proof): implement fleet failure causal reducer`
  3. (this commit) `docs(fleet-causal-reducer): add handoff record`

## 5. Push status

Pushed `HEAD:refs/heads/claude/standalone-fleet-causal-reducer-a020a753bbb4` to `origin` only,
using the disabled-pushurl mechanism (real URL restored only for the single push, then immediately
disabled again). No other ref pushed.

## 6. Exact changed files

See `CHANGED_FILES.txt`. Two files added:
- `src/readme_agent/supervisor/portfolio_proof_engine/failure_causal_reducer.py`
- `tests/unit/test_portfolio_proof_engine_failure_causal_reducer.py`

Plus this handoff directory (`module_handoffs/fleet-causal-reducer/a020a753bbb4/**`), added in its
own commit per the task's instructions.

## 7. Public interface

See `INTERFACE.md`. Entry point: `reduce_fleet_failures(*, observations, dependency_snapshot=None)
-> FleetCausalReductionV1`. Six public models, six public `Literal` aliases.

## 8. Fingerprint and normalization rules

See `CAUSAL_FINGERPRINT_SPEC.md` for the full 7-tier cascade, the narrow normalizer's exact
strip/never-strip lists, the 10-row classification decision table, the deterministic prioritization
sort key, and the minimal-proof-cohort selection algorithm.

## 9. Deeper system assessment (why the module differs from the original brief in four places)

At the user's explicit request, this module was reassessed as a production problem before
finalizing its design, not built strictly to the letter of the original task brief. Three research
passes went into this repo's real evidence: owner-audit findings, the decision-ledger history
behind existing retry/determinism mechanisms, and fine-grained PF-01 failure data. Key findings:

- **LLM-level nondeterminism is real, documented, and already correctly designed around**
  (Decision #105: qwen3-next tool-call arguments are nondeterministic at temperature 0) — this
  module respects the existing no-re-roll/ratchet philosophy rather than fighting it.
- **The deterministic scaffolding meant to compensate for that nondeterminism has its own integrity
  bugs** — most concretely, a confirmed instance of a "reproducible" no-op replay that actually made
  2 live provider calls, contradicting its own zero-call claim.
- **A real evidence-granularity gap**: 10 of 29 real observed PF-01 failures
  (`validation_rejected`) carry no structured per-check detail upstream at all.
- **Verdicts in this codebase don't always consult the checks meant to gate them** (e.g.
  `commands_poc.py` not consulting `disposition_ledger_valid` before labeling a candidate
  `DELIVERED`).

This produced four concrete, evidence-motivated deltas to the module's design, all additive within
the single owned source file:

1. A `confidence: Literal["high","medium","low"]` field on every cluster — required by the task's
   own OUTPUT section ("Confidence based on structured evidence") but missing from the first design
   pass; added and tier-derived.
2. A `pipeline_source` field, folded into the fingerprint hash from tier 4 onward, so weak-signal
   observations never silently merge across this fleet's three non-reconciled observation pipelines
   (zero-provider qualification, `commands_poc` delivery, `local_poc` supervisor seam).
3. A `known_reproducibility_verdict` field (reusing this repo's own `RENDER_REPRODUCIBLE`/
   `TRANSACTION_NO_OP_PROVEN`/`NO_OP_PROVEN` vocabulary from Decision #100) that keeps a false
   "reproducible" claim from silently satisfying closure evidence, and biases representative
   selection toward genuinely-proven-reproducible members.
4. A fail-closed "opaque-bulk" guard: a cluster formed *only* from unstructured free text, with
   `member_count >= 5`, is forced to `unknown`/`confidence="low"`/
   `manual_classification_required` rather than a confident guess — modeled directly on the real
   10-member `validation_rejected` shape.

Full reasoning, evidence citations, and explicit tradeoffs/risks/limits are in the approved plan
(`C:\Users\prora\.claude\plans\chat-name-opt-standalone-fleet-causal-re-temporal-biscuit.md`, not
part of this repo) and restated for durability in `KNOWN_LIMITATIONS.md`.

## PF-01-like and PF-03-like reduction results

**PF-01-like** (`PF01_LIKE_REDUCTION_EXAMPLE.json`): 29 synthetic observations modeled on the real
`qualification.status_counts` split from this repo's own evidence (7 `plan_unavailable`, 12
`render_failed`, 10 `validation_rejected`) reduce to **4 clusters**: two `shared_code_defect`
(7 and 8 members), one `ecosystem_adapter_defect` (4 members), and one honestly-`unknown` cluster
(the 10 opaque `validation_rejected`-shaped members, `confidence="low"`) — not 29 unrelated tasks,
not one over-merged blob, and not a falsely-confident guess on the one bucket this repo's real
evidence proves is currently opaque.

**PF-03-like** (`PF03_LIKE_REDUCTION_EXAMPLE.json`): **illustrative/synthetic only** — PF-03 has no
real evidence yet (see `KNOWN_LIMITATIONS.md` §8). 8 synthetic observations across 4 intended
categories reduce to 7 clusters: 1 `repository_evidence_defect` (packet-construction-shaped), 1
`transient_provider` (401-shaped, dependency-changed), 1 `shared_code_defect` (2 repos, 2
ecosystems, `readme_review_reducer`-shaped), and 4 singleton `candidate_specific_rejection` clusters
(the four presentation repairs) — demonstrating the reducer distinguishes all four named categories
into non-overlapping clusters.

## Tests and static checks

32 tests, all passing. `ruff check`, `ruff format --check`, `mypy` (src module), and
`git diff --check` all clean. Narrow regression suite (contracts/retry_policy/stage_classifier,
33 tests) passes with zero regressions. Full details in `TEST_RESULTS.json`.

## Known limitations

See `KNOWN_LIMITATIONS.md` — foregrounded there, not buried: this module does not by itself move
the fleet's "0/31 accepted" state, its effectiveness on `validation_rejected`-shaped failures is
capped by a real upstream evidence-granularity gap, clusters must be recomputed every fleet pass
(never cached across a code revision), and three concrete upstream fixes are recommended as
BACKLOG items for Codex/the product owner (never implemented in this lane).

## Handoff and recovery paths

- Handoff: `module_handoffs/fleet-causal-reducer/a020a753bbb4/` (this directory)
- Recovery bundle: `runs/parallel_staging/fleet-causal-reducer/a020a753bbb408fbef7675c8562cf677e14cbab4/handoff/`
  (`patches/`, `fleet-causal-reducer.bundle`, `fleet-causal-reducer-combined.patch`)
- Work log: `runs/parallel_staging/fleet-causal-reducer/a020a753bbb408fbef7675c8562cf677e14cbab4/WORKLOG.md`

## Integration recommendation

See `INTEGRATION.md`. Summary: Codex should call `reduce_fleet_failures` after a fleet pass produces
coherence-checked `ProofStageReceiptV1` records, before repair selection — never as a replacement
for `retry_policy.py`, `dashboard.py`, or `portfolio_scheduler/reducer.py`, all of which retain their
existing authority unchanged.

## 13. Confirmation

- Main checkout (`D:\Users\prora\OneDrive\Documents\GitHub\foss-readme-optimizer`): untouched. All
  work happened inside the isolated clone at
  `runs/parallel_staging/fleet-causal-reducer/a020a753bbb408fbef7675c8562cf677e14cbab4/repo`.
- `plans/**`, `AGENTS.md`, `docs/**`, `.github/**`: untouched.
- Graphs, requirement/decision catalogs, mission/status/resume artifacts: untouched (read-only
  referenced during research).
- Existing receipts, evidence, product repositories: untouched.
- Existing scheduler/reducer/runtime modules (`portfolio_scheduler/reducer.py`,
  `retry_policy.py`, `dashboard.py`, `blocked_decision_cache.py`, `local_poc_cache.py`,
  `bounded_review_results.py`, `readme_review_reducer.py`): read-only referenced, never modified or
  duplicated — see "Reused models and utilities" reasoning restated in `INTEGRATION.md` and
  `WORKLOG.md`.
- Other lanes' files (`bounded-review/`, `public-quality-gates/`, `repository-executor/` under
  `runs/parallel_staging/`): untouched, never opened.
- No CLI/runtime registration, no state write, no retry, no repair execution, no fleet/provider/
  Qwen/Docker/product-repository operation, no PR opened, no push beyond the single named feature
  branch, no claim of fleet improvement.

Then stop. No integration, no repair execution.
