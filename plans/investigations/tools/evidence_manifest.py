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
import subprocess
import sys
from argparse import ArgumentParser
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


def _source_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
    ).strip()


def _inventory_paths() -> list[Path]:
    """Return clone-reproducible and deliberate untracked investigation files."""

    result = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "plans/investigations",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [REPO_ROOT / relative for relative in result.stdout.splitlines() if relative]


def _build_manifest(*, source_head_commit: str) -> dict[str, object]:
    entries: dict[str, str] = {}
    secret_hits: list[str] = []
    for p in sorted(_inventory_paths()):
        if not p.is_file() or p.resolve() == OUT.resolve():
            continue
        rel = p.relative_to(REPO_ROOT).as_posix()
        entries[rel] = sha256_norm(p)
        try:
            if SECRET_RE.search(p.read_text(encoding="utf-8", errors="ignore")):
                secret_hits.append(rel)
        except Exception:  # noqa: BLE001
            pass
    return {
        "governed_by": ["plans/master.md", "plans/requirements.md", "plans/GOVERNANCE.md"],
        "artifact_role": "analysis_or_evidence_only",
        "source_head_commit": source_head_commit,
        "file_count": len(entries),
        "secret_scan_hits": secret_hits,
        "sha256_crlf_normalized": entries,
    }


def _verify_committed_manifest(actual: dict[str, object]) -> list[str]:
    if not OUT.is_file():
        return [f"missing manifest: {OUT.relative_to(REPO_ROOT)}"]
    try:
        recorded = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid manifest: {exc}"]
    failures: list[str] = []
    for key in ("file_count", "secret_scan_hits", "sha256_crlf_normalized"):
        if recorded.get(key) != actual.get(key):
            failures.append(f"{key} does not match current investigation evidence")
    source_head = recorded.get("source_head_commit")
    if not isinstance(source_head, str) or len(source_head) != 40:
        failures.append("source_head_commit is not a full Git commit")
    else:
        completed = subprocess.run(
            ["git", "cat-file", "-e", f"{source_head}^{{commit}}"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            failures.append("source_head_commit does not resolve to a repository commit")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the existing manifest without rewriting it",
    )
    args = parser.parse_args(argv)
    manifest = _build_manifest(source_head_commit=_source_head())
    if args.check:
        failures = _verify_committed_manifest(manifest)
        if failures:
            for failure in failures:
                print(f"FAILED: {failure}")
            return 1
        print(f"verified: {OUT.relative_to(REPO_ROOT)}")
        return 0
    OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"files: {manifest['file_count']}  secret_hits: {manifest['secret_scan_hits'] or 'none'}")
    print(f"wrote: {OUT.relative_to(REPO_ROOT)}")
    return 1 if manifest["secret_scan_hits"] else 0


if __name__ == "__main__":
    sys.exit(main())
