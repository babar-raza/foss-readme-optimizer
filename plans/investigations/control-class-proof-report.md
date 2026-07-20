# Control-Class Proof Report — All Five Classes

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)`
> artifact_role: analysis_or_evidence_only · execution_authority: false
> taskcards: ..06 · date: 2026-07-18 · never-push honored throughout (zero remote writes, zero git pushes, zero renames)
> Harnesses: `tools/overwrite_lab.py` + `tools/healed_loop.py` + `tools/control_class_proofs.py`
> Evidence: `evidence/overwrite-lab/lab-report.json`, `evidence/control-class-proofs/*`, `tests/fixtures/overwrite-scenarios/*`, `.state/{lab,proofs}/`

## Headline

Every control class has a passing minimal vertical proof. The shipped tool's overwrite failure
is now **executed evidence** (not code-reading), and the healed loop demonstrates the target
behavior end-to-end including verified second-run no-ops with zero LLM calls.

## Current-failure capture (shipped tool vs product-agent overwrite — OVR-002..008)

Run per scenario after a real P0 (shipped tool, `GENERATED`, fixture LLM, spans committed):

| Scenario | Shipped result | Decisive evidence |
|---|---|---|
| S1 full overwrite (+pom 2.0.0) | `STALE_NONCOMPLIANT`, only `change_boundary` fails | **`facts_hash` unchanged despite the version bump** — manifest/license/README are ALL read from the stale work clone; `exportCsv` (U1-only token) never reaches the tool's working copy |
| S2 partial (corrupt marker) | `STALE_NONCOMPLIANT` (`change_boundary`) | same stale-input blindness |
| S3 generic template | `STALE_NONCOMPLIANT` (`change_boundary`) | no quality-regression detection — only the boundary trip |
| S4 legitimate redesign | `STALE_NONCOMPLIANT` (`change_boundary`) | legitimate improvement indistinguishable from tampering |
| S5 stale facts | `STALE_NONCOMPLIANT` (`change_boundary`) | claim-vs-facts conflict invisible |
| S6 CONTRIBUTING deleted | **`COMPLIANT_NO_CHANGE`** | community-file drift completely invisible |
| S7 concurrent HEAD advance | `STALE_NONCOMPLIANT` | no detection of upstream movement |

**OVR-008 verdict (proven by execution):** the first consistency-loss boundary is **input
acquisition/state reconciliation** — the persistent work clone (never re-synced) feeds README,
pom, and LICENSE into facts, so the fingerprint cannot react to upstream change and
`change_boundary` blocks everything else. Exactly one validator distinguishes all six distinct
situations (S1–S5, S7) — no classification is possible from inside the current design.

## the repository-file proof — Class A repository-file (README + community file)

| Scenario | Healed drift class | Result | Rerun |
|---|---|---|---|
| S1 full overwrite | `MIXED_CHANGE` | `PROPOSED`: candidate = **U1 preserved verbatim** + deterministic resources span; **1 live `qwen3-next` call** (routed per finding L2 — not gpt-oss); 0 stale claims; whitelist/prohibited clean | **`NO_CHANGE`, 0 LLM calls** (fingerprint + generation cache) |
| S2 partial | `UPSTREAM_PRODUCT_CHANGE` | `PROPOSED`, 0 LLM calls (relationship prose survived in U1) | `NO_CHANGE`, 0 calls |
| S3 generic template | **`UPSTREAM_README_REWRITE`** | correctly classified (similarity proxy; production = embeddings, L4) | `NO_CHANGE`, 0 calls |
| S4 legitimate redesign | `MIXED_CHANGE` | **no auto-revert** — the redesign is preserved; spans re-added | `NO_CHANGE`, 0 calls |
| S5 stale facts | `CONFLICTING_FACTS` | **`BLOCKED_PENDING_PRODUCT_OWNER`** + structured handoff; no candidate; nothing invented (FACT-004) | n/a (blocked) |
| S6 CONTRIBUTING deleted | `COMMUNITY_FILE_DRIFT` | restore **proposal** (patch); README untouched; unrelated files untouched | stable re-proposal, 0 calls, no duplicates |
| S7 concurrent HEAD | — | **`STALE_INPUT`** — HEAD moved between snapshot and apply ⇒ no apply (CAS) | n/a (restart required) |

Chain per healing spec: product-agent change → snapshot (fresh, every run) → fact validation →
drift classification → desired state (recompiled from U+Facts+Policy, never a B→P patch replay)
→ candidate + prepared patch (never-push) → validators → `.state/` accept → rerun no-op.
Parser decision (evidence-backed): marko AST round-trip lossy on 7/14 real READMEs ⇒ **raw-bytes
section preservation + markdown-it-py token.map for analysis**.

## the settings proof — Class B API/settings (real pdf pilot fixture)

Input: real captured state (description **null**, homepage **null**, topics **[]**). Desired
computed by a deterministic worker from facts+policy. Output: dry-run proposal with before/after,
required permission (`PATCH /repos` + `PUT /topics`, admin write), rollback = recorded
before-snapshot; validators (length, topic count/normalization, no stuffing) pass.
**Negative controls:** module provably makes no remote write (source scan + no requests import);
rerun with state == desired ⇒ **`NO_PROPOSAL`**. → `evidence/control-class-proofs/proof2-*.json`

## the social-preview proof — Class C manual UI (social preview)

Asset contract (1280×640 PNG ≤1MB, alt text, facts-only claims) + 4-step operator instructions;
validation passes; status **`PREPARED_FOR_MANUAL_APPLY`** and never anything stronger without
operator evidence (SAFE-011); rerun with unchanged fingerprint ⇒ **no duplicate asset**
(`rerun_creates_duplicate: false`). → `proof3-social-preview-spec.json`

## the handoff proof — Class D product-agent owned (REAL finding, not seeded)

Input: the real **D-2** finding — cells README instructs a Maven-Central `<dependency>` while
`org.aspose:aspose-cells-foss` returns **0 results on Central** (queried 2026-07-18); plus D-1
tag-prefix inconsistency (`V` vs `v`). Output: `HandoffFindingV1` (owner, severity, evidence,
required action — *central agent will NOT edit the technical claim*). Simulated product-agent
response consumed ⇒ finding state `SENT → ACKNOWLEDGED_BY_OWNER` (a state transition, not
prose). **Negative control:** no release/package write handler exists in the module (runtime-
assembled needle scan). → `proof4-*.json`

## the generated-surface audit — Class E GitHub generated

Real pilots: 100% Java, **no anomaly** (recorded). Synthetic labeled anomaly (vendored-docs
language skew) → explanation finding naming the Linguist cause; allowed remediation routed as a
class-A `.gitattributes` change to the repo owner; forbidden remediation named;
**`write_proposal_produced: false`**. → `proof5-generated-audit.json`

## Shared proof — surface-aware state + evidence

`RunManifestV1`-prototype records **7 surfaces across all five classes** including a NO_CHANGE
surface and audit-only surfaces; `.state/` (`lab/`, `proofs/`) holds durable per-key records with
atomic writes (dot-prefixed, gitignored, per convention). **Negative control:** flipping one
surface to `FAILED` flips `run_successful` to false — README passing can no longer mask another
surface's failure. → `run-manifest.json`, `run-manifest-negative-control.json`

## Known prototype limitations (honest; carried to T3–T5)

1. Drift similarity uses difflib as an offline proxy — production uses `qwen3-embedding-8b`
 (calibration card in roadmap; L4 evidence exists).
2. Generic-template response is classification-only; quality-restoration compilation
 (desired-presentation model) is Wave-3/4 roadmap work gated on the Phase-20 standard.
3. Claim extraction is heading+bullet MVP; production needs the full claim-to-fact graph.
4. S6 re-proposal is stable but unconditional until a product-agent response loop
 (Proof-4 pattern) is wired to it.
5. Proof-2 desired values are worker-drafted examples, not sponsor-approved copy.

## Checkpoint gate status

All five classes: **minimal proof PASSED** (none blocked). Sprint may proceed to T3–T6 only
after human review of this report (mandatory stop per the authoritative plan).
