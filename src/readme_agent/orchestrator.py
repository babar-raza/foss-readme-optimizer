"""Compatibility orchestration and reporting around canonical capabilities."""

import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from readme_agent import paths
from readme_agent.ecosystems.registry import parse_manifest
from readme_agent.errors import StateBackendError
from readme_agent.evidence.writer import generate_run_id, write_evidence
from readme_agent.gitsafety.clone import (
    clone_baseline,
    force_rmtree,
    remote_head_sha,
)
from readme_agent.gitsafety.verify import verify_push_blocked
from readme_agent.inspection import file_inventory
from readme_agent.profile.cached import get_or_build_profile
from readme_agent.profile.schema import RepositoryProfile
from readme_agent.readme.candidate_pipeline import ReadmeCandidate, prepare_readme_candidate
from readme_agent.readme.gap_detector import GapReport
from readme_agent.readme.presentation_report import detect_presentation
from readme_agent.registry.access import require_permitted
from readme_agent.registry.loader import (
    enabled_entries,
    load_products,
    require_listed,
)
from readme_agent.registry.models import ProductEntry
from readme_agent.state.backend import StateBackend
from readme_agent.state.schema import ProfileCacheV1, RunStateV1


@dataclass
class GenerateResult:
    status: str  # COMPLIANT_NO_CHANGE | GENERATED | STALE_NONCOMPLIANT | BLOCKED_VALIDATION_FAILED
    org_repo: str
    gap_report: GapReport
    llm_called: bool
    llm_calls: list[str]  # `LLM-015`: which job(s) triggered a call this run
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


def record_accepted_readme_state(
    backend: StateBackend,
    org_repo: str,
    facts_hash: str,
    status: str,
    run_id: str | None,
    content_fingerprint: str,
) -> None:
    """Best-effort CAS write-back (Wave 4, `MEM-002`). Public (Wave 7,
    `EFF-001`/`ORC-004`): `commit_readme_candidate()`'s CLI path and
    `specialists/readme_presentation.py`'s `commit_readme_write` path
    (7g) both call this same function -- the whole point of unifying them
    is exactly one writer of `accepted_facts_hash`/`accepted_status`
    regardless of entry point, so this can no longer be a private,
    orchestrator-only helper ("depend on public seams, not `_`-private
    helpers").

    On `stale`, re-loads
    and re-checks rather than retrying blindly: if the now-current durable
    record already reflects this exact facts_hash, another runner already
    accepted the same outcome first and there is nothing to do. Otherwise a
    genuine conflicting write won the race -- this run's own local result
    still stands, it simply does not overwrite the durable record.

    Never able to fail the run by itself -- mirrors `inspect_repo`'s
    `check_install` convention (an opt-in enhancement must not be able to
    take down the command it's enhancing). Found live via a `RUN-003` `act`
    reproduction: a checkout that doesn't persist push credentials (a real,
    observed divergence from a genuine GitHub-hosted runner) made this raise
    `StateBackendError`, which was uncaught -- aborting the whole run and
    losing the evidence bundle for work that had already succeeded. A
    write-back failure now degrades to "not remembered this time," not to
    losing the run's actual, real output.

    Decision #38: builds the new state via `model_copy(update=...)` on top of
    the current record (or a fresh one, if none exists) rather than
    constructing a brand-new `RunStateV1(...)` from scratch -- the latter
    silently dropped `domain_states`/`supervisor_state` on every single call,
    a live bug (not merely a future risk): `supervisor_state` is already
    written today by `supervisor/loop.py::_record_supervisor_state()`, so for
    any `org_repo` where both `supervise` and `run`/`generate --durable-state`
    are ever invoked, this function was silently wiping whatever `supervise`
    had recorded on its very next call."""
    try:
        current = backend.load(org_repo)
        expected_version = current.state_version if current else None
        new_state = (current or RunStateV1(org_repo=org_repo)).model_copy(
            update={
                "accepted_facts_hash": facts_hash,
                "accepted_status": status,
                "upstream_content_fingerprint_at_accept": content_fingerprint,
                "last_run_id": run_id,
                "last_run_timestamp": datetime.now(UTC).isoformat(),
            }
        )
        result = backend.save(org_repo, new_state, expected_version)
        if result.outcome == "stale":
            reloaded = backend.load(org_repo)
            if reloaded is None or reloaded.accepted_facts_hash != facts_hash:
                return  # a genuine conflicting write won; do not clobber it
    except StateBackendError as exc:
        print(
            f"warning: durable state write-back failed, continuing without it: {exc}",
            file=sys.stderr,
        )


