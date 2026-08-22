PILOT VERIFICATION AND KNOWN BUG — read this before integrating

Status: added after the module was already committed and pushed (commits `79afee7bf5`,
`96132beeef`). This document, its companion script, and its captured output are a **separate**
commit on top of those two — see `COMMITS.txt` for the exact hash. Everything in
`REPORT.md`/`PACKET_CONTRACT.md`/`COVERAGE_INVARIANTS.md`/`INTEGRATION.md`/`KNOWN_LIMITATIONS.md`
remains accurate for what it describes (the module's contract, tested against a synthetic
fixture); this document adds what a real-production-data pilot rerun found that the synthetic
fixture could not catch, plus the exact fix. **Read this document fully before wiring the module
in — it changes the production-readiness verdict from "ready" to "ready after one narrow fix."**

## Why this document exists

The module's own test suite (26/26 passing, `tests/unit/test_bounded_review_packets.py`) proves
the module's contract against a synthetic fixture. A separate verification pass ran the module
against **real, already-committed production evidence** — the actual `aspose-3d-foss/
Aspose.3D-FOSS-for-Python` proof candidate and its real 227-claim accountability map — to check
whether the synthetic fixture's assumptions actually hold against real data. They mostly do. One
does not, and it is load-bearing: **the module currently produces zero factual review packets
and zero factual claim coverage against every real candidate it will ever see**, until the fix
below is applied.

This was found, diagnosed to its exact root cause, and confirmed fixable with a one-line change
— all using the module completely unmodified, by constructing inputs from real committed data
and a single targeted diagnostic simulation. Full methodology, evidence, and honest caveats
follow.

## Methodology

The module makes zero provider calls and is not integrated anywhere, so an actual pipeline rerun
cannot exercise it (there is nothing wired up to run). The verification therefore ran the module
directly, as a library, against:

- **Real candidate text**: `plans/investigations/evidence/qwen-section-engine-integration/
  candidate.md` (161,504 bytes, sha256 `ba04406d37c6fb51f061474983137e2e6c48bfd9373f5afd6a7cc99c00ccdcb6`
  in this repo's committed HEAD — evidence-directory `SHA256SUMS`/`REPORT.md` cite 163,049 bytes
  because they were captured against a dirty working tree in a different checkout; the committed
  git blob used here is the 161,504-byte version, confirmed self-consistent below).
- **Real document plan + claim accountability**: `plans/investigations/evidence/
  qwen-section-engine-integration/readme-document-plan.json` (1.47MB), validated as
  `ReadmeDocumentPlanV1`, with its embedded `claim_accountability` (227 real claims). Confirmed:
  `document_plan.candidate_sha256 == claim_accountability.candidate_sha256 ==
  sha256(candidate.md) == ba04406d...` — genuinely self-consistent, unmodified real data.
- **Facts**: no committed artifact in this repository reproduces the exact `facts_hash`
  (`f67966b0...`) bound into that real document plan — the original facts corpus behind this
  specific candidate was not preserved in committed evidence (two other real facts files exist
  for this repo, from different campaigns; neither hashes to `f67966b0...`, confirmed directly).
  This is used productively as a real fail-closed test case (see Finding 1), and separately, a
  facts corpus is derived from the real claim data itself for the happy-path tests (Finding 2+),
  clearly labeled as reconstructed, not the original.

