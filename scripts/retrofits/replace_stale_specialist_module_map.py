"""Replace the stale monolithic specialist module-map row with current truth."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHITECTURE = ROOT / "docs" / "architecture.md"
PREFIX = "| `specialists/` | "
STALE_ASSERTION = "Repository reconciliation, generated-surface audit"
REPLACEMENT = (
    "| `specialists/` | `registry.py` owns registry-driven domain ordering, dependency checks, "
    "and complete domain registration. `readme_reconciliation.py`, "
    "`github_generated_surface_audit.py`, `package_release_audit.py`, "
    "`metadata_presentation.py`, `community_files_presentation.py`, "
    "`cross_surface_validation.py`, `readme_presentation.py`, `visual_preparation.py`, "
    "`presentation_benchmarking.py`, and `independent_verification.py` run through typed "
    "capability dispatch. `metadata_presentation.py` dispatches only "
    "`propose_metadata_changes(org_repo)`; that capability independently derives facts through "
    "`facts/provider.py`. `readme_presentation.py` alone reaches the local README effect, only "
    "after factuality and independent-verification gates. |"
)


def main() -> int:
    lines = ARCHITECTURE.read_text(encoding="utf-8").splitlines()
    matches = [index for index, line in enumerate(lines) if line.startswith(PREFIX)]
    if len(matches) != 1:
        raise RuntimeError(f"expected one specialists module-map row, found {len(matches)}")
    index = matches[0]
    if STALE_ASSERTION not in lines[index]:
        raise RuntimeError("specialists row no longer contains the guarded stale assertion")
    lines[index] = REPLACEMENT
    ARCHITECTURE.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("Replaced stale specialists module-map row")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
