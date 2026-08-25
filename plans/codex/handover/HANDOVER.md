# Agent Handover

## 1. Handover Snapshot

| Item | Current checkpoint |
| --- | --- |
| Repository | `D:\\Users\\prora\\OneDrive\\Documents\\GitHub\\foss-readme-optimizer` |
| Branch | `main` |
| Execution baseline HEAD | `40529bab47c830f0b07ddfcee6ff4a76312f8232` |
| Mission | `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` |
| Mission state version | `1639` |
| Mission graph SHA-256 | `5023a23a9005f2bb57f785398171e5c6051cd4412329995da7a57ce35f77c5f4` |
| Current stage goal | `GOAL-V0B-POST-PYTHON-SLICES` |
| Current task | `L8-PF-05-SEVEN-ECOSYSTEM-CANARIES` (`IN_PROGRESS`) |
| Claim | `994eca3b46be483983e413ce85402143`, held by `codex`, expires `2026-08-25T13:10:20.811619+00:00` |
| Exact next action | Fix `PF05-CXX-LINK-001`, rerun only the C++ canary, then collect/reduce the remaining ecosystem first-boundary receipts. |
| Effects | No product repository write, branch, commit, PR, merge, release, package, or settings effect. |

This handover replaces the historical August 12 Python/non-Python record. Its snapshot is the state before this handover record is committed. The receiving agent must always verify live Git and durable state before acting.

## 2. Ultimate Goal

Deliver the shortest safe path to a publication-ready, verified repository-presentation POC:

- 31/31 processable Aspose FOSS repositories have source-fresh, repository-specific README candidates from the canonical `verified_repository_presentation`/`supervise` path;
- every candidate has immutable snapshot, ProductFactsV2, imported-knowledge dispositions, document plan, native patch, complete source-claim accountability, deterministic and public-quality validation, factual and visitor review, benchmark acceptance, independent 30/30 approval, no hard disqualifiers, and an immediate complete-transaction zero-provider-call no-op;
- two source-empty PSD entries remain current `NON_PROCESSABLE_NO_IMPLEMENTATION` dispositions with resume predicates;
- every accepted processable repository becomes `PR_ELIGIBLE` with a validated `VerifiedProposalV1`, rollback instructions, draft PR body/title, and exact what/why/where authorization packet;
- terminal state is `PORTFOLIO_PUBLICATION_READY_AWAITING_EFFECT_AUTHORIZATION`.

No product-repository effect is authorized in this campaign.

## 3. Authority and Constraints

Authority is resolved by subject, in this order:

1. `AGENTS.md` and `plans/GOVERNANCE.md` — execution, safety, editing, coordination, and effects.
2. `plans/idea.md` — product outcome and presentation intent. SHA-256: `f4e9f1184227ae7d39c3edf82555edc9c541c0fbc88edb898e48d421a49de064`.
3. `plans/master.md` and `plans/decisions/catalog.jsonl` — architecture and sequence. `master.md` SHA-256: `f4ad284aa17dbde439d9bf24dd1ec65c0d774548a7df19076726a3b2e43ba361`.
4. `plans/requirements.md` and `plans/requirements/catalog.jsonl` — obligations and acceptance. Catalog SHA-256: `9a8af7409e1867a1ec16c73ceb5d3b0561b00774ec3b9915b5e396b4f89389f3`.
5. `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` — sole executable graph. SHA-256: `5023a23a9005f2bb57f785398171e5c6051cd4412329995da7a57ce35f77c5f4`.
6. Supervisor Git-ref state — sole authority for claims, transitions, active task, and lifecycle. Narrative documents never override it.
7. `C:\\Users\\prora\\.codex\\attachments\\a1a147bb-62fd-456b-94db-b799adcede5e\\goal-objective.md` — user-supplied execution objective for this sprint.

Non-negotiables:

