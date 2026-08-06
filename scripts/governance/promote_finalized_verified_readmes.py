"""Promote current NO_OP_PROVEN README bytes into stable cohort evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from readme_agent.evidence.promotion_paths import (
    compact_readme_path,
    enumerate_readmes,
    migrate_preserved_entry,
    remove_preserved_entry,
)
from readme_agent.evidence.writer import refresh_sha256sums, verify_sha256sums
from readme_agent.llm.verification_prompts import separated_reviewer_standard_hash
from readme_agent.readme.document_templates import document_template_hash
from readme_agent.registry.loader import require_listed
from readme_agent.state.git_backend import default_state_backend
from readme_agent.state.schema import RunStateV2
from readme_agent.supervisor.convergence import compute_control_plane_fingerprint
from readme_agent.supervisor.local_poc_cache import evaluate_completed_local_poc_cache

if __package__:
    from governance.finalized_promotion_layout import (
        load_or_initialize_manifest,
        remove_obsolete_empty_directories,
        validate_repository_artifact_set,
    )
else:
    from finalized_promotion_layout import (
        load_or_initialize_manifest,
        remove_obsolete_empty_directories,
        validate_repository_artifact_set,
    )

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "plans/investigations/evidence/finalized-repository-readmes-v1"
RUNTIME_ARTIFACTS = {
    "source_revision": "source/revision.json",
    "source_readme": "source/README.md",
    "product_facts": "facts/product-facts.json",
    "provenance": "facts/provenance.json",
    "presentation_component_manifest": "planning/presentation-component-manifest.json",
    "document_plan": "planning/readme-document-plan.json",
    "patch": "candidate/README.patch",
    "claim_map": "candidate/claim-map.json",
    "deterministic_validation": "review/deterministic-validation.json",
    "independent_review": "review/independent-agent-review.json",
    "final_verdict": "review/final-verdict.json",
    "repair_history": "review/repair-history.json",
    "no_op_proof": "review/no-op-proof.json",
    "llm_ledger": "llm-call-ledger.jsonl",
    "manifest": "manifest.json",
}
COMMITTED_ARTIFACTS = {
    "ORIGINAL-README.md": "source/README.md",
    "README.patch": "candidate/README.patch",
    "product-facts.json": "facts/product-facts.json",
    "provenance.json": "facts/provenance.json",
    "presentation-component-manifest.json": "planning/presentation-component-manifest.json",
    "readme-document-plan.json": "planning/readme-document-plan.json",
    "claim-map.json": "candidate/claim-map.json",
    "deterministic-validation.json": "review/deterministic-validation.json",
    "independent-agent-review.json": "review/independent-agent-review.json",
    "final-verdict.json": "review/final-verdict.json",
    "repair-history.json": "review/repair-history.json",
    "no-op-proof.json": "review/no-op-proof.json",
    "llm-call-ledger.jsonl": "llm-call-ledger.jsonl",
    "runtime-manifest.json": "manifest.json",
}
OBSOLETE_AGGREGATE_ACCEPTANCE_KEYS = (
    "independent_campaign_receipt",
    "campaign_scoreboard",
    "campaign_contribution_evidence",
    "independent_page_pdf_receipt",
)


class StaleAcceptanceError(ValueError):
    """A raw terminal record no longer satisfies the current acceptance contract."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _git(state_git: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", f"--git-dir={state_git}", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout


def _states_from_git_snapshot(state_git: Path) -> dict[str, dict[str, Any]]:
    refs = _git(
        state_git,
        "for-each-ref",
        "--format=%(refname)",
        "refs/readme-agent-state",
    ).splitlines()
    states: dict[str, dict[str, Any]] = {}
    for ref in refs:
        try:
            state = json.loads(_git(state_git, "show", f"{ref}:state.json"))
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            continue
        repository = state.get("org_repo")
        if isinstance(repository, str):
            states[repository] = state
    return states


def _current_states(state_git: Path | None, repositories: list[str]) -> dict[str, dict[str, Any]]:
    if state_git is not None:
        return _states_from_git_snapshot(state_git)
    with default_state_backend() as backend:
        loaded = backend.load_many(repositories)
    return {
        repository: state.model_dump(mode="json")
        for repository, state in loaded.items()
        if state is not None
    }


