"""Build and validate an immutable README candidate without applying effects."""

import dataclasses
import sys
from pathlib import Path

from readme_agent import env, paths
from readme_agent.ecosystems.registry import parse_manifest
from readme_agent.errors import NotAllowlistedError, StateBackendError
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.gitsafety.hooks import install_pre_push_hook
from readme_agent.gitsafety.neuter import neuter_push
from readme_agent.gitsafety.verify import verify_push_blocked
from readme_agent.inspection import file_inventory
from readme_agent.license.auditor import detect_license
from readme_agent.llm.client import GeneratedResult, LLMClient
from readme_agent.llm.fixture_client import FixtureLLMClient
from readme_agent.llm.live_client import LiveLLMClient
from readme_agent.llm.prompts import build_prompt, prompt_content_hash
from readme_agent.readme.candidate_models import ReadmeCandidate
from readme_agent.readme.candidate_workspace import ensure_work_clone, policy_content_hash
from readme_agent.readme.facts import (
    GapReportFacts,
    RepositoryFacts,
    compute_facts_hash,
    compute_tracked_content_hash,
)
from readme_agent.readme.gap_detector import detect as detect_gaps
from readme_agent.readme.markers import SPAN_NAMES, find_span, remove_span, upsert_span
from readme_agent.readme.renderer import render_missing_elements
from readme_agent.registry.access import require_permitted
from readme_agent.registry.loader import (
    load_policy,
)
from readme_agent.state.backend import StateBackend
from readme_agent.validation import registry as validation_registry
from readme_agent.validation.context import ValidationContext


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
    ensure_work_clone(entry, baseline_path, work_path, fresh_fingerprint=fresh_fingerprint)
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
        policy_content_hash=policy_content_hash(policy),
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