- work on control-repository `main`; do not reset, restore, clean, force-push, or overwrite unclassified work;
- `supervise` is the canonical local runtime; `local_poc` has zero product-write authority;
- use the existing allow-list, push-blocking, evidence redaction, durable state, Qwen caching, independent review, and imported-knowledge mechanisms;
- do not create a competing plan, controller, lifecycle, task graph, template system, or evidence framework;
- do not do Level 7/8 certification, hosted infrastructure, social previews, analytics, or product effects before candidate readiness;
- run focused tests per repair and the complete non-live runner only at a coherent task/portfolio boundary;
- after two equivalent failures or 15 minutes without material narrowing, record first-principles replan and change the causal tactic; never blindly retry;
- preserve valid snapshots, facts, authored sections, review packets, and provider caches whenever dependency hashes permit reuse.

## 4. Current Verified State

### Verified complete

| Item | Evidence | Proof status |
| --- | --- | --- |
| PF02 current complete-candidate seam | `L8-PF-02-COMPLETE-CANDIDATE-SEAM=CLOSED` in durable state version 1639 | Verified current closure |
| Aspose.3D Python current candidate | `runs/readme-poc/aspose-3d-foss__Aspose.3D-FOSS-for-Python/ee05c1ba9153ef5916b7a108406c794f2e464d01/review/final-verdict.json` | `AGENT_APPROVED`; deterministic validation passed; zero repairs |
| Aspose.3D Python immediate no-op | same bundle `review/no-op-proof.json`; canonical second transaction output | `CONVERGED_NO_TRACKED_CHANGE`, `provider_calls=0`, `cache_reuse=1` |
| C++ contextual-fragment verifier | commit `40529bab47c830f0b07ddfcee6ff4a76312f8232`; `src/readme_agent/facts/cpp_repository_fragments.py`; `tests/unit/test_cpp_repository_fragments.py` | 43 focused tests passed; Ruff, formatting, mypy, and diff checks passed; real isolated harness promoted 5/5 inherited fragments as `SOURCE_BUILD_VERIFIED` |
| No product effects | supervisor outputs and safety design | Verified; local POC only |

### Current portfolio counters

Durable status at version 1639 reports `facts_ready=2/33`, `candidate_generated=1/33`, `deterministic_validated=1/33`, `agent_approved=1/33`, `no_op_proven=1/33`. The denominator is 33 admitted entries: 31 processable README targets and two PSD dispositions. This means one processable repository is current, accepted, and no-op-proven; it is not portfolio completion.

Raw historical lifecycle figures (`26/3/3/3/3`) are not current acceptance evidence because most bundles are stale against the current fact contract.

### Partial / in progress

`L8-PF-05-SEVEN-ECOSYSTEM-CANARIES` is active. C++ has current facts after the committed fragment collector, but its transaction stopped before presentation planning. The other six ecosystem receipts are not sealed under the current contract. PF06 and PF07 remain `TODO`.

## 5. Current First Failing Boundary

### PF05-CXX-LINK-001 — contextual source-link eligibility

- Severity: blocking PF05 C++ canary; agent-fixable.
- Exact terminal result:

  ```text
  ValueError: invalid contextual README links: candidate contains non-linkable Aspose target: https://docs.aspose.org/cells/cpp/
  ```

- Canonical canary: `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp` at `9f852d0ff1cfdad2d661556d6b87a8eff8c063a2`.
- Evidence: `runs/readme-poc/aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp/9f852d0ff1cfdad2d661556d6b87a8eff8c063a2/facts/product-facts.json` contains the inherited verified C++ hyperlink example; the URL is also present in `data/aspose_org_links.json` and a related current canonical documentation route is present in `data/aspose_com_links.json`.
- First failing code: `src/readme_agent/links/contextual_validation.py`, invoked by `src/readme_agent/readme/document_renderer.py` and `src/readme_agent/presentation/verified_template_document.py`.
- Root-cause hypothesis: the preserved source-bound docs.aspose.org URL is present in the approved Aspose.org link inventory but does not satisfy the validator's linkability projection. Do not replace it blindly, disable validation, or claim an arbitrary replacement is equivalent.
- Permanent repair: reconcile contextual-link eligibility with the checked-in link inventories and fact/source accountability. Admit only a catalog-backed, contextually applicable target; retain rejection for unknown, commercial-only, malformed, or non-contextual URLs. Add a direct acceptance regression for this exact catalog-backed target and a negative control for a non-catalog target.
- Focused proof: link validator tests plus C++ source-claim/renderer tests; rerun only the C++ bounded canary. Expected material narrowing: the link error disappears; do not assume later claim, duplication, or DateTime findings are fixed until the canary reports them.

