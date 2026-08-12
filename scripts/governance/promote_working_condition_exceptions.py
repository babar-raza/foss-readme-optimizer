"""Promote human-accepted working-condition-presentation exception READMEs.

This is a deliberately SEPARATE lane from `promote_finalized_verified_readmes.py`. That script
promotes README candidates that cleared the full two-transaction, zero-provider-call
`TRANSACTION_NO_OP_PROVEN` `supervise` pipeline. Decision #100 keeps `readme-agent poc` output
diagnostic-only by default: it cannot independently issue delivery, approval, or no-op states.

This script promotes candidates delivered through the `readme-agent poc` working-condition-
presentation path (Decision #99) for repositories a human has EXPLICITLY accepted, per repository,
because a genuine, evidence-backed *upstream* defect (not an agent-fixable gap) currently prevents
the strict pipeline from ever passing -- see Decision #101. The only repositories this script is
permitted to touch are those listed in `data/working_condition_exceptions.json`; that registry is
hand-maintained (never auto-populated) and is the acceptance record this script enforces against.

Every promoted repository keeps full provenance: the exact poc-bundle `validation.json` verdict,
the acceptance record explaining who accepted the exception and why, and the resume predicate that
returns the repository to the strict lane once upstream is fixed. A promotion here is never
counted as `NO_OP_PROVEN` and never satisfies Gate A/B or full-registry closure -- its evidence
tree is kept structurally separate from `finalized-repository-readmes-v1/repositories/` so that
tree's own clean rebuild (`promote_finalized_verified_readmes.py`) never mixes with, or silently
drops, an exception promoted here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

from readme_agent.evidence.promotion_paths import compact_readme_path
from readme_agent.evidence.writer import refresh_sha256sums, verify_sha256sums
from readme_agent.registry.loader import NotAllowlistedError, require_listed

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "data" / "working_condition_exceptions.json"
POC_SHARE_ROOT = REPO_ROOT / "runs" / "share" / "poc"
DEFAULT_OUTPUT = (
    REPO_ROOT / "plans/investigations/evidence/working-condition-presentation-exceptions-v1"
)
VERDICT = "HUMAN_ACCEPTED_WORKING_CONDITION_EXCEPTION"
REQUIRED_REGISTRY_FIELDS = {
    "repository",
    "platform",
    "family",
    "accepted_date",
    "accepted_by",
    "acceptance_basis",
    "blocking_defect_summary",
    "resume_predicate",
}
REQUIRED_BUNDLE_FILES = ("README.md", "UPSTREAM-DEFECTS.md", "validation.json")
OPTIONAL_BUNDLE_FILES = ("dispositions.json", "noop.json", "agentic-composition-plan.json")


class ExceptionAcceptanceError(ValueError):
    """A registry entry's poc bundle no longer supports the recorded acceptance."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _reject_symlinks(root: Path) -> None:
    """Fail before any mutation if a symlink has been introduced into the tree -- mirrors
    `finalized_promotion_layout._reject_symlinks()`'s check for the same reason: this script
    also deletes and rewrites a whole subtree, and a symlink there could redirect that outside
    its own evidence root."""

    if not root.exists():
        return

    def raise_walk_error(error: OSError) -> None:
        raise error

    for current_root, directories, filenames in os.walk(
        root, topdown=True, onerror=raise_walk_error, followlinks=False
    ):
        for name in [*directories, *filenames]:
            path = Path(current_root) / name
            if path.is_symlink():
                raise ValueError(f"unsupported symlink in working-condition exception tree: {path}")


def _load_registry() -> list[dict[str, Any]]:
    if not REGISTRY_PATH.is_file():
        return []
    value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"{REGISTRY_PATH} must be a JSON array")
    entries: list[dict[str, Any]] = []
    for entry in value:
        if not isinstance(entry, dict) or not REQUIRED_REGISTRY_FIELDS <= entry.keys():
            raise ValueError(f"malformed working-condition exception entry: {entry!r}")
        repository = entry["repository"]
        registered = require_listed(repository)
        if registered.platform != entry["platform"]:
            raise ValueError(
                f"{repository}: registry platform {entry['platform']!r} does not match "
                f"data/products.json platform {registered.platform!r}"
            )
        entries.append(entry)
    return entries


