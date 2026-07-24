"""Record evidence-bounded local immutable-snapshot and pilot-facts progress."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = ROOT / "plans" / "requirements.md"
EVIDENCE = "`plans/investigations/evidence/level8-local-immutable-snapshot-and-facts-2026-07-24/`"

UPDATES = {
    "FACT-001": (
        "PARTIAL",
        "The shared provider now ingests policy and mechanical evidence from one bound "
        "`RepositorySnapshotV1`. All three Java pilots have current, checksum-proven "
        f"`ProductFactsV2` graphs; portfolio and production ingestion remain open. {EVIDENCE}",
    ),
    "FACT-002": (
        "PARTIAL",
        "All 16 required fields are populated with accepted facts for Cells, 3D, and PDF Java. "
        "Capabilities, formats, coordinates, compatibility, release state, limitations, license, "
        "and examples cite repository evidence; audience/problem positioning cites approved "
        f"policy. Other registry repositories remain open. {EVIDENCE}",
    ),
    "FACT-006": (
        "PARTIAL",
        "The three pilot graphs prove stable IDs, source type/location, the same immutable source "
        "revision or explicit timed source, owner, confidence/state, conflicts, and affected "
        f"surfaces. Portfolio and production proof remain open. {EVIDENCE}",
    ),
    "FACT-007": (
        "PARTIAL",
        "Cells, PDF, and 3D source builds and their exact configured Java examples pass in "
        "disposable, secret-free copies; Temurin 21 is checksum-verified for 3D. The same "
        f"isolated job under `act`/Actions and other ecosystems remain open. {EVIDENCE}",
    ),
    "FACT-011": (
        "IMPLEMENTED",
        "`ProductFactsV1` remains a typed compatibility view for existing acquisition and diff "
        "consumers. The canonical provider now additionally resolves complete pilot "
        "`ProductFactsV2` graphs without changing the independent package-registry capability's "
        f"permission boundary. Tests and real pilot evidence: {EVIDENCE}",
    ),
    "RDM-007": (
        "PARTIAL",
        "Live Maven Central checks confirm all three pilot artifacts are unpublished, and "
        "disposable builds prove source-build acquisition for each exact revision. README "
        f"proposal integration and non-Java acquisition remain open. {EVIDENCE}",
    ),
    "RDM-008": (
        "PARTIAL",
        "Policy-selected, source-backed first-use examples now compile against successful "
        "disposable builds for all three Java pilots. Insertion into independently accepted "
        f"README proposals and heterogeneous example proof remain open. {EVIDENCE}",
    ),
    "RDM-025": (
        "PARTIAL",
        "The pre-effect factuality gate rejects the current Cells Maven claim after a live "
        "`NOT_PUBLISHED` result while the fact graph selects verified source build as acquisition. "
        f"Document-plan correction is the next task. {EVIDENCE}",
    ),
    "L8-006": (
        "PARTIAL",
        "`RepositorySnapshotV1` now binds all nested analysis to one revision. Complete accepted "
        "fact graphs, live registry outcomes, source builds/examples, historical checksums, and "
        "an independent factuality review pass for all three Java pilots. Portfolio production "
        f"proof and external owner resolution remain open. {EVIDENCE}",
    ),
    "L8-014": (
        "PARTIAL",
        "The truthful baseline and immutable-snapshot/product-truth child gates are now "
        "checksum-proven locally for all three pilots. Reviewer-ready README proposals, complete "
        f"local resilience, full `act`, and staging remain open in that order. {EVIDENCE}",
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
    REQUIREMENTS.write_text(
        "\n".join(output) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Updated {len(found)} immutable-snapshot/product-facts requirement rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
