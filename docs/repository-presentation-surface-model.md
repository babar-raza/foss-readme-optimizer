# Repository-Presentation Surface Model

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)`
> artifact_role: analysis_or_evidence_only · execution_authority: false
> Sources of authority: `plans/master.md` decision #19 + control matrix; `plans/requirements.md` OWN-001..015, SURF-001..015; the current-state investigation at HEAD `4adbaaf`.

This document freezes the control-class inventory (OWN-001: every visible surface has exactly
one class; OWN-002: only the five classes below exist unless a locked decision adds another).

## 1. Surface inventory — one control class per surface

| # | Surface | Control class | Truth owner | May propose | Final writer / gate (pilot) |
|---|---|---|---|---|---|
| S01 | `README.md` content & structure | A repository-file | product agent (technical) + central (presentation) | product agent, central | central = **final quality gate**; apply = prepared patch, human applies |
| S02 | README product illustration / embedded images | A repository-file | central (presentation) from product facts | central | central gate; prepared patch |
| S03 | `LICENSE` presence/content | A repository-file | sponsor/legal via policy | central (audit + proposal) | central gate; prepared patch (GOV-013 note: *this* project's own repo intentionally has no LICENSE) |
| S04 | `CONTRIBUTING.md` | A repository-file | central per policy; org default may inherit | central | central gate; prepared patch |
| S05 | `CODE_OF_CONDUCT.md` | A repository-file | org default preferred | central | central gate; prepared patch |
| S06 | `SECURITY.md` | A repository-file | central per policy | central | central gate; prepared patch |
| S07 | `SUPPORT.md` | A repository-file | central per policy | central | central gate; prepared patch |
| S08 | Issue templates | A repository-file | central per policy | central | central gate; prepared patch |
| S09 | PR templates | A repository-file | central per policy | central | central gate; prepared patch |
| S10 | Repository description (About) | B API/settings | central from product facts | central | **proposal-only** (dry-run); apply gate deferred |
| S11 | Homepage / website field | B API/settings | central from policy (canonical destination varies per product) | central | proposal-only |
| S12 | Topics | B API/settings | central from facts+policy | central | proposal-only |
| S13 | Feature settings (Issues/Discussions/Wiki/Projects) | B API/settings | sponsor/policy — only where business-justified | central | proposal-only; never "because it exists" |
| S14 | Social-preview image | C manual UI | central prepares; operator applies | central | `PREPARED_FOR_MANUAL_APPLY`; never auto-completed (SAFE-011) |
| S15 | Releases (existence, naming, notes, assets) | D product-agent owned | product agent | central: findings only | **no central writer**; `HandoffFindingV1` |
| S16 | Packages / package metadata / publishing | D product-agent owned | product agent | central: findings only | no central writer; handoff |
| S17 | Release/package-specific technical facts | D product-agent owned | product agent | central: conflict findings | no central writer; handoff (FACT-005/008) |
| S18 | Contributors | E GitHub generated | GitHub (from history) | central: anomaly finding | **audit-only, no write path** |
| S19 | Languages (Linguist) | E GitHub generated | GitHub (from tree) | central: anomaly finding; `.gitattributes` remediation routed to repo owner | audit-only |
| S20 | Stars/forks/watchers/activity/counts | E GitHub generated | GitHub | central: observation only | audit-only; **never quality gates** |
| S21 | Repository page layout / tabs / community-profile surfacing | E GitHub generated | GitHub | — | audit-only (SURF-008: we control files, GitHub controls display) |

Rules: a surface not in this table gets classified (and this table extended) **before** any action
is proposed for it (OWN-001). Community files may be satisfied by **org-level defaults** —
repo-specific files only where policy justifies them (SURF-006); presence is verified via the
community-profile API, display via GitHub only.

## 2. Per-class contract — final authority, apply channel, forbidden operations

### Class A — repository-file managed
- **Apply (pilot):** push-blocked work clone → validated candidate → prepared patch + evidence → human applies. Never push (OWN-008).
- **Overwrite rule:** the product agent MAY overwrite these files; its output is an *upstream draft*. Publishing order runs the central gate after every product-agent run (INT-001); drift is classified, never silently reverted (SAFE-012).
- **Forbidden:** wholesale generic-template rewrite (RDM-003); edits without fact provenance (FACT-003); removing known limitations (FACT-009); any direct remote write.

### Class B — API/settings managed
- **Apply (pilot):** dry-run proposal only — before/after, rationale, required permission, rollback (SURF-005). Remote apply requires the deferred explicit apply gate (SURF-004, SAFE-010).
- **Forbidden:** any PATCH/PUT during pilot; keyword-stuffed topics (SURF-003); promotional-filler descriptions (SURF-001); hard-coded one-size homepage (B2 note).

### Class C — manual UI managed
- **Apply:** operator, via Settings UI, from prepared asset + instructions. Status machine: `NOT_REQUIRED → ASSET_PROPOSED → ASSET_VALIDATED → AWAITING_APPROVAL → PREPARED_FOR_MANUAL_APPLY → MANUALLY_APPLIED_WITH_EVIDENCE | STALE | REJECTED`.
- **Forbidden:** reporting applied without operator evidence (SAFE-011); claiming an upload API exists without documented proof (OWN-007); duplicate asset generation for an unchanged fingerprint.

### Class D — product-agent owned
- **Apply:** none by central. Findings flow through `HandoffFindingV1` with a response loop (receive → ack → correct/reject with evidence → central rerun) — a state transition, not prose.
- **Forbidden:** any write handler existing at all (CORE-022, OWN-004); inferring release facts from stale prose (FACT-008); "fixing" a mismatch directly.

### Class E — GitHub generated
- **Apply:** none, ever (OWN-003/005). Findings explain the underlying cause (history, vendored files, Linguist rules) and route any legitimate source-tree remediation to the owning agent.
- **Forbidden:** cosmetic manipulation of percentages/counts; validators that fail on low stars/contributors/activity; presenting these as settable fields.

## 3. Invariants across classes

1. **One final gate per surface** — no surface has two uncoordinated writers; the central agent is sole final gate for A, sole proposer for B, sole preparer for C, and has no role in D/E outputs.
2. **Authority-class validation precedes any renderer/write selection** (VAL-008); a run that cannot classify a surface is `BLOCKED`, not guessed.
3. **Evidence is surface-aware** — every evaluated surface appears in `RunManifestV1` (incl. no-ops and audit-only); a run is not successful if any required surface was skipped or failed.
4. **Never-push pilot** — no git push, no remote mutation, no manual step claimed done, in any class.