def inspect_repo(org_repo: str, *, check_install: bool = False) -> dict:
    """Clone baseline only, extract facts. No LLM, no work clone, no writes.

    check_install=True adds a live Maven-Central resolution check (Phase 21,
    dimension 5) -- opt-in only, matching the established pattern for live
    network checks (links/validator.py's check_live_reachable, --check-links):
    never a default, never able to fail this command by itself.

    Gated by require_listed(), not require_permitted() (decision #40): this
    is read-only, so mode is irrelevant -- it runs against every registry
    entry, including a mode: "disabled" one.
    """
    entry = require_listed(org_repo)
    baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
    clone_baseline(entry, baseline_path)

    inventory = file_inventory.scan(baseline_path)
    manifest = parse_manifest(entry.ecosystem, baseline_path) if entry.ecosystem else {}
    readme_text = inventory.readme_path.read_text(encoding="utf-8") if inventory.readme_path else ""

    resolver = None
    if check_install:
        # Import scoped to the opt-in path -- inspect never depends on network otherwise.
        from readme_agent.ecosystems.resolver import resolve

        resolver = resolve

    presentation = detect_presentation(
        readme_text,
        platform=entry.platform,
        ecosystem=entry.ecosystem,
        manifest=manifest,
        resolver=resolver,
    )

    return {
        "org_repo": org_repo,
        "manifest": manifest,
        "has_readme": inventory.readme_path is not None,
        "has_license_file": inventory.license_path is not None,
        "readme_length_chars": len(readme_text),
        "presentation_report": presentation,
    }


def commit_readme_candidate(
    candidate: ReadmeCandidate,
    org_repo: str,
    *,
    write_evidence_bundle: bool = True,
    state_backend: StateBackend | None = None,
) -> GenerateResult:
    """The one real write: persists `candidate.final_text` if it differs from
    what's currently on disk (folding the former unconditional callout-
    migration write and the conditional render write into one comparison --
    see `ReadmeCandidate`'s docstring), then durable-state write-back and
    evidence, exactly as `generate_repo()` always has."""
    if candidate.final_text != candidate.original_text:
        candidate.readme_path.parent.mkdir(parents=True, exist_ok=True)
        candidate.readme_path.write_text(candidate.final_text, encoding="utf-8")

    run_id = generate_run_id() if write_evidence_bundle else None

    # Write-back (`MEM-002`, CAS): only on a definitively accepted outcome,
    # and only for a real run -- `validate_repo()` calls this with
    # `write_evidence_bundle=False` specifically to write nothing.
    if (
        state_backend is not None
        and write_evidence_bundle
        and candidate.status in ("GENERATED", "COMPLIANT_NO_CHANGE")
    ):
        record_accepted_readme_state(
            state_backend,
            org_repo,
            candidate.facts_hash,
            candidate.status,
            run_id,
            candidate.fresh_fingerprint,
        )

    evidence_path = None
    if write_evidence_bundle:
        assert run_id is not None  # generated above whenever write_evidence_bundle is True
        evidence_path = paths.evidence_dir(run_id)
        write_evidence(
            evidence_path,
            run_id=run_id,
            org_repo=org_repo,
            mode="dry_run",
            status=candidate.status,
            facts=candidate.facts,
            facts_hash=candidate.facts_hash,
            llm_mode=(candidate.generated_result.mode if candidate.generated_result else None),
            llm_calls=candidate.llm_calls,
            llm_request=candidate.llm_request,
            llm_response=candidate.llm_response,
            baseline_readme=candidate.baseline_readme_text,
            work_readme=candidate.final_text,
            rendered_spans=(
                candidate.new_spans
                if not candidate.skip_regeneration
                else candidate.existing_rendered_spans
            ),
            validation_results=candidate.validation_results,
            push_block_detail=candidate.proof.detail,
        )

    return GenerateResult(
        status=candidate.status,
        org_repo=org_repo,
        gap_report=candidate.gap_report,
        llm_called=candidate.llm_called,
        llm_calls=candidate.llm_calls,
        validation_results=candidate.validation_results,
        facts_hash=candidate.facts_hash,
        work_readme_path=candidate.readme_path,
        evidence_dir=evidence_path,
    )


def generate_repo(
    org_repo: str,
    *,
    force_regenerate: bool = False,
    llm_mode: str = "live",
    fixture_response_path: Path | None = None,
    write_evidence_bundle: bool = True,
    state_backend: StateBackend | None = None,
) -> GenerateResult:
    candidate = prepare_readme_candidate(
        org_repo,
        force_regenerate=force_regenerate,
        llm_mode=llm_mode,
        fixture_response_path=fixture_response_path,
        state_backend=state_backend,
    )
    return commit_readme_candidate(
        candidate,
        org_repo,
        write_evidence_bundle=write_evidence_bundle,
        state_backend=state_backend,
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
    state_backend: StateBackend | None = None,
) -> RunResult:
    entry = require_permitted(org_repo)
    result = generate_repo(
        org_repo,
        force_regenerate=force_regenerate,
        llm_mode=llm_mode,
        fixture_response_path=fixture_response_path,
        state_backend=state_backend,
    )

    work_path = paths.work_dir(entry.org, entry.repo_name)
    proof = verify_push_blocked(work_path)
    # Compatibility façade only: the legacy orchestrator never commits.
    # The sole commit primitive is owned by the registered
    # `commit_readme_write` capability, after independent verification and
    # the effect-ledger gate. Keeping the old local commit here was ORC-005.
    committed = False

    ok = result.status in ("COMPLIANT_NO_CHANGE", "GENERATED") and proof.ok
    return RunResult(
        ok=ok,
        status=result.status,
        org_repo=org_repo,
        push_block_ok=proof.ok,
        committed=committed,
        evidence_dir=result.evidence_dir,
    )


