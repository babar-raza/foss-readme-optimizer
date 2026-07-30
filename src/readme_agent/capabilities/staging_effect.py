"""Execute one qualified trusted proposal against disposable staging."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from readme_agent.authorization.registry import load_authorization_record
from readme_agent.capabilities.domains import README_PRESENTATION
from readme_agent.capabilities.effect_ledger import dispatch_gated_effect
from readme_agent.evidence.writer import sha256_file, write_redacted_json
from readme_agent.github_api.client import get_branch, get_file_content, repo_summary
from readme_agent.state.git_backend import default_state_backend
from readme_agent.state.proposal_schema import TrustedTransformationProposalV1
from readme_agent.state.trusted_cohort_schema import QualifiedTrustedCohortV1
from readme_agent.supervisor.trusted_cohort_qualification import trusted_bundle_dir
from readme_agent.verification.checks import compute_verification_token


def _proposal_id(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def execute_staging_effect(
    *,
    source_repository: str,
    target_repository: str,
    cohort_manifest: Path,
    staging_manifest: Path,
    authorization_dir: Path,
) -> dict:
    cohort = QualifiedTrustedCohortV1.model_validate_json(
        cohort_manifest.read_text(encoding="utf-8")
    )
    member = next((item for item in cohort.members if item.org_repo == source_repository), None)
    if member is None:
        raise ValueError("source repository is not in the qualified cohort")
    bundle = trusted_bundle_dir(source_repository, member.source_revision)
    candidate_path = bundle / "candidate" / "README.md"
    candidate_text = candidate_path.read_text(encoding="utf-8")
    if sha256_file(candidate_path)[0] != member.candidate_sha256:
        raise ValueError("candidate bytes do not match the qualified cohort")

    token = os.environ.get("README_AGENT_STAGING_WRITE_TOKEN")
    if not token:
        raise ValueError("README_AGENT_STAGING_WRITE_TOKEN is required")
    summary = repo_summary(target_repository, token)
    default_branch = summary["default_branch"]
    current_base = get_branch(target_repository, default_branch, token)["commit"]["sha"]
    source_readme = get_file_content(target_repository, "README.md", token, ref=default_branch)
    if hashlib.sha256(source_readme).hexdigest() != member.readme_sha256:
        raise ValueError("staging default README drifted; candidate must be requalified")

    record = load_authorization_record(target_repository, authorization_dir)
    if (
        record is None
        or record.authorization_id is None
        or record.content_assurance != "trusted_inherited"
        or record.proposal_kind != "trusted_readme_transform"
    ):
        raise ValueError("staging authorization is absent or assurance-incompatible")
    if record.expiration is None:
        raise ValueError("staging authorization must expire")

    identity = {
        "source_repository": source_repository,
        "target_repository": target_repository,
        "source_revision": member.source_revision,
        "target_base_revision": current_base,
        "candidate_hash": member.candidate_sha256,
        "cohort_id": cohort.cohort_id,
        "authorization_id": record.authorization_id,
    }
    proposal = TrustedTransformationProposalV1(
        proposal_id=_proposal_id(identity),
        source_repository=source_repository,
        target_repository=target_repository,
        source_revision=member.source_revision,
        target_base_revision=current_base,
        source_readme_hash=member.readme_sha256,
        facts_hash=member.facts_sha256,
        plan_hash=member.plan_sha256,
        candidate_hash=member.candidate_sha256,
        deterministic_validation_hash=member.deterministic_validation_sha256,
        independent_review_hash=member.independent_review_sha256,
        cohort_id=cohort.cohort_id,
        authorization_id=record.authorization_id,
        expires_at=record.expiration,
    )
    nonce = f"staging:{proposal.proposal_id}"
    verdict = compute_verification_token(
        target_repository, member.facts_sha256, member.readme_sha256, nonce
    )
    call = {
        "function": {
            "name": "open_presentation_pr",
            "arguments": {
                "org_repo": target_repository,
                "facts_hash": member.facts_sha256,
                "fresh_fingerprint": member.readme_sha256,
                "final_text": candidate_text,
                "verification_verdict": verdict,
                "verification_nonce": nonce,
                "source_repository": source_repository,
                "staging_target_manifest": str(staging_manifest),
                "trusted_proposal": proposal.model_dump(mode="json"),
                "content_assurance": "trusted_inherited",
            },
        }
    }
    result = dispatch_gated_effect(
        call,
        {"remote_write"},
        default_state_backend(),
        target_repository,
        caller_domain=README_PRESENTATION,
    )
    payload = {
        "schema_version": 1,
        "source_repository": source_repository,
        "target_repository": target_repository,
        "proposal": proposal.model_dump(mode="json"),
        "ledger_outcome": result.outcome,
        "dispatch_outcome": result.dispatch.outcome if result.dispatch else None,
        "result": result.cached_result or (result.dispatch.result if result.dispatch else None),
        "detail": result.detail,
        "error": result.dispatch.error if result.dispatch else None,
    }
    if result.outcome not in {"already_applied", "dispatched"} or (
        result.dispatch is not None and result.dispatch.outcome != "executed"
    ):
        raise RuntimeError(json.dumps(payload, sort_keys=True))
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repository", required=True)
    parser.add_argument("--target-repository", required=True)
    parser.add_argument("--cohort-manifest", type=Path, required=True)
    parser.add_argument("--staging-manifest", type=Path, required=True)
    parser.add_argument("--authorization-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    os.environ["README_AGENT_AUTHORIZATION_DIR"] = str(args.authorization_dir.resolve())
    os.environ["README_AGENT_PRODUCTION_AUTH"] = "staging_pat"
    payload = execute_staging_effect(
        source_repository=args.source_repository,
        target_repository=args.target_repository,
        cohort_manifest=args.cohort_manifest,
        staging_manifest=args.staging_manifest,
        authorization_dir=args.authorization_dir,
    )
    write_redacted_json(args.output, payload)
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
