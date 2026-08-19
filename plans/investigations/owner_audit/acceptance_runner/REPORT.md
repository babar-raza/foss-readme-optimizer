# Acceptance, repeatability, and production-runner audit

Audit date: 2026-08-19  
Acceptance/runtime authority inspected: `babar-raza/foss-readme-optimizer` at
`6d112bbf88bc54f7ef3367b16ef8e9b769bdfb51`  
Main tip observed at audit close: `685246a7a4dc014adcdcd3da5be8ca49498ee2ed`  
Aspose reference: attached `readme-refresh-complete-bundle-20260819-174412`

## Owner verdict

The optimizer has useful, reusable machinery, but it is **not yet an Aspose-equivalent autonomous
README refresher and is not production-ready for the portfolio**. The current generated status is
the controlling evidence: **0/33 contract-valid** at every acceptance boundary, including
`FACTS_READY`, `CANDIDATE_GENERATED`, `AGENT_APPROVED`, and `NO_OP_PROVEN`
(`plans/status.md` at `6d112bbf`). The raw lifecycle has one candidate/approval but no no-op; that
raw label does not satisfy the current contracts.

The fastest route is not another subsystem. It is to make the already-present seams binding:

1. complete and harden the vendored Aspose check bridge;
2. make reconciliation and check coverage fail the candidate-stage promotion rather than emit
   best-effort diagnostics;
3. fix item-level knowledge trust and ensure accepted knowledge is actually expressed;
4. repair the canonical Qwen review route and automatic second-pass no-op;
5. run the verified path in the existing production workflow with persisted bundles;
6. prove it from sealed pre-refresh inputs across all ecosystems and a README-only repository.

`6d112bbf` does close the specific R1 clock-threshold bug left by `2608f125`: enterprise-link
verification now depends on deterministic `relationship`, not `target_map_stale`. It does **not**
by itself prove whole-pipeline repeatability. The full suite reported in the commit is still red
(5 failed, 4194 passed, 1 xfailed), the current portfolio has zero current-contract no-ops, and no
same-input production replay at this SHA is committed.

## Evidence integrity and denominator

- The optimizer registry has **33 repositories**: Python 13, .NET 7, Java 4, C++ 4, TypeScript 2,
  Go 2, Rust 1 (`data/products.json`). The formal Gate-A denominator is therefore 33, not 30.
- The attached Aspose canonical candidate store names
  `reports/repo-presenter-regen-full`; it contains **31** `readme.md` candidates, although skill
  prose still mentions 30. The attached check module contains **103** `check_*` functions, although
  some bundle prose mentions 91. Code and candidate inventory outrank stale narrative counts.
- The optimizer imported **31 knowledge bundles** under `data/imported/knowledge/*/*/merged`;
  the two absent registry products are PSD/.NET and PSD/Python. The selective attached bundle
  contains only eight merged knowledge directories and cannot by itself prove PSD handling.
- Current 3D, Note, and Barcode Python default branches already contain refreshed READMEs. The
  documented historical `3/33 NO_OP_PROVEN` occurred after at least 3D and Barcode had received
  Aspose-style refreshes. It proves preservation/no-op on strong current documents, not generation
  from their pre-refresh documents. Any generation claim must pin a pre-refresh parent commit.
- The attached Aspose evidence has 11 run manifests: one `PUSHED` Note/Python run, one `PLANNED`
  Page/Python run, and nine `ABANDONED` runs. Aspose quality is strongly evidenced by its candidate
  corpus and hard-gate machinery, but the bundle is not a 31-product production-run ledger.

## End-to-end trace

### 1. Candidate and knowledge

The optimizer already imports the correct categories of evidence. `facts/provider.py` calls
`composer_factpack.py::aspose_fact_records`; `aspose_knowledge_selection.py::knowledge_claim_fact_records`
and the SEO fact path project imported Aspose knowledge into `ProductFactsV2`. Candidate planning
and rendering flow through `specialists/readme_presentation.py`,
`readme/agentic_composition*.py`, and `presentation/verified_template_draft.py`.

