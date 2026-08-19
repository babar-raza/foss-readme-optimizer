# Why "did my fix work" kept requiring expensive live passes — root cause and a durable design

Written 2026-08-19, in direct response to a product-owner critique of this session's own working
pattern: seven full `--retry-blocked` portfolio passes (10-25 minutes of real wall-clock time
each, mostly sequential) were run to verify a chain of five related code fixes. The question asked
was not "how should the agent pace its own tool calls" — that was explicitly rejected as
insufficient — but *why the system requires expensive live verification for changes that should be
cheaply provable*, treated as a production engineering problem.

This document separates symptom, immediate mechanical cause, and structural root cause; states
what should be preserved vs. redesigned; and proposes a durable fix with concrete implementation
direction, validation steps, and honestly-stated limits. It does not exaggerate confidence where
the evidence is genuinely incomplete — those places are marked explicitly.

## 1. Symptom

This session made five related fixes in one causal chain (S12 composition-authority defect →
gate-2 factuality wiring → gate-3 independent-verification wiring → `idea_candidate.py` wiring).
After nearly every individual fix, a live `--retry-blocked` portfolio pass was run to confirm it
worked — seven total, one of which produced zero new information (a single-repo canary silently
replayed a stale cached decision) and one of which produced an ambiguous result (a transient
GitHub clone failure indistinguishable at a glance from a real regression, requiring separate
investigation to rule out). The cumulative wall-clock cost was a large fraction of the session.

## 2. Immediate mechanical cause

`--bounded-verified-canary` (the single-repo check) has no way to bypass the pipeline's own
no-unnecessary-work convergence for a repository whose last recorded outcome was `BLOCKED` but
whose *tracked* dependency fingerprints are unchanged — confirmed directly: a canary run for
cells-python after a real code fix produced an empty log and replayed a decision recorded 90
minutes earlier (`recorded_at` in the replayed diagnostics matched the earlier run exactly).

The only bypass, `--retry-blocked`, is documented and enforced as portfolio-only
(`commands_supervision.py`, gated on `args.retry_blocked` inside the `--registry` loop only;
`--repo`/`--registry` are mutually exclusive in the CLI's own argument group). So the only lever
available to force a fresh check of *one* repository after a code change is a full-registry pass
touching all 33 repositories, the large majority irrelevant to the fix being verified, each
potentially doing real git/Docker/LLM work.

This is a real constraint, not a workaround failure — but it explains why every "did it work"
question this session turned into 10-20 minutes of unavoidable wall clock, not why the question
had to be asked so often in the first place. That is the deeper problem, addressed below.

## 3. Root cause, layer 1: the invalidation model has real, evidenced coverage gaps

The pipeline tracks four separate fingerprint mechanisms that gate whether a cached `BLOCKED`
decision gets reused or the repository gets re-checked. All four were read directly this session,
not inferred:

- **`local_verification_contract_hash`** (`facts/verification_contract.py::_COMMON_FILES`) hashes
  a fixed list of files under `facts/` (acquisition, isolated execution, product-truth) plus one
  file outside it (`../supervisor/product_truth.py`). It does not include
  `readme/composition_lineage.py`, `specialists/readme_factuality.py`,
  `verification/checks.py`, or `readme/claim_accountability_llm_disposition.py`.
- **`control_plane_fingerprint`** (`supervisor/convergence.py::compute_control_plane_fingerprint`)
  hashes every registered capability's *declared version string* (in-memory metadata, explicitly
  "no I/O" per its own docstring), shared prompt content, the validation ruleset version constant,
  and policy file content — never the actual capability/verification-gate source bytes. A code
  change with no accompanying manual version bump is invisible to this fingerprint by design.
