# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)
# artifact_role: analysis_or_evidence_only
"""Classify plan coverage for every requirement in the normalized inventory.

Classification vocabulary (the healing directive):
  FULLY_INVESTIGATED / PARTIALLY_INVESTIGATED / NAMED_ONLY / DEFERRED_WITH_DESIGN /
  DEFERRED_WITHOUT_DESIGN / MISSING / NOT_APPLICABLE_WITH_EVIDENCE / ALREADY_PROVEN

Method: (group, status) defaults + explicit per-ID overrides, each override carrying
a judgment note and, for any P0/P1 gap, an explicit repair route. The judgments were
authored from the completed current-state investigation (code + governed docs + runs/
evidence) and the control-class proofs.

Outputs:
  plans/investigations/repository-presentation-requirements-coverage.md
  plans/investigations/control/requirements-coverage.csv
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from collections import Counter
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTROL = REPO_ROOT / "plans" / "investigations" / "control"
INVENTORY = CONTROL / "normalized-requirements-inventory.yaml"
OUT_MD = REPO_ROOT / "plans" / "investigations" / "repository-presentation-requirements-coverage.md"
OUT_CSV = CONTROL / "requirements-coverage.csv"

GOVERNED_BY = "plans/master.md + plans/requirements.md + plans/GOVERNANCE.md"

GAP_CLASSES = {"NAMED_ONLY", "DEFERRED_WITHOUT_DESIGN", "MISSING"}

# ---------------------------------------------------------------------------
# Defaults by requirement STATUS (the honest baseline before overrides):
#  - IMPLEMENTED    -> ALREADY_PROVEN (Phase 0-15 engine, backed by tests + runs/
#                      evidence, verified during the current-state reconstruction)
#  - GOVERNANCE     -> FULLY_INVESTIGATED (active process rules the governed docs
#                      already enforce: permanent IDs, never-push, docs-change-together)
#  - PLANNED        -> DEFERRED_WITH_DESIGN (this investigation's docs carry a design)
#                      ... tightened or loosened per ID below
#  - PARTIAL        -> PARTIALLY_INVESTIGATED (some implementation/proof exists)
#  - BACKLOG        -> DEFERRED_WITH_DESIGN (explicitly tracked but not executable now)
#  - DEPRECATED     -> NOT_APPLICABLE_WITH_EVIDENCE (retained historical obligation)
#  - RESEARCH-GATED -> DEFERRED_WITHOUT_DESIGN (research not performed this sprint)
#                      unless overridden
STATUS_DEFAULT = {
    "IMPLEMENTED": (
        "ALREADY_PROVEN",
        "Phase 0-15 engine behavior; verified in the current-state "
        "reconstruction against code + tests + runs/ evidence",
    ),
    "GOVERNANCE": (
        "FULLY_INVESTIGATED",
        "Active governance rule already enforced by this investigation's process",
    ),
    "PARTIAL": (
        "PARTIALLY_INVESTIGATED",
        "Requirement has partial implementation or proof and retains an explicit open boundary",
    ),
    "PLANNED": ("DEFERRED_WITH_DESIGN", "Carried by the governed roadmap"),
    "BACKLOG": (
        "DEFERRED_WITH_DESIGN",
        "Explicitly tracked backlog item excluded from the active mandatory mission queue",
    ),
    "DEPRECATED": (
        "NOT_APPLICABLE_WITH_EVIDENCE",
        "Deprecated obligation retained for traceability rather than current execution",
    ),
    "RESEARCH-GATED": (
        "DEFERRED_WITHOUT_DESIGN",
        "Research deliverable not performed in this sprint",
    ),
}

# ---------------------------------------------------------------------------
# Per-ID overrides: id -> (classification, note[, route]).
# route is mandatory for any P0/P1 landing in a GAP class.
OVERRIDES: dict[str, tuple] = {
    # --- GOV ---
    "GOV-009": (
        "DEFERRED_WITH_DESIGN",
        "CI traceability check designed via the traceability report + a roadmap "
        "card (validate_requirements.py)",
    ),
    "GOV-012": (
        "FULLY_INVESTIGATED",
        "RunManifestV1 carries per-surface requirement IDs by design; implementation in roadmap",
    ),
    # --- BIZ ---
    "BIZ-002": (
        "PARTIALLY_INVESTIGATED",
        "Product-understanding criteria depend on Phase-20 presentation "
        "standard; measurement hierarchy designed",
    ),
    "BIZ-006": (
        "PARTIALLY_INVESTIGATED",
        "Per-repo tailoring principle encoded; cross-pilot tailoring proof "
        "deferred to roadmap (VAL-016 wave)",
    ),
    "BIZ-007": (
        "FULLY_INVESTIGATED",
        "Three-way reconciliation preserves verified facts by design; the "
        "repository-file proof exercises no-fact-loss",
    ),
    "BIZ-008": (
        "DEFERRED_WITH_DESIGN",
        "Relationship-language quality rides on existing validators + "
        "Phase-21 presentation work in roadmap",
    ),
    "BIZ-004": (
        "DEFERRED_WITH_DESIGN",
        "Measurement hierarchy designed; feasibility study itself is Phase-20 homework in roadmap",
    ),
    # --- OWN ---
    "OWN-001": ("FULLY_INVESTIGATED", "The control-class inventory freezes one class per surface"),
    "OWN-002": ("FULLY_INVESTIGATED", "Five classes fixed; no additions"),
    "OWN-003": (
        "FULLY_INVESTIGATED",
        "The generated-surface audit proof asserts no write path for generated surfaces",
    ),
    "OWN-004": ("FULLY_INVESTIGATED", "The handoff proof asserts no release/package write handler"),
    "OWN-006": (
        "FULLY_INVESTIGATED",
        "The settings proof demonstrates a dry-run-first gated settings "
        "workflow (no remote write in pilot)",
    ),
    "OWN-007": (
        "FULLY_INVESTIGATED",
        "The social-preview proof demonstrates the manual-UI contract with "
        "PREPARED_FOR_MANUAL_APPLY",
    ),
    "OWN-010": (
        "FULLY_INVESTIGATED",
        "Blocking handoff on ambiguous/missing facts in contracts + the "
        "handoff proof's response loop",
    ),
    "OWN-011": (
        "PARTIALLY_INVESTIGATED",
        "Editorial-authority bounds designed; fine-grained rules await "
        "Phase-20 presentation standard",
    ),
    "OWN-012": (
        "FULLY_INVESTIGATED",
        "The generated-surface audit names the underlying cause; no field edits",
    ),
    "OWN-013": ("FULLY_INVESTIGATED", "The handoff proof: findings handed to product owner"),
    "OWN-014": (
        "PARTIALLY_INVESTIGATED",
        "Permission+rollback recorded in the settings proof; full "
        "github-surface-control doc is Phase-20 research in roadmap",
    ),
    "OWN-015": ("FULLY_INVESTIGATED", "RunManifestV1 action-mode field per surface"),
    # --- FACT --- (contracts are this sprint's core)
    "FACT-001": (
        "FULLY_INVESTIGATED",
        "ProductFactsV1 required before content change; the repository-file "
        "and handoff proofs exercise it",
    ),
    "FACT-002": ("FULLY_INVESTIGATED", "Minimum record fields specified; schema to be frozen next"),
    "FACT-003": ("FULLY_INVESTIGATED", "Claim->fact-ID mapping required by contracts + validators"),
    "FACT-004": (
        "FULLY_INVESTIGATED",
        "Missing facts => blocking finding (contracts + the handoff proof)",
    ),
    "FACT-005": (
        "FULLY_INVESTIGATED",
        "Conflicting sources => owner resolution before change (contract + response loop)",
    ),
    "FACT-006": (
        "FULLY_INVESTIGATED",
        "Provenance fields (source type/location/revision/owner/confidence) in ProductFactsV1",
    ),
    "FACT-007": (
        "PARTIALLY_INVESTIGATED",
        "Verified-example field designed; execution/verification mechanics deferred to roadmap",
    ),
    "FACT-008": (
        "FULLY_INVESTIGATED",
        "Release facts via handoff, never stale prose (the handoff proof)",
    ),
    "FACT-009": (
        "FULLY_INVESTIGATED",
        "Reconciliation preserves limitations (never removed for attractiveness)",
    ),
    "FACT-010": (
        "FULLY_INVESTIGATED",
        "dependency_fact_ids per SurfaceStateV1 drives targeted reevaluation",
    ),
    # --- RDM ---
    "RDM-001": (
        "DEFERRED_WITH_DESIGN",
        "Callout retirement is a roadmap card (production change, out of investigation scope)",
    ),
    "RDM-002": (
        "PARTIALLY_INVESTIGATED",
        "Product-first opening principle encoded; measurable criteria await Phase-20 standard",
    ),
    "RDM-003": (
        "FULLY_INVESTIGATED",
        "No-generic-template: three-way recompile + embedding similarity "
        "detection (the repository-file proof's generic-template scenario)",
    ),
    "RDM-004": (
        "FULLY_INVESTIGATED",
        "Surgical fact-backed changes: desired-state compile + change classification",
    ),
    "RDM-013": ("ALREADY_PROVEN", "Existing resources-span behavior; Phase 0-15 tests + evidence"),
    "RDM-014": (
        "FULLY_INVESTIGATED",
        "Span presence != completeness (established in the current-state findings)",
    ),
    "RDM-019": (
        "DEFERRED_WITHOUT_DESIGN",
        "First-screen/minute/install standard is Phase-20 research; P2",
        "Roadmap Wave 0 card (Phase-20 research)",
    ),
    "RDM-020": (
        "PARTIALLY_INVESTIGATED",
        "Generic/mechanical-prose detection via endpoint embeddings; "
        "calibration in the repository-file proof",
    ),
    "RDM-021": (
        "PARTIALLY_INVESTIGATED",
        "Markdown/anchor/fence validation designed on AST model; implementation in roadmap",
    ),
    "RDM-022": ("DEFERRED_WITH_DESIGN", "Per-change rationale field in proposals (RunManifestV1)"),
    "RDM-023": ("ALREADY_PROVEN", "Secondary-links best-effort tracking shipped"),
    # --- SURF ---
    "SURF-004": (
        "FULLY_INVESTIGATED",
        "The settings proof negative-asserts no remote write without an apply gate",
    ),
    "SURF-005": (
        "FULLY_INVESTIGATED",
        "Proposal = before/after + rationale + permission + rollback + "
        "evidence (the settings proof)",
    ),
    "SURF-008": (
        "FULLY_INVESTIGATED",
        "File-vs-GitHub-display distinction encoded in the control-class model",
    ),
    "SURF-009": (
        "FULLY_INVESTIGATED",
        "Community files use the same push-blocked evidence model (the repository-file proof)",
    ),
    "SURF-010": (
        "FULLY_INVESTIGATED",
        "Illustration vs social preview separated (the social-preview proof)",
    ),
    "SURF-014": (
        "FULLY_INVESTIGATED",
        "Release/package audit without touching the owned surface (the handoff proof)",
    ),
    "SURF-015": (
        "FULLY_INVESTIGATED",
        "Generated-surface anomalies investigated via repo evidence (the generated-surface audit)",
    ),
    # --- CORE ---
    "CORE-012": (
        "PARTIALLY_INVESTIGATED",
        "IMPLEMENTED as scoped, but the current-state evidence proves "
        "work-clone-as-state fails portability/CI; routed to a supersession "
        "delta (work clone -> cache role)",
    ),
    "CORE-031": (
        "PARTIALLY_INVESTIGATED",
        "Runtime layout works locally; durable-state role superseded by "
        "the .state/ StateStore proposal",
    ),
    "CORE-020": (
        "FULLY_INVESTIGATED",
        "The spine extends the one pipeline across surfaces (no second pipeline)",
    ),
    "CORE-021": (
        "FULLY_INVESTIGATED",
        "Per-surface detector/class/proposal/validators/evidence/gate is "
        "the control-class proof structure",
    ),
    "CORE-022": (
        "FULLY_INVESTIGATED",
        "The handoff and generated-surface audit proofs assert no write handler for classes D/E",
    ),
    "CORE-023": (
        "DEFERRED_WITHOUT_DESIGN",
        "Registry sync script is Phase-18 ops; P2",
        "Roadmap ops card",
    ),
    "CORE-024": (
        "DEFERRED_WITHOUT_DESIGN",
        "Broader README corpus (.NET etc.) is Phase-19; P2",
        "Roadmap verification-wave card",
    ),
    "CORE-025": (
        "DEFERRED_WITH_DESIGN",
        "Offline evidence replay designed in the reconciliation/apply "
        "design (replay from evidence bundle)",
    ),
    # --- OPS ---
    "OPS-001": (
        "DEFERRED_WITHOUT_DESIGN",
        "act local CI simulation not performed (system package install needs approval); P1",
        "Roadmap card: install act + workflow_dispatch e2e (Phase 16)",
    ),
    "OPS-004": (
        "DEFERRED_WITH_DESIGN",
        "Golden-set monitor = scheduled safety-net mode in the consolidated "
        "architecture's publishing design",
    ),
    "OPS-005": ("DEFERRED_WITHOUT_DESIGN", "Registry sync ops; P2", "Roadmap ops card (Phase 18)"),
    "OPS-006": ("DEFERRED_WITHOUT_DESIGN", "Dependabot config; P2", "Roadmap ops card (Phase 18)"),
    # --- LLM ---
    "LLM-005": (
        "FULLY_INVESTIGATED",
        "Future jobs consume only approved facts: facts-only prompt "
        "coupling generalized in contracts",
    ),
    "LLM-006": (
        "FULLY_INVESTIGATED",
        "No invented capabilities: schema + referential-integrity pattern "
        "generalized; weak-LLM design in place",
    ),
    "LLM-009": (
        "PARTIALLY_INVESTIGATED",
        "Description prose validation partially exercised by the settings "
        "proof; full validators in roadmap",
    ),
    "LLM-010": (
        "DEFERRED_WITH_DESIGN",
        "Visual-claims validation designed with the asset contract; implementation in roadmap",
    ),
    "LLM-011": (
        "PARTIALLY_INVESTIGATED",
        "Prompt-injection-as-untrusted-data named in the consolidated "
        "architecture's security section; adversarial fixtures deferred (Phase-17 wave)",
    ),
    "LLM-012": (
        "DEFERRED_WITH_DESIGN",
        "Model-drift monitoring = scheduled safety-net + the LLM gateway-characterization baseline",
    ),
    # --- VAL ---
    "VAL-005": (
        "DEFERRED_WITH_DESIGN",
        "READMEPresentationReport awaits the Phase-20 standard; roadmap wave",
    ),
    "VAL-006": (
        "FULLY_INVESTIGATED",
        "Presentation validation must not reward moving promo links up (plan principle + MET-005)",
    ),
    "VAL-007": (
        "FULLY_INVESTIGATED",
        "Claim provenance validation via contracts (FACT-003) in proofs",
    ),
    "VAL-008": (
        "FULLY_INVESTIGATED",
        "Authority-class validation before renderer/write selection (the "
        "control-class inventory + proof structure)",
    ),
    "VAL-009": (
        "FULLY_INVESTIGATED",
        "The settings proof: dry-run/permission/before-after/rollback validation",
    ),
    "VAL-012": (
        "PARTIALLY_INVESTIGATED",
        "Community-file validation exercised minimally in the "
        "repository-file proof; full checks in roadmap",
    ),
    "VAL-013": (
        "PARTIALLY_INVESTIGATED",
        "Visual validation contract in the social-preview proof "
        "(dimensions/type/size/claims); full suite in roadmap",
    ),
    "VAL-014": (
        "PARTIALLY_INVESTIGATED",
        "Markdown/link/anchor validation designed on the AST model; roadmap wave",
    ),
    "VAL-015": (
        "FULLY_INVESTIGATED",
        "Unresolved fact conflict => proposal blocked (contracts + the handoff proof)",
    ),
    "VAL-016": (
        "PARTIALLY_INVESTIGATED",
        "Template-clone similarity via endpoint embeddings; calibration "
        "method defined in the reuse/LLM analysis",
    ),
    "VAL-017": (
        "DEFERRED_WITH_DESIGN",
        "Adversarial fixtures enumerated in the negative-control list; "
        "execution in roadmap (Phase-17 wave)",
    ),
    # --- SAFE ---
    "SAFE-006": (
        "DEFERRED_WITH_DESIGN",
        "Monitor structurally unable to escalate: workflow-hardcoded "
        "dry-run design (the consolidated architecture)",
    ),
    "SAFE-010": (
        "FULLY_INVESTIGATED",
        "Remote writes need authorization+snapshot+rollback: designed; "
        "apply itself deferred (never-push pilot)",
    ),
    "SAFE-011": (
        "FULLY_INVESTIGATED",
        "The social-preview proof: manual step never reported complete without operator evidence",
    ),
    "SAFE-012": (
        "FULLY_INVESTIGATED",
        "No-silent-revert: drift => proposal/handoff only (three-way recompile, never auto-revert)",
    ),
    "SAFE-013": (
        "FULLY_INVESTIGATED",
        "RunManifestV1 records class/action-mode/source/changes/validators/status per surface",
    ),
    "SAFE-014": (
        "FULLY_INVESTIGATED",
        "Requirement IDs recorded in evidence (RunManifestV1 field)",
    ),
    "SAFE-015": (
        "FULLY_INVESTIGATED",
        "Reproducibility via desired-state fingerprint + generation cache",
    ),
    "SAFE-016": (
        "PARTIALLY_INVESTIGATED",
        "Binary asset checksums+provenance designed; implementation in roadmap",
    ),
    "SAFE-017": (
        "FULLY_INVESTIGATED",
        "Failed validation blocks + names failed requirement IDs (RunManifestV1)",
    ),
    "SAFE-018": (
        "DEFERRED_WITHOUT_DESIGN",
        "Lockfile+dependabot; P2",
        "Roadmap ops card (Phase 18)",
    ),
    # --- INT ---
    "INT-001": (
        "FULLY_INVESTIGATED",
        "Publishing ordering: central after product agent (one-final-writer)",
    ),
    "INT-002": (
        "FULLY_INVESTIGATED",
        "Drift taxonomy covers markers/sections/prose/facts/visuals/links/files (12 categories)",
    ),
    "INT-003": (
        "FULLY_INVESTIGATED",
        "Drift compares facts AND the accepted baseline (base/accepted/upstream/facts/policy)",
    ),
    "INT-004": (
        "FULLY_INVESTIGATED",
        "Drift => evidence + proposal/handoff, never silent overwrite",
    ),
    "INT-005": (
        "FULLY_INVESTIGATED",
        "Technical->product-owner routing vs presentation->central-gates (classification)",
    ),
    "INT-006": (
        "FULLY_INVESTIGATED",
        "Fact-change => dependent-surface reevaluation (dependency_fact_ids)",
    ),
    "INT-007": (
        "DEFERRED_WITH_DESIGN",
        "Scheduled re-audit = safety-net mode; history preservation in roadmap",
    ),
    "INT-008": (
        "FULLY_INVESTIGATED",
        "Generic-template overwrite detection: the generic-template scenario + embeddings",
    ),
    "INT-009": (
        "FULLY_INVESTIGATED",
        "Legitimate-update vs regression distinction: change classification "
        "(the repository-file proof)",
    ),
    "INT-010": ("FULLY_INVESTIGATED", "Machine-readable versioned contracts (all V1)"),
    # --- NFR ---
    "NFR-002": (
        "PARTIALLY_INVESTIGATED",
        "Proven on a dev machine; the current-state evidence shows it does "
        "NOT hold on ephemeral CI (no durable state) -> strengthening delta",
    ),
    "NFR-005": (
        "FULLY_INVESTIGATED",
        "Modular surfaces on a common pipeline+evidence model (CORE-020 spine)",
    ),
    "NFR-006": (
        "PARTIALLY_INVESTIGATED",
        "Human-readable proposal/report formats designed; full reports in roadmap",
    ),
    "NFR-007": (
        "PARTIALLY_INVESTIGATED",
        "Repo-specific character preserved by design; similarity checks partial (embeddings)",
    ),
    "NFR-008": (
        "FULLY_INVESTIGATED",
        "Reversibility via baseline/diff/settings-snapshot (rollback design)",
    ),
    "NFR-009": (
        "PARTIALLY_INVESTIGATED",
        "CRLF determinism implemented; full Windows/Linux cross-platform test matrix in roadmap",
    ),
    "NFR-010": (
        "FULLY_INVESTIGATED",
        "Per-repo AND per-surface failure isolation (portfolio idempotency)",
    ),
    "NFR-011": (
        "PARTIALLY_INVESTIGATED",
        "Report stability via versioned schemas; history comparisons in roadmap",
    ),
    "NFR-012": (
        "FULLY_INVESTIGATED",
        "LLM-call minimization: deterministic workers + generation cache + skip logic",
    ),
    # --- PIL ---
    "PIL-002": (
        "PARTIALLY_INVESTIGATED",
        "Repo-specific proposals by design; cross-pilot tailoring "
        "comparison deferred (VAL-016 wave)",
    ),
    "PIL-003": (
        "FULLY_INVESTIGATED",
        "No expansion until the rollout gates pass (plan constraint)",
    ),
    "PIL-006": (
        "FULLY_INVESTIGATED",
        "Simulated product-agent refresh survival IS the repository-file "
        "proof (this sprint's core)",
    ),
    # --- MET ---
    "MET-001": (
        "DEFERRED_WITHOUT_DESIGN",
        "Referral baseline study = Phase-20 homework, not this sprint; P1",
        "Roadmap Wave 0 card (Phase-20 traffic study)",
    ),
    "MET-002": (
        "DEFERRED_WITHOUT_DESIGN",
        "Feasibility-study contents = Phase-20; P1",
        "Roadmap Wave 0 card (Phase-20 traffic study)",
    ),
    "MET-003": (
        "DEFERRED_WITH_DESIGN",
        "UTM already policy-driven; measurement hierarchy designed",
    ),
    "MET-006": (
        "DEFERRED_WITHOUT_DESIGN",
        "Observation period definition = Phase-20; P1",
        "Roadmap Wave 0 card (Phase-20 traffic study)",
    ),
    "MET-008": (
        "FULLY_INVESTIGATED",
        "Target changes only via a governed decision (plan constraint)",
    ),
    # --- DOC ---
    "DOC-003": (
        "DEFERRED_WITHOUT_DESIGN",
        "Presentation-standard research (n8n/nuget) not in sprint; P1",
        "Roadmap Wave 0 card (Phase-20 research)",
    ),
    "DOC-004": (
        "DEFERRED_WITHOUT_DESIGN",
        "Presentation-standard contents; P1",
        "Roadmap Wave 0 card (Phase-20 research)",
    ),
    "DOC-005": (
        "PARTIALLY_INVESTIGATED",
        "Surface model covers classes/authority; official-GitHub-doc "
        "verification pass deferred to a Phase-20 card",
    ),
    "DOC-006": ("FULLY_INVESTIGATED", "Product-facts/handoff schema drafted this sprint"),
    "DOC-007": (
        "DEFERRED_WITHOUT_DESIGN",
        "Traffic study; P1",
        "Roadmap Wave 0 card (Phase-20 traffic study)",
    ),
    "DOC-008": (
        "PARTIALLY_INVESTIGATED",
        "Stale docs (architecture.md/AGENTS.md callout) found; fixes routed "
        "via the contradiction ledger",
    ),
    "DOC-009": (
        "FULLY_INVESTIGATED",
        "Honest-status rule enforced (nothing IMPLEMENTED for drafts)",
    ),
    "DOC-010": ("FULLY_INVESTIGATED", "The traceability report generates this mapping"),
}


# ---------------------------------------------------------------------------
# REVIEW DOWNGRADES (independent-review honesty pass, 2026-07-18).
# FULLY_INVESTIGATED must mean shipped+proven OR exercised by a control-class
# proof — NOT "designed" or "will be frozen next". These IDs were over-credited;
# corrected here:
#   DEFERRED_WITH_DESIGN = design exists, no proof/schema yet
#   PARTIALLY_INVESTIGATED = prototype/behavior shown, contract not frozen
REVIEW_DOWNGRADES: dict[str, tuple[str, str]] = {
    "FACT-001": (
        "PARTIALLY_INVESTIGATED",
        "block-on-missing-facts behavior proven (the stale-facts and "
        "handoff proofs); ProductFactsV1 record not yet frozen",
    ),
    "FACT-002": ("DEFERRED_WITH_DESIGN", "minimum-fields listed but the schema is not yet frozen"),
    "FACT-003": (
        "PARTIALLY_INVESTIGATED",
        "claim->fact matching is a prototype heading/bullet MVP; full contract pending",
    ),
    "FACT-006": (
        "DEFERRED_WITH_DESIGN",
        "provenance fields specified; ProductFactsV1 schema not written yet",
    ),
    "FACT-009": (
        "DEFERRED_WITH_DESIGN",
        "limitation preservation designed; no dedicated proof this sprint",
    ),
    "FACT-010": (
        "DEFERRED_WITH_DESIGN",
        "dependency_fact_ids designed in the state model; targeted reevaluation not proven",
    ),
    "INT-001": (
        "DEFERRED_WITH_DESIGN",
        "publishing ordering / one-final-writer is architecture design, not proven",
    ),
    "INT-006": ("DEFERRED_WITH_DESIGN", "fact-change targeted reevaluation designed only"),
    "INT-010": ("DEFERRED_WITH_DESIGN", "machine-readable versioned contracts not yet frozen"),
    "DOC-006": (
        "DEFERRED_WITH_DESIGN",
        "product-facts/handoff schema is a pending deliverable, not yet frozen",
    ),
    "SAFE-010": (
        "DEFERRED_WITH_DESIGN",
        "authorization+snapshot+rollback designed; apply gate deferred, unproven",
    ),
    "SAFE-013": (
        "PARTIALLY_INVESTIGATED",
        "RunManifestV1 is a prototype in the proofs; schema not frozen",
    ),
    "SAFE-014": (
        "PARTIALLY_INVESTIGATED",
        "requirement-ID recording shown in the prototype manifest; not frozen",
    ),
    "SAFE-015": (
        "PARTIALLY_INVESTIGATED",
        "rerun no-op via fingerprint shown in the prototype; full reproducibility unproven",
    ),
    "GOV-012": (
        "PARTIALLY_INVESTIGATED",
        "prototype manifest carries requirement IDs; not the frozen schema",
    ),
    "OWN-015": (
        "PARTIALLY_INVESTIGATED",
        "action_mode present in the prototype manifest; not frozen",
    ),
    "VAL-007": (
        "PARTIALLY_INVESTIGATED",
        "claim provenance uses prototype matching; frozen validator pending",
    ),
    "VAL-008": (
        "PARTIALLY_INVESTIGATED",
        "surfaces classified + proofs route by class; blocking validator not built",
    ),
    "LLM-005": (
        "DEFERRED_WITH_DESIGN",
        "facts-only prompt coupling for future jobs designed, not built",
    ),
    "LLM-006": (
        "PARTIALLY_INVESTIGATED",
        "referential-integrity pattern shipped + gpt-oss reliability risk "
        "proven; future-job guard unbuilt",
    ),
    "NFR-005": (
        "PARTIALLY_INVESTIGATED",
        "shared spine shown in the prototype; production modularity unproven",
    ),
    "NFR-010": (
        "PARTIALLY_INVESTIGATED",
        "surface-level one-fail-flips proven; per-repo isolation untested",
    ),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    inv = yaml.safe_load(INVENTORY.read_text(encoding="utf-8"))
    rows = inv["requirements"]
    unknown_statuses = sorted({row["status"] for row in rows} - set(STATUS_DEFAULT))
    if unknown_statuses:
        print(f"ERROR: requirement statuses without coverage defaults: {unknown_statuses}")
        return 1
    out_rows = []
    for r in rows:
        rid, status = r["id"], r["status"]
        if rid in OVERRIDES:
            entry = OVERRIDES[rid]
            cls, note = entry[0], entry[1]
            route = entry[2] if len(entry) > 2 else ""
        else:
            cls, note = STATUS_DEFAULT[status]
            route = ""
        if rid in REVIEW_DOWNGRADES:
            cls, dnote = REVIEW_DOWNGRADES[rid]
            note = f"[review-downgraded] {dnote}"
        is_gap = cls in GAP_CLASSES
        p0p1_gap = is_gap and r["priority"] in ("P0", "P1")
        if p0p1_gap and not route:
            print(f"ERROR: P0/P1 gap without repair route: {rid}")
            return 1
        out_rows.append(
            {**r, "coverage": cls, "note": note, "repair_route": route, "p0p1_gap": p0p1_gap}
        )

    tot_cls = Counter(x["coverage"] for x in out_rows)
    tot_grp: dict[str, Counter] = {}
    for x in out_rows:
        tot_grp.setdefault(x["group"], Counter())[x["coverage"]] += 1
    p0p1_gaps = [x for x in out_rows if x["p0p1_gap"]]
    p0_gaps = [x for x in p0p1_gaps if x["priority"] == "P0"]

    # CSV
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=[
            "id",
            "group",
            "priority",
            "status",
            "coverage",
            "note",
            "repair_route",
            "section",
        ],
    )
    writer.writeheader()
    for x in out_rows:
        writer.writerow({k: x[k] for k in writer.fieldnames})
    csv_text = csv_buffer.getvalue().replace("\r\n", "\n")

    # Markdown report
    md = [
        "# Repository-Presentation Requirements Coverage Matrix",
        "",
        f"governed_by: `{GOVERNED_BY}`  ",
        "artifact_role: analysis_or_evidence_only  ",
        f"({inv['totals']['requirements']} requirements @ HEAD `{inv['source_head_commit'][:7]}`)",
        "",
        "Coverage counts a requirement only when this investigation defines all 10 "
        "elements (authoritative input, owner, current behavior, gap, target, state, "
        "failure handling, implementation direction, acceptance test, evidence). "
        "Judgments: per-ID overrides over status defaults, with an independent-review "
        "downgrade pass — see `tools/coverage_classify.py` for every note.",
        "",
        "## Totals by classification",
        "",
        "| Classification | Count |",
        "|---|---:|",
        *[f"| {k} | {v} |" for k, v in sorted(tot_cls.items(), key=lambda kv: -kv[1])],
        "",
        "## Totals by group x classification",
        "",
        "| Group | " + " | ".join(sorted(tot_cls)) + " | Total |",
        "|---|" + "---:|" * (len(tot_cls) + 1),
    ]
    for g in sorted(tot_grp):
        c = tot_grp[g]
        md.append(
            f"| {g} | "
            + " | ".join(str(c.get(k, 0)) for k in sorted(tot_cls))
            + f" | {sum(c.values())} |"
        )
    md += [
        "",
        "## Totals by priority",
        "",
        "| Priority | Total | In gap classes (NAMED_ONLY/DEFERRED_WITHOUT_DESIGN/MISSING) |",
        "|---|---:|---:|",
    ]
    for p in ("P0", "P1", "P2"):
        n = sum(1 for x in out_rows if x["priority"] == p)
        gp = sum(1 for x in out_rows if x["priority"] == p and x["coverage"] in GAP_CLASSES)
        md.append(f"| {p} | {n} | {gp} |")
    md += [
        "",
        f"## P0/P1 requirements in gap classes -- {len(p0p1_gaps)} (P0: {len(p0_gaps)})",
        "",
        "Every P0/P1 gap carries an explicit repair route (enforced by this script).",
        "",
        "| ID | Pri | Coverage | Why deferred | Repair route |",
        "|---|---|---|---|---|",
        *[
            f"| {x['id']} | {x['priority']} | {x['coverage']} | {x['note']} | {x['repair_route']} |"
            for x in p0p1_gaps
        ],
        "",
        "## Notes on contested classifications",
        "",
        "- **CORE-012 / CORE-031 / NFR-002** are `PARTIALLY_INVESTIGATED` despite "
        "IMPLEMENTED status: the current-state evidence proves the "
        "work-clone-as-durable-state design fails portability and ephemeral CI; "
        "routed to a supersession delta (work clone -> cache; `.state/` StateStore; "
        "idempotency strengthening).",
        "- **DOC-003/004/007, MET-001/002/006, OPS-001** are the only P1 gap-class "
        "rows: all are Phase-16/20 research/ops deliverables this investigation "
        "sprint intentionally does not perform; each is routed to an explicit "
        "roadmap card.",
        "- **No P0 requirement is in a gap class.** No requirement is `MISSING` or `NAMED_ONLY`.",
        "",
        "Full per-requirement rows: `control/requirements-coverage.csv`.",
    ]
    markdown_text = "\n".join(md) + "\n"
    if args.check:
        stale = [
            path.relative_to(REPO_ROOT)
            for path, expected in ((OUT_CSV, csv_text), (OUT_MD, markdown_text))
            if not path.exists() or path.read_text(encoding="utf-8") != expected
        ]
        if stale:
            print(f"stale: {', '.join(str(path) for path in stale)}")
            return 1
    else:
        OUT_CSV.write_text(csv_text, encoding="utf-8", newline="")
        OUT_MD.write_text(markdown_text, encoding="utf-8")

    print(f"classified: {len(out_rows)}  overrides: {len(OVERRIDES)}")
    print(f"by class: {dict(sorted(tot_cls.items()))}")
    print(f"P0/P1 gaps: {len(p0p1_gaps)} (P0: {len(p0_gaps)}) -> {[x['id'] for x in p0p1_gaps]}")
    verb = "current" if args.check else "wrote"
    print(f"{verb}: {OUT_MD.relative_to(REPO_ROOT)}")
    print(f"{verb}: {OUT_CSV.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