def _validate_bundle(entry: dict[str, Any], bundle_dir: Path) -> dict[str, Any]:
    repository = entry["repository"]
    missing = [name for name in REQUIRED_BUNDLE_FILES if not (bundle_dir / name).is_file()]
    if missing:
        raise ExceptionAcceptanceError(
            f"{repository}: poc share bundle is missing required files {missing} under {bundle_dir}"
        )
    validation = _json(bundle_dir / "validation.json")
    source_revision = validation.get("source_revision")
    if not isinstance(source_revision, str) or len(source_revision) != 40:
        raise ExceptionAcceptanceError(f"{repository}: invalid source_revision in validation.json")
    if (
        validation.get("org_repo") != repository
        or validation.get("deterministic_verdict") != "accept"
        or validation.get("independent_review_verdict") != "ACCEPT"
        or validation.get("review_open") is not False
        or validation.get("disposition_ledger_valid") is not True
        or validation.get("disposition_ledger_errors") not in ([], None)
    ):
        raise ExceptionAcceptanceError(
            f"{repository}: poc bundle validation.json does not show a clean accepted verdict"
        )
    return validation


def _promote_entry(entry: dict[str, Any], output_root: Path) -> dict[str, Any]:
    repository = entry["repository"]
    platform = entry["platform"]
    bundle_dir = POC_SHARE_ROOT / repository.replace("/", "__")
    if not bundle_dir.is_dir():
        raise ExceptionAcceptanceError(f"{repository}: no poc share bundle at {bundle_dir}")
    validation = _validate_bundle(entry, bundle_dir)
    source_revision = validation["source_revision"]
    candidate = bundle_dir / "README.md"
    candidate_hash = _sha256(candidate)

    relative = compact_readme_path(repository, platform, source_revision, candidate_hash)
    destination = output_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(candidate.read_bytes())
    if _sha256(destination) != candidate_hash:
        raise ValueError(f"promoted exception README hash mismatch for {repository}")

    committed_artifacts: dict[str, list[str]] = {}
    for name in (*REQUIRED_BUNDLE_FILES[1:], *OPTIONAL_BUNDLE_FILES):
        source = bundle_dir / name
        if not source.is_file():
            continue
        promoted = destination.parent / name
        promoted.write_bytes(source.read_bytes())
        digest = _sha256(promoted)
        if digest != _sha256(source):
            raise ValueError(f"durable exception artifact hash mismatch for {repository}: {name}")
        committed_artifacts[name] = [promoted.relative_to(REPO_ROOT).as_posix(), digest]

    acceptance_record = {
        "schema_version": 1,
        "record_type": "WorkingConditionExceptionAcceptanceRecordV1",
        "repository": repository,
        "platform": platform,
        "family": entry["family"],
        "source_revision": source_revision,
        "candidate_sha256": candidate_hash,
        "verdict": VERDICT,
        "accepted_date": entry["accepted_date"],
        "accepted_by": entry["accepted_by"],
        "acceptance_basis": entry["acceptance_basis"],
        "blocking_defect_summary": entry["blocking_defect_summary"],
        "resume_predicate": entry["resume_predicate"],
        "poc_bundle_source": bundle_dir.relative_to(REPO_ROOT).as_posix(),
        "decision_reference": "plans/decisions/catalog.jsonl#101",
    }
    acceptance_path = destination.parent / "ACCEPTANCE-RECORD.json"
    _write_json(acceptance_path, acceptance_record)
    committed_artifacts["ACCEPTANCE-RECORD.json"] = [
        acceptance_path.relative_to(REPO_ROOT).as_posix(),
        _sha256(acceptance_path),
    ]

    return {
        "repository": repository,
        "platform": platform,
        "family": entry["family"],
        "source_revision": source_revision,
        "candidate_sha256": candidate_hash,
        "committed_readme": destination.relative_to(REPO_ROOT).as_posix(),
        "verdict": VERDICT,
        "accepted_date": entry["accepted_date"],
        "accepted_by": entry["accepted_by"],
        "resume_predicate": entry["resume_predicate"],
        "committed_artifacts": committed_artifacts,
    }


