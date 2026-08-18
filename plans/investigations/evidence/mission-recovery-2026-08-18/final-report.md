# Mission-recovery final report — 2026-08-18 session

Operator directive: "Recover and Complete the Aspose.org `readme-refresh` Migration
Autonomously." Executed under `L8-PORT-01-LOCAL-README-PORTFOLIO-ASPOSE-PARITY` (claimed in the
local durable mission store, state_version 2). Session commits: `93fbe707c..8d90114dc` (17
commits on `main`).

## 1. Executive verdict

The system was failing for identified, now-engineered reasons, not from mystery model behavior.
Root causes fell into four classes: (1) the portfolio loop re-executed already-triaged BLOCKED
repositories on every pass with fresh provider calls, starving 22/33 registry entries of slice
budget; (2) the gateway model's tool-call arguments are **nondeterministic at temperature 0**
(live-proven this session), so every retry re-rolled classifications and counts fluctuated
without inputs changing; (3) two repositories are blocked by **genuine upstream defects** (html:
invalid build-backend; tex: 35/45 source files unparseable at the pinned "Release 26.5"
revision) that no local work can clear; (4) the residual claim-accountability blocks are a
category mismatch (inherited claims needing reasoned exclusion/reframing, incl. code blocks)
that the accept-only LLM fallback cannot close by design. Fixes landed with tests for (1), (2)
partially (ratchet), (3) (classification + evidence), and the mechanism for (4) is precisely
diagnosed with new offline diagnostics; its disposition-vocabulary extension is the top queued
engineering item.

## 2. Live repository and state reconstruction

`live-state-reconstruction.md` (this directory). Key facts: main @ `46ed34630` at session
start, dirty only with protected CRLF-only `plans/requirements.md`; Gate A plateau-stopped at
**complete=3/33** at 20:04 (3D/Cells/PDF Python NO_OP_PROVEN); durable state = 19 refs in
`runs/local-poc-state/state.git`; no leases held; no optimizer process running; a *different*
still-active session was auditing the aspose.org portfolio (left untouched); 17 stale pid
files; three prunable temp worktrees (left in place).

## 3. Findings from the attached execution record

