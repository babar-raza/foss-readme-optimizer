# Implementation-ready repair sequence: K3 (post-render knowledge accountability) + C1 (accepted knowledge changes useful bytes)

Pin: `aa998102191c530af4dca3a6895d62a4027a613e`. Design-only; no code in this pass. Uses only existing
plan/render/provenance machinery -- no new pipeline, no product/platform branches.

## Confirmed current state (evidence: causal-module-tracer subagent + direct reads, this task)

- `facts/knowledge_application_evidence.py::build_knowledge_application_report` (L103-183) is
  **already document_plan-aware** (`document_plan: ReadmeDocumentPlanV1 | None = None`) but scans
  only `document_plan.operations[*].fact_ids` (L144-160) -- never
  `document_plan.candidate_content_provenance` (defined `readme/document_plan.py:125-152`, field at
  `:264`).
- Its **only production call site** is `supervisor/product_truth.py:473-481`, which never passes
  `document_plan=` (always `None`), and runs before any document is rendered. A full-`src/` grep
  found no second call site anywhere -- the module's own docstring (L25-33) promises one in
  `readme/idea_candidate.py` that does not exist. Confirmed live: today's (2026-08-20) fresh
  `knowledge-application.json` for 3D/Note/Barcode all show `sections_influenced: []`,
  `rendered_output_spans: []`.
- `readme/idea_candidate.py::prepare_idea_fidelity_candidate` (L33-155) is the real, existing,
  already-wired function that has `document_plan`, `facts`, `claim_map`, `org_repo`,
  `snapshot.source_revision`, and `final_text` all in scope together (L101-124), called from
  `commands_poc.py:333` and `capabilities/render_readme_candidate.py` -- i.e. it IS the local_poc
  candidate-building entry point, and it is the exact file the existing docstring already names.
- `supervisor/local_poc_evidence.py` already has the idiom to copy: `write_local_poc_readme_candidate`
  (L377+) calls two "best-effort, never block persistence" builders --
  `_readme_reconciliation_report_or_error` (L327-344) and `_check_coverage_report_or_error`
  (L352-374) -- each degrading to `{"schema_version": 1, "error": str(exc)}` on failure rather than
  raising, with the actual **blocking** decision applied later, at
  `local_poc_cache.py::_evaluate_local_poc_cache` (def L291) -> `validate_acceptance_artifact_chain`
  (`local_poc_acceptance_binding.py:74-188`, already takes `readme_reconciliation`/`check_coverage`
  params wired at `local_poc_cache.py:395-414`). This is the exact hook shape K3's gate reuses.
- `claim_map.py::build_readme_claim_map` already rejects any operation or provenance entry citing an
  unverified/conflicted fact (L100-107 operations, L167-174 `candidate_content_provenance`) -- sound
  machinery, reused as-is.
- 5 of 6 imported-claim fields (`feature_claims`/`format_support_claims`/`install_claims`/
  `limitation_claims`/`troubleshoot_claims`) have zero consumers anywhere (render_views.py,
  verified_template_capabilities.py, every `document_*.py` editorial module) -- see
  `MISSING_CONSUMER_MATRIX.json`. `relevant_seo_keywords` is the one already-shipped consumer
  (KNOW-013, attribution-only by design).
- **Sequencing hazard, live-confirmed this task**: today's live 3D dispositions show 2
  format_support / 2 limitation / 1 feature claim that are individually `verified`/`corroborated`
  but excluded from today's 8-item selection purely by `exceeds_selection_cap` -- among them
  `CLM-3d-2d3c40`/`CLM-3d-4ae50d`, independently confirmed by the 2026-08-20
  readme-knowledge-lineage-audit (KGAP-002) to be false positives (cited methods raise
  `NotImplementedError`). `_file_evidence_corroboration` only checks file existence, never content
  polarity. **C1 must not ship a format_support/feature consumer that trusts `verification_state`
  alone without either K1 landing first or an equivalent narrow polarity check inline** (see C1-2).

---

## K3 -- Post-render knowledge accountability

### K3-1: Extend the report schema for exact per-item disposition (schema v3)

