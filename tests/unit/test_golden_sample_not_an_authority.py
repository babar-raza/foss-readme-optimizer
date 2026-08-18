"""T2 -- golden-sample retirement is enforced mechanically, not just claimed in prose.

See plans/investigations/evidence/golden-sample-harvest-v1/RETIREMENT-STAMP.md for the
scope note: this concerns only the freshness-service plan's own composition machinery,
not the separate, currently-active POC-freeze track that also references golden-sample/.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_no_production_code_reads_golden_sample_as_an_authority() -> None:
    offenders = []
    for directory in ("src", "scripts"):
        root = REPO_ROOT / directory
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "golden-sample" in text or "golden_sample" in text:
                offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == [], (
        "golden-sample/ must not be read as a runtime authority by production code; "
        f"found references in: {offenders}"
    )
