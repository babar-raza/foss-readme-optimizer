# Failure-signature ledger — Gate A portfolio, reconstructed 2026-08-18 (Phase 9)

Signatures are clustered by *mechanism*, not repo count. Sources: live
`runs/readme-poc/portfolio-summary.json` (20:04), `runs/gate-a-local-poc-portfolio-2026-08-18/`,
`runs/local-poc-state/state.git` refs, `plans/backlog-post-poc.md`, the 2026-08-16→18 session
transcript (verified line-by-line), and `plans/investigations/evidence/readme-portfolio-aspose-parity/`.

| # | Signature | Affected repos | Stage | Det./model-var. | Root cause | Next diagnostic / fix | Retry policy |
|---|---|---|---|---|---|---|---|
| S1 | `claim accountability has N blocking claim(s)` | barcode(2), email(1), font(3), note(2), slides(4), words(1–2) | presentation_plan (DETERMINISTIC_VALIDATED) | **Model-variable** counts over a **deterministic core defect** | Two-layer: (a) mechanical `_covered_by_fact_variants` demands every substantive character of a claim be substring-coverable by fact phrases — author framing ("canonical or alias", "generic") can never pass; (b) the live `claim_disposition_check` fallback can only *accept* defensible original text, never author replacement text or grant a reasoned exclusion; residual claims are `correction_candidate`s (root-caused on integration branch, commit `216fd2836` on main). Corroboration is re-rolled every pass → counts fluctuate (words 1→2, note 2→1→2). | (1) Ratchet: persist corroborated dispositions content-addressed so an accepted verdict is never re-rolled; (2) add the reasoned-exclusion / correction disposition path mirroring aspose.org's `merged_reframed`/`excluded`+reason vocabulary; canary = note-python (2 claims, 11 identical consecutive failures) | **STOP re-running until (1)+(2) land**; then canary → cohort |
| S2 | `product_truth_not_ready:BLOCKED_MISSING_EVIDENCE` — unpublished pkg + missing policy | tex | FACTS_COLLECTING | Deterministic | PyPI 404 (genuinely unpublished, Pre-Alpha) → local source-build fallback requires `product_truth.minimal_example`; `config/policies/aspose-tex-foss-python.yml` has no `product_truth:` block. Fix fully scoped in `plans/backlog-post-poc.md` (46ed34630) incl. a working in-README example. | Author the complete `ProductTruthPolicy` block with real evidence grounding against `src/aspose_tex/` (45 files) | No retry until policy block lands (zero provider calls anyway) |
| S3 | `BLOCKED_MISSING_EVIDENCE` — upstream repo defect | html | FACTS_COLLECTING | Deterministic | Upstream `pyproject.toml` declares nonexistent `build-backend = "setuptools.backends.legacy:build"`; every `pip install .` fails. **Miscategorized `agent_fixable`; genuinely `infra_external`** (no push access). | Fix category at the site that produces it (GOVERNANCE rule 13); route into Decision #101 working-condition exception lane + per-repo UPSTREAM-DEFECTS.md | Never retry on unchanged upstream revision |
| S4 | `BLOCKED_MISSING_EVIDENCE` — source repo has no content | psd (README is 2 lines) | FACTS_COLLECTING | Deterministic | Near-empty upstream README/source evidence; registry `mode: disabled` for both psd entries | Product-owner lane decision (working-condition presentation); document as external blocker | Never retry on unchanged upstream revision |
| S5 | `unauthorized protected-content loss` | slides (`technical_terminology:01e8…`), page (`protected_losses=1` via factuality_rejected) | CANDIDATE_GENERATED / DETERMINISTIC_VALIDATED | Deterministic trigger, model-influenced content | Untriaged; distinct from every 2026-08-18 fix. Integration's `api_method_index` slot closed the *api-reference* protected-loss class; `technical_terminology` is a different protection class. | Reproduce on slides canary, inspect the protected-region inventory for that hash, determine which slot should carry the term | STOP until triaged |
| S6 | Throughput: 22/33 entries never reached in a slice | all non-Python + tex/words | portfolio loop | Deterministic | Known-BLOCKED repos re-execute fully every pass (no blocked-decision cache; only COMPLETE bundles short-circuit), burning the 1200s slice + provider calls (note 4, slides 7 per pass) on already-triaged failures | **Blocked-decision skip cache** keyed to the same dependency fingerprints as `local_poc_cache.py`, so a block is retried only after a semantically relevant change | n/a (this is the retry-policy enforcement mechanism) |
| S7 | `UNKNOWN_LEGACY` portfolio accounting with EXACT per-repo counts | summary line only | reporting | Deterministic | Aggregator downgrades to UNKNOWN_LEGACY instead of summing per-repo EXACT counts | Fix aggregation to sum EXACT rows; UNKNOWN_LEGACY only when a row is genuinely legacy | n/a |
| S8 | Masked test failures: `N failed … [exited with code 0]` | test/orchestration commands | process | Deterministic | pytest piped through wrappers without pipefail/PIPESTATUS capture; systemic (8+ occurrences in transcript) | Use `scripts/governance/run_full_pytest.py` exclusively; audit remaining piped invocations | n/a |
| S9 | Evidence loss: reused iteration names / driver LOG_DIR | `runs/gate-a-local-poc-portfolio-2026-08-18/iteration-00N.log` overwritten by resume | process | Deterministic | LOG_DIR fixed per date; restart resets counter to 001 (first run's logs 001–003 gone; confirmed from transcript) | Unique run-id subdir per driver invocation | n/a |
| S10 | 14 registry entries pre-intake (no state ref) | 3d-java/ts, cells-cpp/go/java/net/rust/ts, email-cpp/net, pdf-go/java/net, psd-net, words-net | intake | Deterministic | Never reached: slice budget exhausted by S6; psd-net additionally `mode: disabled` + missing ecosystem/policy_profile (`readonly_intake:BLOCKED_CLASSIFICATION` per L8-PORT-01 audit) | Unblocked automatically once S6 lands; psd-net needs registry data fix | Normal processing after S6 |

Quality-gap signatures (Decision #104 diagnostics — not blocking, but the actual mission bar):

| # | Signature | Evidence | Root-cause hypothesis |
|---|---|---|---|
| Q1 | Thin Key Capabilities (4/4 reviewed repos) | `candidate-quality-gap-list.md` | The S1 coverage rule selects the *shortest claim that passes*, not the most informative — Q1 and S1 are one defect seen from two ends |
| Q2 | API Reference 56 vs 130 public types (cells) | same | Unconfirmed: extraction depth (`detect_api_public_surface`) vs stricter public-surface definition; check real `__all__` before assuming |
| Q3 | Missing real capability (FormulaEvaluator, cells) | same | Capability selection never surfaced it — needs capability-inventory parity check against aspose.org candidate |
| Q4 | Missing testing guidance / redundant badge / missing contributor link | same | Template/composition gaps, triaged minor |

Engineering queue (priority order, one variable per experiment):

1. **E1 — blocked-decision skip cache** (S6; enables everything else to run cheaply). No LLM.
2. **E2 — claim-disposition ratchet** (S1 variance): persist corroborated verdicts keyed by
   (claim id, claim text hash, candidate hash, prompt hash, model); reuse deterministically.
3. **E3 — blocked-category corrections** (S3): site-specific `infra_external` for upstream defects.
4. **E4 — tex product_truth policy block** (S2; fully scoped content task).
5. **E5 — reasoned-exclusion/correction disposition path** (S1 core; canary note-python).
6. **E6 — slides/page protected-content triage** (S5).
7. **E7 — probes**: max-output ladder, forced-named-tool shape, temp-0 determinism diff
   (gaps 1/3/7 from the probe-coverage audit).
8. **E8 — accounting + process fixes** (S7, S9).
9. **E9 — quality parity work** (Q1–Q3) after unblocking, driven by Decision #104 reviews.

## 2026-08-18 probe addendum (qwen-output-limits evidence, plans/investigations/evidence/llm-probe/)

- **Forced-named-tool transport shape: PROVEN** — 5/5 trials returned exactly one
  correctly-named call with schema-valid nested arguments (closes probe gap 1).
- **Structured output size: exact through ~7,000 completion tokens** (200-item JSON array,
  finish=stop); breaks only at the 8,000 max_tokens cap (400 items, finish=length). The
  codebase's 8000-token jobs run near the proven edge (closes gap 3).
- **Temperature-zero determinism: freeform prose IS byte-deterministic (5/5 identical);
  forced-tool ARGUMENTS ARE NOT (5 distinct payloads in 5 trials).** This is the mechanism
  behind every observed claim-count fluctuation (S1's model-variance) and the formal
  justification for the ratchet (E2): re-asking an unchanged question is a dice roll on this
  gateway; only persisted, deterministically re-corroborated acceptances converge (closes gap 7
  with a negative result that changes design assumptions — any cache key that assumes tool-call
  reproducibility at temp 0 is unsound).

## 2026-08-18 parity-tool addendum (compare_candidate_parity.py; parity-*.json in this directory)

First three-way numeric parity for the approved repos (original vs aspose.org candidate vs ours):

| repo | original terms kept (ours) | kept (aspose.org) | capability bullets (ours/aspose) |
|---|---|---|---|
| pdf-python | **22/24** | 15/24 | **14/12** |
| 3d-python | **174/234** | 72/234 | 4/8 |
| cells-python | 31/159 | 159/159* | 7/12 |

*cells' "original" IS aspose.org's previously-published refresh (identical profile: 2,558 words,
159 spans) — so aspose.org's 159/159 is trivial, and OUR 31/159 means we heavily recompose a
README that was already at the reference bar. **New systemic finding: when the upstream README
is already the aspose.org-refreshed output, wholesale recomposition is the wrong lane —
preservation/minimal-delta should dominate.** (This also reframes several claim-accountability
blocks: the "source claims" being dropped are aspose.org's own generated claims.)

Universal one-character contract divergence: all three of our candidates render
`## Documentation and Resources`; aspose.org's required-section contract says
`## Documentation & Resources`. Queue the template fix for AFTER the current portfolio pass
(a template edit mid-pass would rotate fingerprints between iterations); it is a
VALID_UPDATE_AVAILABLE-class improvement under Decision #90, not a forced recomposition.

pdf-python is the working proof that the pipeline can meet/beat the reference bar; 3d shows the
preservation machinery outperforming aspose.org's own reframing; the capability-bullet deficit
(Q1) is now numerically tracked per repo.

## 2026-08-18 iteration-1 addendum (post-fix portfolio pass, runs/gate-a-local-poc-portfolio/)

- **E2 portfolio-proven**: note's ratchet replayed both accepted verdicts live
  (`cache_reuse=2`, provider_calls 4→2, blocking count rock-stable at 1 across canary and
  portfolio passes — the historical 2→1→2 fluctuation is gone).
- **Cross-repo boilerplate claims**: page's blocking claim has the SAME content hash
  (`7ff54c1da64deecb`) as the claim note's ratchet already accepted — identical claim text
  recurs across repos (dependency-boilerplate class). Enhancement queued: a portfolio-level
  shared ratchet keyed by claim-content hash (safe by construction — replay still
  re-corroborates against each repo's own candidate/source before acceptance).
- 6 blocked-decision records banked in iteration 1; iteration 2 is the E1 skip demonstration.

## 2026-08-18 fleet-parity addendum (7-repo table; parity-*.json)

| repo | terms kept (ours) | terms kept (aspose) | capability bullets (ours/aspose) |
|---|---|---|---|
| pdf | 22/24 | 15/24 | 14/12 |
| 3d | 174/234 | 72/234 | 4/8 |
| note | 76/238 | 234/238 | 8/7 |
| font | 108/258 | 258/258 | 3/9 |
| barcode | 32/81 | 81/81 | 6/7 |
| email | 27/192 | 192/192 | 5/7 |
| cells | 31/159 | 159/159 | 7/12 |

**Headline systemic finding:** kept_aspose ≈ 100% for note/font/barcode/email/cells means those
repos' "original" upstream READMEs already ARE aspose.org's previously published refreshes (the
aspose.org action ledger records e.g. note-python PR #5). For the majority of the Python
cohort, our pipeline recomposes already-at-bar content and drops 60–85% of its terminology —
the single largest quality divergence, and it reframes most S1 claim-accountability blocks as
"we dropped aspose.org's own generated claims". Consequence: the E5 spec's
preserve/minimal-delta lane for aspose-refreshed sources (design §6) is the MAIN lane for the
Python cohort, not an edge case — implement its detection (profile identity / near-identity
with the reference candidate) early. Secondary: our blocked candidates for barcode/email/
font/note render no `## Dependencies` section while aspose.org's do — check why the 1.20 slot
stays empty there; and the universal `Documentation & Resources` ampersand divergence repeats
in all 7.

## S11 (new, iteration-3 discovery): non-Python family reached — first .NET evidence

3D-.NET (member 14, first .NET-family member processed in any recorded slice this session)
blocked on 14 claim-accountability claims (S1-class, distinct claim ids — no cross-family
sharing with the Python cohort observed) PLUS a new deterministic presentation-lint finding:
`presentation.capability_description_repeats_title` — a real, legitimate prose-quality gate
(`readme/presentation_lint_public_contract.py:118-129`, `semantically_repeats(title,
first_sentence, threshold=0.9)`) catching a Key-Capabilities row whose explanation just restates
its own title. Not a defect: this is exactly the kind of deterministic quality gate the mission
wants MORE of, not less. Cells-.NET (member 15) is mid-verification with a longer wall-clock
than any Python member this session — consistent with a real dotnet build/restore in the
isolated verifier, not a hang; confirmed via live process check, not assumed.

This is the first evidence that the S1/E5 claim-accountability closure work generalizes across
families: 3D-.NET's 14 claims are a DIFFERENT set from the Python cohort's, so Lane A/B/C fixes
will need per-family validation once Python closes, not a single global "done".

## 2026-08-18 cross-family ratchet confirmation (iteration 3, mid-flight)

E2's ratchet mechanism, previously proven only on the Python cohort, is now confirmed working
identically on .NET: `aspose-3d-foss__Aspose.3D-FOSS-for-.NET` has 5 accepted verdicts,
`aspose-cells-foss__Aspose.Cells-FOSS-for-.NET` has 20 — cells-.NET's real-time member
processing (a genuinely long isolated .NET build/verify, confirmed alive via rising CPU, not
stalled) is running well past the claim-accountability stage the earlier-blocked 3D-.NET member
stopped at. No family-specific code path was needed; the mechanism generalized for free.

## E3 fix live-confirmed (iteration 3): aspose-email-foss/.Net

`aspose-email-foss/Aspose.Email-FOSS-for-.Net: BLOCKED (product_truth_not_ready:
BLOCKED_MISSING_EVIDENCE; category=infra_external)` — a genuinely fresh derivation (zero
provider calls, `executed` not `deduplicated` intake) correctly classified `infra_external`.
Confirms `17f8cc595` works exactly as designed once findings are freshly computed; the
html/psd/tex `agent_fixable` staleness documented in `e3-residual-empty-findings-bug.md` is
specifically a cache/empty-findings issue, not a defect in the classification logic itself.

## Expected post-merge invalidation (2026-08-18): 3 approved repos need re-verification

Mission status after merging graph-loader/E5/lane-ab-fixes shows
`stale_acceptance_repositories: aspose-3d-foss, aspose-cells-foss, aspose-pdf-foss` (the three
NO_OP_PROVEN repos from the pre-merge pass). This is the exact, disclosed footprint the Lane A/B
prepared-change specs predicted: `template_version` 1.20.0->1.21.0 (heading fix) and the
Documentation/API-Method-Index rendering changes rotate `document_template_hash()` /
`candidate_stage_dependency_key`, so Decision #90's component-versioned invalidation correctly
marks their prior candidates stale. Facts are unaffected (`facts_ready` held/advanced). Cheap to
clear: the next portfolio pass re-verifies these three with the new template, no re-collection
of facts needed. Confirms the fingerprinting mechanism itself is working precisely as designed
under a genuine, deliberate runtime change — not a bug.

Mission narrowing recorded (`--mission-action record-narrowing`, state_version 4) citing this
ledger + the slides/S1-residue/E5-correction evidence, satisfying Decision #97's 15-minute
material-narrowing requirement that fired during post-merge canary verification.

## Final boundary full-suite result (2026-08-18, post all merges + characterization fixes)

`4021 passed, 1 failed` (down from the session's starting 5-10 documented baseline failures).
The one remaining failure is the pre-existing `test_current_note_feature_and_api_deferrals_have_
accepted_fact_ids` stale-fixture data drift (gitignored `runs/baseline` Note README no longer
matches its pinned hash — documented earlier this session, unrelated to any change here).
`run_full_pytest.py`'s leaked-process detector flagged PIDs 13160/70256; verified these are the
concurrently-launched page-verification canary's own live supervise process (started at the
exact same timestamp), not leaked pytest workers — a false positive from running gates and
canaries in parallel, not a real leak. `tree_changed_during_run: true` with identical start/end
tree fingerprints is the same concurrent-canary artifact (gitignored `runs/` writes, no
git-tracked source drift).

## S12 (new, 2026-08-19 portfolio pass): `composition.segment.NNNN: substantive generated bytes
lack exact candidate authority`

Observed live for cells-python (`presentation_plan:blocked:['composition.segment.0032: ...',
'composition.segment.0034: ...', 'composition.segment.0036: ...', 'claim accountability has 1
blocking claim(s): ...']`) and page-python (segments `0030`/`0033`, then `0035`/`0039`/`0044` on
a later iteration) in the fresh 2026-08-19 portfolio re-verification pass (post Lane A–E). Not
present anywhere in S1–S11 or the 2026-08-18 sweep. **Notable**: cells-python had already
reached `AGENT_APPROVED` once (2026-08-18, per `candidate-quality-gap-list.md`) — this pass
shows it newly BLOCKED, raising a real possibility that Lane A–E's composer/template changes
introduced this regression rather than merely re-surfacing a pre-existing gap; not confirmed
either way.

**Mechanism traced (not guessed)**: `readme/composition_lineage.py` (last modified `0cbf7b1f3`,
2026-08-17 — predates today's Lane A–E work, so the *validator* itself is not what changed)
classifies every non-source-preserved candidate segment's `authority`. When a segment has no
`fact_ids`/`standard_ids` reachable from `candidate_provenance` bindings covering its byte range
AND `_is_governed_mechanical_structure(text)` is false, `authority = "unbound"` —
`composition_lineage_validation.py`'s `composition_ledger_errors()` then hard-fails any
`"unbound"` segment. So S12 is not a validator bug: it is real, freshly-composed prose (or
structural bytes) whose provenance never got threaded through to `candidate_provenance` at
composition time. Multiple segment IDs firing together across two repos suggests a shared,
newly-introduced (or newly-exposed) composed slot lacking provenance wiring — a hypothesis, not
yet confirmed which slot.

**Reproduction attempted, honestly incomplete**: tried to reconstruct the exact failing
`ReadmeCompositionLedgerV1` offline via `build_readme_document_candidate()` against cells-
python's real cached facts + a cached `agentic-composition-plan.json`
(`runs/readme-poc/.../26c3bd1633e84b91.../superseded/6a81aad191328bbf/`) — the only persisted
plan for this revision. `validate_readme_composition_plan()` initially rejected it
(`facts_hash`/`assessment_hash`/`input_sha256` mismatch) until re-paired with its own sibling
facts bundle under the same `superseded/` directory (mixing the top-level facts with the
superseded plan is what caused the mismatch). Once paired consistently, it DID build — but
segments `0032`/`0034`/`0036` came back `authority="presentation_policy_correction"` (whitespace
content, `'\n'`/`'\n\n'`), not `"unbound"` — this superseded plan is from a different (earlier)
LLM composition attempt than the one that actually produced today's live blocked result, so it
does not reproduce the real failure; segment IDs are not stable across different agentic plans
for the same repo. No live-matching plan was found cached anywhere accessible offline. Next
diagnostic: either (a) let the current portfolio pass reach cells/page-python again fresh and
immediately snapshot the resulting bundle before anything supersedes it, or (b) run a bounded
single-repo canary deliberately (consumes real provider calls) and inspect the ledger from that
exact run. Do not attempt a fix without a genuine, live-matching repro — this session's own
"disposition IS the render" lesson and the earlier `_richer_fact_bound_source_capability` bug
both turned out to have non-obvious root causes that static reading alone got wrong twice before
empirical verification corrected them; the same discipline applies here.

**Follow-up (same investigation, minutes later)**: caught the portfolio pass re-processing
cells-python live (iteration 3; the log line lacked the `(cached, not re-executed...)` prefix
other members carry, and `readme_presentation` was reported as having "failed 3 consecutive
runs" — confirming this is a stable, structurally-reproducible block, not LLM-variance noise)
and tried to capture its exact plan before anything could supersede it — found that a BLOCKED
attempt never persists `planning/agentic-composition-plan.json` to disk at all (only an
already-*promoted*/accepted bundle does, confirmed by directory structure: `planning/` exists
only under the one `AGENT_APPROVED` revision's own subtree, never under a currently-blocked
one). Only `diagnostics/blocked-candidate.md`/`blocked-presentation-plan.json` are written, and
neither carries the raw plan. **This is itself a real, disclosed gap for next time**: there is
currently no way to inspect a blocked attempt's exact composition ledger after the fact without
either modifying the pipeline to persist it on block too, or live-monkeypatching during a
canary run (the T5 investigation's own precedent technique). One suggestive data point from the
offline (non-matching) repro: its equivalent segment slots 0032/0034/0036 were pure whitespace
separators (`'\n'`/`'\n\n'`), not prose — raising a hypothesis, unconfirmed, that the live
"unbound" segments may also be trivial inter-section whitespace rather than substantive dropped
prose, which would point at `_is_governed_mechanical_structure(text)` having a gap for certain
separator patterns rather than a real content-provenance loss. Not verified; flagged for
whoever picks this up next to check first, before assuming richer prose is involved.

**Persistence gap closed (2026-08-19)**: `_persist_blocked_plan_diagnostics`
(`specialists/readme_presentation.py`) read `claim_accountability`/`source_claim_resolutions`/
`candidate_sha256` from `presentation_plan_record["presentation_plan"]`
(`RepositoryPresentationPlanV1.model_dump()`) — that model has no such fields (only
`org_repo`/`immutable_base_revision`/`facts_hash`/`source_sha256`/`archetype`/`findings`/
`actions`/`candidate_sha256`), so the first two always persisted `null`, a real pre-existing bug
independent of S12. The correct source is the sibling top-level key
`presentation_plan_record["readme_document_plan"]` (`ReadmeDocumentPlanV1.model_dump()`, built by
`build_document_repository_presentation_plan()`/`capabilities/build_presentation_plan.py`), which
carries all three correctly *and* the full `composition_ledger` (every segment's exact
`content_text`/`authority`/byte range) — closing the "no way to inspect a blocked attempt's
composition ledger" gap above without any new computation, model, or pipeline change: the ledger
was already built and present in memory at this call site, just never read. Fixed by switching
the extraction source and adding `composition_ledger` to the persisted payload; regression test
`test_blocked_plan_diagnostics_write_claims_and_candidate` updated to assert against the real
`readme_document_plan` nesting (previously asserted against the buggy `presentation_plan` shape,
which is why the bug went unnoticed). Focused suite green (6/6), ruff/mypy clean.

**Live verification attempted, structurally deferred**: a `--bounded-verified-canary` rerun for
cells-python did not exercise the new code — the pipeline's own no-unnecessary-work convergence
(VER-003) reused the prior terminal outcome unchanged (recorded ~06:18Z, ~90 min before the
rerun; empty command output confirms no fresh work), since none of the tracked dependency
fingerprints changed and a diagnostics-only edit isn't one of them (correctly — it doesn't affect
candidate identity). `--retry-blocked` is portfolio-only, not available to a single-repo canary,
so a bounded `--registry data/products.json --retry-blocked --portfolio-time-budget-seconds 1200`
pass was started instead to force fresh re-verification of the whole currently-blocked cohort
(S1/S5/S12 members alike) under real dependency-unchanged conditions — deliberately justified by
a real code change, not a blind re-run.

**S12 ROOT-CAUSED AND FIXED (2026-08-19)**: the bounded retry-blocked pass produced real, fresh
`composition_ledger` evidence (diagnostics files jumped ~13KB -> ~487KB, confirming the fix
above works). Segments 0032/0034/0036 (cells-python) and their barcode-python equivalents
(0033/0035) are **not whitespace** — refuting the prior offline-repro hypothesis. Their exact
`content_text`:

```
'\n\n### Required Package Dependencies\n\n'
'\n### Optional Dependencies\n\nInstall optional dependencies by scenario:\n\n'
'\n### Development Dependencies\n\n'
```

These are the literal H3 sub-heading strings `development_dependency_markdown()`/
`verified_template_draft.py` render unconditionally under `## Dependencies` — confirmed present
in the real rendered candidate at `## Dependencies` -> `### Required Package Dependencies` ->
`### Optional Dependencies` -> `### Development Dependencies`. **This is a real regression from
today's own earlier Lane A part B / Lane F work**: those lanes added three new template-mandated
Dependencies H3 headings but never added them to `composition_lineage.py`'s
`_GOVERNED_STRUCTURAL_LINES` — the exact set `"### Tests"` is already in, for the identical
reason (a template-shell heading with no fact/standard binding of its own). The parent `##
Dependencies` H2 heading was unaffected (already bound via a separate mechanism, standard_id
`readme.composition.mechanical-markdown-v1`, confirmed in the same evidence) — only the three
child H3 headings were missing.

Fixed: added `"### Required Package Dependencies"`, `"### Optional Dependencies"`,
`"### Development Dependencies"` to `_GOVERNED_STRUCTURAL_LINES`. Regression test
`test_dependencies_subsection_headings_are_governed_mechanical_structure`
(`tests/unit/test_composition_lineage_replay.py`) added and confirmed to fail without the fix
(reproduces the exact `composition.segment.NNNN: substantive generated bytes lack exact
candidate authority` error) and pass with it. Full composition-lineage + diagnostics suites green
(27/27). Full governed suite: 5 failed / 4084 passed — all 5 are the already-documented
pre-existing baseline (`plans/backlog-post-poc.md`, GOV-014: 3 Java plan-hash characterization
drifts, 1 agentic-composition-plan characterization drift, 1 note-python stale-fixture drift) —
zero new regressions. ruff/mypy clean on all changed files.

**Next**: this fix should unblock cells-python and page-python (S12's only two directly-named
repos) and likely also barcode-python (confirmed same signature live) — any other currently-S1-
blocked repo whose *only* remaining block was this exact composition-authority gap would also
clear. A fresh portfolio/canary pass is needed to confirm actual promotion to
`DETERMINISTIC_VALIDATED`/beyond; S1 (claim accountability) remains a separate, still-open
signature for repos that fail there independently of S12.

**Follow-up lead, not yet confirmed (2026-08-19)**: a static sweep of every literal `"## "`/`"### "`
heading string in `src/readme_agent/presentation/` and `src/readme_agent/readme/` for the same bug
class (bare template-shell heading, no accompanying fact/standard provenance, not registered in
`composition_lineage.py::_GOVERNED_STRUCTURAL_LINES`) found three more candidates:
`### Golden Workflow` (`verified_template_golden_workflow.py`), `### Example results` and
`### Repository example files` (both `verified_template_sections.py`). Unlike the Dependencies
headings, none of these have appeared as an `unbound` segment in any live evidence captured so far
(cells-python, barcode-python, page-python) — either no current Python repo's real facts trigger
these code paths, or they already receive real provenance through a mechanism not yet traced.
**Do not fix speculatively** — same discipline as S12 itself: needs a genuine live repro (a repo
whose facts include golden-workflow/example-asset evidence) before touching anything. Worth a
five-minute check the next time a repo's facts are known to include that evidence.

**S12 fix was incomplete — corrected same day, live-caught by the second retry-blocked pass**:
the first fix (three bare H3 heading strings) reduced cells-python's unbound segments 3->1
(0032/0036 gone, 0034 remained) — proof it was real and directional, but not sufficient, caught
immediately by rerunning rather than declaring victory on the first partial improvement. Fresh
evidence from font-python and note-python made the remaining gap unambiguous: `### Optional
Dependencies` and `### Required Package Dependencies` are each followed, in the same contiguous
unbound byte range, by a fixed, non-fact-derived lead-in/verified-empty sentence
(`verified_template_sections.py`): `"Install optional dependencies by scenario:"` (always,
`scenario_dependency_markdown()`) and `"No required third-party package dependencies."`
(verified-empty case, `dependency_markdown()`). Both registered in `_GOVERNED_STRUCTURAL_LINES`
alongside the sibling verified-empty sentence for Development Dependencies (`"No development
dependencies declared in \`pyproject.toml\`."`, `development_dependency_markdown()`) — the
identical pattern in the identical function family, not yet observed live but essentially certain
to recur the first time a Python repo declares zero dev dependencies, so fixed proactively rather
than waited on. Regression test strengthened to the exact real segment shape (heading + lead-in
sentence together, not heading alone) — confirmed it now fails on the heading-only version of the
fix and passes on the complete one. Full composition-lineage + diagnostics suite: 27/27. ruff/mypy
clean.

**Lesson**: a partial live improvement (3->1) is evidence the mechanism is right, not evidence the
fix is complete — the discipline that caught this was rerunning immediately against fresh live
data rather than trusting the first green regression test in isolation.

## Two-gate factuality wiring (2026-08-19): implemented, unit-verified, live-verification pending

S12's fix cleared cells-python and font-python past presentation-plan validation, surfacing gate 2
(`evaluate_candidate_factuality`, `readme_factuality.py`) as the next real blocker for barcode/
cells-python — traced precisely to the pre-existing `architectural-finding-two-gate-claim-
accountability.md` finding: gate 2 never received the `llm_disposition_client`/`repository_root`/
`disposition_ratchet_path` gate 1 already resolves, so it could never replay an accepted
`excluded_with_reason` disposition. Fixed (`fix(factuality)`, commit `b32d4998c`): a new shared
`resolve_claim_disposition_context(org_repo)` helper, wired into both real callers. Unit-verified
(wiring reaches the rebuild; defaults to None when omitted; fails closed for an unlisted repo);
174 tests across all four changed modules pass. **Not yet live-verified** — a bounded
`--retry-blocked` pass is running to confirm it actually closes barcode/cells-python's remaining
block rather than surfacing a further signature.

## font-python's two remaining S1 claims: precise evidence gathered, real fix needs new extraction

Re-confirmed live (2026-08-19, same content-hashes as the 2026-08-18 diagnosis) and now traced to
exact real source text and facts, closing the gap between "diagnosed" and "ready to implement":

- **`source:claim:2544:3523960e3ec2b571`**: `"...magic-byte detection picks the format
  automatically unless you pass \`font_type\` explicitly."` — `font_type` is a real parameter of
  `FontLoader.open`/`FontLoader.load` (confirmed: `api.public_surface.classes[FontLoader].members`
  gives `surface: "open(source, font_type=None, collection_index) -> Font"`), but no existing
  matcher recognizes a bare backtick identifier as a valid reference merely because it names a
  parameter of an already-cited method in the same claim — only whole callables/classes/imports
  are matched today. **The real fix needs signature-string parsing** (extract parameter names from
  the `surface` string, match a bare backtick token against them, gated to only fire when the
  owning method is *also* cited and resolved in the same claim to avoid matching a coincidental
  common word) — meaningfully more design than a registration-style fix, not attempted here.
- **`source:claim:6367:f76ee53ac612c3f9`**: `"...vendored, pure-Python codec
  (\`aspose_font._brotli\`), not an external C library..."` — confirmed `aspose_font._brotli` is a
  **real** private submodule (`src/aspose_font/_brotli/` genuinely exists in the cloned source).
  The existing import-statement matcher (Lane F) validates against `api.public_surface.modules`,
  which — unconfirmed but likely, given Python convention — only lists *public* modules, so a
  private (`_`-prefixed) submodule may not be checkable through that path at all. **Needs
  confirming whether private modules are captured anywhere in the facts schema** before any fix is
  designed; if not, this needs new extraction, not a new matcher.

Both are genuinely "different, unscoped mechanisms" per the 2026-08-18 diagnosis, confirmed by
this deeper trace rather than superseded by it — ready for a dedicated pass with this evidence in
hand, not attempted here to avoid an unverified guess at the extraction-layer question.

## Disposition-context wiring gap: found in 5 places total, 4 fixed, 1 left as a documented lead

A full-codebase audit for every caller of `build_readme_document_candidate()` (prompted by gate 3
turning out to be a live recurrence of the exact gate-2 bug) found **five** independent-rebuild
call sites, not two:

1. `presentation/document_planner.py` (gate 1) — already correctly wired, the reference shape.
2. `specialists/readme_factuality.py` (gate 2) — fixed, `b32d4998c`.
3. `verification/checks.py` (gate 3) — fixed, `5acf011b3`.
4. `readme/idea_candidate.py` (`prepare_idea_fidelity_candidate`, `readme-agent poc`'s compose
   step and `capabilities/render_readme_candidate.py`'s real-generation path) — fixed, `e33e631ed`.
   Same easy shape as gate 3 (`entry` already resolved via `require_listed()` before the call);
   not covered by a new dedicated test (no existing fixture cheap to extend — this function does
   real git clone/push-neuter/hook work), verified by inspection against the 3x-proven pattern and
   142 existing tests across its callers continuing to pass unchanged.
5. `verification/readme_proposal_bundle.py::verify_readme_proposal_bundle()` — **not fixed**.
   The "author != verifier" bundle-proof verifier for `L8-LOCAL-README-PROPOSAL-PROOF`/`VER-001`;
   its docstring literally describes doing the identical independent-rebuild-and-compare gates 2/3
   did. Harder shape than the other four: `org_repo` isn't a function parameter here (the function
   takes only a `bundle_dir: Path` and reads `org_repo` from the bundle's own plan/manifest partway
   through), so there is no already-resolved `entry`/`require_listed()` call to piggyback on --
   fixing it means resolving the disposition context fresh at whatever point `org_repo` first
   becomes known, the same shape gates 2's `readme_presentation.py`/`readme_review_repair.py` call
   sites needed (defensive fallback on failure, not an unconditional resolve). Not yet observed
   failing live in this session's evidence (unlike gates 2/3, which came from real production
   failures) -- left as a precisely-scoped, ready-to-implement lead rather than an unverified guess
   at a path with no direct failure evidence behind it.

## Two/three-gate fix LIVE-CONFIRMED: barcode-python reaches AGENT_APPROVED (2026-08-19)

One intervening pass showed `baseline_clone_failed`/`readonly_intake:BLOCKED_ACCESS` for
barcode/cells-python instead of a claim-accountability result -- verified transient before
concluding anything: `git ls-remote` against barcode-python's real remote succeeded identically
with and without the documented `GH_TOKEN` recipe, ruling out a credential regression; most likely
GitHub-side rate limiting after five consecutive `--retry-blocked` passes in under an hour. Waited,
reran once clean.

**Result**: barcode-python — `AGENT_APPROVED`. Full chain confirmed live: S12 (composition
authority) → gate 2 (factuality) → gate 3 (independent verification) → agent review, all cleared
with the real, ratcheted `excluded_with_reason` disposition for `source:claim:3930:
c5ac180c4dd86b4f` finally reaching every gate that needed it. 3D-Python is re-proving through the
same lifecycle stages after the shared verification-contract change (expected, not a regression --
Decision #90's component-versioned invalidation). cells-python was not reached in this pass's time
budget (still `CANDIDATE_GENERATED`, its last confirmed state before the retry cycle) -- a future
pass should confirm the same fix chain reaches it, since it shares barcode's exact signature
history (S12 confirmed cleared, `factuality_rejected`/`verification_rejected` confirmed cleared for
barcode specifically).

## Terminal confirmation: 3/33 NO_OP_PROVEN (2026-08-19) -- 3D, barcode, cells-Python

A follow-up pass confirmed cells-python advancing all the way to `NO_OP_PROVEN` (same as
barcode-python already had). Official mission numerator: `candidate_generated=3,
deterministic_validated=3, agent_approved=3, no_op_proven=3` -- an exact, clean set with no
partial/stuck-in-between member. Up from 1/33 no-op-proven at session start.

## Shared-ratchet backfill fix (`56a5f09c8`) confirmed working; surfaces a distinct, deeper gap

The shared ratchet now genuinely contains the backfilled entry for claim-content
`7ff54c1da64deecb...` (confirmed by direct inspection post-pass) -- the fix works exactly as
designed. It did **not**, however, close note-python's or page-python's blocking claims for this
content, which remained blocking both before and after. Traced precisely (page-python's fresh
diagnostics): the block is not one claim but **two separate claim records sharing the same
content hash**:

- `source:claim:...:7ff54c1da64deecb` (`expected_disposition: unjustified_loss`, `stage: source`)
  -- the original text disappearing from the candidate. This is what the disposition ratchet
  resolves, and does resolve (confirmed accepted, `redundant_with_candidate`).
- `candidate:claim:...:7ff54c1da64deecb` (`expected_disposition: unbound_generated`,
  `stage: candidate`, `origin: generated`) -- the byte-identical replacement text the composer
  rendered, tracked as a *separate* claim needing its own fact binding.

Both claim records carry `equivalent_candidate_claims`/`equivalence_group_id` fields, currently
empty/null on both -- these look like exactly the intended linkage mechanism ("a source claim
resolved via disposition should transitively justify its byte-identical candidate claim"), present
in the schema but not populated by anything in the current disposition-resolution path. **Not
fixed here** -- this is a distinct, deeper design question (should disposition acceptance
propagate through byte-identical content across the source/candidate claim split, and if so where
does that linkage get established) that deserves its own scoped investigation rather than a guess
grafted onto the ratchet fix that already did its own job correctly. Confirmed not a regression
from the ratchet fix: this exact two-claim block pattern (`candidate:claim:4579`/`source:claim:4064`
for note-python) pre-dates it.
