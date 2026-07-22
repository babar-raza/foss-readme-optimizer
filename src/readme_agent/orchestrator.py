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
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from readme_agent import env, paths
from readme_agent.ecosystems.registry import parse_manifest
from readme_agent.errors import NotAllowlistedError, StateBackendError
from readme_agent.evidence.writer import generate_run_id, write_evidence
from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.clone import (
    clone_baseline,
    create_work_clone,
    force_rmtree,
    remote_head_sha,
)
from readme_agent.gitsafety.hooks import install_pre_push_hook
from readme_agent.gitsafety.neuter import neuter_push
from readme_agent.gitsafety.verify import PushBlockProof, verify_push_blocked
from readme_agent.inspection import file_inventory
from readme_agent.license.auditor import detect_license
from readme_agent.llm.client import GeneratedResult, LLMClient
from readme_agent.llm.fixture_client import FixtureLLMClient
from readme_agent.llm.live_client import LiveLLMClient
from readme_agent.llm.prompts import build_prompt, prompt_content_hash
from readme_agent.profile.cached import get_or_build_profile
from readme_agent.profile.schema import RepositoryProfile
from readme_agent.readme.facts import (
    GapReportFacts,
    RepositoryFacts,
    compute_facts_hash,
    compute_tracked_content_hash,
)
from readme_agent.readme.gap_detector import GapReport
from readme_agent.readme.gap_detector import detect as detect_gaps
from readme_agent.readme.markers import SPAN_NAMES, find_span, remove_span, upsert_span
from readme_agent.readme.presentation_report import detect_presentation
from readme_agent.readme.renderer import render_missing_elements
from readme_agent.registry.loader import (
    enabled_entries,
    find_entry,
    load_policy,
    load_products,
    require_listed,
)
from readme_agent.registry.models import PolicyProfile, ProductEntry
from readme_agent.state.backend import StateBackend
from readme_agent.state.schema import ProfileCacheV1, RunStateV1
from readme_agent.validation import registry as validation_registry
from readme_agent.validation.context import ValidationContext


@dataclass
class ReadmeCandidate:
    """The read-only render/validate decision for one `org_repo`'s README --
    no filesystem write happens until `commit_readme_candidate` is called
    with this result. Splits `generate_repo()`'s single pipeline at its write
    boundary (Wave 7 `EFF-001` fix, decision #26 addendum): the prior design
    wrapped the whole pipeline behind one `gated_effector` capability keyed on
    `facts_hash` -- but `facts_hash` is computed mid-pipeline, not a call
    argument, so it can't be supplied pre-dispatch the way the effect ledger
    requires (decision #36 already found and rejected this exact design for
    a different capability). This dataclass is the boundary: everything
    above it is pure computation (including validation -- no filesystem
    mutation), everything below it (`commit_readme_candidate`) is the one
    real write.

    `final_text != original_text` is the single source of truth for "does a
    write need to happen" -- deliberately replaces two separate write sites
    the original pipeline had (an unconditional callout-migration write, and
    a conditional render write): both collapse to one comparison here, with
    zero observable difference in end state, `GenerateResult`, or evidence
    content, since nothing reads the intermediate on-disk state between them
    within a single `generate_repo()` call.
    """

    entry: ProductEntry
    work_path: Path
    readme_path: Path
    baseline_readme_text: str
    original_text: str
    final_text: str
    facts: RepositoryFacts
    facts_hash: str
    fresh_fingerprint: str
    gap_report: GapReport
    skip_regeneration: bool
    durable_skip: bool
    new_spans: dict[str, str]
    existing_rendered_spans: dict[str, str]
    llm_called: bool
    llm_calls: list[str]
    llm_request: list[dict[str, str]] | None
    llm_response: object | None
    generated_result: GeneratedResult | None
    validation_results: list
    status: str
    proof: PushBlockProof


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