- **`candidate_stage_dependency_key`** (`supervisor/stage_dependencies.py::
  _CANDIDATE_DEPENDENCY_GROUPS`) is the most granular real "component model": a hand-maintained
  dict of ~13 semantic groups, each an explicit tuple of file paths. Read in full (197 lines):
  `readme/composition_lineage.py`, `specialists/readme_factuality.py`,
  `verification/checks.py`, `readme/claim_accountability_llm_disposition.py`,
  `readme/claim_accountability_api_index.py`, `readme/source_claim_api_detail_binding.py`, and
  `readme/document_plan_finalizer.py` are **absent from every group** — confirmed by grep across
  the complete file returning no matches for any of them.
- **`reviewer_standard_hash`** (`llm/verification_prompts.py`) hashes prompt content and a small
  set of manually-declared contract-version string constants for the review/reducer layer — the
  same "manually declared, not derived" pattern, and again not the disposition/verification code.

**None of the four tracked fingerprints cover the five files this session's fixes actually
touched.** This is not a one-off oversight in one file — it is the predictable failure mode of the
model itself: every one of these mechanisms is a hand-curated allowlist of "things believed to
matter," never a derived, exhaustive answer to "what can actually affect the output." A
hand-curated list is correct only until someone adds or changes a file and does not update every
list that should include it. Corroborating evidence that this already happens routinely, not just
to this session's changes: several files landed by *other* lanes earlier the same day (e.g.
`presentation/verified_template_sections.py`, touched by today's own Dependencies-heading work) are
also absent from `_CANDIDATE_DEPENDENCY_GROUPS`.

A related, already-known symptom of the same root cause runs the opposite direction: a backlog
entry (`plans/backlog-post-poc.md`, GOV-014, 2026-08-18) documents that editing
`supervisor/product_truth.py` — inside `_COMMON_FILES` — rotates `local_verification_contract_hash`
for *every* ecosystem on any edit, including purely classificatory changes that alter no fact
value, over-invalidating every cached candidate including already-accepted ones. Under-coverage
(this session's problem) and over-coverage (the backlog's problem) are two symptoms of the same
underlying defect: file-list membership is manually maintained at the wrong granularity in both
directions, because it is maintained by hand at all.

## 4. Root cause, layer 2: irreducible model nondeterminism at the composition step

Separately and independently, this repository's own probe evidence (2026-08-18,
`plans/investigations/evidence/llm-probe/`) already established that the live LLM gateway's
forced-tool-call **arguments are not deterministic at temperature 0** — five trials against an
unchanged prompt returned five distinct payloads — even though freeform prose from the same
gateway *is* byte-deterministic. This means any live pass that re-invokes real LLM composition
(as opposed to replaying an already-corroborated, ratcheted verdict) can legitimately produce a
different candidate or claim set than the previous pass, with zero code or data change involved.

This is not a defect to eliminate; it is a property of the provider that must be *managed*. The
already-built, correct architectural answer to it is the claim-disposition ratchet
(`readme/claim_accountability_llm_disposition.py`): persist a once-corroborated LLM verdict,
content-addressed by claim hash, and replay it deterministically with zero further provider calls.
This session's entire "two-gate/three-gate" bug was, structurally, exactly this protection being
wired at the first gate that produces a disposition and silently *not* wired into every downstream
gate that independently re-derives the same judgment — the mechanism that already solves
nondeterminism existed, it just was not reached everywhere it needed to be.

## 5. Two distinct problems — do not conflate them

- **(a) Invalidation-model gaps** (Section 3) force full, portfolio-wide live passes to prove
  *anything* changed, even when the actual proof is cheap, local, and fully deterministic. This is
  a solvable engineering defect.
- **(b) Composition-step nondeterminism** (Section 4) means that even a fully-corrected,
  fully-covered invalidation model still cannot guarantee an identical rerun reproduces an
  identical result, because part of the system is not deterministic by construction. This must be
  *contained* (via the ratchet pattern, applied everywhere it is needed), not "fixed" away.

Every fix this session addressed (a) — it never touched, and could not have touched, (b). Any
proposal that only makes rechecking cheaper without also confirming ratchet coverage is complete
would still leave real, provider-driven inconsistency across reruns unaddressed.