The seam exists, but trust and expression are incomplete:

- accepted knowledge can be grouped into one field-level fact while individual claim items have
  different verification states; downstream authorization by fact ID can therefore over-authorize
  an unverified item;
- non-license corroboration currently establishes that a cited file exists, not that its symbol,
  line, polarity, or implementation supports the claim;
- real imported knowledge can be internally contradictory (for example 3D/Python positive FBX
  export claims versus `NotImplementedError` limitations while `has_conflicts: false`);
- the renderer consumes a narrower subset of capabilities/install/formats/limitations/SEO facts
  than the Aspose agent uses when composing a complete document.

Classification: **partly implemented, publication-blocking trust gap, output use unproven**.

### 2. Existing README reconciliation

`readme/readme_reconciliation.py::build_readme_reconciliation_report` derives a byte partition into
preserved/corrected/relocated/superseded/omitted from the existing document plan and composition
ledger. Internally it raises on unexplained source loss. That is useful and should be retained.

However `supervisor/local_poc_evidence.py::_readme_reconciliation_report_or_error` catches the
failure and writes `{error: ...}` because it "must never" break candidate persistence. The report
therefore does not gate candidate promotion. Further, an operation touching a gap is enough to
label it omitted, and `move_exact` relocation accepts a byte substring occurring anywhere in a
replacement. This is weaker than the Aspose four-ledger contract:

- `content-dispositions.json` for prose/content units;
- `structure-dispositions.json` for fenced/structural units;
- `code-example-dispositions.json` for code examples;
- `badge-dispositions.json` for badge semantics.

The existing composition ledger should be projected into those inputs; a second reconciliation
architecture is unnecessary.

Classification: **fail-open and semantically weaker than the reference**.

### 3. Deterministic checks, classification, and coverage

Actual parity against the attached canonical check module is **89/103 = 86.4%**. Fourteen checks
are absent:

`check_additional_example_headings`,
`check_code_example_excluded_reason_citation_too_narrow`,
`check_content_unit_redundant_claim_verifiable`,
`check_dependency_development_claim_not_in_manifest`,
`check_dependency_section_subheadings_present`,
`check_diagram_from_scratch_capability_labeled`,
`check_diagram_label_geometry`,
`check_frozen_blocks_unchanged`,
`check_image_content_unit_excluded_reason_verified`,
`check_issue_draft_rejection_list`,
`check_no_internal_details_leaked_into_issue_draft`,
`check_no_upstream_issue_leaked_into_install_or_quickstart`,
`check_scope_compliance`, and
`check_seo_keyword_plan_usage`.

Two are issue-draft-only; the other twelve affect candidate quality, reconciliation, or surgical
convergence.

`data/aspose_check_classification.json` describes 89 checks: 45 runnable and 44 non-runnable;
61 `applicable_after_adaptation`, 11 `applicable_reusable`, and 17 diagnostic heuristics. Only
**11/103 canonical functions (10.7%)** are currently able to block through the imported
classification. It is correct that heuristics remain nonblocking, but it is not acceptable that
hard gates skip or error without rejecting acceptance.

`validation/aspose_checks_bridge.py::run_aspose_checks` honestly records missing parameters as
`checks_skipped` and exceptions/non-list results as `checks_errored`; nevertheless `.valid` only
looks for critical findings. A skipped or errored hard gate therefore passes this signal.
`readme/document_validation.py::validate_document_candidate` promotes only findings returned by
`blocking_aspose_check_findings`; skipped/errored governed blockers are not findings.

`validation/aspose_check_coverage.py::build_check_coverage_report` accounts for every vendored
check, but an unclassified registry check becomes a nonblocking skip. Its caller,
`local_poc_evidence.py::_check_coverage_report_or_error`, catches errors and writes an error record.
Coverage is consequently **diagnostic only**, not acceptance evidence.

