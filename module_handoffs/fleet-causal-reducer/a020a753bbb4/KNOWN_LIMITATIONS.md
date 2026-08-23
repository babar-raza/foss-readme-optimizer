# Known limitations

This section is foregrounded, not a footnote: read it before deciding how to use this module's
output. It exists because a deeper, evidence-backed reassessment of this repo's real fleet-failure
data (owner-audit findings, decision-ledger history, and fine-grained PF-01 evidence) was done
before finalizing this module's design, at the user's explicit request to treat the task as a
production problem rather than build strictly to the letter of the original brief. That research is
summarized here so its conclusions travel with the code, not just with a chat transcript.

## 1. This module will not by itself move the fleet's "0/31 accepted" state

It triages and prioritizes already-collected evidence; it cannot manufacture missing signal. Real
evidence from this repo's own PF-01 qualification run shows `validation_rejected`-shaped failures
(10 of 29 real observed failures, ~34%) carry **no per-check structured detail upstream**
(`blocking_finding_count: 0, blocking_gap_count: 0` despite `document_valid: false` and 103 checks
run). For as long as that upstream gap exists, this class of failure will correctly — not as a bug —
collapse toward `unknown` / `manual_classification_required` rather than a sharp, actionable
cluster. The bundled `PF01_LIKE_REDUCTION_EXAMPLE.json` shows this honestly: group D (10 opaque
repos) resolves to one `unknown` cluster with every member individually preserved in the minimal
proof cohort, not a confident guess.

**Recommended upstream fix (out of this lane's scope — BACKLOG for Codex/product owner):**
`document_validation.py`/`aspose_check_coverage.py` should emit a per-check structured failure ID
into whatever evidence eventually feeds this reducer's `gate_or_check_id`/`structured_error_code`
fields. Until then, this module's reduction power on that failure class is capped by design, not by
implementation quality.

## 2. Clusters have a short shelf life in this codebase today

Comparing two runs of the same zero-provider qualification script, 11 hours apart, on an identical
`registry_sha256`, showed 60%+ of the 31 processable repos change failure bucket — some from real,
uncoordinated code fixes landing in between, at least one (`Aspose.PDF-FOSS-for-Java`) from a
`source_revision` that silently differed despite an identical registry hash. **Any caller that
caches or persists this module's cluster output across a code-revision boundary will silently go
stale** and could misdirect a repair effort at an already-fixed defect. Recompute fresh every fleet
pass; never treat a stored `FleetCausalReductionV1` as valid once the codebase has moved.

**Recommended regression control (out of this lane's scope — BACKLOG for Codex):** a CI job that
runs this reducer against two evidence snapshots taken hours apart on an otherwise-unchanged
`registry_sha256` and asserts cluster-membership stability — the automatable version of the manual
comparison that surfaced the drift above.

## 3. `transient_provider` classification is lower-confidence than the decision table's other rows

This repo's own probes (Decision #105, and the 2026-08-18 mission-recovery evidence) establish that
qwen3-next tool-call arguments are nondeterministic at temperature 0, but explicitly acknowledge the
characterization is incomplete ("neither should be generalized to always/never works"). This
module's `transient_provider` row is an exception-type-name heuristic — the best available
inference from structured evidence, not ground truth about whether a given failure will actually
reproduce differently on retry. Treat it as a hint, not a guarantee.

## 4. The `member_count >= 5` opaque-bulk threshold is a judgment call

Deliberately conservative, motivated directly by the real 10-member `validation_rejected` bucket
found in this repo's evidence, but not derived from a larger statistical study. Under-tuning it (too
high) risks a future opaque bulk cluster slipping through as false-confident; over-tuning it (too
low) risks needlessly demoting small, plausibly-real clusters to `unknown`. Documented as tunable —
if a future integration finds this threshold wrong for a different failure population, changing the
single `_OPAQUE_BULK_THRESHOLD` constant is the intended extension point.

## 5. Verdicts this module consumes may themselves be unreliable — garbage in, garbage out

Independent owner-audit findings on this repo (read-only, during this module's research) found that
`commands_poc.py::run_poc_for_repo`'s promotion/`DELIVERED` computation does not currently consult
`disposition_ledger_valid`, and that independent LLM review has issued `ACCEPT` for candidates with
known self-contradictions and failing deterministic checks. This module reflects whatever evidence
it is fed — consistent with "never a second scoring system," it does not independently re-verify
claims. **If fed observations sourced from an unreliable upstream verdict, its clusters will
faithfully reflect that unreliability.**

**Recommended upstream fix (out of this lane's scope — BACKLOG for Codex/product owner):**
`commands_poc.py::run_poc_for_repo` should consult `disposition_ledger_valid` before this reducer is
fed anything from that delivery pipeline; prefer feeding it `ProofStageReceiptV1`-backed
observations that have already passed `dashboard.py`'s receipt-chain coherence checks.

## 6. Three non-reconciled pipelines exist in this fleet today

The zero-provider qualification diagnostic, the `commands_poc` delivery path, and the real-provider
`local_poc` supervisor seam are three separate observation systems whose outcomes for the same repo
do not currently cross-validate. This module's `pipeline_source` field and its participation in
tiers 4-6 of the fingerprint hash (see `CAUSAL_FINGERPRINT_SPEC.md`) keeps weak-signal observations
from silently merging across these pipelines, but it does not — and cannot, from inside this lane —
reconcile the three pipelines into one coherent fleet-truth. That is a larger architectural question
outside this module's scope.

## 7. `docs/architecture.md`'s module map was not updated

AGENTS.md's general convention is that a new module updates the module map in
`docs/architecture.md`. This lane's explicit prohibited-actions list forbids touching `docs/**`, so
that update was deliberately skipped here. **Recorded as a required Codex-side follow-up at
integration time.**

## 8. The PF-03-like fixture is illustrative, not real evidence

PF-03 (`L8-PF-03-SEALED-CANDIDATE-NO-OP`) is a real task ID in this repo's mission graph, scoped to
exactly one repository, currently `TODO` with no evidence directory yet. The four category names in
this module's own test brief for that scenario do not appear anywhere in this repo's commits, plans,
or evidence — a hypothesis linking them to the concurrent `fix(review):` bounded-review-packet
commit cluster could not be confirmed by any documented source. `PF03_LIKE_REDUCTION_EXAMPLE.json`
and the corresponding test are explicitly labeled illustrative/synthetic and grounded in real code
shapes (not invented wholesale), but **must never be read as a replay of observed PF-03 failures.**

## 9. No claim of fleet improvement

Per the task's own instruction: this module has not been run against production fleet state, has
not been shown to move fleet acceptance metrics, and no such claim is made anywhere in this handoff.