def profile_repo_with_cache(
    entry: ProductEntry, state_backend: StateBackend | None
) -> RepositoryProfile:
    """Deterministic-wiring counterpart to the now-stateless
    `profile.cached.get_or_build_profile()` (decision #26(b), Part E of the
    follow-up plan): owns loading `RunStateV1.profile_cache` before the call
    and CAS-writing the fresh result back after it -- exactly what this
    module's own docstring convention says wiring code, not a capability,
    should own. Mirrors `record_accepted_readme_state()`'s best-effort
    CAS write-back pattern immediately above (never able to fail the caller
    itself).

    Resolves `remote_head_sha()` a second time for the write-back rather
    than reusing `get_or_build_profile()`'s internal one: that function
    only ever returns a `RepositoryProfile`, never the revision it resolved,
    so on a cache *miss* there is no other way to know what revision the
    fresh profile is actually current as of. The extra `git ls-remote` is
    cheap (no clone) -- correctness here matters more than saving one small
    network round-trip."""
    prior_upstream_revision = None
    prior_profile_result = None
    if state_backend is not None:
        try:
            current = state_backend.load(entry.org_repo)
        except StateBackendError:
            current = None
        if current is not None and current.profile_cache is not None:
            prior_upstream_revision = current.profile_cache.upstream_revision
            prior_profile_result = current.profile_cache.profile_result

    profile = get_or_build_profile(
        entry,
        prior_upstream_revision=prior_upstream_revision,
        prior_profile_result=prior_profile_result,
    )

    if state_backend is not None:
        current_revision = remote_head_sha(entry.clone_url)
        if current_revision is not None:
            try:
                current = state_backend.load(entry.org_repo)
                expected_version = current.state_version if current else None
                cache = ProfileCacheV1(
                    upstream_revision=current_revision,
                    profile_result=profile.model_dump(mode="json"),
                )
                new_state = (current or RunStateV1(org_repo=entry.org_repo)).model_copy(
                    update={"profile_cache": cache}
                )
                state_backend.save(entry.org_repo, new_state, expected_version)
            except StateBackendError as exc:
                print(
                    f"warning: durable state write-back failed, continuing without it: {exc}",
                    file=sys.stderr,
                )

    return profile


def run_registry(
    only: list[str] | None = None, state_backend: StateBackend | None = None
) -> list[RunResult]:
    results = []
    for entry in enabled_entries():
        if only and entry.org_repo not in only:
            continue
        try:
            results.append(run_repo(entry.org_repo, mode=entry.mode, state_backend=state_backend))
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
        finally:
            # Decision #40/Part B: baseline_path is only ever re-cloned fresh
            # right before its *own* next clone (clone_baseline() force-
            # removes then), never cleaned up after -- fine for a single
            # repo, but a registry-wide loop over several large repos in one
            # job otherwise accumulates every one of their baseline clones on
            # disk for the rest of the batch. paths.work_dir() is untouched
            # here -- that one is deliberately persistent across runs
            # (decision #12), not scoped to this loop.
            baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
            if baseline_path.exists():
                force_rmtree(baseline_path)
    return results


def run_registry_profiling_sweep(
    state_backend: StateBackend | None = None, only: list[str] | None = None
) -> list[RepositoryProfile]:
    """The actual answer to "large-repo profiling latency across several
    huge registry repos, on free GitHub runners" (decision #40, Part E):
    nothing before this looped the registry calling profiling at all.
    Iterates `load_products()` -- **every** entry, not `enabled_entries()`
    -- since this is read-only, and decision #40 already established
    read-only capabilities cover the whole registry regardless of mode, the
    same reasoning `require_listed()` already applies one level down.
    Reuses `run_registry()`'s exact failure-isolation and disk-cleanup shape
    (a repo that fails to profile is skipped, not fatal to the sweep; its
    baseline clone, if any, is removed before moving to the next repo)."""
    profiles: list[RepositoryProfile] = []
    for entry in load_products():
        if only and entry.org_repo not in only:
            continue
        try:
            profiles.append(profile_repo_with_cache(entry, state_backend))
        except Exception as exc:  # noqa: BLE001 -- continue past any single repo's failure
            print(f"warning: profiling {entry.org_repo} failed: {exc}", file=sys.stderr)
        finally:
            baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
            if baseline_path.exists():
                force_rmtree(baseline_path)
    return profiles


def report(run_id: str) -> dict:
    evidence_path = paths.evidence_dir(run_id)
    manifest_path = evidence_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"no evidence found for run_id {run_id!r} at {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))
