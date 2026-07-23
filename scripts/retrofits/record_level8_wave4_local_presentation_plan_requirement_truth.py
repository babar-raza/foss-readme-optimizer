"""Record evidence-bounded Wave-4 local presentation-plan requirement status."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = ROOT / "plans" / "requirements.md"
EVIDENCE = (
    "`plans/investigations/evidence/level8-wave4-local-presentation-plan-foundation-2026-07-23/`"
)

UPDATES = {
    "OWN-011": (
        "PARTIAL",
        "`RepositoryPresentationPlanV1` now binds each README action to the policy-derived "
        "ownership class and an operation matrix enforced by the typed contract before "
        "verification. Metadata and README are fact-gated; complete cross-specialist region "
        "enforcement remains open. "
        f"Local proof: {EVIDENCE}.",
    ),
    "FACT-003": (
        "PARTIAL",
        "`TechnicalClaimV1` citations now gate metadata proposals and every executable README "
        "resources action in `RepositoryPresentationPlanV1`; the candidate's actual license, "
        "URLs, and relationship prose must match their selected fact values, and losing, "
        "missing, conflicting, or wrong-surface facts fail closed. Other technical-claim "
        "producers remain open. "
        f"Local proof: {EVIDENCE}.",
    ),
    "RDM-003": (
        "PARTIAL",
        "The structured README planner permits only one marker-owned source-span action and native "
        "Git proves the candidate patch; whole-document or outside-span changes are rejected. "
        "Future approved regions and portfolio-level template-similarity proof remain open. "
        f"Local proof: {EVIDENCE}.",
    ),
    "RDM-004": (
        "PARTIAL",
        "Every executable README resources action now records its exact UTF-8 byte span, selected "
        "fact citations, ownership class, operation, validators, rollback, and stop conditions; "
        "the render revision and source hash are bound into the plan, while stale, overlapping, "
        "unsafe-path, malformed-hash, or outside-span edits fail before verification. Other "
        f"presentation surfaces remain open. Local proof: {EVIDENCE}.",
    ),
    "L8-007": (
        "PARTIAL",
        "`RepositoryPresentationPlanV1` is built and wired before README candidate verification. "
        "It carries ten-dimension findings plus revision-bound, semantically fact-backed, "
        "ownership-compatible, hash-guarded source-span actions checked by native Git; "
        "protected-content loss remains a separate pre-effect rejection gate. Complete "
        "cross-surface plans, archetype depth, and the governed golden-set threshold remain "
        f"open. Evidence: {EVIDENCE}.",
    ),
}


def main() -> int:
    lines = REQUIREMENTS.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    found: set[str] = set()
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
    print(f"Updated {len(found)} Wave-4 local requirement rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
