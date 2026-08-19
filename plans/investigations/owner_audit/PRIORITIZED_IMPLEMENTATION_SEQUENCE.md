# Prioritized implementation sequence

This sequence governs future optimizer implementation prompts. It is intentionally built from the
existing fact, composition, review, validation, cache, and scheduler machinery. Each gate is one
atomic commit unless a live repository change proves it must be split.

Do not start a new writer while the current VS Code fast-path writer is active. Read-only audits may
continue in parallel. At every handoff, re-read GitHub `main`, inspect intervening commits, and
remove work already closed rather than replaying an old prompt.

## E0 — Ingest the reviewed owner evidence

At the next clean writer checkpoint, copy the final checksum-verified bundle into one governed,
non-runtime evidence location such as
`plans/investigations/evidence/readme-quality-owner-audit-2026-08-19/`, validate every checksum,
and commit it as one evidence-only commit. Do not copy stale standalone execution prompts as
authority; retain them only when clearly labeled supporting history. This gives every later gate a
stable GitHub citation and prevents repeated rediscovery. Reconcile against the actual latest main
before committing, and regenerate only governance artifacts that repository policy explicitly
requires.

## K1 — Item-level evidence and polarity

**Inputs:** imported selected claims; `evidence.file` and `evidence.source_file`; sealed repository
tree; limitation/stub/raise evidence.  
**Change:** preserve verification/corroboration per selected item; recognize both evidence keys;
replace file-existence support with symbol/content/polarity resolution; a mixed aggregate must be
split or remain non-authorizing.  
**Outputs:** individually authorized item records and explicit conflict/rejection dispositions.  
**Required red/green fixtures:** 3D FBX, Barcode PDF, synthetic one-good plus two-unverified field,
and public/internal COLLADA distinction.  
**Stop condition:** any unverified/conflicted item can still reach accepted composition through a
field-level verified ID.

## K2 — Structured API normalization

**Inputs:** actual 3D, Note, and Barcode API-surface schema variants plus repository export/public
reachability evidence.  
**Change:** normalize dictionary/list shapes and ecosystem-specific visibility/reachability into the
existing canonical fact representation; suppress API claims as “covered” only after a non-empty,
usable structured API fact is produced. Keep symbol presence distinct from implemented capability;
an exported method whose body raises `NotImplementedError` may appear as a limitation or API
signature, but must not receive positive capability prose.  
**Outputs:** stable class/member counts and a Qwen/template-safe public surface.  
**Required red/green fixture:** public `NurbsSurface.to_mesh` remains discoverable as a signature,
but the renderer does not say it supports mesh conversion while its body is a stub.  
**Stop condition:** claims disappear as covered while the corresponding public-surface fact is
empty.

## K3 — Post-render knowledge accountability

**Inputs:** knowledge-selection dispositions, final document plan, candidate-content provenance,
claim map, candidate bytes/hash.  
**Change:** keep the current pre-render artifact as provisional if useful, then rewrite one final
knowledge-application artifact after rendering. Join both operation fact IDs and verified-template
candidate provenance.  
**Outputs:** every selected item is `rendered`, `preserved_equivalent`, `superseded`, or
`omitted_with_verified_reason`, with exact output spans when visible.  
**Acceptance:** missing or invalid final accountability blocks candidate promotion.  
**Stop condition:** “prompt-visible” or “cited” can still be reported as visible influence without
candidate-span evidence.

## V1 — Reconciliation and canonical checks become binding

**Inputs:** existing composition ledger/placements, old source README, final candidate, vendored
check module/classification.  
**Change:** repair exact relocation and omission ownership at the causal ledger; project the current
ledger into Aspose's content/structure/code-example/badge dispositions; vendor/adapt the missing 14
canonical checks; classify all 103; make applicable hard skips/errors and all reconciliation
errors promotion-blocking. Remove the real-fixture relocation `xfail`.  
**Outputs:** valid four-family dispositions, exact five-bucket partition, 103-check coverage with a
typed result for every check.  
**Stop condition:** `{error: ...}` evidence, an applicable hard skip/error, an unexplained byte, or
an unclassified check can coexist with candidate promotion.

## D1 — Dependency evidence across real manifest shapes

**Inputs:** existing dependency snapshot/acquisition modules and one sealed manifest fixture per
ecosystem/shape.  
**Change:** remove silent empty-list semantics. For Python, parse supported `pyproject.toml`,
`setup.cfg`, and statically readable `setup.py` declarations without executing repository code, or
return a typed non-applicability/error. Then reuse existing ecosystem parsers to complete .NET,
Java, C++, TypeScript, and Go snapshots, including required/optional/dev/native/proprietary buckets
where evidence exists.  
**Required first regression:** setup.py-only fixture with non-empty `install_requires` must not
become `[]`; current 3D's genuinely empty declaration remains explicit and honest.  
**Stop condition:** missing parser support is indistinguishable from verified zero dependencies.