Reproduce every number below by running `pilot/real_candidate_pilot.py` in this same directory
(pure-Python, read-only, needs only this repo's own venv on `PYTHONPATH`). Full captured output
from the exact run that produced these numbers is at `pilot/real_candidate_pilot_output.txt`.

## Finding 1 — fail-closed proof against a genuine real-world evidence gap

```
plan_bounded_review_packets(
    candidate_text=<real candidate.md>,
    document_plan=<real, unmodified>,
    claim_accountability=<real, unmodified>,
    product_facts=<closest real facts file that exists for this repo, unmodified>,
    ...
)
-> BoundedReviewInputMismatchError: document_plan.facts_hash does not match
   product_facts.canonical_hash()
```

Both sides of this mismatch are real, unmodified, committed data — the module correctly refused
to fabricate a plan rather than silently proceed on unverifiable facts. This is the fail-closed
contract (`REPORT.md` redesign point 4, `PACKET_CONTRACT.md`'s `BoundedReviewInputMismatchError`)
working exactly as designed, on a real condition, not a synthetic one.

## Finding 2 — THE BUG: zero factual coverage on real data

With a self-consistent (claim-derived) facts corpus bound in (see "How the facts corpus was
built" below), planning the real 161,504-byte candidate at `budget_chars=30000` produced:

| | value |
|---|---|
| factual packets | **0** |
| visitor packets | 21 |
| unpacketizable records | 0 |
| factual claim spans in coverage ledger | **0** |
| visitor spans in coverage ledger | 101 |

Zero factual packets against 227 real claims (115 of them genuinely fact-backed) is not a
tolerance issue — it is total absence of the module's core "retain complete candidate coverage"
promise for the factual facet, on real data, every time.

### Root cause, confirmed against the actual production source

`bounded_review_packets.py`'s `_valid_claims_and_gaps()` (the sole gate before any claim is
eligible for factual packetization, used by both `plan_bounded_review_packets()` and
`build_atomic_units()`):

```python
candidate_claims = [
    claim
    for claim in claim_accountability.claims
    if claim.stage == "candidate" and claim.survives_in_candidate
]
```

Confirmed directly against real data:

```
claim stage counts: {'candidate': 129, 'source': 98}
survives_in_candidate by stage: {'candidate': Counter({None: 129}), 'source': Counter({False: 62, True: 36})}
claims matching the filter (stage==candidate and survives_in_candidate): 0
```

This is not a data quirk of one evidence file. It is confirmed structural, universal behavior of
the real production builder — `src/readme_agent/readme/claim_accountability.py`, the
`stage="candidate"` construction call:

```python
expected, accountable, rationale = expected_disposition(
    stage="candidate",
    origin=origin,
    current=claim.disposition,
    accepted_fact_ids=fact_ids,
    configured_standard_ids=candidate_standard_ids,
    survives_in_candidate=None,      # <-- hardcoded, unconditional, for every candidate-stage claim
    ...
)
```

`survives_in_candidate` is only ever populated (`True`/`False`) for `stage="source"` claims — it
answers "did this *source* claim survive into the candidate," which is semantically inapplicable
to a claim that is already, by definition, a candidate-stage claim. The packetizer's filter
requires a signal that production code never sets for the population it's filtering. Every real
candidate, from every repository this pipeline has ever run against, will hit this — it is not
specific to the Aspose.3D candidate used here.

### Why the module's own 26-test suite did not catch this

`tests/unit/test_bounded_review_packets.py`'s claim-fixture builder:

```python
claims.append(
    ReadmeClaimAccountabilityV1(
        claim_id=spec.claim_id,
        stage="candidate",
        ...
        survives_in_candidate=True,      # <-- hardcoded True regardless of stage
        currently_accountable=True,
        ...
    )
)
```

The synthetic fixture sets `survives_in_candidate=True` on every claim, all of which are
`stage="candidate"`. That combination — `stage="candidate"` with `survives_in_candidate=True` —
is exactly the shape the module's filter expects, and exactly the shape that (per the real
builder source above) **never occurs in production**. Tests green, real feature dark. This is
recorded here not to assign blame — it is the predictable, structural failure mode of testing
exclusively against a hand-built fixture for a filter condition whose real-world population
was never independently checked. It is exactly the kind of gap a real-data pilot exists to
catch, and exactly why this document says "prove it," not "trust the test suite," before
integration.

## Finding 3 — the fix is narrow; everything downstream is already sound

A diagnostic (data-only — the module's source was **not** modified for this check) copied the
real claim records with `survives_in_candidate` overridden to equal `currently_accountable` for
every `stage="candidate"` claim, then re-ran the unmodified module:

```
with the filter's precondition satisfied -- factual packets: 35
visitor packets: 21
unpacketizable: 1
factual packet sizes: min=11 max=15814, all<=budget: True
distinct claim_ids covered across factual packets: 128
```

128 of 129 real candidate-stage claims covered (the 129th is presumably a genuine unresolved-
fact-reference case, correctly routed to `unpacketizable` rather than silently dropped — matches
the module's own designed behavior, not a new problem). All factual packets within budget.
Determinism reran byte-identical (`plan1.canonical_hash() == plan2.canonical_hash()` both equal
`9b229e1547b9eb2c8ae8e161c27ce814f829b6690a8e8f1124847193611d5d94`). A real (non-vacuous —
the first attempt against the unfixed `plan1` was vacuous, 0 invalidated only because there were
0 packets to begin with) cache-invalidation check against the corrected simulation: changing one
fact's value invalidated 32 of 35 factual packets while all 21 visitor packets stayed
byte-identical (`visitor packet set unchanged (before == after): True`). The wide (32/35) blast
radius is a real, honest data point, not a bug in the invalidation logic — the changed fact
(`api.public_surface:python-exports`) is cited by claims spread across most sections of this
particular candidate, so a broad invalidation footprint is the structurally correct outcome for
*that specific fact*, not evidence of an over-eager invalidation rule.

**Conclusion: this is a one-line predicate defect, not an architectural problem.** Packet
building, budget enforcement, coverage-ledger construction, determinism, and cache invalidation
all check out correctly once the filter receives data in the shape it actually needs.

## The exact fix

**File:** `src/readme_agent/specialists/bounded_review_packets.py`
**Function:** `_valid_claims_and_gaps` (around line 1192 as of commit `79afee7bf5`)

Current:

```python
    candidate_claims = [
        claim
        for claim in claim_accountability.claims
        if claim.stage == "candidate" and claim.survives_in_candidate
    ]
```

Proposed:

```python
    candidate_claims = [
        claim
        for claim in claim_accountability.claims
        if claim.stage == "candidate" and claim.currently_accountable
    ]
```

`currently_accountable` is confirmed populated `True` for all 129 real candidate-stage claims in
the evidence used here (all `current_disposition == "preserve"`), and is the field the real
builder actually sets meaningfully for this stage — unlike `survives_in_candidate`, which the
real builder unconditionally sets to `None` for `stage == "candidate"` (see Finding 2). This is
the only line that needs to change in `bounded_review_packets.py` for both
`plan_bounded_review_packets()` and `build_atomic_units()` (both funnel through
`_valid_claims_and_gaps()`), per the diagnostic in Finding 3.

**Before applying:** confirm `currently_accountable`'s exact semantics against
`src/readme_agent/readme/claim_accountability_models.py` and `expected_disposition()` in
`claim_accountability.py` directly — this document's confidence in `currently_accountable` as
the correct replacement signal is high (confirmed against real data and real builder source, not
guessed), but it was not exhaustively cross-checked against every disposition-lifecycle edge
case (e.g. a claim that is `currently_accountable=True` today but whose disposition is
mid-transition) before writing this addendum. Whoever applies the fix should have that model's
full field semantics in view, not just this document's summary.

## Required companion test fix

`tests/unit/test_bounded_review_packets.py`'s `_build_claim_accountability()` fixture builder
(around line 157) should be extended — not merely have its existing `survives_in_candidate=True`
line changed, since that would keep hiding this exact gap. Recommended: add one new test using a
claim shaped like real production data —

```python
ReadmeClaimAccountabilityV1(
    ...,
    stage="candidate",
    survives_in_candidate=None,   # the real, production-accurate value for this stage
    currently_accountable=True,   # the real, production-accurate selection signal
    ...,
)
```

— and assert it **is** selected into a factual packet after the fix (and, run against the
*current* code before the fix, that it is not — a regression test in the literal sense, proving
the exact gap this document found rather than merely asserting the fixed behavior in isolation).
Suggested name: `test_candidate_stage_claim_is_selected_via_currently_accountable_not_survives_in_candidate`.
The existing 26 tests are expected to keep passing unchanged after the fix (their fixture already
sets `currently_accountable=True` alongside its incidental `survives_in_candidate=True`), so this
is additive, not a rewrite.

## Updated production-readiness verdict

Visitor-side packetization: **production-ready as committed**, real-data verified (21 packets,
101 covered spans, 28 correctly excluded/justified API-inventory spans, deterministic, budget-
compliant, cache-correctly-isolated from fact changes).

Factual-side packetization: **not production-ready as committed** — will silently produce zero
factual coverage against every real candidate until the one-line fix above is applied and the
companion regression test is added. Everything downstream of the fix point is already verified
sound (Finding 3), so this is scoped as a small, low-risk, well-understood follow-up commit, not
a redesign.

## What was and was not changed by this verification pass

Nothing in `src/readme_agent/specialists/bounded_review_packets.py` or
`tests/unit/test_bounded_review_packets.py` was modified to produce this document — the bug and
its fix were diagnosed with the module fully unmodified, by constructing/adapting *input data*
only (real claim records copied with one field overridden, entirely outside the module). The fix
proposed above has **not** been applied to the branch; this document, its companion script
(`pilot/real_candidate_pilot.py`), and its captured output (`pilot/real_candidate_pilot_output.txt`)
are the only new files this verification pass added, all under `module_handoffs/`. No plan,
graph, state machine, existing integration, product repository, or `main` file was touched.