## 6. Ordered Execution Queue

1. **PF05-CXX-LINK-001.** Repair contextual eligibility for catalog-backed inherited links. Allowed paths: `src/readme_agent/links/`, relevant renderer/binding seam, and focused tests. Run focused link/renderer/source-claim tests, safety regressions if a link policy changes, then one C++ canary.
2. **PF05 first-boundary completion.** Collect or refresh exactly one canonical receipt for .NET, Java, C++, TypeScript, Rust, and Go while preserving the completed Python Aspose.3D receipt. Do not make another shared repair until receipts are complete.
3. **PF05 causal reduction.** Use the existing canonical reducer and its current receipt inventory. Group only evidence-backed shared causes; opaque or incomplete inputs fail closed. Apply one coherent shared repair per cluster and rerun only affected canaries.
4. **PF05 seal.** Obtain 30/30 approval and immediate zero-call no-op for all seven. Record isolation/parallelism evidence before enabling up to two disjoint repository workers.
5. **PF06.** Perform all-visibility discovery, freeze `RegistryRevisionV1`, current snapshots/facts/knowledge for all processable repositories, and preserve two current PSD dispositions. PF06 must not create candidates.
6. **Portfolio fan-out.** Run the canonical `readme-agent supervise --registry data/products.json --execution-profile local_poc` over the frozen 31 processable repositories. Use at most three disjoint workers only after PF05 transaction isolation proof; coordinator exclusively owns shared state, integration, commits, and closure.
7. **PF07.** Refresh source freshness, reopen only drifted repositories, create effect-neutral `VerifiedProposalV1` payloads and authorization packets, and derive `PORTFOLIO_PUBLICATION_READY_AWAITING_EFFECT_AUTHORIZATION`. Stop before any product effect.

## 7. Receiving Agent Startup Procedure

1. Read `AGENTS.md`, this file, the goal objective, and the four authority artifacts listed above.
2. Run `git status --short --branch`, `git log -1 --format=fuller`, and inspect repository-owned processes.
3. Run mission `status`. If graph drift, claim expiry, or state inconsistency is shown, run mission `evaluate`.
4. Never steal a live unexpired claim. If the previous PF05 claim expired, reclaim only the controller-printed eligible task.
5. Begin PF05-CXX-LINK-001. Do not rerun the unchanged failed C++ canary before the repair.
6. Keep evidence under existing `runs/readme-poc/` and task-transition evidence locations; do not create timestamped handover duplicates.
7. After a coherent implementation slice, run the focused test set, exact canary, and only then commit directly to `main` with `Co-Authored-By: Codex <noreply@openai.com>` (or the actual author identity).
8. Refresh these same three handover files after each task transition, coherent commit, true external block, or deliberate safe checkpoint.

## 8. Closure Standard

Do not close the umbrella goal until current evidence proves all 31 processable repositories are source-fresh, independently 30/30 accepted, immediate-no-op-proven, and PR_ELIGIBLE; both PSD dispositions are current; hard disqualifiers and agent-fixable failures are zero; portfolio manifests/checksum inventories reproduce; durable graph/lifecycle agree; terminal state is `PORTFOLIO_PUBLICATION_READY_AWAITING_EFFECT_AUTHORIZATION`; and no product-repository effect occurred.

## 9. Handover Verification

This handover is `HANDOVER_READY` only after `CONTINUE.md` and `state.json` agree, JSON validates, paths exist, current Git/mission values are rechecked, and no repository-owned process remains. The commit containing this handover is not part of the pre-write execution baseline; the receiving agent must always re-read live HEAD.
