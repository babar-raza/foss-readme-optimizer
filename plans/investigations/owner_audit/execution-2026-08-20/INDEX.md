# Owner audit evidence — execution 2026-08-20

Coordinating index for six owner-audit bundles ingested from `runs/owner_audit_staging/`
(gitignored working area) into tracked, permanent evidence storage. All six bundles were
produced read-only, at optimizer pin `aa998102191c530af4dca3a6895d62a4027a613e`, and this
integration commit changed no production code, tests, requirements, mission state, candidates,
or product repositories — only evidence files were copied and these two coordinating files were
added.

Per-file SHA-256 for every copied file, plus the local/origin HEAD observed at integration time,
is in `MANIFEST.json`.

---

## note-ledger-accountability

- **Source lane:** OPT-NOTE-LEDGER-ROOT-CAUSE (`runs/owner_audit_staging/note-disposition-root-cause-aa9981021`)
- **Audited SHA:** `aa998102191c530af4dca3a6895d62a4027a613e`
- **Decisive conclusion:** Two independent, unrelated defects, not one. (1) Note's `reject`
  verdict is caused entirely by `document_validation.py`'s claim-accountability gate finding 2
  unresolved blocking claims — unique to Note among the three calibration repos. (2)
  `disposition_ledger_valid: false` on **all three** repos (Note, Barcode, 3D — including the two
  that otherwise `accept` cleanly) is a systemic identity-mismatch bug in
  `commands_poc.py::build_source_disposition_ledger`'s heading-to-slot lookup: a granularity
  mismatch (sub-headings can never match top-level `compiled_slot_blocks` keys) plus a
  case/wording mismatch (source heading spelling vs. contract-canonical title). 3D's imported
  knowledge is `current` (not stale) yet still fails identically, ruling out import staleness as
  a cause. Fixing (1) would not fix (2) and vice versa.
- **Affected causal owners:** `src/readme_agent/commands_poc.py::build_source_disposition_ledger`
  (lines 185-193) and `_disposition_acceptance` (lines 282-300); `document_validation.py`'s claim
  accountability gate (separate defect); `scripts/governance/promote_working_condition_exceptions.py`
  (the one blocking consumer of `disposition_ledger_valid`).
- **Status:** Open. Root cause identified for both defects; smallest generic repair described but
  not implemented.
