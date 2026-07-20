# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)
# artifact_role: analysis_or_evidence_only
"""Emit a checksum manifest over all investigation evidence so the bundle is
tamper-evident (SAFE-008/009 hygiene). CRLF-normalized sha256, matching the shipped
evidence writer's convention. Also re-scans for secret patterns and records the clean
result in the manifest."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
INV = REPO_ROOT / "plans" / "investigations"
OUT = INV / "control" / "evidence-sha256-manifest.json"

SECRET_RE = re.compile(
    r"ghp_[A-Za-z0-9]{20}|ghu_[A-Za-z0-9]{20}|sk-[A-Za-z0-9]{20}"
    r"|AIzaSy[A-Za-z0-9_-]{20}|Bearer\s+[A-Za-z0-9._-]{12}"
)


def sha256_norm(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main() -> int:
    entries: dict[str, str] = {}
    secret_hits: list[str] = []
    for p in sorted(INV.rglob("*")):
        if not p.is_file() or p.name == OUT.name:
            continue
        rel = p.relative_to(REPO_ROOT).as_posix()
        entries[rel] = sha256_norm(p)
        try:
            if SECRET_RE.search(p.read_text(encoding="utf-8", errors="ignore")):
                secret_hits.append(rel)
        except Exception:  # noqa: BLE001
            pass
    manifest = {
        "governed_by": ["plans/master.md", "plans/requirements.md", "plans/GOVERNANCE.md"],
        "artifact_role": "analysis_or_evidence_only",
        "source_head_commit": "4adbaaf33d3c733afc8f9c9a14761f10e5b10d7c",
        "file_count": len(entries),
        "secret_scan_hits": secret_hits,
        "sha256_crlf_normalized": entries,
    }
    OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"files: {len(entries)}  secret_hits: {secret_hits or 'none'}")
    print(f"wrote: {OUT.relative_to(REPO_ROOT)}")
    return 1 if secret_hits else 0


if __name__ == "__main__":
    sys.exit(main())