## 6. What should be preserved

- **The disposition ratchet itself.** Content-addressed, deterministic replay of a corroborated
  LLM verdict, zero provider calls on reuse. The fix this session needed was not to change this
  mechanism — it was to make sure every gate that depends on the same judgment actually receives
  it.
- **The multi-gate independent-verification architecture** (gate 1 build, gate 2 factuality, gate
  3 independent verify — "author != verifier"). Defense in depth is a real safety property here,
  not incidental complexity; collapsing it into one mega-check to reduce wiring surface would trade
  a real correctness guarantee for convenience.
- **`AGENTS.md` rule 15's prohibition on ad hoc, direct-import verification scripts.** The concern
  behind it — never let a shadow verification path silently diverge from real production
  behavior — is correct and must survive any redesign. The right fix is to make a *fast* path
  sanctioned and governed (Section 7.2), not to loosen the rule that currently, correctly, blocks
  workarounds.
- **The blocked-decision skip-cache as a portfolio-wide throughput optimization** (avoid redoing
  already-known-blocked repositories on every delivery pass). This is orthogonal to the
  single-repo developer-verification problem and should not be weakened to solve it.

## 7. What must be redesigned

### 7.1 Replace hand-curated dependency file lists with a derived, import-graph-based hash

Instead of `_CANDIDATE_DEPENDENCY_GROUPS` (and the sibling `_COMMON_FILES` lists) being maintained
by hand, compute the relevant hash by statically walking the real first-party import graph from
each pipeline entry point (`build_readme_document_candidate`, `evaluate_candidate_factuality`,
`independently_verify_readme_candidate`, `prepare_idea_fidelity_candidate`, and any sibling
entry points) and hashing every transitively-imported `src/readme_agent/**` module's content,
sorted by path. This structurally eliminates the "forgot to register a new file" failure mode
instead of requiring perpetual manual vigilance that has already visibly lapsed at least twice
(this session's five files, and the backlog's own documented over-invalidation case).

**Implementation direction**: a static AST-based import walker (safer than actually importing —
no side effects, no need to construct real inputs) rooted at the named entry functions, filtered
to first-party modules, producing the same `(path, content_sha256)` shape the current manifest
already uses so it is a drop-in replacement, not a parallel system. The existing hand-curated
groups can remain as human-readable documentation of *intent* (`semantic_scope`,
`earliest_affected_stage` labels are genuinely useful for people and for stage-targeted
invalidation) but should no longer be the sole source of the hash used to decide reuse.

### 7.2 A sanctioned, first-class offline-replay capability

