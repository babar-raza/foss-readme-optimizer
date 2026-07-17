"""Wires every module into the CLI's verbs. This is the one place that knows
the full pipeline order: allow-list -> gitsafety -> inspect -> gap-detect ->
facts -> (LLM only if needed) -> render -> validate -> (commit if mode=full).

Idempotency note: since this tool never pushes, a persistent local work clone
(paths.work_dir, stable across invocations -- see its docstring) is the only
place "run twice, second run makes zero LLM calls" can be real. `dataclasses`
is used for the force_regenerate gap-report override, not because GapReport
needs broader mutability elsewhere.
"""

import dataclasses
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from readme_agent import env, paths
from readme_agent.ecosystems.registry import parse_manifest
from readme_agent.errors import NotAllowlistedError
from readme_agent.evidence.writer import generate_run_id, write_evidence
from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.clone import clone_baseline, create_work_clone
from readme_agent.gitsafety.hooks import install_pre_push_hook
from readme_agent.gitsafety.neuter import neuter_push
from readme_agent.gitsafety.verify import verify_push_blocked
from readme_agent.inspection import file_inventory
from readme_agent.license.auditor import detect_license
from readme_agent.llm.client import GeneratedResult, LLMClient
from readme_agent.llm.fixture_client import FixtureLLMClient
from readme_agent.llm.live_client import LiveLLMClient
from readme_agent.llm.prompts import build_prompt
from readme_agent.readme.facts import (
    GapReportFacts,
    RepositoryFacts,
    compute_facts_hash,
)
from readme_agent.readme.gap_detector import GapReport
from readme_agent.readme.gap_detector import detect as detect_gaps
from readme_agent.readme.markers import SPAN_NAMES, find_span, upsert_span
from readme_agent.readme.renderer import render_missing_elements
from readme_agent.registry.loader import enabled_entries, find_entry, load_policy
from readme_agent.registry.models import PolicyProfile, ProductEntry
from readme_agent.validation import registry as validation_registry
from readme_agent.validation.context import ValidationContext


@dataclass
class GenerateResult:
    status: str  # COMPLIANT_NO_CHANGE | GENERATED | STALE_NONCOMPLIANT | BLOCKED_VALIDATION_FAILED
    org_repo: str
    gap_report: GapReport
    llm_called: bool
    validation_results: list
    facts_hash: str
    work_readme_path: Path
    evidence_dir: Path | None = None


@dataclass
class RunResult:
    ok: bool
    status: str
    org_repo: str
    push_block_ok: bool
    committed: bool
    evidence_dir: Path | None = None


def _require_permitted(org_repo: str) -> ProductEntry:
    entry = find_entry(org_repo)
    if entry is None or entry.mode == "disabled":
        raise NotAllowlistedError(
            f"{org_repo} is not in data/products.json with an enabled mode -- "
            "refusing to touch it. This is the hard allow-list gate."
        )
    return entry


