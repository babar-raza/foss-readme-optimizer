# Integration guidance for Codex

## Exact commit(s) to cherry-pick

Two commits on `claude/standalone-public-quality-gates-e731ea56ebb5`, based on `main`
@ `e731ea56ebb50c6002d7fb5459e02d8b32f0cc71`:

1. `85a5bbd9` — `feat(validation): add standalone public-candidate quality gate`
   (the only commit that needs cherry-picking to get the module + tests; adds exactly
   `src/readme_agent/validation/public_candidate_quality.py` and
   `tests/unit/test_public_candidate_quality.py`, nothing else).
2. A final handoff-docs commit (see `COMMITS.txt` for its hash) adding
   `module_handoffs/public-quality-gates/e731ea56ebb5/**` — informational only, not meant to be
   cherry-picked into `main`; keep it on this branch or discard it, your call.

Cherry-picking commit 1 alone onto current `main` should apply cleanly as long as
`readme/presentation_lint.py`, `readme/capability_semantics.py`, `readme/claim_accountability_models.py`,
`facts/schema_v2.py`, and `readme/document_structure.py` haven't changed their public signatures
since `e731ea56ebb5` (see "Interface drift" below for what to re-check if they have).

## Required existing inputs

- `candidate_text: str` — the only required argument.
- `facts: ProductFactsV2 | None` (`readme_agent.facts.schema_v2`) — optional; without it,
  `claim_grounding_negative_fact` is skipped entirely (absent from `checks_run`).
- `claim_accountability: ReadmeClaimAccountabilityMapV1 | None`
  (`readme_agent.readme.claim_accountability_models`) — accepted but **not yet read** by any check
  body (see `KNOWN_LIMITATIONS.md`). Pass it if you have it; it's forward-compatible plumbing, not
  currently load-bearing.

## Proposed call site (not made — Codex's call)

The natural integration point is wherever a candidate's final text and its `ProductFactsV2` are
both already in scope right before a candidate is accepted/promoted — e.g. alongside the existing
`lint_readme_presentation()` call in the presentation-lint pass, or as an additional gate in
`supervisor/portfolio_proof_engine/rubric.py`'s evidence-collection step (it already gathers
several typed evidence artifacts per criterion; this report's `findings`/`counts` would fit as one
more `evidence_artifact`/`evidence_key` pair, likely informing a new criterion or an existing
`deterministic_check`-type criterion rather than a hard disqualifier by itself). This module makes
no call-site edit and expresses no opinion on which is correct — it only produces the evidence.

## Expected blocking/advisory mapping

Use `PublicQualityFindingV1.blocking`, not `severity` alone, to decide gate behavior — see
`INTERFACE.md`'s mapping table for exactly which `(check_id, confidence)` combinations set it.
Two policy notes:
- `structural_quality` findings are **always** `blocking=False` by construction — this module
  deliberately never treats section-size/density outliers as hard disqualifiers, per the brief's
  "report this separately from hard factual disqualifiers" requirement. If you want structural
  outliers to ever block, that's a policy decision to make at the integration layer, not something
  to change in this module without also updating `KNOWN_LIMITATIONS.md`'s stated design intent.
- `contradiction_capability_phrase` findings without a shared discriminator token are `blocking=False`
  by design (precision-over-recall on the blocking path — see `REPORT.md`). If your acceptance
  policy currently only consults blocking findings, these weaker-evidence matches are effectively
  informational unless you also route advisory findings to a review queue.

## Tests that must run after integration

```
pytest -q tests/unit/test_public_candidate_quality.py
pytest -q tests/unit/test_readme_presentation_lint.py    # the reused dependency's own suite
ruff check src/readme_agent/validation/public_candidate_quality.py tests/unit/test_public_candidate_quality.py
ruff format --check src/readme_agent/validation/public_candidate_quality.py tests/unit/test_public_candidate_quality.py
mypy src/readme_agent/validation/public_candidate_quality.py
```
If you add a call site, also re-run whatever test currently exercises that call site's existing
behavior, since this module is pure and side-effect-free but its *caller* now has a new dependency.

## Rollback procedure

The module is entirely unregistered and standalone — no `__init__.py` export, no call site, no
config entry. Rollback is: `git revert 85a5bbd9` (or simply delete the two files) — nothing else in
the tree references them, so there is no cascading change to undo.

## Recommended follow-up (not done here, out of this lane's scope)

The module is a single file by this lane's explicit charter (a deliberate, documented exception to
AGENTS.md's "no monoliths" ~300-line guidance). It's internally organized as a registry tuple
(`_CHECKS`) exactly like `validation/registry.py`'s `RULES` tuple, so splitting it into
`validation/public_candidate_quality/` (one file per check, mirroring `validation/rules/`) once the
isolation constraint no longer applies should be mechanical — each check function is already a
self-contained `(text, headings, facts, claim_accountability) -> list[PublicQualityFindingV1]`
callable with no cross-check-function state.

## Interface drift noticed after the pinned base

None. `git ls-remote origin refs/heads/main` still resolves to `e731ea56ebb50c6002d7fb5459e02d8b32f0cc71`
as of the final verification pass (see `BASE_AND_DRIFT.json`) — this branch is current with `main`,
not behind it.