**File:** `src/readme_agent/facts/knowledge_application_evidence.py`

- Bump `KnowledgeApplicationV1.schema_version` to `3`.
- Add `status: Literal["provisional", "final"]` (provisional = fact-stage call with
  `document_plan=None`; final = post-render call).
- Add `candidate_sha256: str | None` (bind to `document_plan.candidate_sha256`, already computed at
  `document_plan_finalizer.py:72` as `sha256_hex(candidate)`) so the artifact is byte-anchored and
  goes stale on any candidate edit -- mirrors the `replacement_sha256` anchor pattern already used
  by `RenderedOutputSpanV1`.
- Add `final_dispositions: tuple[FinalKnowledgeDispositionV1, ...]`, one entry per **selected**
  (`accepted=True`) item from `KnowledgeSelectionResultV1.dispositions`, each carrying:
  `global_claim_id`, `resulting_fact_field`, `final_state` (new enum, the task's 8-value vocabulary:
  `rendered_with_exact_span` / `preserved_equivalent` / `supplied_to_qwen_not_used` /
  `selected_never_supplied` / `rejected_with_reason` / `silently_lost` / `unverified_supporting_only`
  / `incorrectly_reported_influential`), `output_span: RenderedOutputSpanV1 | None`,
  `omission_reason: str | None` (**required non-null whenever `final_state` is not
  `rendered_with_exact_span`/`preserved_equivalent`** -- enforced by a pydantic `model_validator`,
  not by convention).

### K3-2: Join `candidate_content_provenance`, not just `operations[*].fact_ids`

**File:** same module, `build_knowledge_application_report` (L133-162).

- Add parameter `candidate_content_provenance: tuple[CandidateContentProvenanceV1, ...] = ()`.
- Extend the existing `field_by_fact_id` scan (currently only over `document_plan.operations`) to
  also iterate `candidate_content_provenance` entries' `fact_ids` (the verified-template route's real
  lineage channel, per repair-backlog.md P0-3 and confirmed present at
  `document_plan_finalizer.py:81-103`), producing the same `RenderedOutputSpanV1` shape using
  `provenance.candidate_byte_start/end` in place of an operation's `replacement_sha256` where no
  operation covers the span. This directly satisfies the task's "join both operation fact IDs and
  verified-template candidate provenance" requirement.
- Compute `final_dispositions` by cross-referencing every selected item's field against
  `sections_influenced`/the new joined spans:
  - item's field appears in a produced span -> `rendered_with_exact_span` (attach the span).
  - item's field is one of the six K3 fields with **no consumer at all** (per
    `MISSING_CONSUMER_MATRIX.json`, i.e. `feature`/`install`/`troubleshoot` today, and
    `format_support`/`limitation`/`license` until C1 ships their consumers) but the field itself
    reached `accepted_composition_fact_ids` -> `supplied_to_qwen_not_used`.
  - item's field verification_state is not `verified`/`policy_approved` (never reached
    `accepted_composition_fact_ids`) -> `unverified_supporting_only`.
  - item was `accepted=False` with a `rejection_reason` -> `rejected_with_reason` (carry the reason).
  - (reserved for post-C1 runs) a field the renderer explicitly consulted but decided against, with
    an explicit deterministic reason recorded by the consumer itself -> `selected_never_supplied`.
  - a span existed in a prior/expected disposition but does not reconstruct against the current
    candidate hash -> `silently_lost` (fail-closed condition, see K3-4).
  - `incorrectly_reported_influential` is a **self-check**, not a normal outcome: raised only if a
    prior stored report claimed a span this rebuild cannot reproduce byte-for-byte against the
    current candidate -- i.e. this state should never appear in a healthy run; its presence is itself
    the bug signal K3 exists to catch.

### K3-3: Add the real post-render call site

**File:** `src/readme_agent/readme/idea_candidate.py::prepare_idea_fidelity_candidate` (L119-124,
right after `claim_map = build_readme_claim_map(...)`).