def _render_index(manifest: dict[str, Any], output_root: Path) -> str:
    rows = []
    for item in manifest["repositories"]:
        label = {"python": "Python", "net": ".NET", "java": "Java"}.get(
            item["platform"], item["platform"]
        )
        readme_relative = Path(os.path.relpath(REPO_ROOT / item["committed_readme"], output_root))
        rows.append(
            f"| {label} | `{item['repository']}` | `{item['source_revision'][:12]}` | "
            f"{item['accepted_date']} | [Review README]({readme_relative.as_posix()}) |"
        )
    exclusion_lines = (
        [
            "",
            "Registry entries excluded from this promotion (their poc bundle no longer supports "
            "the recorded acceptance -- fix the bundle or the registry entry before relying on "
            "them):",
            "",
            *[
                f"- `{item['repository']}` ({item['platform']}): {item['reason']}"
                for item in manifest["promotion_exclusions"]
            ],
        ]
        if manifest["promotion_exclusions"]
        else []
    )
    return "\n".join(
        [
            "# Working-Condition-Presentation Exceptions",
            "",
            "This tree is **not** the finalized, fresh-transaction-no-op-proven cohort at",
            "`plans/investigations/evidence/finalized-repository-readmes-v1/`. Every README",
            "here is delivered through the `readme-agent poc` diagnostic path (Decision #100)",
            "and promoted only because a human explicitly accepted it, per repository, as a",
            "bounded exception (Decision #101) -- the strict `supervise` pipeline cannot",
            "currently pass for these repositories because of a genuine, evidence-backed",
            "*upstream* defect, not an agent-fixable gap. None of these count toward",
            "`NO_OP_PROVEN`, Gate A/B, or full-registry closure.",
            "",
            "The gate for what this script is even allowed to promote is",
            "`data/working_condition_exceptions.json`, hand-maintained and never auto-populated.",
            "Each promoted repository's directory also contains its poc `validation.json`,",
            "`UPSTREAM-DEFECTS.md`, and an `ACCEPTANCE-RECORD.json` recording who accepted the",
            "exception, the exact blocking defect, and the resume predicate that returns the",
            "repository to the strict lane once upstream is fixed.",
            "",
            "Current exception count: "
            f"**{manifest['exception_count']} / {manifest['registry_denominator']} "
            "registry entries**.",
            "",
            "| Platform | Repository | Source revision | Accepted | README |",
            "| --- | --- | --- | --- | --- |",
            *rows,
            *exclusion_lines,
            "",
        ]
    )


def promote(output_root: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    """Clean-rebuild the exception evidence tree from `data/working_condition_exceptions.json`."""

    if output_root.is_symlink() or (output_root.exists() and not output_root.is_dir()):
        raise ValueError(f"unsupported working-condition exception output root: {output_root}")
    _reject_symlinks(output_root)
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    registry = _load_registry()
    rows: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for entry in sorted(registry, key=lambda item: item["repository"].casefold()):
        try:
            rows.append(_promote_entry(entry, output_root))
        except (ExceptionAcceptanceError, NotAllowlistedError) as exc:
            exclusions.append(
                {
                    "repository": entry["repository"],
                    "platform": entry["platform"],
                    "reason": str(exc),
                }
            )

    manifest = {
        "schema_version": 1,
        "manifest_type": "WorkingConditionExceptionManifestV1",
        "scope": "HUMAN_ACCEPTED_EXCEPTIONS_NOT_NO_OP_PROVEN",
        "registry_path": "data/working_condition_exceptions.json",
        "registry_sha256": _sha256(REGISTRY_PATH) if REGISTRY_PATH.is_file() else None,
        "decision_reference": "plans/decisions/catalog.jsonl#101",
        "registry_denominator": len(registry),
        "exception_count": len(rows),
        "repositories": rows,
        "promotion_exclusions": exclusions,
    }
    _write_json(output_root / "exceptions-manifest.json", manifest)
    (output_root / "README.md").write_text(
        _render_index(manifest, output_root), encoding="utf-8", newline="\n"
    )
    refresh_sha256sums(output_root)
    if not verify_sha256sums(output_root):
        raise ValueError("working-condition exception tree checksum verification failed")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = promote(args.output_root.resolve())
    print(
        json.dumps(
            {
                "exception_count": manifest["exception_count"],
                "registry_denominator": manifest["registry_denominator"],
                "promotion_exclusions": manifest["promotion_exclusions"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