def _policy_content_hash(policy: PolicyProfile) -> str:
    canonical = json.dumps(policy.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _ensure_work_clone(entry: ProductEntry, baseline_path: Path, work_path: Path) -> Path:
    if work_path.exists() and (work_path / ".git").exists():
        return work_path  # reuse -- see module docstring on why this matters
    return create_work_clone(entry, baseline_path, work_path)


def inspect_repo(org_repo: str) -> dict:
    """Clone baseline only, extract facts. No LLM, no work clone, no writes."""
    entry = _require_permitted(org_repo)
    baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
    clone_baseline(entry, baseline_path)

    inventory = file_inventory.scan(baseline_path)
    manifest = parse_manifest(entry.ecosystem, inventory) if entry.ecosystem else {}
    readme_text = inventory.readme_path.read_text(encoding="utf-8") if inventory.readme_path else ""

    return {
        "org_repo": org_repo,
        "manifest": manifest,
        "has_readme": inventory.readme_path is not None,
        "has_license_file": inventory.license_path is not None,
        "readme_length_chars": len(readme_text),
    }


def generate_repo(
    org_repo: str,
    *,
    force_regenerate: bool = False,
    llm_mode: str = "live",
    fixture_response_path: Path | None = None,
    write_evidence_bundle: bool = True,
) -> GenerateResult:
    entry = _require_permitted(org_repo)
    if entry.policy_profile is None or entry.ecosystem is None:
        raise NotAllowlistedError(f"{org_repo} has no policy_profile/ecosystem configured yet")
    policy = load_policy(entry.policy_profile)

    baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
    work_path = paths.work_dir(entry.org, entry.repo_name)
    clone_baseline(entry, baseline_path)
    _ensure_work_clone(entry, baseline_path, work_path)
    neuter_push(work_path)
    install_pre_push_hook(work_path)
    proof = verify_push_blocked(work_path)
    if not proof.ok:
        raise RuntimeError(f"push-block verification failed, aborting: {proof.detail}")

    inventory = file_inventory.scan(work_path)
    readme_path = inventory.readme_path or (work_path / "README.md")
    baseline_readme_path = baseline_path / readme_path.name
    baseline_readme_text = (
        baseline_readme_path.read_text(encoding="utf-8") if baseline_readme_path.exists() else ""
    )
    current_text = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

    manifest = parse_manifest(entry.ecosystem, inventory)
    license_state = detect_license(manifest.get("license"), inventory.license_path)

    gap_report = detect_gaps(current_text, detected_license=license_state.detected)
    facts = RepositoryFacts(
        org_repo=entry.org_repo,
        commit_sha=None,
        manifest=manifest,
        detected_license=license_state.detected,
        gap_report=GapReportFacts.from_gap_report(gap_report),
        policy_content_hash=_policy_content_hash(policy),
    )
    facts_hash = compute_facts_hash(facts)

    existing = find_span(current_text, "resources") or find_span(current_text, "callout")
    embedded_hash = existing.facts_hash if existing else None
    existing_rendered_spans = {
        name: m.content for name in SPAN_NAMES if (m := find_span(current_text, name))
    }

    def _validate(readme_text: str, llm_response, rendered_spans: dict[str, str]):
        ctx = ValidationContext(
            readme_text=readme_text,
            baseline_readme_text=baseline_readme_text,
            policy=policy,
            pre_render_gap_report=gap_report,
            rendered_spans=rendered_spans,
            llm_response=llm_response,
            facts_hash=facts_hash,
            embedded_hash=embedded_hash,
            detected_license=license_state.detected,
        )
        return validation_registry.run_all(ctx)

    skip_regeneration = not force_regenerate and (
        gap_report.fully_compliant or (existing is not None and embedded_hash == facts_hash)
    )

    llm_called = False
    llm_request = None
    llm_response = None
    generated_result: GeneratedResult | None = None

    if skip_regeneration:
        results = _validate(current_text, None, existing_rendered_spans)
        status = (
            "COMPLIANT_NO_CHANGE" if validation_registry.passed(results) else "STALE_NONCOMPLIANT"
        )
        new_text = current_text
        new_spans: dict[str, str] = {}
    else:
        render_gap_report = gap_report
        if force_regenerate and gap_report.relationship_explained:
            render_gap_report = dataclasses.replace(gap_report, relationship_explained=False)

        if render_gap_report.relationship_explained is False:
            llm_request = build_prompt(facts, policy)
            client: LLMClient
            if llm_mode == "fixture":
                if fixture_response_path is None:
                    raise ValueError("llm_mode='fixture' requires fixture_response_path")
                client = FixtureLLMClient(fixture_response_path)
            else:
                client = LiveLLMClient(env.llm_base_url(), env.llm_api_key(), env.llm_model())
            generated_result = client.generate(llm_request)
            llm_response = generated_result.response
            llm_called = True

        new_spans = render_missing_elements(
            render_gap_report,
            policy,
            relationship_paragraph=llm_response.relationship_paragraph if llm_response else None,
        )
        new_text = current_text
        for span_name, content in new_spans.items():
            new_text = upsert_span(new_text, span_name, content, facts_hash)

        readme_path.parent.mkdir(parents=True, exist_ok=True)
        readme_path.write_text(new_text, encoding="utf-8")

        results = _validate(new_text, llm_response, new_spans)
        status = "GENERATED" if validation_registry.passed(results) else "BLOCKED_VALIDATION_FAILED"

    evidence_path = None
    if write_evidence_bundle:
        run_id = generate_run_id()
        evidence_path = paths.evidence_dir(run_id)
        write_evidence(
            evidence_path,
            run_id=run_id,
            org_repo=org_repo,
            mode="dry_run",
            status=status,
            facts=facts,
            facts_hash=facts_hash,
            llm_mode=(generated_result.mode if generated_result else None),
            llm_request=llm_request,
            llm_response=llm_response,
            baseline_readme=baseline_readme_text,
            work_readme=new_text,
            rendered_spans=new_spans if not skip_regeneration else existing_rendered_spans,
            validation_results=results,
            push_block_detail=proof.detail,
        )

    return GenerateResult(
        status=status,
        org_repo=org_repo,
        gap_report=gap_report,
        llm_called=llm_called,
        validation_results=results,
        facts_hash=facts_hash,
        work_readme_path=readme_path,
        evidence_dir=evidence_path,
    )


def validate_repo(org_repo: str, check_links: bool = False) -> GenerateResult:
    """Re-runs generate's read+validate path without ever calling the LLM or
    writing anything -- a simplified stand-in for the plan's "fully offline
    against a prior evidence dir" design; this implementation re-derives from
    the current work clone instead of reloading a historical evidence bundle.
    """
    return generate_repo(org_repo, force_regenerate=False, write_evidence_bundle=False)


def run_repo(
    org_repo: str,
    *,
    mode: str = "dry_run",
    force_regenerate: bool = False,
    llm_mode: str = "live",
    fixture_response_path: Path | None = None,
) -> RunResult:
    entry = _require_permitted(org_repo)
    result = generate_repo(
        org_repo,
        force_regenerate=force_regenerate,
        llm_mode=llm_mode,
        fixture_response_path=fixture_response_path,
    )

    work_path = paths.work_dir(entry.org, entry.repo_name)
    proof = verify_push_blocked(work_path)

    committed = False
    if mode == "full" and result.status == "GENERATED":
        run_git(["add", "-A"], cwd=work_path)
        commit = run_git(
            ["commit", "-m", f"readme-agent: close promotional gaps ({result.facts_hash[:12]})"],
            cwd=work_path,
        )
        committed = commit.returncode == 0

    ok = result.status in ("COMPLIANT_NO_CHANGE", "GENERATED") and proof.ok
    return RunResult(
        ok=ok,
        status=result.status,
        org_repo=org_repo,
        push_block_ok=proof.ok,
        committed=committed,
        evidence_dir=result.evidence_dir,
    )


def run_registry(only: list[str] | None = None) -> list[RunResult]:
    results = []
    for entry in enabled_entries():
        if only and entry.org_repo not in only:
            continue
        try:
            results.append(run_repo(entry.org_repo, mode=entry.mode))
        except Exception as exc:  # noqa: BLE001 -- continue past any single repo's failure
            results.append(
                RunResult(
                    ok=False,
                    status=f"ERROR: {exc}",
                    org_repo=entry.org_repo,
                    push_block_ok=False,
                    committed=False,
                )
            )
    return results


def report(run_id: str) -> dict:
    evidence_path = paths.evidence_dir(run_id)
    manifest_path = evidence_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"no evidence found for run_id {run_id!r} at {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))