```python
knowledge_report = build_knowledge_application_report(
    org_repo, entry.family, entry.platform,
    data_root=paths.imported_knowledge_dir(),           # same values product_truth.py:473-480 already uses
    clone_cache=paths.baseline_dir(entry.org, entry.repo_name),
    source_revision=snapshot.source_revision,
    document_plan=document_plan,
    candidate_content_provenance=document_plan.candidate_content_provenance,
    candidate_sha256=document_plan.candidate_sha256,
)
```
Add `"knowledge_application": knowledge_report.model_dump(mode="json")` to the returned dict
(alongside the existing `readme_document_plan`/`claim_map` entries, L152-153 pattern).

**File:** `src/readme_agent/supervisor/local_poc_evidence.py::write_local_poc_readme_candidate`
(L377+, same function that already calls `_readme_reconciliation_report_or_error` /
`_check_coverage_report_or_error`) -- add a third best-effort wrapper
`_knowledge_application_report_or_error(render_result, bundle_dir)` following the identical
try/except-to-error-dict idiom (L327-344/352-374), then call
`write_local_poc_knowledge_application(snapshot, final_report)` a **second** time from inside this
function (the writer already exists unmodified, per repair-backlog.md's "rewrite/finalize" design;
`status="final"` distinguishes it from `product_truth.py`'s existing `status="provisional"` write at
the same path -- last write wins, matching `write_redacted_json`'s existing overwrite semantics).

**File:** `src/readme_agent/supervisor/product_truth.py:473-481` -- no behavior change required, but
add `status="provisional"` at construction (K3-1's new field) so the pre-render write is honestly
labeled from the start, not silently superseded.

### K3-4: Acceptance gate -- missing/invalid final accountability blocks promotion

**File:** `src/readme_agent/supervisor/local_poc_acceptance_binding.py::validate_acceptance_artifact_chain`
(L74-188) -- add a `knowledge_application: dict | None = None` parameter, loaded and threaded exactly
like `readme_reconciliation`/`check_coverage` are today (`local_poc_cache.py:312-313, 395-414`).
Gating rules (mirrors the existing L164-188 pattern):
- artifact absent, `status != "final"`, or `{"error": ...}` present -> blocking
  `knowledge_application_error`.
- `candidate_sha256` != the candidate's own hash -> blocking `knowledge_application_stale`.
- any `final_dispositions` entry with `final_state` not in
  `{rendered_with_exact_span, preserved_equivalent}` and `omission_reason is None` -> blocking
  `knowledge_application_missing_omission_reason:{global_claim_id}` (this is the schema-level
  invariant from K3-1 surfacing as a *second*, defense-in-depth check at the gate).
- any entry with `final_state == incorrectly_reported_influential` -> blocking
  `knowledge_application_integrity_failure:{global_claim_id}` (never soft-accept a self-detected
  lie).

**File:** `src/readme_agent/supervisor/local_poc_cache.py::_evaluate_local_poc_cache` (L291-414) --
load `knowledge-application.json` the same way `readme_reconciliation`/`check_coverage` are loaded
(near L312-313) and thread it into the L395-414 call.

### K3-5: Candidate/fact/cache invalidation

**File:** `src/readme_agent/facts/acceptance_contract.py` -- no change to `_COMPONENT_FILES` needed
(K3 adds a *consumer* of already-fingerprinted inputs, not a new fact-producing input). The existing
`imported_knowledge` component (L58-62) already invalidates `FACTS_COLLECTING` on selector/loader/
manifest changes; K3's new post-render write is naturally invalidated whenever `candidate_sha256`
changes, per K3-4's staleness check -- no separate cache-key change required, consistent with the
task's "reuse existing plan/render/provenance machinery, no new pipeline" constraint.

---

## C1 -- Accepted knowledge changes useful bytes

Ship **after** K3-1..K3-4 land (the accountability artifact must exist before there is anything to
hold a new consumer accountable to), and only for fields where the sequencing hazard above is closed.

### C1-1: `limitation_claims` -> `document_limitations.py` (lowest risk, ship first)

Limitation prose is inherently negative/cautionary -- no polarity-inversion risk the way a positive
capability claim has (a false "supports X" is dangerous; a false "does NOT support X" merely
overstates caution, which existing review/reconciliation machinery already tolerates better).
Extend the module's existing limitation-row assembly to append verified `limitation_claims` items
whose normalized text does not already duplicate a canonical `product.limitations` entry, **capped
at a small fixed N per run** (reuse the selector's own per-field cap value, already 8, as the
render-time ceiling too -- do not introduce a second, independent cap constant). Each appended row
cites its real `fact_id` in the owning operation's `fact_ids`/the relevant
`candidate_content_provenance` entry, so `claim_map.py`'s existing verified/conflict rejection
(L100-107/167-174) applies automatically. When zero verified `limitation_claims` items survive
dedup, add nothing and record `omission_reason: "no_novel_verified_limitation"` (K3 surfaces this,
not a separate mechanism).

### C1-2: `format_support_claims` + `feature_claims` -> capability rows, gated by a narrow polarity check

Extend `presentation/verified_template_capabilities.py::_capability_rows` (the same function the
already-shipped SEO consumer touches, `~L698-769`) to admit a bounded number of additional capability
rows sourced from verified `format_support_claims`/`feature_claims` items **only after** a new,
narrow, source-polarity check: for each candidate item, re-read the cited `evidence[].file`/
`evidence[].source_file` line range from the current clone (already available at this stage -- the
repository snapshot is in scope) and reject if the cited body is a bare `raise NotImplementedError`
(or ecosystem-equivalent stub marker) -- a minimal, targeted version of K1/KGAP-002's fix, scoped
only to what C1 needs to ship safely, not a full K1 implementation. Cap at a small fixed N (same cap
discipline as C1-1); cite real `fact_ids`; every excluded item gets an `omission_reason` (either
`duplicates_canonical_format` or `polarity_check_failed`).

### C1-3: `install_claims` -> `document_acquisition.py`

Same shape as C1-1 (additive, capped, deduped against `installation.verified_acquisition`,
fact_id-cited) -- lower risk than C1-2 since install claims describe procedure, not capability
polarity.

### C1-4: `troubleshoot_claims` -> new bounded editorial module `document_troubleshooting.py`

Only field with no existing canonical section to merge into. Follow the exact
`document_limitations.py`/`document_release.py` one-responsibility-per-module pattern (per
`docs/readme-composition-seams.md`'s before/after map) -- render a "Troubleshooting" subsection only
when >=1 verified item survives the cap; omit the heading entirely (not an empty section) at zero,
recording `omission_reason: "no_verified_troubleshoot_items"`.

### C1-5: SEO stays as-is

`relevant_seo_keywords`'s attribution-only design (KNOW-013, already shipped) is intentionally
different from C1-1..C1-4: it is unverified by design and must never gain a `fact_ids` citation. No
change proposed.

---

## Sequencing summary

1. K3-1 (schema) -> K3-2 (provenance join) -> K3-3 (real call site) -- evidence-only, no acceptance
   behavior change yet; safe to land and observe against a live run first.
2. K3-4 (acceptance gate) -- flips the gate from advisory to blocking; land only after K3-3 has been
   observed producing a sane `final_dispositions` list against at least one real run (3D first, per
   the existing "Proof campaign" order in `PRIORITIZED_IMPLEMENTATION_SEQUENCE.md`).
3. C1-1 (limitations) -- safest, ships first, immediately exercises K3's new gate honestly.
4. C1-3 (install) -- same low-risk shape.
5. C1-2 (format_support/feature) -- **only after** its inline polarity check is implemented and
   red-tested (see RED_TEST_PLAN.md); do not ship on `verification_state` alone.
6. C1-4 (troubleshoot) -- new module, ships last since it has no existing section to anchor risk
   comparisons against.

Every step stays inside existing `document_*.py`/`presentation/*.py`/`facts/*.py` modules or adds
one new same-shaped module (C1-4) -- no new orchestrator, no product/platform `if` branches (all
logic is field-keyed and ecosystem-generic), consistent with `AGENTS.md`'s "Extending the runtime"
rules 1-13 and GOV-015.