`Pasted markdown(20260818-153907).md` was not delivered into context and does not exist on disk
(searched exhaustively). Its source session was identified
(`~/.claude/projects/...(429a25c4).jsonl`, 23.7 MB) and mined directly — a stronger source than
the paste. All 14 mandatory findings verified with line-level evidence (see the transcript-
verification lane report reproduced in the session log): 3/33 plateau ✓; recurring identical
claim failures with rising escalation counters ✓; count variance on unchanged inputs ✓
(now explained mechanistically); plateau-stop → same-loop restart ✓; the ~30–35 min idling
admission ✓ (verbatim, user-prompted); invalidation churn 10/32→0/32 by design ✓;
UNKNOWN_LEGACY beside EXACT rows ✓; detached processes + iteration-log overwriting ✓ (the
first driver run's logs are unrecoverable); `12 failed, 3906 passed` beside `[exited with code
0]` ✓ systemic (8+ occurrences); `git stash` used 9+ times and institutionalized ✓;
cells-python fix → first AGENT_APPROVED ✓; cells parity gaps (56 vs 130 API types,
FormulaEvaluator absent, thin capabilities 4/4) ✓; tex root cause as then understood ✓
(superseded this session — see 19); html/psd distinct blockers ✓.

## 4. Root causes of wasted execution and quality divergence

- **Throughput:** no blocked-decision cache → known-BLOCKED repos re-ran fully each pass
  (4–7 provider calls each), so a 1200s slice never got past member ~11 of 33.
- **Variance:** temp-0 tool-call arguments are nondeterministic on this gateway (5 distinct
  payloads / 5 identical trials) → every "retry" was a dice roll; counts read as
  progress/regression when they were neither.
- **Quality:** the mechanical claim-coverage rule pushes composition toward the *shortest claim
  that passes* — the same defect that blocks repos also thins Key Capabilities (Q1≡S1).
- **Upstream:** html (invalid `build-backend`) and tex (whitespace-mangled sources at the
  squashed "Release 26.5" history) are externally blocked; both were miscategorized
  `agent_fixable` by a value-shape gap (fixed).
- **Process:** masked pytest exit codes; overwritten iteration logs; a canary path dead-ended by
  the mission-state backend split.

## 5. Aspose.org dependency-closure manifest

Full closure traced (dependency-closure lane report; pinned at aspose.org
`80de6805f3d0`, working tree dirty and actively edited by another session). Highlights: the
skill (`.agents/skills/readme-refresh/SKILL.md`, 967 lines ×3 synced copies + 1 divergent
registry copy) drives a 12-subcommand state machine in `readme_refresh_run.py` (~3.1k lines);
98 deterministic `check_*` functions; `dependency_extract.py` per-ecosystem manifest parsers;
registries (`products/package_registry/diagram_*/families/format_descriptions/
aspose_com_targets` + backlink YAMLs); knowledge tree (`merged/` api_surface/formats/claims/
limitations/snippets with `model.yaml` repo_sha pins); reference-site `_index.md` files;
candidate store `reports/repo-presenter-regen-full` (31 candidates; sidecar
`content/structure/badge/code-example-dispositions.json`); per-run evidence with pinned
clone-cache HEADs. **There is no programmatic Claude call anywhere in the closure** — Claude is
the interactive agent; composition rules live in the skill + the external 20.9k-line historical
plan + `_briefing.md`. The optimizer already owns the consumable inputs as hashed bundles under
`data/imported/**` (18 knowledge bundles + registries + keywords, per-member sha256, repo_sha
pins) and vendored checks under `vendored_asposeorg/`.

## 6. Exact Qwen provider/model identity

**`qwen3-next`** at `https://llm.professionalize.com/v1` — configured
(`env.py:DEFAULT_LLM_MODEL`), live-confirmed against `/v1/models`, and echoed by completions.
**No `qwen2-next` exists**; the user's "Qwen2 Next" is a colloquial alias. Aux routes:
`qwen3-embedding-8b` (similarity), `Qwen2.5-VL-7B` (vision-only route).

## 7. Model capability results

Existing evidence audited against the mission's 12 required probes (probe-coverage lane):
COVERED — strict JSON-schema (5/5, 9/9, 4+3), long-context to ~71k prompt tokens, citation
fidelity (8/9 + enum-bound schemas), blind grounded review (fail-closed proven). NEW this
session (`llm-probe/qwen-output-limits-20260818.json`): forced-NAMED-tool shape **5/5**
shape+schema valid; structured output **exact to ~7,000 completion tokens** (breaks only at
the 8,000 cap); **temp-0 freeform prose byte-deterministic; temp-0 tool ARGUMENTS
nondeterministic (5/5 distinct)** — a design-changing negative result now bound into Decision
#105. Remaining gaps (recorded, queued): fault-injection/retry probe; live proof for
`trusted_readme_section_transform` (the least schema-constrained job — its TRP-02 live attempt
was an HTTP 500).

## 8. Stage-by-stage parity results

Not yet built as a standing harness (honest gap). What exists: aspose.org's stage artifacts are
fully enumerated (5), the optimizer's counterpart stages are mapped
(prompt-contract/call-shape inventory), and this session added the missing observability that
stage comparison needs on the optimizer side — blocked runs now persist their composed
candidate + full per-claim accountability analysis to `runs/readme-poc/<repo>/diagnostics/`.
The three-way (original/aspose.org/optimizer) comparison machinery remains queued behind the
E5 disposition work; Decision #104 reviews are its interim substitute.

## 9. Canary comparison results

- **note-python** (claim-accountability canary, 11 identical prior failures): 2 blocking claims
  → **1**; the accepted claim + one narrative_filler verdict are now permanently ratcheted
  (`claim-disposition-ratchet.json`, 2 entries). The residual claim is precisely identified:
  the source README's Quick Start **code block** — needs the reasoned-exclusion/
  obligation-replacement disposition (queued E5), not another retry.
- **tex-python**: policy `product_truth` block authored (all anchors source-verified) →
  exposed and fixed the cached-facts invalidation gap → recollection reached
  `product.capabilities: verified` → isolated source-build verification then failed on the
  **genuine upstream defect** (35/45 files unparseable at the committed revision). Terminal
  external blocker, correctly categorized after the classification fix.
- **3d/cells-python** (through the post-change re-verification): re-approved cleanly (3d with
  2 provider calls) — accepted repos survived the session's semantic changes.

## 10. Failure-signature backlog and dispositions

`failure-signature-ledger.md` (this directory): S1–S10 clusters + Q1–Q4 quality gaps + E1–E9
engineering queue + probe addendum. Landed this session: E1 (blocked-decision cache), E2
(ratchet), E3 (infra_external classification), E4 (tex policy — superseded by the upstream
verdict), E7 (three probes), E8 (S7 accounting + S9 log-dir). Queued: E5
(reasoned-exclusion/code-example dispositions — top priority), E6 (slides/page
protected-content triage; diagnostics now persist the needed analysis), E9 (Q1–Q3 quality
parity), fault-injection probe, `verified_against_source` soundness review (a quote from the
source README itself would corroborate circularly).

## 11. Cache/invalidation improvements

- Blocked-decision skip cache bound to the same dependency sources as the completed-bundle
  cache (never drifts on "what counts as a change"); `--retry-blocked` escape hatch; live
  reproduction counters.
- Claim-disposition ratchet: replay-through-corroboration, content-hash keyed.
- **New dependency captured:** facts manifests now record `product_truth_policy_hash`; the
  cached-facts gate refuses bundles collected under a different/absent policy block (found
  live: the tex policy change was silently ignored by the cache).
- Known remaining coarseness (backlogged): `supervisor/product_truth.py` sits in the
  fingerprinted verifier seam, so classification-only edits still rotate
  `local_verification_contract_hash` portfolio-wide (observed: one-time full re-verification
  this session).

## 12. Continuous-work scheduler proof

This session ran with zero idle waits: five parallel investigation lanes at start; every
canary/portfolio/pytest/probe wait was overlapped with landed engineering (16 code/evidence
commits, three governance artifacts, two live canaries, capability probes, drift detection).
The repo-level enforcement remains GOVERNANCE rule 24/Decision #103 (pre-existing).

## 13. Compaction-safe resume artifacts

`scripts/governance/mission_resume_capsule.py` derives
`plans/investigations/control/mission-resume-capsule.md` entirely from durable state (state-git
refs, portfolio summary, blocked-decision + ratchet records, HEAD) and `--check` fails when the
capsule is stale — the bootstrap command the mission required. Memory index updated to make
reading it the session-start ritual.

## 14. State-machine and plan changes

No parallel plan created. Work ran under the claimed L8-PORT-01 card via the local mission
store (evaluate/claim now possible locally at all — see 15). Decision #105 appended
(catalog + master.md index; validate_compact_authority clean at 105 decisions). The
freshness-service branch reconciliation demanded by `L8-FRESH-00` is executed: 25/27 commits
were already content-identical on main; the 2 unique commits were cherry-picked with recorded
dispositions (control-state files imported as *evidence*, never live control state);
`freshness-service/integration` and the coord worktree now hold nothing unique.

## 15. Test-command and process-control fixes

- Mission-state backend split closed: `--mission-action` under local_poc uses the local store —
  the exact defect that killed every bounded-verified canary ("durable mission state is
  unavailable", reproduced live pre-fix).
- Gate A driver: unique per-invocation log directories (the overwritten-evidence incident
  cannot recur).
- Partial-slice summaries now expose exact processed-slice provider/cache totals beside the
  honestly-UNKNOWN whole-registry figure.
- The imported TB-04 conftest ledger-reset + TA-01 `run_full_pytest` doctrine; the
  long-standing baseline failure
  `test_completed_local_poc_status_advances_only_with_valid_bundle` now **passes** via the
  imported fix. This session used unmasked exit codes throughout (file-redirect + `$?`).
- No `git stash` was used anywhere this session (temp read-only worktree instead).

## 16. GitHub-runner proof

Not executed this session (honest gap). Groundwork landed: the Note golden-workflow fixture +
`norecursedirs`/ruff excludes (the hosted-CI runner-environment unblockers), and the capsule
records the next resumable step. A clean-checkout local simulation remains the defined
integration gate before enabling any workflow.

## 17. Local portfolio status

At session start: complete=3/33 (plateau). This session's changes forced a one-time full
re-verification (verifier-seam fingerprint rotation); the relaunched pass re-approved
3d/cells (…and was still executing at report time — see the live summary in
`runs/readme-poc/portfolio-summary.json` and the newest
`runs/gate-a-local-poc-portfolio/<run-id>/`). Structural expectation once this pass completes:
every claim-blocked member persists a dependency-bound blocked decision + offline diagnostics;
the NEXT pass skips them with zero provider calls and reaches the 22 never-processed members;
html/tex/psd carry precise external-blocker records.

## 18. Candidate and evidence paths

- Candidates/bundles: `runs/readme-poc/<org>__<repo>/<revision>/` (+ `diagnostics/`,
  `blocked-decision.json`, `claim-disposition-ratchet.json` per repo).
- Session evidence: `plans/investigations/evidence/mission-recovery-2026-08-18/` (this
  directory), `.../llm-probe/qwen-output-limits-20260818.json`,
  `.../aspose-upstream-drift/drift-20260818-171524.json`,
  `.../freshness-service-registration/`, `logs/2026-08-18.md` (11th+ entries),
  `runs/mission-recovery-2026-08-18/` (canary + suite logs).

## 19. Remaining external blockers

1. **tex-python** — upstream sources syntactically invalid at pinned `2f4bfab` ("Release
   26.5", squashed history; 35/45 files fail `ast.parse` in the *committed* bytes). Clears on
   a new upstream revision (blocked-decision record auto-retries then).
2. **html-python** — upstream `pyproject.toml` declares nonexistent
   `build-backend = "setuptools.backends.legacy:build"`.
3. **psd-python/-net** — near-empty upstream content (2-line README); registry `mode:
   disabled`; product-owner working-condition decision required.
4. Production hosted proof + repo secrets (`LLM_BASE_URL`, `LLM_API_KEY`) — pre-existing,
   user-owned.

## 20. No target repository was modified

Confirmed. All writes were to this repository's working tree, `runs/**`, and the local state
store. No push, no PR, no remote mutation of any kind; the aspose.org checkout was read-only
throughout (its live edits came from a different session); the only target-repo interactions
were read-only clones/HEAD queries.
