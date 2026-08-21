"""Import current Aspose.org presentation ledgers as non-authoritative local hints."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from readme_agent.facts.presentation_hint_anchors import technical_anchors
from readme_agent.facts.presentation_knowledge_schema import (
    PresentationKnowledgeCatalogV1,
    PresentationKnowledgeHintV1,
)

_FIELDS = {
    "Key Capabilities": "product.capabilities",
    "Scope and Limitations": "product.limitations",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_sha256(paths: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git_value(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _clean_text(value: object) -> str:
    text = str(value or "").strip()
    return re.sub(r"^[-*]\s+", "", text).strip()


def build_catalog(source_root: Path, registry_path: Path) -> PresentationKnowledgeCatalogV1:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    expected = sorted(
        (str(row["family"]), str(row["platform"]))
        for row in registry
        if str(row["family"]).casefold() != "psd"
    )
    files = sorted(source_root.glob("*/*/content-dispositions.json"))
    observed = sorted((path.parent.parent.name, path.parent.name) for path in files)
    if observed != expected:
        missing = sorted(set(expected) - set(observed))
        extra = sorted(set(observed) - set(expected))
        raise ValueError(
            f"presentation knowledge denominator mismatch: missing={missing}, extra={extra}"
        )

    hints: list[PresentationKnowledgeHintV1] = []
    for path in files:
        family, platform = path.parent.parent.name, path.parent.name
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload:
            section = str(row.get("target_section") or "")
            verification = row.get("verification") or {}
            if (
                section not in _FIELDS
                or verification.get("status") != "verified_against_source"
                or verification.get("evidence_type") != "clone_cache_path"
                or not verification.get("evidence_ref")
            ):
                continue
            text = _clean_text(row.get("excerpt"))
            anchors = technical_anchors(text, list(row.get("salient_tokens") or []))
            if not text or not anchors:
                continue
            hints.append(
                PresentationKnowledgeHintV1(
                    family=family,
                    platform=platform,
                    unit_id=str(row.get("unit_id") or "unknown"),
                    field=_FIELDS[section],
                    text=text,
                    evidence_path=str(verification["evidence_ref"]).replace("\\", "/"),
                    anchors=anchors,
                    source_file_sha256=_sha256(path),
                )
            )

    status = _git_value(source_root, "status", "--short", "--untracked-files=all")
    return PresentationKnowledgeCatalogV1(
        producer_head=_git_value(source_root, "rev-parse", "HEAD"),
        producer_dirty_fingerprint=hashlib.sha256(status.encode("utf-8")).hexdigest(),
        source_tree_sha256=_tree_sha256(files, source_root),
        repository_count=len(expected),
        source_file_count=len(files),
        hints=sorted(
            hints, key=lambda item: (item.family, item.platform, item.unit_id, item.field)
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--registry", type=Path, default=Path("data/products.json"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/imported/presentation_knowledge.json"),
    )
    args = parser.parse_args()
    catalog = build_catalog(args.source_root.resolve(), args.registry.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(catalog.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "repositories": catalog.repository_count,
                "source_files": catalog.source_file_count,
                "hints": len(catalog.hints),
                "producer_head": catalog.producer_head,
                "source_tree_sha256": catalog.source_tree_sha256,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
