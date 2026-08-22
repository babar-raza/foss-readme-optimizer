# Known limitations

Written to be read before trusting this module in production, not after something goes wrong.

## Recall is bounded and unproven beyond the tested/corpus cases

Contradictions expressed as pure narrative prose with no shared code symbol and no shared
discriminator token (e.g. "Every operation works out of the box" vs. "Several operations do not
function") will not be caught by Tier B/C. This is a structural limit of pattern-based detection
without an LLM, not an oversight — see `REPORT.md`'s design section for why the tiering exists
instead of trying to force one heuristic to be both high-precision and high-recall.

## Precision-over-recall is a deliberate choice on the blocking path

`contradiction_capability_phrase` without a shared discriminator is `blocking=False` by design. If
the integration policy only acts on blocking findings, those weaker-evidence matches are
effectively informational-only unless routed to a review queue. This trades missed defects for
avoided false alarms — the wrong tradeoff for some deployments, the right one for a gate meant to
stay trusted over many runs. Reconsider if real-world usage shows the advisory tier is being
ignored entirely rather than reviewed.

## Sentence-boundary heuristic, not real sentence segmentation

Positive/negative cue detection operates per markdown *line* (via `presentation_lint_text
.visible_lines`), not per grammatical sentence. A multi-sentence bullet or paragraph where the
polarity cue and the capability phrase land in different sentences on the same line will be
compared as one unit; a capability claim that wraps across two lines will be split and may be
missed entirely. This matches the surrounding codebase's own convention (e.g.
`presentation_lint_public_contract.py`'s `_CAPABILITY_ROW` regex is also line-scoped) but is a real
recall limit worth knowing about.

## `claim_accountability` parameter is accepted but not yet consulted

`evaluate_public_candidate_quality`'s `claim_accountability: ReadmeClaimAccountabilityMapV1 | None`
argument is plumbed through the signature and into every check function's parameter list, but no
check currently reads it — only `facts` is consulted by `claim_grounding_negative_fact`. It's
forward-compatible scaffolding (the model already has the right shape for a future check that cross-
references `ReadmeClaimAccountabilityV1.expected_disposition`/`currently_accountable` against
prose), not a silently-broken feature — but don't assume passing it changes behavior today.

## Structural-outlier thresholds are starting heuristics, not calibrated

`structural_size_outlier` (>4x or <0.25x the sibling median word count) and
`structural_detail_density` (>4x the sibling median identifier density) are reasonable first-pass
constants, not calibrated against a labeled corpus of known-good vs. known-pathological candidates
— none exists yet in this repo. Expect some false "outlier" flags on legitimately short sections
(e.g. a one-line Installation section is completely normal and still may get flagged relative to a
verbose sibling) — this is exactly why these findings are always advisory, never blocking.

## Determinism guarantees are about identical bytes, not semantic equivalence

Two differently-phrased-but-equally-correct (or equally-defective) candidates are not guaranteed
the same verdict on the prose-only tiers (B/C) — if a regenerated candidate rewords a contradiction
using cue words outside `_POSITIVE_CUE`/`_NEGATIVE_CUE`, that rerun's contradiction goes undetected
even though a previous rerun's phrasing was caught. Only Tier A (structured-evidence-anchored) is
designed to be stable across such rewording, because it's keyed on `fact_id`/`verification_state`
rather than on the candidate's specific wording. Treat a single Tier A finding as high-confidence;
treat an isolated Tier C finding that disappears on the next rerun as weaker signal, not proof the
underlying issue was fixed.

## Cue-pattern lists are hand-authored, not exhaustively validated against real-world diversity

`_POSITIVE_CUE`/`_NEGATIVE_CUE`/`_SCOPE_QUALIFIER`/`_EXCEPTION_CLAUSE`/`_CONDITIONAL_MARKER` were
grown against the required test cases from the brief plus a manual precision dry-run against three
real committed candidates (see `WORKLOG.md`'s implementation log for the two false positives found
and fixed during that dry-run). They are not proven against the full diversity of real README
phrasing this repo will eventually generate. Recommended practice going forward: grow a golden
corpus fixture (this module doesn't ship one — see below) the same way
`tests/fixtures/presentation_defects/corpus.json` grew, adding a case whenever a real miss or false
positive is found, rather than hand-tuning regexes reactively without a regression anchor.

## No golden-corpus fixture file shipped

The plan called for `tests/fixtures/public_candidate_quality/corpus.json` as a growable regression
anchor. In practice, every required test case fit cleanly as a small inline markdown fixture
(matching the brief's anonymized-generic-fixture requirement), so no fixture file was strictly
necessary to reach green — `tests/fixtures/public_candidate_quality/` was not created. If Codex (or
a future contributor) starts accumulating real-candidate-derived cases the way
`presentation_defects/corpus.json` did, introducing that file at that point is the right move; it
wasn't invented preemptively here.

## Single-file module (deliberate exception to AGENTS.md's "no monoliths")

`public_candidate_quality.py` is ~850 lines, well past the ~300-line guidance in AGENTS.md/
`GOVERNANCE.md`, because this lane's explicit write-allowlist restricted production code to exactly
that one path. It's internally organized as a check registry to make a future split mechanical —
see `INTEGRATION.md`'s recommended follow-up.

## Environmental: Windows MAX_PATH inside this isolation lane (not a module defect)

Running `tests/unit/test_readme_presentation_lint.py` from inside this lane's deeply-nested working
tree (`runs/parallel_staging/public-quality-gates/<64-char-sha>/repo/...`) fails 13 of 48 tests with
`FileNotFoundError` on long evidence paths, because the resolved absolute path exceeds Windows'
260-character `MAX_PATH` and this machine has `LongPathsEnabled=0`. Confirmed via a control run
against `main`'s normal (short-path) checkout: all 48 pass. This is purely an artifact of the lane's
path depth on this machine, not a regression caused by this module — but if another Windows
machine without long-path support ever runs tests from a similarly deep working directory, expect
the same artifact on unrelated pre-existing tests, not just this module's own suite.
