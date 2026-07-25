# Full-registry README POC — recon report

Taskcard `RPOC-001`, sprint `FULL-REGISTRY-README-POC-RESET-001`. Answers the 15 recon questions from
the sprint charter. Companion: `full-registry-readme-poc-build-vs-adopt-audit.md` (`RPOC-002`).
Ledger: `plans/investigations/control/full-registry-readme-poc-taskcards.yaml`.

All findings below are grounded in direct reads of `data/products.json`, `config/policies/*.yml`,
`plans/requirements.md`, and the `plans/investigations/evidence/` bundles — cited by path throughout.

## 1. Repository count

**31**, computed live from `data/products.json` (a JSON list; `len()` gives the count — the
acceptance/portfolio logic built in this sprint must call this at runtime, never hard-code 31 or 3).
Mode breakdown: 29 `dry_run`, 2 `full` (`aspose-3d-foss`, `aspose-cells-foss`, both Java), 0
`disabled`.

## 2. Source README snapshot completeness

**30 of 31 have a populated README snapshot; 1 does not — and it's a known bug, already being
fixed.** 27 of 28 non-pilot repos have real snapshot content (2,137–102,171 bytes) under
`plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25/<slug>/original-readme.md`;
all 3 Java pilots have snapshots under their own 2026-07-24 evidence dir. The one gap —
`aspose-words-foss/Aspose.Words-FOSS-for-.NET` — has an empty evidence directory because
`clone_baseline()` hit `SCL-010` (`WinError 145`, a Windows long-path/directory-not-empty cleanup
failure in `gitsafety/clone.py`) before the pipeline could run. A snapshot *does* exist elsewhere on
disk (`runs/baseline/aspose-words-foss__Aspose.Words-FOSS-for-.NET/README.md`, 7,171 bytes, from an
earlier unrelated clone) — this repo has been snapshotted before, just not by the current pipeline.
`RPOC-040` (in progress as of this report) fixes the underlying bug; re-running the portfolio
collector afterward should close this gap without further work.

## 3. Repository profile completeness

**0 repos have a genuine, current, complete `RepositoryProfile` (`profile/schema.py`) on disk.**
The closest artifacts — `full-registry-ecosystem-survey/survey-results.json` and
`full-registry-wave6-survey/survey-results.json` — cover only 25 of the current 31 repos (stale by
registry growth; 6 repos including `Aspose.Words-FOSS-for-.NET` and 5 others are missing entirely)
and lack `source_revision`/full `package_roots` (schema grew since these surveys ran). This is a real
gap, not previously tracked as a blocking requirement — noted here for whoever executes `RPOC-081`
(the full-registry batch run), since running the drafting pipeline across all repos will naturally
produce fresh, complete profiles as a side effect; no separate remediation taskcard is needed.

## 4. Adequate verified product facts

**3 of 31** (`aspose-3d-foss`, `aspose-cells-foss`, `aspose-pdf-foss` — all Java) have a substantive
`product_truth` block in their `config/policies/*.yml`. Confirmed by direct parse of all 31 policy
files.

## 5. Local candidates exist