The classification fixtures cover only three Python candidates (3D, Barcode, Cells). Promotion
based on "did not fire on currently accepted candidates" is not semantic proof and is especially
weak because those candidates are already refreshed. Mutation tests and one real fixture per
ecosystem are still required.

Classification: **11-check partial hard gate; 44/89 non-runnable; skips/errors fail open**.

### 4. Independent review and repair

The verified local path has a real non-authoring review seam:
`specialists/separated_readme_review.py::run_separated_readme_review`, review acceptance bindings,
candidate hashes, deterministic bindings, and a bounded two-attempt repair loop in
`specialists/readme_review_repair_loop.py`. Candidate changes require deterministic revalidation
before rereview. This is one of the strongest existing parts and should be repaired, not replaced.

The canonical live route currently combines blind-quality and factual-plan verdicts in one forced
tool call. `llm/reviewer_client.py::LiveMergedReadmeReviewClient` has `max_tokens=4000`, one
transport attempt, and one response attempt. The committed status records the exact production
failure: Qwen ended at `finish_reason='length'`, emitted truncated JSON at 4000 completion tokens,
and left 3D/Python in `SYSTEM_FAILURE`. A separate-client path already exists with 3000/6000-token
budgets, but malformed/truncated merged output does not transparently fall back to it.

Context-isolated facets from one model call are useful review structure, but they are not empirical
proof of reviewer accuracy. The required missed-defect corpus / repeated evaluation evidence is
not current-contract portfolio proof.

Classification: **blocking as designed, but operationally unreliable and unproven on Qwen**.

### 5. Cache, no-op, and invalidation

`supervisor/local_poc_cache.py` and `local_poc_acceptance_binding.py` provide strong acceptance
binding: source revision, facts, fact/local-verification contracts, prompts, template, candidate,
reviewer standard, component manifest, artifact inventory, final verdict, and zero-provider-call
no-op proof are checked. `local_poc_review_evidence.py::write_local_poc_no_op_evidence` rejects a
no-op that made a provider call. This should be preserved.

Four gaps prevent repeatable production use:

1. reconciliation and check-coverage success are not in the acceptance chain, so a complete cache
   can preserve a candidate whose new diagnostic file contains `{error: ...}`;
2. the candidate component manifest does not explicitly bind all newly imported check,
   classification, coverage, and reconciliation owners; invalidation depends too heavily on broad
   manually curated groups/version signals;
3. first approval needs a later scheduler pass to become `NO_OP_PROVEN`; the scheduler does not
   immediately perform the zero-call second pass;
4. hosted matrix runners upload the local bundle as a 30-day artifact but do not restore it on the
   next run. Durable lifecycle state can therefore outlive the artifact it references.

Blocked-decision caching is also unsafe for autonomy. `commands_supervision.py::_cmd_supervise_registry`
reuses a cached blocked outcome unless a human passes `--retry-blocked`, without first limiting
reuse to `infra_external`. A transient malformed Qwen response or code defect can thus become a
manual-only retry loop even though repository governance says agent-fixable blocks must be repaired
and resumed.

Classification: **good local acceptance cache, incomplete dependency chain, hosted persistence
missing, agent-fixable blocked cache can stall**.

### 6. Portfolio scheduler and GitHub runner

The local registry command correctly orders entries with
`registry/priority.py::order_entries_by_platform_priority` and has a 300-second slice budget, but
the budget is checked only between members and cannot bound one long repository transaction.

The hosted workflow is not the verified path:

- `.github/workflows/readme-agent-production.yml` runs `github_observe` for hosted analysis;
- `supervisor/execution_profile.py` defines `github_observe` with no `local_write`, no independent
  verification, and `verify_local_product_facts=False`;
- its ACT path still targets suspended `TRUSTED_NO_OP_PROVEN`, not verified `NO_OP_PROVEN`;
- the production matrix uses `commands_lifecycle.py::cmd_runtime_matrix`, which preserves registry
  order rather than the governed platform priority;
