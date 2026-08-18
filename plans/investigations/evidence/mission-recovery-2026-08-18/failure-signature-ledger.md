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