- **Next implementation gate:** Make the ledger lookup identity-aware (canonicalize both sides;
  resolve nested headings to their enclosing contract slot before the `compiled_slot_blocks`
  lookup) per `RED_TEST_PLAN.md`. Separately, retrieve and resolve Note's 2 blocking
  claim-accountability records (their literal text was not located within this pass's time-box).

## repository-processability

- **Source lane:** OPT-REGISTRY-PROCESSABILITY-AUDIT (`runs/owner_audit_staging/repository-processability-aa9981021`)
- **Audited SHA:** `aa998102191c530af4dca3a6895d62a4027a613e`
- **Decisive conclusion:** 31 of 33 registry entries are PROCESSABLE under the binding policy's
  generic tree-shape rule. Only the 2 PSD repos (`Aspose.PSD-FOSS-for-.NET`/`-Python`, both
  already `mode: "disabled"` in the live registry) are `UNPROCESSABLE_SKIP` — each has a pinned
  tree of exactly one file, `README.md`. The earliest production-runtime gate point is
  `registry/intake.py::classify_readonly_intake()` (via `supervisor/intake.py::run_readonly_intake_preflight()`),
  which runs before facts collection, Qwen calls, candidate generation, and review. The audit
  recommends reusing the existing `IntakePreflightOutcomeV1`/`ReadOnlyIntakePreflightV1` typed
  model rather than a new controller, and confirms the org-policy MIT-license fact
  (`config/policies/*.yml`) must stay distinct from GitHub-file-detected license evidence — real,
  observed divergence exists for the `cells/*` family.
- **Affected causal owners:** `registry/intake.py::classify_readonly_intake`,
  `supervisor/intake.py::run_readonly_intake_preflight`, `state/lifecycle_schema.py`
  (`IntakePreflightOutcomeV1`/`IntakePreflightBindingV1`), `repository_snapshot.py`
  (`inventory_sha256`, the precedent this audit's substitute hash should be replaced with).
- **Status:** Open. Audit/design only — no production gate implemented.
- **Next implementation gate:** Implement the generic repository-shape classifier and new
  outcome branch inside `classify_readonly_intake()`, reusing `inventory_sha256` rather than this
  audit's two substitute hashes; explicitly resolve the two open borderline fixtures (`B8`
  docs-and-assets-only, `B10` binary-with-no-manifest) per `RED_TEST_PLAN.md`.
- **Validation note (recorded, not repaired):** This bundle's `SHA256SUMS` declares checksums for
  only 4 of the 39 files actually present (`REPORT.md`, `REGISTRY_PROCESSABILITY_MATRIX.json`,
  `INTEGRATION_POINTS.md`, `RED_TEST_PLAN.md`). The `_fetch_and_classify.py` helper and all 33
  `raw/*.json` GitHub API captures are present on disk and parse/scan clean (all valid JSON, no
  secret patterns detected), but are **not** individually checksum-attested by the bundle's own
  manifest. All 4 declared checksums verify against their files. `MANIFEST.json` (this commit)
  supplies an independent SHA-256 for every one of the 39 files as compensating coverage.

## candidate-aspose-parity

- **Source lane:** OPT-CANDIDATE-ASPOSE-PARITY-AUDIT (`runs/owner_audit_staging/candidate-aspose-parity-aa9981021`)
- **Audited SHA:** `aa998102191c530af4dca3a6895d62a4027a613e`
- **Decisive conclusion:** None of the three Stage-5 optimizer README candidates (Aspose.3D,
  Aspose.BarCode, Aspose.Note — all FOSS-for-Python) reach acceptance against the 30-point rubric;
  each carries 2-3 hard disqualifiers (self-contradicted API/limitations claims within the same
  document; the disposition ledger failing while promotion/delivery proceeds anyway; old-README
  content silently dropped with no ledger record). The portfolio `RESULTS.md` summary is not
  reconciled against per-run evidence — Note is labeled `DELIVERED`/`none` despite a `reject`
  verdict in its own `validation.json`.
- **Affected causal owners:** `src/readme_agent/commands_poc.py` (disposition ledger +
  `run_poc_for_repo` promotion-status logic — same code as note-ledger-accountability's Finding
  2), `presentation/verified_template_*` composers, the `RESULTS.md` reconciliation step.
- **Status:** Open. 23 non-blocking findings logged as `BACKLOG-ASPOSE-PARITY-*` rows in
  `CAUSAL_OWNER_BACKLOG.json` for owner triage; nothing fixed.
- **Next implementation gate:** Make the disposition-ledger fail-closed check actually block
  delivery/labeling instead of being purely diagnostic; add dedicated badge/media/code-example
  ledgers (only heading-level units are tracked today); reconcile `RESULTS.md` against
  `validation.json` before any `DELIVERED` label is emitted.

## knowledge-to-readme-bytes

- **Source lane:** OPT-KNOWLEDGE-TO-README-BYTES (`runs/owner_audit_staging/knowledge-to-readme-bytes-aa9981021`)
- **Audited SHA:** `aa998102191c530af4dca3a6895d62a4027a613e`
- **Decisive conclusion:** K3 (post-render knowledge accountability) and C1 (5 of 6
  imported-claim fields never reach any renderer consumer) are both confirmed still open, with
  live evidence from today's fresh `knowledge-application.json` for all three calibration
  products — causal mechanics unchanged since a 2026-08-19 prior audit across the 12 intervening
  commits. New finding: two of 3D's known false-positive format-support claims were excluded
  today only by a selection-cap tiebreak, not by the corroboration check (which never verifies
  claim content, only that the cited file exists). An implementation-ready K3/C1 repair design is
  included, reusing existing plan/render/provenance/acceptance-binding machinery with no new
  pipeline.
- **Affected causal owners:** `supervisor/product_truth.py:473-481` (the sole, pre-render
  knowledge-application call site), `readme/idea_candidate.py` (missing the promised second,
  post-render call), `render_views.py`/`verified_template_capabilities.py`/`document_*.py`
  (missing consumers for 5 of 6 imported-claim fields), `aspose_knowledge_selection.py` (K1
  corroboration/selection-cap interaction).
- **Status:** Partially closed — repair design complete and implementation-ready (K3-1..K3-5,
  C1-1..C1-5); not yet implemented.
- **Next implementation gate:** Implement per `IMPLEMENTATION_SEQUENCE.md`. Re-validate this
  bundle's `unverified_supporting_only` classifications and the `exceeds_selection_cap` finding
  once the concurrently in-progress K1 fix — observed as uncommitted working-tree changes during
  this audit, not touched by it — actually lands.

## qwen-review-recovery

- **Source lane:** OPT-QWEN-REVIEW-RECOVERY-DESIGN (`runs/owner_audit_staging/qwen-review-recovery-aa9981021`)
- **Audited SHA:** `aa998102191c530af4dca3a6895d62a4027a613e`
- **Decisive conclusion:** The merged Qwen review call has 5 unrecovered failure modes
  (truncation, malformed tool arguments, top-level schema failure, transport failure, and factual
  -facet grounding failure) because only the blind-quality facet has a fallback today. The
  factual fallback client is already constructed but silently discarded
  (`separated_readme_review.py:104-107`, `build_live_role_review_clients()[1]` thrown away). An
  implementation-ready recovery-dispatcher design closes all 5 gaps by reusing existing budgets,
  caps, and receipt shapes — worst case 5 physical calls, normal-path unchanged at 1 — and
  satisfies all 14 stated requirements including the zero-secrets-in-receipt requirement.
- **Affected causal owners:** `src/readme_agent/specialists/merged_readme_review.py::execute_merged_readme_review`,
  `llm/reviewer_client.py`, `specialists/separated_readme_review.py` (the discarded
  `factual_fallback_client`).
- **Status:** Open. Design complete and implementation-ready; not implemented.
- **Next implementation gate:** Implement per `IMPLEMENTATION_PATCH_MAP.md`'s rollout order —
  schema/exception additions, `finish_reason`/`latency_ms` capture, pre-flight request-ceiling
  guard, the recovery dispatcher plus fallback-client wiring (the one behavior-changing patch),
  the two-line `separated_readme_review.py` fix, then receipt persistence. `RED_TEST_PLAN.md`
  holds the required tests.

## canonical-check-gap

- **Source lane:** OPT-CANONICAL-103-CHECK-GAP (`runs/owner_audit_staging/canonical-check-gap-aa9981021`)
- **Audited SHA:** `aa998102191c530af4dca3a6895d62a4027a613e`
- **Decisive conclusion:** Of 103 canonical Aspose.org `check_*` functions, 89 are vendored and
  14 remain missing — unchanged since the prior audit (the vendored file is byte-identical since
  commit `d71f38b6`). Of the 11 vendored checks classified `blocking: true`, 10 have no skip risk
  but can still fail open on an internal error outside the local-POC acceptance path (only
  error-only, local-POC-scoped fail-closed handling was added 2026-08-20 by `907ac0847`).
  `check_banner_present` is the one blocking check with a real, wide-open skip pathway: its
  family/platform inputs are derived only from imported-knowledge facts surviving selection, even
  though `data/products.json` already carries family/platform generically for every registered
  repository and simply isn't wired into the bridge. A further, distinct population of 32
  hard-gate checks never runs at all today (no producer wired for their inputs).
- **Affected causal owners:** `src/readme_agent/validation/aspose_checks/__init__.py` (registry),
  `aspose_checks_bridge.py::_real_kwargs` (the `check_banner_present` family/platform gap),
  `document_validation.py::validate_readme_document_candidate` (the broader gate, reached from 5
  call sites, that still does not fail closed on skip/error), `local_poc_acceptance_binding.py`
  (the partial 2026-08-20 fix, error-only, local-POC-scoped).
- **Status:** Partially closed. D11 (blocking skip/error fails open) partially fixed 2026-08-20
  for the local-POC path only; D12 (14 missing checks) and the `check_banner_present` skip gap
  remain open.
- **Next implementation gate:** Wire `data/products.json` family/platform (joined via
  `RepositorySnapshotV1.org_repo`) into `aspose_checks_bridge.py` so `check_banner_present`
  actually runs on every candidate; extend `document_validation.py`'s broader gate to fail closed
  on skip/error, not just the local-POC path; port/adapt the 14 missing checks per
  `MISSING_CHECK_ADAPTATION_PLAN.json`, honoring its `not_applicable_for_readme_only_scope`
  bucket for the 2 issue-draft-only checks.