## C1 — Accepted knowledge changes useful bytes

**Inputs:** individually verified facts, preserved source content, existing agentic plan and
verified-template slots.  
**Change:** use existing plan/render paths to express the five still-unconsumed verified claim
families—capabilities, format support, installation, limitations, and troubleshooting—plus
dependencies, API, and examples; keep section/item caps and require an omission reason instead of
overstuffing. Preserve `05ef1e5...`'s rule that SEO may shape bounded generic title wording but may
not authorize factual prose.  
**Outputs:** exact, reviewed candidate deltas attributable to accepted facts.  
**Calibration:** first 3D sealed replay, then Note and Barcode.  
**Stop condition:** a run only adds layout/TOC/markers, or silently ignores accepted facts.

## R1 — Bounded Qwen author/reviewer recovery

**Inputs:** existing merged and separated Qwen clients, deterministic reducer, bounded repair loop.  
**Change:** on merged `length`, malformed tool arguments, transport failure, or top-level schema
failure, invoke the existing separated blind-quality and factual clients. Include the factual facet
and retain deterministic validation plus at most two repair attempts. Run only unresolved facets:
normally one merged call; malformed merged recovery uses three calls (merged + blind + factual),
and the absolute worst case is five when each isolated facet uses its one compact grounding
correction. Use the existing 3,000/6,000 separated output budgets and never repeat the unchanged full
request. Preserve candidate anchors, all selected referenced facts, and plan claim coverage; remove
only duplicated model-authored fields that deterministic binders already materialize.  
**Outputs:** typed review evidence with complete claim coverage or an honest terminal failure.  
**Stop condition:** the known 4,000-token truncation can become a cached/manual-only system failure,
or a reviewer can approve without disposing every material claim group.

## N1 — Immediate, correctly bound no-op

**Inputs:** accepted candidate, final knowledge/reconciliation/check/review artifacts and all owner
code/data hashes.  
**Change:** bind all final evidence into acceptance/cache identity; after first approval, run the
existing approved-cache path immediately in the same job; retry agent-fixable/transient blocks and
cache only external-infrastructure blocks.  
**Outputs:** identical candidate/evidence hashes and zero provider calls on the second pass.  
**Stop condition:** a later scheduler visit is required for no-op, or an errored diagnostic remains
reusable as accepted state.

## P1 — Generic README-only profile

**Inputs:** the still-pending PSD evidence bundle, repository README/history, approved owner/product
identity authorities, and explicit absence of manifests/source/license.  
**Change:** implement repository-shape policy, not PSD-specific branching. `source absent` means code,
install, API, dependency, example, and license claims are not applicable unless separately
evidenced; it does not mean the product or repository purpose is absent.  
**Outputs:** polished, useful repository-status README with zero fabricated implementation claims.  
**Stop condition:** PSD is silently excluded, treated as successful without evidence, or forced
through code-repository requirements.

## H1 — Verified hosted execution

**Inputs:** existing production workflow/profile, platform-priority registry order, immutable run
bundles.  
**Change:** enable local fact verification, independent review, and local evidence writes in the
existing hosted read-only path; target current `NO_OP_PROVEN`; restore/save content-addressed
bundles; require candidate artifacts to exist; retain zero product-repository writes. Start at
`max-parallel: 1`, then measure before increasing to 2.  
**Outputs:** hosted, reconstructible canary and aggregate evidence.  
**Stop condition:** a green workflow can omit candidate evidence, use observation-only facts, or
depend on a local machine cache.

## Proof campaign

1. Run 3D/Note/Barcode from sealed pre-refresh SHAs without exposing refreshed README bytes to the
   author.
2. Run the PSD README-only calibration after its evidence bundle is reconciled.
3. Run one representative repository per remaining ecosystem.
4. Only after those pass, run the dynamic 33-entry registry portfolio with declared exclusions and
   outcomes.
5. For every accepted repository require: factual lineage, old-content dispositions, all applicable
   hard checks, independent review, exact candidate hash, immediate zero-call no-op, and no target
   write.
6. Score the sealed candidate with `aspose_candidate_rubric/RUBRIC_30.md`. A numeric 30 is accepted
   only with no hard disqualifier and candidate-bound evidence for all criteria; length, table count,
   example count, and copied Aspose wording earn no points.

Aspose's active 30-product set remains the presentation calibration set. The optimizer's governed
completion denominator is 33 unless its registry/governance is explicitly changed.
