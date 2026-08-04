"""Promote current NO_OP_PROVEN README bytes into stable cohort evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from readme_agent.evidence.writer import refresh_sha256sums, verify_sha256sums

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_GIT = REPO_ROOT / "runs/control/local-verified-canary-state.git"
DEFAULT_OUTPUT = REPO_ROOT / "plans/investigations/evidence/finalized-repository-readmes-v1"
RUNTIME_ARTIFACTS = {
    "source_revision": "source/revision.json",
    "source_readme": "source/README.md",
    "product_facts": "facts/product-facts.json",
    "document_plan": "planning/readme-document-plan.json",
    "patch": "candidate/README.patch",
    "deterministic_validation": "review/deterministic-validation.json",
    "independent_review": "review/independent-agent-review.json",
    "repair_history": "review/repair-history.json",
    "no_op_proof": "review/no-op-proof.json",
    "llm_ledger": "llm-call-ledger.jsonl",
    "manifest": "manifest.json",
}


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


def _current_states(state_git: Path) -> dict[str, dict]:
    refs = _git(
        state_git,
        "for-each-ref",
        "--format=%(refname)",
        "refs/readme-agent-state",
    ).splitlines()
    states: dict[str, dict] = {}
    for ref in refs:
        try:
            state = json.loads(_git(state_git, "show", f"{ref}:state.json"))
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            continue
        repository = state.get("org_repo")
        if isinstance(repository, str):
            states[repository] = state
    return states


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


def _validated_entry(repository: str, state: dict, output_root: Path) -> dict:
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

    family = repository.split("/", 1)[0].removeprefix("aspose-").removesuffix("-foss")
    relative = (
        Path("repositories/python")
        / f"{family}--{revision[:12]}--{candidate_hash[:12]}"
        / "README.md"
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
    return {
        "repository": repository,
        "platform": "python",
        "source_revision": revision,
        "candidate_sha256": candidate_hash,
        "committed_readme": destination.relative_to(REPO_ROOT).as_posix(),
        "verdict": "NO_OP_PROVEN",
        "replay_provider_calls": 0,
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
            "no-op rerun. Runtime trees remain under `runs/`; `cohort-manifest.json` binds",
            "their exact bytes without copying those mutable trees.",
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
            "review tree; superseded bytes remain recoverable from Git history and runtime",
            "evidence.",
            "",
        ]
    )


def promote(state_git: Path, output_root: Path, independent_receipt: Path | None) -> dict:
    """Promote all current Python no-op states while preserving non-Python evidence."""

    manifest_path = output_root / "cohort-manifest.json"
    manifest = _json(manifest_path)
    registry = _registry()
    python_repositories = sorted(
        _org_repo(item) for item in registry if str(item.get("platform", "")).casefold() == "python"
    )
    states = _current_states(state_git)
    promoted = [
        _validated_entry(repository, states[repository], output_root)
        for repository in python_repositories
        if repository in states
        and states[repository].get("readme_poc_lifecycle", {}).get("status") == "NO_OP_PROVEN"
    ]
    preserved = [
        item for item in manifest.get("repositories", []) if item.get("platform") != "python"
    ]
    repositories = sorted(promoted, key=lambda item: item["repository"].casefold()) + sorted(
        preserved, key=lambda item: (item["platform"], item["repository"].casefold())
    )
    expected_readmes = {(REPO_ROOT / item["committed_readme"]).resolve() for item in promoted}
    actual_readmes = {
        path.resolve() for path in (output_root / "repositories/python").rglob("README.md")
    }
    if actual_readmes != expected_readmes:
        unexpected = sorted(path.as_posix() for path in actual_readmes - expected_readmes)
        missing = sorted(path.as_posix() for path in expected_readmes - actual_readmes)
        raise ValueError(
            "canonical review tree does not match the promoted manifest: "
            f"unexpected={unexpected}; missing={missing}"
        )
    manifest.update(
        {
            "registry_sha256": _sha256(REPO_ROOT / "data/products.json"),
            "registry_denominator": len(registry),
            "promoted_verified_readmes": len(repositories),
            "python_denominator": len(python_repositories),
            "promoted_python_readmes": len(promoted),
            "repositories": repositories,
        }
    )
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
    parser.add_argument("--state-git", type=Path, default=DEFAULT_STATE_GIT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--independent-receipt", type=Path)
    args = parser.parse_args()
    manifest = promote(
        args.state_git.resolve(), args.output_root.resolve(), args.independent_receipt
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
