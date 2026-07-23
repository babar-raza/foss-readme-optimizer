"""Record evidence-bounded Wave-3 local product-truth requirement status."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = ROOT / "plans" / "requirements.md"
EVIDENCE = "`plans/investigations/evidence/level8-wave3-local-product-truth-foundation-2026-07-23/`"

UPDATES = {
    "OWN-001": (
        "GOVERNANCE",
        f"`registry/surface_ownership.py` materializes exactly one class for every known surface; "
        f"unknown surfaces fail closed. Local proof: {EVIDENCE}.",
    ),
    "OWN-002": (
        "GOVERNANCE",
        "The typed ownership schema permits only `repository_file`, `settings_api`, `manual_ui`, "
        "`product_owned`, and `github_generated`; tested in "
        "`tests/unit/test_surface_ownership.py`. "
        f"Local proof: {EVIDENCE}.",
    ),
    "OWN-010": (
        "PARTIAL",
        "`facts/resolution.py` records same-precedence disagreement as unresolved and "
        "`facts/gating.py` blocks affected surfaces. A real external product-owner handoff and "
        f"owner-resolution lifecycle remain open. Local proof: {EVIDENCE}.",
    ),
    "OWN-011": (
        "PARTIAL",
        "`facts/gating.py` and `specialists/readme_factuality.py` now prevent metadata/README "
        "effects where facts or protected-content rules do not permit them. General "
        f"cross-specialist region ownership remains open. Local proof: {EVIDENCE}.",
    ),
    "OWN-014": (
        "PARTIAL",
        "`SurfaceOwnershipMapV1` records required permission and rollback for every settings/API "
        "surface. Propagation into every proposal/effect manifest remains open. "
        f"Local proof: {EVIDENCE}.",
    ),
    "OWN-015": (
        "PARTIAL",
        "The ownership map distinguishes audit, proposal, local patch, manual apply, and remote "
        f"apply modes. Every terminal evidence manifest does not yet carry this classification. "
        f"Local proof: {EVIDENCE}.",
    ),
    "FACT-001": (
        "PARTIAL",
        "`get_product_facts` now emits provenance-complete `ProductFactsV2`; the README specialist "
        "obtains it before its verifier/effect boundary. Full-field ingestion and every "
        f"product-facing specialist remain open. Real read-only proof: {EVIDENCE}.",
    ),
    "FACT-002": (
        "PARTIAL",
        "`schema_v2.py` requires identity, audience, problems, capabilities, formats, platforms, "
        "installation/acquisition, example, docs, release, limitations, compatibility, license, "
        "support, and commercial/FOSS relationship selections. Unavailable values remain explicit "
        f"`missing`, not invented; their ingestion is open. Local proof: {EVIDENCE}.",
    ),
    "FACT-003": (
        "PARTIAL",
        "`TechnicalClaimV1`/`validate_claim_citations()` enforce fact IDs, accepted verification "
        "state, and affected-surface membership; metadata proposals emit citations. Coverage of "
        f"every technical-claim producer remains open. Local proof: {EVIDENCE}.",
    ),
    "FACT-004": (
        "PARTIAL",
        "Missing facts block dependent metadata actions and prevent generic description/topic "
        "replacement while an independent homepage action can continue. All surfaces and a real "
        f"product-owner handoff remain open. Real isolation proof: {EVIDENCE}.",
    ),
    "FACT-005": (
        "PARTIAL",
        "`resolve_product_facts()` applies explicit precedence, preserves conflicting provenance, "
        "and marks same-rank disagreement unresolved; affected-surface gating is built. External "
        f"owner resolution remains open. Local proof: {EVIDENCE}.",
    ),
    "FACT-006": (
        "PARTIAL",
        "`FactRecordV2` requires stable ID/field, value, source type/location/revision or "
        "retrieval "
        "time, owner, confidence, state, conflicts, and affected surfaces. Portfolio-wide real "
        f"fact population remains open. Local and Cells/Java proof: {EVIDENCE}.",
    ),
    "FACT-007": (
        "PARTIAL",
        "`facts/example_execution.py` provides a bounded, secret-free, no-shell process boundary "
        "with descendant cleanup and redacted output. Real isolated per-ecosystem example "
        "execution "
        f"in disposable Actions jobs remains open. Security tests: {EVIDENCE}.",
    ),
    "FACT-009": (
        "PARTIAL",
        "`facts/protected_content.py` fingerprints limitation sections, and the README pre-effect "
        "gate rejects their removal. Semantic weakening beyond removal and portfolio proof remain "
        f"open. Local protected-loss proof: {EVIDENCE}.",
    ),
    "FACT-010": (
        "PARTIAL",
        "`facts/gating.py` supplies the fact-to-surface dependency map and metadata consumes it "
        "for "
        "independent blocking. Fact-change-driven targeted scheduling for every presentation "
        f"section remains open. Local proof: {EVIDENCE}.",
    ),
    "RDM-025": (
        "PARTIAL",
        "`specialists/readme_factuality.py` now dispatches live package acquisition before a "
        "README "
        "effect and rejects a candidate retaining a positively false coordinate; the real "
        "Cells/Java claim is proven blocked. Product-aware corrective wording and "
        "freshness-triggered "
        f"rerendering remain open. Real proof: {EVIDENCE}.",
    ),
    "L8-006": (
        "PARTIAL",
        "`ProductFactsV2`, explicit V1 migration, precedence/conflicts, dependent-surface gating, "
        "ownership, README-claim distrust, and a real Cells/Java false-coordinate rejection are "
        "built and checksum-proven. Full-field ingestion, external owner resolution, and "
        f"portfolio production proof remain open. Evidence: {EVIDENCE}.",
    ),
    "L8-007": (
        "PARTIAL",
        "`markdown-it-py` protected-content fingerprints and the README pre-effect rejection gate "
        "cover terminology, commands, examples, limitations, and maintainer regions. "
        "`RepositoryPresentationPlanV1`, source-span planning, and full golden-set proof remain "
        f"open. Evidence: {EVIDENCE}.",
    ),
}


def main() -> int:
    lines = REQUIREMENTS.read_text(encoding="utf-8").splitlines()
    found: set[str] = set()
    output: list[str] = []
    for line in lines:
        requirement_id = next(
            (candidate for candidate in UPDATES if line.startswith(f"| {candidate} |")),
            None,
        )
        if requirement_id is None:
            output.append(line)
            continue
        cells = line.split("|")
        if len(cells) != 8:
            raise RuntimeError(f"cannot safely update malformed row {requirement_id}")
        status, evidence = UPDATES[requirement_id]
        cells[3] = f" {status} "
        cells[5] = f" {evidence} "
        output.append("|".join(cells))
        found.add(requirement_id)

    missing = set(UPDATES) - found
    if missing:
        raise RuntimeError(f"requirements not found: {sorted(missing)}")
    REQUIREMENTS.write_text("\n".join(output) + "\n", encoding="utf-8", newline="\n")
    print(f"Updated {len(found)} Wave-3 requirement rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