def require_permitted(org_repo: str) -> ProductEntry:
    """The hard allow-list gate (decision #4) -- public (Wave 5) so
    `supervisor/loop.py` enforces the exact same check, not a second
    near-duplicate implementation ("depend on seams, not internals")."""
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


def _work_clone_fingerprint_sidecar(work_path: Path) -> Path:
    # Sibling to, never inside, the git working tree -- `run_repo()`'s
    # `git add -A` must never pick this up as repo content (decision #38).
    return work_path.parent / f"{work_path.name}.tracked-content-fingerprint"


def _is_valid_work_clone(work_path: Path) -> bool:
    """A `.git` directory can exist yet be incomplete/corrupted (an
    interrupted clone missing `HEAD`/`config`/`refs`) -- git then silently
    walks up to the nearest valid PARENT repository instead of failing, so
    `.git`'s mere existence is not proof this clone is usable. Found live,
    2026-07-22: a work clone left with only `hooks/`+`objects/` resolved
    `rev-parse --show-toplevel` to this project's OWN repo root, not
    `work_path` -- meaning `neuter_push()` (called against what the caller
    believed was the target's own work clone) silently disabled push on this
    project's real remote instead. Guarding on the resolved toplevel actually
    matching `work_path` catches both failure shapes: a hard git error, or
    the surprising-but-real silent-walk-up-to-parent case."""
    result = run_git(["rev-parse", "--show-toplevel"], cwd=work_path)
    if result.returncode != 0:
        return False
    try:
        resolved = Path(result.stdout.strip()).resolve()
    except OSError:
        return False
    return resolved == work_path.resolve()


def _ensure_work_clone(
    entry: ProductEntry, baseline_path: Path, work_path: Path, *, fresh_fingerprint: str
) -> Path:
    """Reuse the persistent work clone (decision #12) only when the tracked
    upstream content (README/LICENSE/community files) hasn't actually
    changed since it was last built -- gated on `fresh_fingerprint`
    (`readme/facts.py::compute_tracked_content_hash`, computed from the
    always-fresh baseline clone), not merely on the clone's existence.

    Before decision #38, this reused an existing `work_path` unconditionally,
    with zero content comparison -- meaning `current_text`/`gap_report`/
    `facts_hash` (all read from `work_path`, not `baseline_path`) could go
    stale relative to real upstream edits for as long as the work clone
    survived. A blind `git fetch && reset --hard` was rejected instead: it
    would discard the uncommitted rendered span
    `test_second_run_is_idempotent_zero_llm_calls` depends on for its
    zero-LLM-calls guarantee. Fingerprint-gating preserves that guarantee
    exactly when content is unchanged (same fingerprint -> reuse, identical
    to today) and rebuilds from the already-fresh baseline the moment it
    isn't."""
    sidecar = _work_clone_fingerprint_sidecar(work_path)
    if work_path.exists() and (work_path / ".git").exists() and _is_valid_work_clone(work_path):
        if sidecar.exists() and sidecar.read_text(encoding="utf-8").strip() == fresh_fingerprint:
            return work_path  # reuse -- unchanged tracked content
    result = create_work_clone(entry, baseline_path, work_path)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(fresh_fingerprint, encoding="utf-8")
    return result


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