Up to 30 of 31 have had a candidate generated at some point (27/28 non-pilot + 3 pilots), via two
different code paths (see #6) — "a candidate file exists" is explicitly listed in the sprint charter
as something that must NOT be conflated with agent approval, and this recon confirms why: see #7/#8.

## 6. Candidates produced by an LLM-driven (fact-discovery) path

**0.** The only existing LLM call anywhere in the candidate-generation pipeline
(`relationship_explained`, in the older `candidate_pipeline.py` path used for the 28 non-pilot repos)
phrases already-supplied facts into one paragraph — it never reads repository source to discover or
draft product understanding. The 3 pilots' path (`idea_candidate.py`) is fully deterministic
(`llm_called: False`, hardcoded). This is the exact gap `RPOC-033` (agentic fact drafting, in
progress) closes.

## 7. Passed deterministic validation

Of the 27 non-pilot repos that reach the validation stage (see #8 for the 1 that doesn't):
**schema validation passes 27/27; checksum validation passes 27/27; citation validation fails
27/27** (`portfolio-proof-manifest.json`: `schemas_valid: true`, `artifact_checksums_match: true`,
but `cited_facts_accepted: false` and `independent_validation_valid: false`, for every single repo).
The specific, consistent failure reason across all 27: missing product facts — `product.audience`,
`product.capabilities`, and a missing verified minimal example, repeated identically per repo
(`independent-review.json`'s `citation_errors`). **This is direct, strong confirmation that the
missing-product-truth gap (#4) is the singular root cause blocking every non-pilot repo today** —
not 27 different problems, one problem repeated 27 times. Validates the sprint's core thesis and the
priority given to `RPOC-033`.

## 8. Passed independent agentic review

**0**, and this number will stay structurally 0 until `RPOC-021`/`022`/`023` land — no independent
agentic reviewer (the 5-way `ACCEPT`/`REJECT_REPAIRABLE`/`BLOCKED_FACT_CONFLICT`/
`BLOCKED_MISSING_EVIDENCE`/`SYSTEM_FAILURE` role the charter defines) exists yet as a system
component. The 27/28 figure above is *deterministic* validation only.

## 9. Required manual prose repair

**None found — with affirmative counter-evidence, not just absence of evidence.** A keyword sweep
across all `plans/investigations/evidence/` found no sign of hand-edited generated content. Stronger:
every one of the 27 "ok" repos' evidence shows `independent_reconstruction_byte_identical: true`,
`native_git_apply_produces_candidate: true`, and `identical_rerun_noop: true` — each candidate was
independently, mechanically re-derived byte-for-byte from its stored facts/plan, leaving no gap for
undetected hand-editing to hide in. (Also: nothing has been applied to a real upstream repo yet, so
there is no "candidate vs. committed" diff to inspect in the first place.)

## 10. Honestly agent-approved

**0** — the `AGENT_APPROVED` status (charter §8) doesn't exist as a system concept before `RPOC-070`
(lifecycle state machine, in progress) lands, and no repo can earn it before `RPOC-022` (the
reviewer) exists.

## 11. Conflicting decisions

- `plans/master.md` Wave 6 labels the 3-Java pilot "Level 5" — conflicts with the all-registry goal.
  Addressed by `RPOC-011`.
- Wave ordering runs Wave 5 (PR effects, GitHub App tokens) before Wave 6 (the pilot) — backwards
  relative to Gate A/B-before-PR-work. Addressed by `RPOC-011`.
- `--enable-dynamic-planning` still opt-in (`cli.py:198`) — conflicts with "agentic by default."
  Documented as a known gap in `RPOC-014`'s `AGENTS.md` update; the flag itself is not flipped to
  default-on in this sprint (out of this sprint's taskcard scope — flagged for a follow-up, not
  silently ignored).
- `render_readme_candidate.py:92-96` makes hand-authored policy YAML the precondition for the
  deterministic path — resolved in substance by `RPOC-033`'s design (drafted facts populate the same
  `product_truth` artifact shape, so the existing dispatch logic needs no change).
- Draft PR authorization records for the 3 Java pilots already committed (`f89da60`) — inert
  (placeholder `approving_identity`), left in place, not acted on before Gate A/B.
- `idea.md` has a real uncommitted "Production-Readiness Standard" edit — reconciled, not
  overwritten, by `RPOC-010`.

## 12. Overclaiming requirements

**Confirmed and quantified: the generated `plans/status.md` and `master.md`'s own decision #56 note
are both stale relative to live `requirements.md`.** Decision #56 (2026-07-23) cites "~170"
`PLANNED`/`BACKLOG`/`PARTIAL` rows needing a deeper semantic sweep; the live count today is
**PLANNED 108 + PARTIAL 77 + BACKLOG 26 = 211** — a 24% increase in two days as later waves logged
new rows. `status.md` (before this sprint's `RPOC-017` regeneration) was even further behind. This
sweep remains genuinely out of this sprint's scope (it's a pre-existing, separately-tracked gap, not
something the README-POC charter asks this sprint to close) — recorded here so the number is at
least accurate, not silently left at the stale "~170."

## 13. Plans/workflows prioritizing Java PR or GitHub App prematurely

Same as #11's Wave-ordering finding, plus: `plans/codex/idea-fidelity-to-level-8-autonomous-
execution-plan.md`'s own Phase 5 sequences staging before full-registry proof — its Phase 0-2
content remains useful raw material (renderer split, local verifier, `act` parity) but its
sequencing is superseded by this charter, noted in the execution plan's Part C.9.

## 14. Custom subsystems needing battle-tested comparison

Full inventory + recommendations in `full-registry-readme-poc-build-vs-adopt-audit.md` (`RPOC-002`).
Summary: orchestration, Markdown parsing, GitHub API, retry/HTTP, and state/checkpointing all
`KEEP_CURRENT` (each already a documented build-vs-adopt decision); structured LLM output
`WRAP_WITH_PROVEN_LIBRARY` for the two new job routes only (`RPOC-021`/`RPOC-033`); observability
`DEFER_REPLACEMENT` to Wave 2.

## 15. Shortest route to all-products local approval

Sketched in the execution plan (`C:\Users\prora\.claude\plans\executive-verdict-the-swirling-adleman.md`
Part B) and now sharpened by #7 above: since all 27 non-pilot repos fail validation for the *same*
reason (missing product facts), the shortest real path is exactly the plan's existing Phase 2→3→4→6
sequence — build the drafting pipeline once (`RPOC-030`-`035`), the independent reviewer once
(`RPOC-020`-`023`), the production verification wiring once (`RPOC-050`-`052`), prove it on a 4-repo
pilot (`RPOC-060`-`061`), then apply the same already-proven mechanism across the remaining repos in
batches (`RPOC-081`) — not 27 separate investigations.