- analysis and recovery use `max-parallel: 1`, each repo may consume 120 minutes, and every matrix
  job reinstalls dependencies. A full 33-repository pass can consume 11-66 serial runner-hours
  before retries, Docker pulls, and LLM repair;
- only pip packages are cached. Product bundles, Docker images, acquired dependencies, and
  immutable verification results are not restored across hosted runs;
- candidate uploads deliberately use the default `if-no-files-found: warn`, so a green upload step
  does not prove candidate evidence existed.

Classification: **production wiring missing; current workflow cannot prove Gate A**.

## Ecosystem and README-only support

The registry, manifest parsers, acquisition resolvers, and example-verifier modules nominally span
all seven ecosystems. Real acceptance depth does not:

| Ecosystem | Registry count | Example-verifier module | Dependency snapshot | Current check fixture proof |
|---|---:|---|---|---|
| Python | 13 | yes | implemented | 3 refreshed candidates |
| .NET | 7 | yes | explicitly not implemented | none |
| Java | 4 | yes | explicitly not implemented | none |
| C++ | 4 | yes | explicitly not implemented | none |
| TypeScript | 2 | yes | explicitly not implemented | none |
| Rust | 1 | yes | implemented | none |
| Go | 2 | yes | explicitly not implemented | none |

`facts/dependency_snapshot.py` leaves native-system and proprietary-runtime buckets empty for all
ecosystems and marks five ecosystems non-applicable. This is honest, but not parity with the
canonical dependency checks.

PSD is not proven. Both PSD repositories are in the 33-entry denominator and absent from imported
knowledge. PSD/Python is explicitly `BLOCKED_MISSING_EVIDENCE` in the current generated status;
both registry entries are disabled/read-only. The attached Aspose bundle has no PSD candidate,
knowledge bundle, or run manifest, so the user's report that Aspose handles PSD should be treated
as a requirement needing a narrow supplemental evidence bundle, not as proof already present.

The generic fix is a repository-shape policy, not a PSD branch: a README-only repository can be
`FACTS_READY` when every material claim in its candidate is verified from the README plus approved
external/owner authorities, while install/API/example slots are explicitly not applicable and no
code claim is invented. `verified_template_draft.py` currently expects installation/example-like
facts and must support this honest sparse-document route.

## Minimum bounded closure route

Do these in order and stop if a gate fails:

1. **Freeze truth and tests.** Pin optimizer `6d112bbf`, the 103-check bundle hash, registry 33,
   target document identities (pre-refresh/current/candidate), and one fixture per ecosystem plus
   one README-only fixture. Fix the five existing full-suite failures; no baseline-red exception.
2. **Close knowledge trust before prose.** Preserve per-item verification/disposition in grouped
   knowledge facts; require semantic evidence resolution and polarity/conflict reconciliation;
   add tests for the real 3D FBX contradiction and stale/current trio. A mixed fact must never
   authorize an unverified item.
3. **Reach canonical check parity.** Vendor the exact current 103-check module and its direct helper
   dependencies. Classify the 14 additions. Maintain heuristics as reviewer-visible, but every
   applicable hard gate must run and errors/skips must reject promotion.
4. **Use existing lineage as the Aspose input adapter.** Extend the bridge to accept source text,
   document plan/composition ledger, repository root, knowledge texts, badges, examples, and
   dependency snapshot. Project the existing ledger into the four Aspose disposition input shapes;
   do not build a parallel ledger system.
5. **Make candidate-stage evidence fail closed.** Before
   `portfolio_scheduler/stages.py::promote_candidate_stage`, require a valid five-bucket report,
   four complete disposition projections, no unclassified check, no check execution error, and no
   skipped applicable hard gate. Persist rejected attempts, but never promote them.
6. **Complete dependency inputs.** Reuse the seven existing manifest parsers/resolvers to populate
   dependency snapshots for .NET/Java/C++/TypeScript/Go; add native/proprietary limitations from
   accepted evidence. Test direct/transitive/dev/optional/native distinctions per ecosystem.