def prepare_readme_candidate(
    org_repo: str,
    *,
    force_regenerate: bool = False,
    llm_mode: str = "live",
    fixture_response_path: Path | None = None,
    state_backend: StateBackend | None = None,
    prior_facts_hash: str | None = None,
    prior_content_fingerprint: str | None = None,
    prior_status: str | None = None,
) -> ReadmeCandidate:
    """Everything through the render/skip decision and validation -- no
    filesystem write. See `ReadmeCandidate`'s docstring for why this split
    exists and why `final_text != original_text` alone is what decides
    whether `commit_readme_candidate` needs to write anything.

    `prior_facts_hash`/`prior_content_fingerprint`/`prior_status` (Wave 7
    production-reliability fix, found by independent review 2026-07-20): a
    second way to supply the same durable-skip signal `state_backend`
    already provides, as plain values rather than a live backend object --
    for `capabilities/render_readme_candidate.py`, which must stay stateless
    (decision #26(b)) and therefore cannot hold a `state_backend` itself.
    `specialists/readme_presentation.py`'s own `DomainStateV1` already IS
    this project's durable record of the last accepted render; without this
    parameter set, that capability had no way to learn it, so a fresh work
    clone (the normal case on an ephemeral CI runner, `RUN-001`) could never
    engage the durable-skip path here even though this exact function has
    had it, via `state_backend`, since decision #38 -- the result was a real
    LLM call on every single run with any upstream commit at all, not just
    one touching tracked content. If both `state_backend` and these
    arguments are supplied, `state_backend`'s own durable record wins (the
    original, CLI-path precedent); today no caller supplies both."""
    entry = require_permitted(org_repo)
    if entry.policy_profile is None or entry.ecosystem is None:
        raise NotAllowlistedError(f"{org_repo} has no policy_profile/ecosystem configured yet")
    policy = load_policy(entry.policy_profile)

    baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
    work_path = paths.work_dir(entry.org, entry.repo_name)
    clone_baseline(entry, baseline_path)
    # Computed from the baseline clone, which is always fresh (unlike
    # work_path) -- zero extra clone cost. The single canonical fingerprint
    # (decision #38): gates both the local work-clone reuse below and the
    # durable-skip decision further down, so "did tracked content change" is
    # answered the same way in both places, not reinvented twice.
    fresh_fingerprint = compute_tracked_content_hash(baseline_path)
    _ensure_work_clone(entry, baseline_path, work_path, fresh_fingerprint=fresh_fingerprint)
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
    original_text = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

    # Phase 21 migration (decision #9 as corrected): strip any legacy "callout"
    # span left over from before its retirement -- computed here, in memory,
    # regardless of this run's skip/render decision below, since everything
    # downstream must reason about migrated content; persisting it is
    # `commit_readme_candidate`'s job (folded into `final_text != original_
    # text`, not a separate write site anymore). Confirmed live: 2/3 pilots'
    # real evidence had a callout span (pdf/java: callout only, no resources
    # span at all).
    current_text = remove_span(original_text, "callout")

    manifest = parse_manifest(entry.ecosystem, work_path)
    license_state = detect_license(manifest.get("license"), inventory.license_path)

    gap_report = detect_gaps(current_text, detected_license=license_state.detected)
    facts = RepositoryFacts(
        org_repo=entry.org_repo,
        commit_sha=None,
        manifest=manifest,
        detected_license=license_state.detected,
        gap_report=GapReportFacts.from_gap_report(gap_report),
        policy_content_hash=_policy_content_hash(policy),
        prompt_content_hash=prompt_content_hash(),
    )
    facts_hash = compute_facts_hash(facts)

    # No callout fallback here -- it was stripped above, unconditionally, before
    # this point. "resources" is the sole owned span since Phase 21.
    existing = find_span(current_text, "resources")
    embedded_hash = existing.facts_hash if existing else None
    existing_rendered_spans = {
        name: m.content for name in SPAN_NAMES if (m := find_span(current_text, name))
    }

    # Wave 4 (`MEM-001`/`RUN-001`): `existing`/`embedded_hash` above answer
    # "does *this* work clone already carry the accepted marker" -- true only
    # when `paths.work_dir()`'s persistent local clone (decision #12)
    # survived between runs. On a fresh GitHub Actions runner it never does.
    # `durable_state` answers the same question from a backend that *does*
    # survive a fresh runner -- additive, not a replacement for the check
    # above. Best-effort like the write-back below (see `record_accepted_readme_state`):
    # a read failure degrades to "no durable state known," never aborts the run.
    durable_state = None
    if state_backend is not None:
        try:
            durable_state = state_backend.load(org_repo)
        except StateBackendError as exc:
            print(
                f"warning: durable state read failed, continuing without it: {exc}", file=sys.stderr
            )
    # A live state_backend's own record wins when supplied (the original
    # CLI-path precedent); otherwise fall back to the caller-supplied plain
    # values (see this function's own docstring for why those exist).
    if durable_state is not None:
        accepted_facts_hash = durable_state.accepted_facts_hash
        accepted_content_fingerprint = durable_state.upstream_content_fingerprint_at_accept
    else:
        accepted_facts_hash = prior_facts_hash
        accepted_content_fingerprint = prior_content_fingerprint
    # Decision #38: `accepted_facts_hash` matching alone is NOT sufficient --
    # `facts_hash` deliberately excludes README content (decision #11), so on
    # its own it is blind to a real upstream README/community-file edit. On
    # the exact topology this project runs on (a fresh GitHub Actions runner,
    # where `existing is None` is the normal case, not the exception --
    # `RUN-001`), that blindness was permanent: once facts_hash stabilized,
    # this fast path would skip validation forever regardless of what changed
    # upstream. Requiring the content fingerprint to also match closes that
    # gap while preserving the exact same skip behavior whenever content is
    # genuinely unchanged.
    durable_skip = (
        not force_regenerate
        and existing is None
        and accepted_facts_hash is not None
        and accepted_facts_hash == facts_hash
        and accepted_content_fingerprint == fresh_fingerprint
    )

    def _validate(readme_text: str, llm_response, rendered_spans: dict[str, str]):
        # Re-derive the embedded hash from the *text actually being
        # validated*, not the pre-render `embedded_hash` closed over above --
        # after a fresh render, `readme_text` carries a brand-new span
        # embedding today's facts_hash, and validating against the stale
        # pre-render value made `idempotency` fail on every single
        # force-regenerate (or any re-render of an already-spanned repo),
        # even a fully correct one. Found live in the same Phase 21 pilot
        # re-proof that surfaced the link-dropping bug above.
        validated_span = find_span(readme_text, "resources")
        ctx = ValidationContext(
            readme_text=readme_text,
            baseline_readme_text=baseline_readme_text,
            policy=policy,
            pre_render_gap_report=gap_report,
            rendered_spans=rendered_spans,
            llm_response=llm_response,
            facts_hash=facts_hash,
            embedded_hash=validated_span.facts_hash if validated_span else None,
            detected_license=license_state.detected,
        )
        return validation_registry.run_all(ctx)

    skip_regeneration = not force_regenerate and (
        gap_report.fully_compliant
        or (existing is not None and embedded_hash == facts_hash)
        or durable_skip
    )

    llm_called = False
    llm_calls: list[str] = []
    llm_request = None
    llm_response = None
    generated_result: GeneratedResult | None = None

    if skip_regeneration:
        if durable_skip:
            # Fresh-runner path (`RUN-001`'s actual target scenario): the
            # local work clone carries no marker of its own, but the durable
            # record (a live `state_backend`, or the plain `prior_*` values a
            # stateless capability caller supplied instead) already accepted
            # this exact facts_hash. Trust that record rather than
            # re-validating `current_text` -- it's the plain, unmodified
            # baseline content, not what was actually accepted, and would
            # fail validation for reasons that have nothing to do with this
            # run.
            results: list = []
            if durable_state is not None:
                status = durable_state.accepted_status or "COMPLIANT_NO_CHANGE"
            else:
                status = prior_status or "COMPLIANT_NO_CHANGE"
        else:
            results = _validate(current_text, None, existing_rendered_spans)
            status = (
                "COMPLIANT_NO_CHANGE"
                if validation_registry.passed(results)
                else "STALE_NONCOMPLIANT"
            )
        final_text = current_text
        new_spans: dict[str, str] = {}
    else:
        # Correctness fix (found live during the Phase 21 pilot re-proof,
        # force-regenerating cells/java): render decisions must never treat a
        # gap as "already satisfied" when the only evidence is inside the
        # resources span this render is about to replace -- upsert_span
        # overwrites the whole span, so basing render_gap_report on
        # gap_report (computed from current_text, which includes that same
        # span) silently dropped previously-rendered org/com links whenever
        # only *other* elements needed re-rendering. Re-detect against the
        # span-stripped text so every element the new span must carry is
        # correctly flagged as a gap again. The *skip* decision above
        # deliberately still uses the span-inclusive gap_report -- that's
        # what makes a hash-mismatch-only change land as STALE_NONCOMPLIANT
        # rather than silently auto-regenerating (decision #16).
        render_gap_report = detect_gaps(
            remove_span(current_text, "resources"), detected_license=license_state.detected
        )
        if force_regenerate and render_gap_report.relationship_explained:
            render_gap_report = dataclasses.replace(render_gap_report, relationship_explained=False)

        if render_gap_report.relationship_explained is False:
            llm_request = build_prompt(facts, policy)
            client: LLMClient
            if llm_mode == "fixture":
                if fixture_response_path is None:
                    raise ValueError("llm_mode='fixture' requires fixture_response_path")
                client = FixtureLLMClient(fixture_response_path)
            else:
                client = LiveLLMClient(
                    env.llm_base_url(),
                    env.llm_api_key(),
                    env.llm_model_for_job("relationship_explained"),
                )
            generated_result = client.generate(llm_request)
            llm_response = generated_result.response
            llm_called = True
            llm_calls.append("relationship_explained")

        new_spans = render_missing_elements(
            render_gap_report,
            policy,
            relationship_paragraph=llm_response.relationship_paragraph if llm_response else None,
        )
        final_text = current_text
        for span_name, content in new_spans.items():
            final_text = upsert_span(final_text, span_name, content, facts_hash)

        results = _validate(final_text, llm_response, new_spans)
        status = "GENERATED" if validation_registry.passed(results) else "BLOCKED_VALIDATION_FAILED"

    return ReadmeCandidate(
        entry=entry,
        work_path=work_path,
        readme_path=readme_path,
        baseline_readme_text=baseline_readme_text,
        original_text=original_text,
        final_text=final_text,
        facts=facts,
        facts_hash=facts_hash,
        fresh_fingerprint=fresh_fingerprint,
        gap_report=gap_report,
        skip_regeneration=skip_regeneration,
        durable_skip=durable_skip,
        new_spans=new_spans,
        existing_rendered_spans=existing_rendered_spans,
        llm_called=llm_called,
        llm_calls=llm_calls,
        llm_request=llm_request,
        llm_response=llm_response,
        generated_result=generated_result,
        validation_results=results,
        status=status,
        proof=proof,
    )


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


def commit_generated_readme(work_path: Path, facts_hash: str, status: str, *, mode: str) -> bool:
    """The one real git commit into the local work clone (never pushed) --
    gated on `mode == "full"` and `status == "GENERATED"`, extracted
    unchanged from `run_repo()`'s own inline logic (Wave 7g, `EFF-001`) so
    `capabilities/commit_readme_write.py` (the new gated-effector capability)
    calls this exact same real-commit logic instead of reimplementing it a
    second time. `run_repo()` below is refactored onto this with zero
    behavior change, proven by `test_orchestrator.py::TestRunModeFullCommitsLocally`
    passing unmodified."""
    if mode != "full" or status != "GENERATED":
        return False
    run_git(["add", "-A"], cwd=work_path)
    commit = run_git(
        ["commit", "-m", f"readme-agent: close promotional gaps ({facts_hash[:12]})"],
        cwd=work_path,
    )
    return commit.returncode == 0


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
    committed = commit_generated_readme(work_path, result.facts_hash, result.status, mode=mode)

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