Register a new capability, through the same registry/manifest pattern every other capability
already uses, that takes a persisted evidence bundle for one repository (its facts, candidate, and
plan — already captured on disk thanks to this session's own diagnostics-persistence fix) and
re-runs only the genuinely deterministic stages — composition-ledger build/validate,
claim-accountability check, disposition-ratchet replay — entirely offline: no LLM composition
call, no git clone, no Docker isolated execution. This turns "does my code fix this specific,
already-documented failure" from a 10-20 minute live pass into a sub-second local check.

This directly satisfies, rather than works around, `AGENTS.md` rule 15's actual concern: it is a
real, registered, tested, reviewable capability that goes through the same state/evidence system
as everything else, with its output explicitly labeled non-portfolio-eligible (so it can never be
mistaken for real acceptance evidence, matching the existing rule that "a candidate produced
outside the tracked supervise lane cannot count as portfolio progress").

**Required regression control, not optional**: a meta-test proving the offline replay produces an
identical verdict to a live run against the same frozen bundle, run repeatedly (CI or at Gate-A
boundaries), not verified once and assumed stable — see Section 9's risk note.

### 7.3 A scoped, safe cache-bypass for single-repo developer verification

Add a narrow, explicitly-scoped option — e.g. `--repo X --bounded-verified-canary
--bypass-blocked-decision-cache` — that skips only the "reuse the cached blocked decision"
shortcut for that one repository, touching no allow-list, mode, or push-blocking gate. This
directly removes the reason every single-repo developer-verification question this session had to
become a 33-repository pass, independent of whether 7.1/7.2 land.

**Required safety test**: prove this flag cannot be used to bypass any write-permission or mode
check — it must affect only whether a `BLOCKED` decision is replayed vs. re-derived, nothing else.

### 7.4 Systematic capture of live-diagnosed failures as frozen fixtures

Extend the diagnostics-persistence mechanism (already landed this session) so that a live `BLOCKED`
outcome automatically stages a fixture directory (the real facts, candidate, and error already
captured) under a clearly-named location, ready to be wired into a parametrized regression test
with minimal manual transcription. This closes the exact gap that made this session's *first* S12
fix incomplete: the hand-typed regression test used a simplified candidate shape because the real
one was not directly in front of the person writing it, and a heading-only reproduction happened to
pass while the real, live segment shape (heading plus an adjacent fixed sentence) still failed.

## 8. Open questions — not resolved by this document

- Whether `specialist_selection`, `repair_capability_selection`, or the independent
  `blind_quality`/`trusted_readme_fidelity_review` LLM calls have their own ratchet-equivalent
  protection against temp-0 nondeterminism was not checked. If they do not, they remain a live,
  unaddressed source of inconsistency across reruns, structurally identical to the "two/three-gate"
  bug this session found and fixed for the disposition path specifically. This needs its own
  audit before anyone claims the nondeterminism problem (Section 4) is contained everywhere it
  needs to be.
- Whether the real import graph from the five relevant entry points contains any *dynamic* imports
  (`importlib.import_module` with a runtime-computed name) was not checked. A static AST walker
  (Section 7.1) cannot see through those; if any exist on the hot path, the derived hash would
  need either a supplementary dynamic-import allowlist (smaller, more stable, easier to keep
  correct than today's full file lists) or a different mechanism for that specific case.

## 9. Tradeoffs, risks, and honest limits

- This is genuinely multi-day engineering work across four separate changes, not a quick patch —
  it should be scoped and staffed as such, not squeezed into "the next fix."
- **7.1's biggest risk**: under-coverage if the real code path uses a dynamic import an AST walker
  cannot see (see Section 8) — a known, stated limit, not a claim of completeness.
- **7.2's biggest risk**: silent drift between the offline-replay path and real live behavior if
  its own agreement meta-test is not actually kept running over time. A fast path that *looks*
  authoritative but has quietly diverged from production truth is more dangerous than having no
  fast path at all — this requires ongoing owner discipline, not a one-time implementation.
- **Section 4's nondeterminism is not eliminated by any of this** — only the specific decisions
  that reach a ratchet are protected from it. Any LLM call without one (Section 8) remains a real
  source of inconsistency, independent of how good the invalidation model becomes.
- None of this removes the need for occasional real live passes — composition itself can only be
  verified by actually running it end to end. The goal is to shrink *when* a live pass is required
  (to "the composition/prompt layer itself changed") rather than to eliminate live verification.

## 10. Recommended sequencing, if this is approved for implementation

1. **7.3 first** (scoped cache-bypass) — smallest change, immediately shrinks the *size* of every
   future single-repo verification even before the deeper fixes land.
2. **7.1 next** (import-graph hash) — highest-leverage structural fix; alone, it would have
   prevented most of this session's forced full-portfolio waits, since the affected code would
   have auto-invalidated its own cached decisions the moment it changed.
3. **7.2** (offline replay) as a separate, larger effort — highest total time savings, but the
   most implementation work and the most ongoing-maintenance risk (Section 9).
4. **7.4** (fixture capture) as ongoing hygiene alongside whatever live bug gets diagnosed next.
5. **The Section 8 audit** (ratchet coverage for the other LLM call sites) before declaring the
   nondeterminism half of this problem contained anywhere beyond the disposition path.
