#!/usr/bin/env python3
"""One-shot: log a backlog row for a confirmed operational gap found on
2026-08-27 while promoting aspose-3d-foss/Aspose.3D-FOSS-for-Python to
NO_OP_PROVEN: `readme-agent portfolio-proof --mode fleet/failed-only` can
never refresh its own registry revision cache. Three separate retries
(`--only "aspose-3d-foss/Aspose.3D-FOSS-for-Python"`, one with a
freshly-fetched GH_TOKEN) all failed identically with "registry revision is
not eligible for portfolio fan-out: source_scan_stale" once the cached
revision crossed its 24h freshness TTL
(src/readme_agent/registry/revision.py's default `freshness_ttl=timedelta
(days=1)`).

Root cause: `build_registry_supervise_namespace()`
(src/readme_agent/supervisor/portfolio_proof_engine/mode_shared.py:111)
unconditionally sets `no_registry_heal=True` on the internal argparse
namespace it builds for every portfolio-proof mode -- there is no CLI flag
on `portfolio-proof` to override this, unlike the plain `supervise` command
where `--no-registry-heal` defaults to off. The `--no-registry-heal` CLI
help text says "a dedicated once-per-pass job heals instead", but no code
path was found that runs such a job automatically; the registry can only be
refreshed by invoking the plain `readme-agent supervise --registry
data/products.json --execution-profile local_poc [--only ...]` command
directly (confirmed live: this refreshed runs/registry-heal/last_heal.json
and runs/registry-revisions/current.json, and cleared the gate reason
immediately). Any `portfolio-proof` fleet pass spanning the 24h TTL boundary
will hit this identically, with no self-recovery.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/log_gov014_portfolio_proof_registry_heal_gap.py`
Kept after use as the executable record of what was appended (repo layout
placement rule 5).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

ROWS: list[dict] = [
    {
        "requirement_id": "OPS-014",
        "section": "10. README generation requirements",
        "status": "BACKLOG",
        "priority": "P2",
        "requirement": (
            "`readme-agent portfolio-proof` (all modes) MUST have a way to refresh its "
            "registry revision when the cached one goes stale, or the `--no-registry-heal` "
            "CLI help text's claim that 'a dedicated once-per-pass job heals instead' MUST be "
            "made true by wiring an actual heal call into the fleet/failed-only entry path -- "
            "currently neither exists, so any portfolio-proof pass spanning the 24h freshness "
            "TTL fails closed with no self-recovery path."
        ),
        "acceptance_evidence": (
            "OPS014-REGISTRY-HEAL-GAP-001 (2026-08-27): confirmed live while promoting "
            "aspose-3d-foss/Aspose.3D-FOSS-for-Python to NO_OP_PROVEN. Three separate "
            "`readme-agent portfolio-proof --mode fleet --retry-blocked --only "
            '"aspose-3d-foss/Aspose.3D-FOSS-for-Python"` retries (one with a freshly-fetched '
            "GH_TOKEN via `GH_TOKEN=$(env -u GH_TOKEN -u GITHUB_TOKEN -u GITHUB_PAT gh auth "
            'token)`) all failed identically with "registry revision is not eligible for '
            "portfolio fan-out: source_scan_stale\" once runs/registry-revisions/current.json's "
            "fresh_until (captured_at + 1 day, src/readme_agent/registry/revision.py) had "
            "passed. runs/registry-heal/last_heal.json never updated across all three retries. "
            "Root cause: build_registry_supervise_namespace() "
            "(src/readme_agent/supervisor/portfolio_proof_engine/mode_shared.py:111) "
            "unconditionally sets no_registry_heal=True for every portfolio-proof mode -- no "
            "flag exists to override it. Confirmed fix (workaround, not a code change): running "
            "the plain `readme-agent supervise --registry data/products.json "
            '--execution-profile local_poc --only "aspose-3d-foss/Aspose.3D-FOSS-for-Python"` '
            "(heal enabled by default on this command) refreshed both files immediately and the "
            "very next portfolio-proof retry then succeeded, reaching NO_OP_PROVEN with "
            "provider_calls=0. This workaround should be used whenever a portfolio-proof pass "
            "reports source_scan_stale; the code gap itself remains open."
        ),
        "traceability": (
            "GOV-014; found while restoring the mission's NO_OP_PROVEN milestone, 2026-08-27"
        ),
    },
]


def _synthetic_hash(marker: str) -> str:
    return hashlib.sha256(f"native-authored:{marker}".encode()).hexdigest()


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    existing = {json.loads(line)["requirement_id"] for line in lines}
    new_rows = [row for row in ROWS if row["requirement_id"] not in existing]
    if not new_rows:
        print("no new rows to append (already present)")
        return
    for row in new_rows:
        record = {
            **row,
            "schema_version": 1,
            "legacy_line": len(lines) + 1,
            "legacy_row_sha256": _synthetic_hash(row["requirement_id"]),
        }
        lines.append(json.dumps(record, ensure_ascii=False))
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"appended {len(new_rows)} requirement rows to {CATALOG_PATH}")


if __name__ == "__main__":
    main()
