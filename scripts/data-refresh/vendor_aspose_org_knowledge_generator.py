"""Vendor the qualified deterministic Aspose.org knowledge extractor from Git objects."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

SOURCE_FILES = (
    "scripts/pipeline/extraction/__init__.py",
    "scripts/pipeline/extraction/api_surface.py",
    "scripts/pipeline/extraction/claims.py",
    "scripts/pipeline/extraction/formats.py",
    "scripts/pipeline/extraction/outputs.py",
    "scripts/pipeline/extraction/package_manifest.py",
    "scripts/pipeline/extraction/package_root.py",
    "scripts/pipeline/extraction/scout.py",
    "scripts/pipeline/extraction/snippets.py",
    "scripts/pipeline/extraction/tree_helpers.py",
    "scripts/pipeline/extraction/validate_scout_output.py",
    "scripts/pipeline/scout_enrichers/README.md",
    "scripts/pipeline/scout_enrichers/__init__.py",
    "scripts/pipeline/scout_enrichers/_doxygen.py",
    "scripts/pipeline/scout_enrichers/_javadoc.py",
    "scripts/pipeline/scout_enrichers/_xml_doc.py",
)
SCHEMA_VERSION = "1.1"


def _destination_relative(source_path: str) -> str:
    extraction_prefix = "scripts/pipeline/extraction/"
    enricher_prefix = "scripts/pipeline/scout_enrichers/"
    if source_path.startswith(extraction_prefix):
        return source_path.removeprefix(extraction_prefix)
    if source_path.startswith(enricher_prefix):
        return "../scout_enrichers/" + source_path.removeprefix(enricher_prefix)
    raise ValueError(f"source file is outside the qualified pipeline paths: {source_path}")


def _git(source: Path, *args: str, text: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", "-C", str(source), *args],
        capture_output=True,
        text=text,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() if text else result.stderr.decode(errors="replace").strip()
        raise ValueError(detail or f"git {' '.join(args)} failed")
    return result.stdout


def _canonical_sha256(files: dict[str, dict[str, object]]) -> str:
    identities = {
        path: {
            "blob": item["git_blob"],
            "sha256": item["sha256"],
            "bytes": item["bytes"],
        }
        for path, item in sorted(files.items())
    }
    payload = json.dumps(identities, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _load_existing(manifest_path: Path) -> dict[str, object] | None:
    if not manifest_path.is_file():
        return None
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("existing generator manifest must be an object")
    return payload


def _guard_local_edits(destination: Path, existing: dict[str, object] | None) -> None:
    if existing is None:
        return
    records = existing.get("files")
    if not isinstance(records, dict):
        raise ValueError("existing generator manifest has no file inventory")
    for source_path, raw in records.items():
        if not isinstance(source_path, str) or not isinstance(raw, dict):
            raise ValueError("existing generator manifest file inventory is invalid")
        relative = raw.get("destination")
        expected = raw.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ValueError(f"invalid manifest record for {source_path}")
        path = destination / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual != expected:
            raise ValueError(
                f"refusing to overwrite locally changed vendored file: {path} "
                f"(expected {expected}, found {actual})"
            )


def vendor(
    source: Path, revision: str, destination: Path, manifest_path: Path
) -> dict[str, object]:
    """Copy an exact allow-listed committed extractor revision and return its manifest."""

    source = source.resolve()
    commit = str(_git(source, "rev-parse", f"{revision}^{{commit}}", text=True)).strip()
    existing = _load_existing(manifest_path)
    _guard_local_edits(destination, existing)
    records: dict[str, dict[str, object]] = {}
    staged: dict[Path, bytes] = {}
    for source_path in SOURCE_FILES:
        content = _git(source, "show", f"{commit}:{source_path}")
        assert isinstance(content, bytes)
        blob = str(_git(source, "rev-parse", f"{commit}:{source_path}", text=True)).strip()
        relative = _destination_relative(source_path)
        staged[destination / relative] = content
        records[source_path] = {
            "destination": relative,
            "git_blob": blob,
            "sha256": hashlib.sha256(content).hexdigest(),
            "bytes": len(content),
        }
    for path, content in staged.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "source_repository": "aspose.org",
        "source_path": "scripts/pipeline/{extraction,scout_enrichers}",
        "source_commit": commit,
        "import_policy": "committed_git_objects_allowlist",
        "qualified_scope": [
            "deterministic_repository_scout",
            "api_surface_extraction",
            "format_direction_extraction",
            "limitation_detection",
            "snippet_extraction",
            "deterministic_javadoc_enrichment",
            "deterministic_doxygen_enrichment",
            "deterministic_xml_doc_enrichment",
        ],
        "explicitly_not_imported_as_authority": [
            "llm_enrichment_confidence",
            "promotion_and_indexing_controller",
            "site_state",
            "upstream_fact_graph",
        ],
        "files": dict(sorted(records.items())),
    }
    manifest["aggregate_sha256"] = _canonical_sha256(records)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path("src/readme_agent/vendored_asposeorg/scripts/pipeline/extraction"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/imported/aspose_org_knowledge_generator_manifest.json"),
    )
    args = parser.parse_args()
    manifest = vendor(args.source_root, args.revision, args.destination, args.manifest)
    print(json.dumps({"source_commit": manifest["source_commit"], "files": len(SOURCE_FILES)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
