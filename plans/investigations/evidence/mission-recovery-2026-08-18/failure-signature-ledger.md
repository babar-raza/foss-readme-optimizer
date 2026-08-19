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
