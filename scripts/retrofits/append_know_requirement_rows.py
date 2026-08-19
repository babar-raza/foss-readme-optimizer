#!/usr/bin/env python3
"""One-shot: append the KNOW-001..012 requirement rows (imported-knowledge
application layer, Decision 106) to `plans/requirements/catalog.jsonl`.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/append_know_requirement_rows.py`
Kept after use as the executable record of what was appended (repo layout
placement rule 5 -- a one-shot script is never deleted "after use").
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

ROWS: list[dict] = [
    {
        "requirement_id": "KNOW-001",
        "section": "21. Imported knowledge application",
        "status": "IMPLEMENTED",
        "priority": "P1",
        "requirement": (
            "Production MUST load and index the complete imported aspose.org knowledge corpus "
            "(all documented claim kinds, every product/platform bundle) by product, platform, "
            "artifact type, claim type, source revision, and stable claim identity, retaining "
            "provenance, verification status, and source revision -- not only the dependency-kind "
            "subset."
        ),
        "acceptance_evidence": (
            "facts/aspose_knowledge_claims.py loads all 12 kinds across 31 real bundles (97,303 "
            "claims); tests/unit/test_aspose_knowledge_claims.py proves real-corpus loading, "
            "per-bundle provenance, and graceful degradation."
        ),
        "traceability": "Decision 106",
    },
    {
        "requirement_id": "KNOW-002",
        "section": "21. Imported knowledge application",
        "status": "IMPLEMENTED",
        "priority": "P1",
        "requirement": (
            "Evidence selection MUST use repository/section relevance and confidence ranking, "
            "never arbitrary first-N truncation, and MUST bound what reaches a candidate or "
            "prompt to a small, section-relevant slice while keeping the complete corpus "
            "deterministically checksum-bound."
        ),
        "acceptance_evidence": (
            "facts/aspose_knowledge_selection.py caps selection per fact field by confidence "
            "rank; data/imported/knowledge_manifest.json + "
            "scripts/data-refresh/build_imported_knowledge_manifest.py checksum the complete "
            "corpus; tests/unit/test_aspose_knowledge_selection.py proves bounded selection and "
            "confidence-based ranking against real over-supply."
        ),
        "traceability": "Decision 106",
    },
    {
        "requirement_id": "KNOW-003",
        "section": "21. Imported knowledge application",
        "status": "IMPLEMENTED",
        "priority": "P1",
        "requirement": (
            "Current repository evidence MUST win over imported knowledge on conflict; an "
            "imported claim whose bundle revision is stale or unmatched relative to the "
            "repository revision the current run observed MUST require corroboration or be "
            "carried at reduced, unverified confidence -- never silently promoted to verified "
            "truth."
        ),
        "acceptance_evidence": (
            "facts/aspose_knowledge_claims.py::assess_bundle_freshness + "
            "aspose_knowledge_selection.py's freshness-scaled confidence and license "
            "corroboration; tests/unit/test_aspose_knowledge_selection.py proves stale-revision "
            "rejection and real license corroboration/non-corroboration."
        ),
        "traceability": "Decision 106",
    },
    {
        "requirement_id": "KNOW-004",
        "section": "21. Imported knowledge application",
        "status": "PARTIAL",
        "priority": "P1",
        "requirement": (
            "A governance-compliant knowledge-application.json evidence artifact MUST be "
            "persisted per governed run, recording imported knowledge version/hashes, "
            "considered/selected/rejected claims and reasons, fact fields produced, and sections "
            "influenced."
        ),
        "acceptance_evidence": (
            "facts/knowledge_application_evidence.py wired into supervisor/product_truth.py + "
            "supervisor/local_poc_evidence.py::write_local_poc_knowledge_application(); "
            "tests/unit/test_knowledge_application_evidence.py proves real-corpus report "
            "building and determinism. Remaining gap: not yet proven through an actual "
            "end-to-end governed supervise run against a real registry repository -- pending "
            "bounded calibration."
        ),
        "traceability": "Decision 106",
    },
    {
        "requirement_id": "KNOW-005",
        "section": "21. Imported knowledge application",
        "status": "IMPLEMENTED",
        "priority": "P1",
        "requirement": (
            "Every vendored aspose.org check MUST be classified (applicable-reusable / "
            "applicable-after-adaptation / diagnostic-heuristic / unrelated) with an explicit "
            "reason, tracked as run/skipped/errored/not-applicable, and proven-applicable checks "
            "MUST become blocking acceptance gates -- never treating skipped as passed."
        ),
        "acceptance_evidence": (
            "scripts/data-refresh/classify_aspose_checks.py + "
            "data/aspose_check_classification.json classify all 89 checks; "
            "validation/aspose_checks_bridge.py::blocking_aspose_check_findings() promotes 10 "
            "empirically-validated checks to readme/document_validation.py's blocking errors; "
            "tests/unit/test_aspose_check_classification.py; verified against the 3 currently "
            "accepted candidates and this repo's full relevant unit-test suite with zero "
            "regressions."
        ),
        "traceability": "Decision 106",
    },
    {
        "requirement_id": "KNOW-006",
        "section": "21. Imported knowledge application",
        "status": "IMPLEMENTED",
        "priority": "P2",
        "requirement": (
            "Imported SEO keywords MUST be filtered for repository relevance (family/format/"
            "capability grounding) and platform-mismatch before becoming candidate evidence, "
            "with a negative test proving irrelevant and platform-mismatched terms are excluded."
        ),
        "acceptance_evidence": (
            "facts/aspose_detectors.py::detect_relevant_seo_keywords() adapts the vendored "
            "filter_relevant_seo_keywords(); facts/aspose_seo_keyword_facts.py projects the "
            "result into aspose.relevant_seo_keywords; "
            "tests/unit/test_aspose_seo_keyword_facts.py includes explicit negative "
            "platform-mismatch and ungrounded-keyword tests plus a drift-guard against the "
            "vendored source."
        ),
        "traceability": "Decision 106",
    },
    {
        "requirement_id": "KNOW-007",
        "section": "21. Imported knowledge application",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "Deterministic capability-title and Additional-Examples heading generation SHOULD "
            "consume the relevance-filtered imported SEO keyword vocabulary directly (today it "
            "derives titles only from verified format/capability facts), with explicit "
            "keyword-to-heading lineage recorded in evidence."
        ),
        "acceptance_evidence": (
            "Not implemented. presentation/verified_template_capability_seo.py's deterministic "
            "regex cascade does not read aspose.relevant_seo_keywords; rewiring it safely is a "
            "larger, higher-risk change than this session's budget covered."
        ),
        "traceability": "Decision 106",
    },
    {
        "requirement_id": "KNOW-008",
        "section": "21. Imported knowledge application",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "The agentic editorial layer SHOULD reason, through a validated structured "
            "contract, about visitor journey, capability/example selection and titling, "
            "dependency presentation, and existing-content disposition beyond today's scope "
            "(summaries, opening text, source decisions, fact selection, diagram vocabulary)."
        ),
        "acceptance_evidence": (
            "Not implemented this session -- readme/agentic_composition_models.py's existing "
            "contract is unchanged. A real, scoped expansion of "
            "ReadmeAgenticCompositionPlanV1 was judged too large to attempt safely without "
            "dedicated design/testing time."
        ),
        "traceability": "Decision 106",
    },
    {
        "requirement_id": "KNOW-009",
        "section": "21. Imported knowledge application",
        "status": "BACKLOG",
        "priority": "P3",
        "requirement": (
            "Regression tests derived from aspose.org's own imported content-disposition "
            "ledgers (data/imported/reports/repo-presenter/**/content-dispositions.json) "
            "SHOULD be added against this repo's existing "
            "claim_accountability/ClaimDispositionRecordV1 machinery to encode systemic "
            "reconciliation behavior natively."
        ),
        "acceptance_evidence": (
            "Not implemented this session. readme/claim_accountability_models.py::"
            "ClaimDispositionRecordV1 already exists and is wired; mining the imported corpus "
            "for regression-worthy patterns was not attempted."
        ),
        "traceability": "Decision 106",
    },
    {
        "requirement_id": "KNOW-010",
        "section": "21. Imported knowledge application",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "Dependency evidence (required/optional/dev/native-system, or explicitly-zero) "
            "SHOULD be built uniformly across every ecosystem in the active cohort; today "
            "Python/.NET/Rust have acquisition schemas but Java/TypeScript/Go/C++ do not."
        ),
        "acceptance_evidence": (
            "Not implemented this session. facts/python_dependency_schema.py, "
            "facts/dotnet_dependency_schema.py, facts/rust_dependency_schema.py exist; no "
            "equivalent module exists for java/typescript/go/cpp (confirmed by direct source "
            "audit during this session's research phase)."
        ),
        "traceability": "Decision 106",
    },
    {
        "requirement_id": "KNOW-011",
        "section": "21. Imported knowledge application",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "The 51 vendored checks currently blocked on missing production inputs "
            "(dependency_snapshot, content_units, available_badges, reference_index, etc.) "
            "SHOULD have those inputs constructed so they can be reclassified beyond "
            "applicable-after-adaptation; the 3 checks found this session to false-positive "
            "against this repo's own real content (check_process_narration_smells, "
            "check_scope_limitations_format, check_no_excluded_domain_links) SHOULD be either "
            "narrowed or reconciled with this repo's template."
        ),
        "acceptance_evidence": (
            "Not implemented this session. data/aspose_check_classification.json records the "
            "exact reason and evidence for every non-blocking check."
        ),
        "traceability": "Decision 106",
    },
    {
        "requirement_id": "KNOW-012",
        "section": "21. Imported knowledge application",
        "status": "BACKLOG",
        "priority": "P1",
        "requirement": (
            "Investigate whether readme/document_link_hygiene.py has a real gap allowing "
            "forum.aspose.com/*.aspose.app links to survive into a rendered candidate -- "
            "discovered live this session when check_no_excluded_domain_links fired on a real "
            "captured NET fixture candidate; excluded from blocking promotion only to avoid "
            "breaking that existing test, not because the finding was judged false."
        ),
        "acceptance_evidence": (
            "Not investigated this session. See data/aspose_check_classification.json's "
            "check_no_excluded_domain_links entry and "
            "tests/unit/test_readme_existing_section_regressions.py::"
            "test_real_net_partial_sections_preserve_maintainer_content_without_fact_duplication "
            "for the reproducing evidence."
        ),
        "traceability": "Decision 106",
    },
]


def main() -> None:
    existing_ids = set()
    with CATALOG_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            existing_ids.add(json.loads(line)["requirement_id"])
    new_rows = [row for row in ROWS if row["requirement_id"] not in existing_ids]
    if not new_rows:
        print("no new rows to append (already present)")
        return
    with CATALOG_PATH.open("a", encoding="utf-8", newline="\n") as handle:
        for row in new_rows:
            row = {**row, "schema_version": 1}
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"appended {len(new_rows)} requirement rows to {CATALOG_PATH}")


if __name__ == "__main__":
    main()