def _state_source_record(state_git: Path | None) -> dict[str, str]:
    if state_git is None:
        return {
            "kind": "authoritative_durable_backend",
            "location": (
                "environment_override" if os.environ.get("README_AGENT_STATE_REMOTE") else "origin"
            ),
        }
    try:
        location = state_git.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        location = "external_offline_snapshot"
    return {
        "kind": "explicit_offline_git_snapshot",
        "location": location,
    }


def _reconcile_current_manifest_metadata(manifest: dict[str, Any]) -> None:
    for key in OBSOLETE_AGGREGATE_ACCEPTANCE_KEYS:
        manifest.pop(key, None)
    manifest["template_sha256"] = document_template_hash()
    manifest["reviewer_standard_sha256"] = separated_reviewer_standard_hash()


def _registry() -> list[dict]:
    value = json.loads((REPO_ROOT / "data/products.json").read_text(encoding="utf-8"))
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("data/products.json must be a list of objects")
    return value


def _org_repo(entry: dict) -> str:
    url = entry.get("repo_url")
    if not isinstance(url, str) or "github.com/" not in url:
        raise ValueError("registry entry lacks a GitHub repository URL")
    return url.split("github.com/", 1)[1].strip("/")


def _git_file_at_head(relative: Path) -> bytes:
    result = subprocess.run(
        ["git", "show", f"HEAD:{relative.as_posix()}"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        timeout=30,
    )
    return result.stdout


def _remove_committed_entry(item: dict, output_root: Path) -> None:
    committed = item.get("committed_artifacts")
    if isinstance(committed, dict):
        for value in committed.values():
            if not isinstance(value, list) or len(value) != 2:
                raise ValueError(f"invalid committed artifact record: {value!r}")
            relative, expected_hash = value
            if not isinstance(relative, str) or not isinstance(expected_hash, str):
                raise ValueError(f"invalid committed artifact record: {value!r}")
            path = REPO_ROOT / relative
            path.resolve().relative_to(output_root.resolve())
            if _sha256(path) != expected_hash:
                raise ValueError(f"committed artifact hash mismatch: {relative}")
            path.unlink()
    remove_preserved_entry(
        item,
        repo_root=REPO_ROOT,
        output_root=output_root,
        read_committed_file=_git_file_at_head,
    )


def _remove_legacy_evidence(repository: str, output_root: Path) -> None:
    legacy = output_root / repository.replace("/", "__")
    if not legacy.exists():
        return
    legacy.resolve().relative_to(output_root.resolve())
    if legacy.is_symlink() or not legacy.is_dir():
        raise ValueError(f"unsupported legacy evidence path: {legacy}")
    shutil.rmtree(legacy)


def _validated_entry(repository: str, state: dict, output_root: Path, platform: str) -> dict:
    lifecycle = state.get("readme_poc_lifecycle")
    if not isinstance(lifecycle, dict) or lifecycle.get("status") != "NO_OP_PROVEN":
        raise ValueError(f"repository is not NO_OP_PROVEN: {repository}")
    revision = lifecycle.get("source_revision")
    candidate_hash = lifecycle.get("candidate_hash")
    if not isinstance(revision, str) or len(revision) != 40:
        raise ValueError(f"invalid source revision for {repository}")
    if not isinstance(candidate_hash, str) or len(candidate_hash) != 64:
        raise ValueError(f"invalid candidate hash for {repository}")
    bundle = REPO_ROOT / "runs/readme-poc" / repository.replace("/", "__") / revision
    typed_state = RunStateV2.model_validate(state)
    entry = require_listed(repository)
    acceptance = evaluate_completed_local_poc_cache(
        typed_state,
        bundle,
        current_source_revision=revision,
        current_control_plane_fingerprint=compute_control_plane_fingerprint(entry.policy_profile),
        ecosystem=entry.ecosystem,
        family=entry.family,
    )
    if not acceptance.reusable:
        reasons = ",".join(acceptance.mismatch_reasons) or "current_contract_rejected"
        raise StaleAcceptanceError(f"stale finalized acceptance for {repository}: {reasons}")
    candidate = bundle / "candidate/README.md"
    manifest = _json(bundle / "manifest.json")
    deterministic = _json(bundle / "review/deterministic-validation.json")
    independent = _json(bundle / "review/independent-agent-review.json")
    no_op = _json(bundle / "review/no-op-proof.json")
    if _sha256(candidate) != candidate_hash:
        raise ValueError(f"candidate hash mismatch for {repository}")
    if not verify_sha256sums(bundle):
        raise ValueError(f"runtime checksum inventory failed for {repository}")
    if (
        manifest.get("org_repo") != repository
        or manifest.get("source_revision") != revision
        or manifest.get("lifecycle_status") != "NO_OP_PROVEN"
        or manifest.get("content_assurance") != "repository_verified"
        or manifest.get("candidate_hash") != candidate_hash
        or manifest.get("complete") is not True
    ):
        raise ValueError(f"incomplete runtime manifest for {repository}")
    deterministic_checks = deterministic.get("checks")
    if (
        deterministic.get("verdict") != "accept"
        or not isinstance(deterministic_checks, dict)
        or not deterministic_checks
        or not all(value is True for value in deterministic_checks.values())
    ):
        raise ValueError(f"deterministic validation is not accepted for {repository}")
    if independent.get("verdict") != "ACCEPT":
        raise ValueError(f"independent review is not accepted for {repository}")
    if (
        no_op.get("verdict") != "NO_OP_PROVEN"
        or no_op.get("candidate_hash") != candidate_hash
        or no_op.get("new_provider_call_count") != 0
        or no_op.get("agentic_review_reused") is not True
        or no_op.get("patch_created") is not False
        or no_op.get("duplicate_bundle_created") is not False
    ):
        raise ValueError(f"unchanged no-op proof failed for {repository}")

    relative = compact_readme_path(
        repository,
        platform,
        revision,
        candidate_hash,
    )
    destination = output_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(candidate.read_bytes())
    if _sha256(destination) != candidate_hash:
        raise ValueError(f"promoted README hash mismatch for {repository}")

    artifacts: dict[str, list[str]] = {}
    for name, relative_artifact in RUNTIME_ARTIFACTS.items():
        path = bundle / relative_artifact
        if path.is_file():
            artifacts[name] = [path.relative_to(REPO_ROOT).as_posix(), _sha256(path)]
    required = set(RUNTIME_ARTIFACTS) - {"repair_history"}
    if not required <= artifacts.keys():
        raise ValueError(f"runtime evidence is incomplete for {repository}")
    committed_artifacts: dict[str, list[str]] = {}
    for name, relative_artifact in COMMITTED_ARTIFACTS.items():
        source = bundle / relative_artifact
        if name == "repair-history.json" and not source.is_file():
            continue
        if not source.is_file():
            raise ValueError(f"durable promotion artifact is missing for {repository}: {name}")
        promoted_artifact = destination.parent / name
        promoted_artifact.write_bytes(source.read_bytes())
        digest = _sha256(promoted_artifact)
        if digest != _sha256(source):
            raise ValueError(f"durable promotion artifact hash mismatch for {repository}: {name}")
        committed_artifacts[name] = [
            promoted_artifact.relative_to(REPO_ROOT).as_posix(),
            digest,
        ]
    return {
        "repository": repository,
        "platform": platform,
        "source_revision": revision,
        "candidate_sha256": candidate_hash,
        "committed_readme": destination.relative_to(REPO_ROOT).as_posix(),
        "verdict": "NO_OP_PROVEN",
        "acceptance_cache_key": acceptance.cache_key,
        "replay_provider_calls": 0,
        "committed_artifacts": committed_artifacts,
        "runtime_artifacts": artifacts,
    }


def _render_index(manifest: dict, output_root: Path) -> str:
    rows = []
    for item in manifest["repositories"]:
        label = {"python": "Python", "net": ".NET", "java": "Java"}.get(
            item["platform"], item["platform"]
        )
        path = Path(item["committed_readme"])
        relative = Path(os.path.relpath(REPO_ROOT / path, output_root))
        rows.append(
            f"| {label} | `{item['repository']}` | `{item['source_revision']}` | "
            f"`{item['verdict']}` | [Review README]({relative.as_posix()}) |"
        )
    return "\n".join(
        [
            "# Finalized Verified README Evidence",
            "",
            "This index exposes exact, committed README candidates only after repository",
            "verification, deterministic validation, independent approval, and an unchanged",
            "no-op rerun. Durable review evidence is copied beside each README, while the",
            "runtime trees remain under `runs/` for complete replay detail.",
            "",
            "Current committed promotion count: "
            f"**{manifest['promoted_verified_readmes']} / {manifest['registry_denominator']} "
            "registry repositories**. Python promotion count: "
            f"**{manifest['promoted_python_readmes']} / {manifest['python_denominator']} "
            "Python repositories**. This is a partial verified portfolio result, not verified "
            "Gate A or the complete Python POC.",
            "",
            "| Platform | Repository | Source revision | Verdict | README |",
            "| --- | --- | --- | --- | --- |",
            *rows,
            "",
            "Only the current candidate for each listed repository is present in this canonical",
            "review tree. Its directory also contains the committed original, facts, provenance,",
            "plan, patch, claim map, validation, independent review, final verdict, no-op proof,",
            "LLM ledger, and runtime manifest. Superseded bytes remain recoverable from Git",
            "history.",
            "",
        ]
    )


def promote(state_git: Path | None, output_root: Path, independent_receipt: Path | None) -> dict:
    """Promote all current Python no-op states while preserving non-Python evidence."""

    manifest_path = output_root / "cohort-manifest.json"
    manifest = load_or_initialize_manifest(output_root, repo_root=REPO_ROOT)
    _reconcile_current_manifest_metadata(manifest)
    registry = _registry()
    python_repositories = sorted(
        _org_repo(item) for item in registry if str(item.get("platform", "")).casefold() == "python"
    )
    prior_rows = [item for item in manifest.get("repositories", []) if isinstance(item, dict)]
    state_repositories = sorted(
        set(python_repositories)
        | {
            repository
            for item in prior_rows
            if isinstance((repository := item.get("repository")), str)
        }
    )
    states = _current_states(state_git, state_repositories)
    excluded: list[dict[str, Any]] = []
    promoted: list[dict[str, Any]] = []
    for repository in python_repositories:
        state = states.get(repository)
        lifecycle = state.get("readme_poc_lifecycle") if isinstance(state, dict) else None
        status = lifecycle.get("status") if isinstance(lifecycle, dict) else None
        if state is None or status != "NO_OP_PROVEN":
            excluded.append(
                {
                    "repository": repository,
                    "platform": "python",
                    "raw_status": status,
                    "reason": "missing_current_no_op_state",
                }
            )
            continue
        try:
            promoted.append(_validated_entry(repository, state, output_root, "python"))
        except StaleAcceptanceError as exc:
            excluded.append(
                {
                    "repository": repository,
                    "platform": "python",
                    "raw_status": status,
                    "reason": str(exc),
                }
            )
    preserved = []
    for item in prior_rows:
        if item.get("platform") == "python":
            continue
        repository = item.get("repository")
        platform = item.get("platform")
        if not isinstance(repository, str) or not isinstance(platform, str):
            raise ValueError(f"preserved manifest row lacks identity: {item!r}")
        state = states.get(repository)
        lifecycle = state.get("readme_poc_lifecycle") if isinstance(state, dict) else None
        status = lifecycle.get("status") if isinstance(lifecycle, dict) else None
        if state is None or status != "NO_OP_PROVEN":
            excluded.append(
                {
                    "repository": repository,
                    "platform": platform,
                    "raw_status": status,
                    "reason": "missing_current_no_op_state",
                }
            )
            continue
        try:
            current = _validated_entry(repository, state, output_root, platform)
        except StaleAcceptanceError as exc:
            excluded.append(
                {
                    "repository": repository,
                    "platform": platform,
                    "raw_status": status,
                    "reason": str(exc),
                }
            )
            continue
        if current["source_revision"] == item.get("source_revision") and current[
            "candidate_sha256"
        ] == item.get("candidate_sha256"):
            migrate_preserved_entry(
                item,
                repo_root=REPO_ROOT,
                output_root=output_root,
                read_committed_file=_git_file_at_head,
            )
        preserved.append(current)
    repositories = sorted(promoted, key=lambda item: item["repository"].casefold()) + sorted(
        preserved, key=lambda item: (item["platform"], item["repository"].casefold())
    )
    current_identities = {
        (item["repository"], item["source_revision"], item["candidate_sha256"])
        for item in repositories
    }
    for item in prior_rows:
        prior_identity = (
            item.get("repository"),
            item.get("source_revision"),
            item.get("candidate_sha256"),
        )
        if prior_identity not in current_identities:
            _remove_committed_entry(item, output_root)
    for item in repositories:
        _remove_legacy_evidence(item["repository"], output_root)
    expected_readmes = {(REPO_ROOT / item["committed_readme"]).resolve() for item in repositories}
    repositories_root = output_root / "repositories"
    repositories_root.mkdir(exist_ok=True)
    actual_readmes = enumerate_readmes(repositories_root)
    if actual_readmes != expected_readmes:
        unexpected = sorted(path.as_posix() for path in actual_readmes - expected_readmes)
        missing = sorted(path.as_posix() for path in expected_readmes - actual_readmes)
        raise ValueError(
            "canonical review tree does not match the promoted manifest: "
            f"unexpected={unexpected}; missing={missing}"
        )
    validate_repository_artifact_set(repositories, output_root, repo_root=REPO_ROOT)
    remove_obsolete_empty_directories(output_root)
    validate_repository_artifact_set(repositories, output_root, repo_root=REPO_ROOT)
    manifest.update(
        {
            "registry_sha256": _sha256(REPO_ROOT / "data/products.json"),
            "registry_denominator": len(registry),
            "promoted_verified_readmes": len(repositories),
            "python_denominator": len(python_repositories),
            "promoted_python_readmes": len(promoted),
            "promotion_exclusions": sorted(
                excluded, key=lambda item: (item["platform"], item["repository"].casefold())
            ),
            "state_source": _state_source_record(state_git),
            "repositories": repositories,
        }
    )
    manifest.pop("current_python_independent_receipt", None)
    if independent_receipt is not None:
        receipt = independent_receipt.resolve()
        receipt.relative_to(REPO_ROOT)
        receipt_value = _json(receipt)
        accepted_rows = {
            item.get("org_repo"): item.get("candidate_sha256")
            for item in receipt_value.get("repositories", [])
            if isinstance(item, dict) and item.get("verdict") == "ACCEPT"
        }
        receipt_denominator = receipt_value.get("denominator")
        expected_partial_verdict = f"PARTIAL_ACCEPT_{len(promoted)}_OF_{len(python_repositories)}"
        if (
            receipt_value.get("verdict") not in {"ACCEPT", expected_partial_verdict}
            or not isinstance(receipt_denominator, dict)
            or receipt_denominator.get("python_repositories") != len(python_repositories)
            or receipt_denominator.get("independently_accepted") != len(promoted)
            or set(accepted_rows) != {item["repository"] for item in promoted}
            or any(
                accepted_rows.get(item["repository"]) != item["candidate_sha256"]
                for item in promoted
            )
        ):
            raise ValueError("independent cohort receipt does not accept every promoted README")
        manifest["current_python_independent_receipt"] = {
            "path": receipt.relative_to(REPO_ROOT).as_posix(),
            "sha256": _sha256(receipt),
        }
    _write_json(manifest_path, manifest)
    (output_root / "README.md").write_text(
        _render_index(manifest, output_root), encoding="utf-8", newline="\n"
    )
    refresh_sha256sums(output_root)
    if not verify_sha256sums(output_root):
        raise ValueError("finalized cohort checksum verification failed")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state-git",
        type=Path,
        help=(
            "explicit offline Git-state snapshot; omit to read the authoritative durable "
            "state backend"
        ),
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--independent-receipt", type=Path)
    args = parser.parse_args()
    manifest = promote(
        args.state_git.resolve() if args.state_git is not None else None,
        args.output_root.resolve(),
        args.independent_receipt,
    )
    print(
        json.dumps(
            {
                "promoted_verified_readmes": manifest["promoted_verified_readmes"],
                "promoted_python_readmes": manifest["promoted_python_readmes"],
                "python_denominator": manifest["python_denominator"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