7. **Ensure knowledge affects output.** Expand the existing agentic composition plan and verified
   template slots so every selected accepted knowledge item has exactly one disposition:
   rendered, preserved-equivalent, superseded, or omitted-with-verified-reason. Make unused
   accepted item IDs a blocking coverage failure.
8. **Repair Qwen review, using existing clients.** On merged `length`, malformed tool arguments,
   or schema failure, automatically run the already-existing separate blind and factual clients;
   use their 3000/6000 budgets and bounded retry. Preserve two repair attempts and deterministic
   revalidation. Do not turn a review failure into acceptance.
9. **Close no-op automatically and invalidate precisely.** After `AGENT_APPROVED`, immediately run
   the existing approved-cache path once in the same repository job and require zero provider
   calls. Bind vendored checks, classification, bridge, reconciliation, and coverage to stage
   dependency manifests. Cache only `infra_external` blocked decisions; retry/repair
   `agent_fixable` outcomes autonomously.
10. **Put verified execution on the existing hosted workflow.** Upgrade the existing read-only
    hosted profile/job to permit local evidence writes, local fact verification, independent
    review, and target verified `NO_OP_PROVEN` while retaining zero product-remote writes. Make
    `runtime-matrix` use platform priority. Restore/save repository-specific `runs/readme-poc`
    bundles across jobs/runs. Start `max-parallel: 1`; increase to 2 only after measured isolation.
11. **Prove quality, then fan out.** Replay 3D/Note/Barcode from sealed pre-refresh commits and a
    genuinely unrefreshed repository; run the README-only fixture; then one repository per
    ecosystem. Compare candidate bytes/sections and all 103 check outcomes against the Aspose
    candidate where available. Require two identical runs, second-run zero provider calls, exact
    artifact hashes, no fail-open diagnostic records, and independent acceptance. Only then run
    the full dynamic 33-entry denominator.

## Release acceptance

Do not claim 30/30 or 33/33 until all of the following are true on one committed SHA:

- official lint, format, mypy, and complete non-live suite are green;
- 103/103 canonical checks are inventoried; every applicable hard gate runs and passes;
- every original README unit has a verified disposition and no reconciliation error;
- every selected knowledge item has a candidate disposition and item-level trust state;
- sealed pre-refresh/unrefreshed and README-only replays meet the quality rubric;
- each repository reaches current-contract `AGENT_APPROVED` and `NO_OP_PROVEN`;
- the no-op run makes zero provider calls and reproduces identical candidate/artifact hashes;
- the hosted workflow, not a local hand-run, reconstructs the final 33-entry aggregate;
- no product repository is written during proof.

Until then, the honest status remains **pre-POC, 0/33 current-contract complete**.

## Main-tip change after the audit pin

Main advanced from `6d112bbf` to `685246a7` while this audit was running. The new commit is
Decision #107, control-repository post-commit auto-push. It adds governance documentation,
`scripts/governance/post_commit_push.py`, hook installation, and local bare-repository tests. It
does not change README candidate, facts, validation, review, cache, scheduler, workflow, or product
effect code, so none of the acceptance conclusions above changes.

Its scope is correctly separate from product-repository writes: the established product work-clone
neuter and explicit product authorization remain. Two bounded control-repository risks should be
closed before relying on the hook broadly:

- the script refuses only the literal `DISABLED` push URL; it does not prove that `origin` is the
  expected `babar-raza/foss-readme-optimizer` control repository, so an accidentally repointed
  origin could receive the push;
- a post-commit hook failure cannot reject the commit and its console message is not durable queue
  state. A failed/non-fast-forward push can remain unpushed until another commit or manual action.

Add an exact control-repository remote-identity allowlist and a durable pending-push/status check.
This is a contained governance hardening item, not a reason to delay the acceptance closure order.
