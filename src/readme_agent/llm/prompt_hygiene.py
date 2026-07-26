"""Reconcile prompt assets, routes, consumers, call sites, and documentation."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from readme_agent import env
from readme_agent.errors import ConfigError
from readme_agent.llm import prompt_registry
from readme_agent.llm.prompt_source_audit import scan_prompt_source, source_path_for_module

_DOC_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|")
_NON_PROMPT_LEDGER_IDS = frozenset({"embeddings", "local_poc_complete_bundle"})


class PromptInventoryEntryV1(BaseModel):
    """One reconstructable active prompt inventory row."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_id: str
    path: str
    sha256: str
    category: str
    version: str
    model_route: str
    owner: str
    runtime_consumer: str
    output_contract: str
    invalidation_scope: str
    dependent_artifacts: list[str]
    content_reference_paths: list[str] = Field(default_factory=list)
    hash_reference_paths: list[str] = Field(default_factory=list)
    route_reference_paths: list[str] = Field(default_factory=list)


class PromptHygieneReportV1(BaseModel):
    """Blocking prompt inventory result used by CI and paid campaign entry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    prompt_registry_content_hash: str | None
    prompt_hashes: dict[str, str]
    dependency_hashes: dict[str, str]
    entries: list[PromptInventoryEntryV1]
    errors: list[str]

    @property
    def clean(self) -> bool:
        return not self.errors


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _documented_prompt_rows(readme_path: Path) -> list[list[str]]:
    if not readme_path.is_file():
        return []
    rows: list[list[str]] = []
    for line in readme_path.read_text(encoding="utf-8").splitlines():
        if not _DOC_ROW.match(line):
            continue
        rows.append([cell.strip().strip("`") for cell in line.strip("|").split("|")])
    return rows


def audit_prompt_hygiene(
    *,
    repo_root: Path | None = None,
    prompts_dir: Path | None = None,
    readme_path: Path | None = None,
    model_routes: dict[str, str] | None = None,
) -> PromptHygieneReportV1:
    """Return every blocking mismatch without issuing any provider call."""

    root = (repo_root or _repo_root()).resolve()
    prompt_root = prompts_dir or root / "prompts"
    docs = readme_path or prompt_root / "README.md"
    routes = model_routes if model_routes is not None else env.JOB_MODEL_ROUTING
    errors: list[str] = []
    try:
        manifests, raw_content = prompt_registry._build(prompt_root)
    except ConfigError as exc:
        return PromptHygieneReportV1(
            prompt_registry_content_hash=None,
            prompt_hashes={},
            dependency_hashes={},
            entries=[],
            errors=[str(exc)],
        )

    prompt_ids = set(manifests)
    expected_files = {
        (prompt_root / manifest.category / f"{prompt_id}.yaml").resolve()
        for prompt_id, manifest in manifests.items()
    } | {docs.resolve()}
    unexpected_files = sorted(
        path.relative_to(prompt_root).as_posix()
        for path in prompt_root.rglob("*")
        if path.is_file() and path.resolve() not in expected_files
    )
    if unexpected_files:
        errors.append(f"unregistered files in active prompt tree: {unexpected_files}")
    route_to_prompt = {manifest.model_route: prompt_id for prompt_id, manifest in manifests.items()}
    missing_routes = sorted(set(route_to_prompt) - set(routes))
    orphan_routes = sorted(set(routes) - set(route_to_prompt))
    if missing_routes:
        errors.append(f"prompt model routes absent from JOB_MODEL_ROUTING: {missing_routes}")
    if orphan_routes:
        errors.append(f"JOB_MODEL_ROUTING entries without prompts: {orphan_routes}")

    for prompt_id, manifest in manifests.items():
        owner_path = source_path_for_module(root, manifest.owner)
        if not owner_path.is_file():
            errors.append(
                f"prompt {prompt_id!r} owner does not exist: "
                f"{owner_path.relative_to(root).as_posix()}"
            )
        consumer_path = source_path_for_module(root, manifest.runtime_consumer)
        if not consumer_path.is_file():
            errors.append(
                f"prompt {prompt_id!r} runtime consumer does not exist: "
                f"{consumer_path.relative_to(root).as_posix()}"
            )

    content_refs, hash_refs, route_refs, keyword_ids, inline_errors = scan_prompt_source(root)
    errors.extend(inline_errors)
    for prompt_id, paths in sorted(content_refs.items()):
        if prompt_id not in manifests:
            errors.append(f"runtime references unknown prompt {prompt_id!r}: {sorted(paths)}")
    for prompt_id, paths in sorted(hash_refs.items()):
        if prompt_id not in manifests:
            errors.append(f"runtime hashes unknown prompt {prompt_id!r}: {sorted(paths)}")
    for prompt_id, manifest in manifests.items():
        expected = (
            source_path_for_module(root, manifest.runtime_consumer).relative_to(root).as_posix()
        )
        actual = sorted(content_refs.get(prompt_id, set()))
        if actual != [expected]:
            errors.append(f"prompt {prompt_id!r} must be loaded only by {expected}; found {actual}")
        if not route_refs.get(manifest.model_route):
            errors.append(f"prompt route {manifest.model_route!r} has no runtime call site")
    for route, paths in sorted(route_refs.items()):
        if route not in routes:
            errors.append(f"runtime invokes unknown model route {route!r}: {sorted(paths)}")
    for prompt_id, path in keyword_ids:
        if prompt_id not in prompt_ids and prompt_id not in _NON_PROMPT_LEDGER_IDS:
            errors.append(f"runtime passes unknown prompt_id {prompt_id!r}: {path}")

    documented_rows = _documented_prompt_rows(docs)
    documented = [row[0] for row in documented_rows]
    if len(documented) != len(set(documented)):
        errors.append("prompts/README.md contains duplicate prompt inventory rows")
    if set(documented) != prompt_ids:
        errors.append(
            "prompts/README.md inventory mismatch: "
            f"missing={sorted(prompt_ids - set(documented))}, "
            f"extra={sorted(set(documented) - prompt_ids)}"
        )
    for row in documented_rows:
        if len(row) != 7 or row[0] not in manifests:
            continue
        manifest = manifests[row[0]]
        documented_expected = [
            manifest.prompt_id,
            manifest.category,
            manifest.model_route,
            manifest.owner,
            manifest.runtime_consumer,
            manifest.output_contract,
            manifest.invalidation_scope,
        ]
        if row != documented_expected:
            errors.append(f"prompts/README.md metadata is stale for {manifest.prompt_id!r}")

    prompt_hashes = {
        prompt_id: hashlib.sha256(raw_content[prompt_id].encode("utf-8")).hexdigest()
        for prompt_id in sorted(raw_content)
    }
    scopes: dict[str, list[str]] = {}
    for prompt_id, manifest in manifests.items():
        scopes.setdefault(manifest.invalidation_scope, []).append(prompt_id)
    dependency_hashes = {
        scope: hashlib.sha256(
            "\x00".join(raw_content[item] for item in sorted(prompt_ids_for_scope)).encode("utf-8")
        ).hexdigest()
        for scope, prompt_ids_for_scope in sorted(scopes.items())
    }
    entries = [
        PromptInventoryEntryV1(
            prompt_id=prompt_id,
            path=(prompt_root / manifest.category / f"{prompt_id}.yaml")
            .relative_to(root)
            .as_posix(),
            sha256=prompt_hashes[prompt_id],
            category=manifest.category,
            version=manifest.version,
            model_route=manifest.model_route,
            owner=manifest.owner,
            runtime_consumer=manifest.runtime_consumer,
            output_contract=manifest.output_contract,
            invalidation_scope=manifest.invalidation_scope,
            dependent_artifacts=manifest.dependent_artifacts,
            content_reference_paths=sorted(content_refs.get(prompt_id, set())),
            hash_reference_paths=sorted(hash_refs.get(prompt_id, set())),
            route_reference_paths=sorted(route_refs.get(manifest.model_route, set())),
        )
        for prompt_id, manifest in sorted(manifests.items())
    ]
    combined = "\x00".join(raw_content[item] for item in sorted(raw_content))
    return PromptHygieneReportV1(
        prompt_registry_content_hash=hashlib.sha256(combined.encode("utf-8")).hexdigest(),
        prompt_hashes=prompt_hashes,
        dependency_hashes=dependency_hashes,
        entries=entries,
        errors=sorted(set(errors)),
    )


def require_prompt_hygiene(**kwargs: Any) -> PromptHygieneReportV1:
    """Fail closed before any paid fan-out when the inventory is inconsistent."""

    report = audit_prompt_hygiene(**kwargs)
    if not report.clean:
        raise ConfigError("prompt hygiene failed: " + "; ".join(report.errors))
    return report
