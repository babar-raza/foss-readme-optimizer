"""Deterministically classify a read-only repository intake snapshot."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field

from readme_agent.ecosystems.registry import known_manifest_globs
from readme_agent.registry.models import ProductEntry
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.state.lifecycle_schema import IntakePreflightOutcomeV1

INTAKE_PREFLIGHT_CONTRACT_VERSION = "read-only-intake-v1"
INTAKE_PREFLIGHT_CONTRACT_HASH = hashlib.sha256(
    INTAKE_PREFLIGHT_CONTRACT_VERSION.encode("utf-8")
).hexdigest()

_SECTION_SIGNAL = re.compile(
    r"\b(install|getting started|quick start|usage|example|documentation|"
    r"license|contribut|security|support)\b",
    re.IGNORECASE,
)


class ReadmeIntakeSignalsV1(BaseModel):
    """Small structural signal set used only to select a proof route."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    byte_count: int = Field(ge=0)
    heading_count: int = Field(ge=0)
    h1_count: int = Field(ge=0)
    code_block_count: int = Field(ge=0)
    link_count: int = Field(ge=0)
    reader_section_signal_count: int = Field(ge=0)


class ReadOnlyIntakePreflightV1(BaseModel):
    """Evidence-safe result; a fast-path decision never grants approval."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    org_repo: str = Field(min_length=3)
    provider_repository_id: int = Field(gt=0)
    source_revision: str = Field(pattern=r"^[0-9a-f]+$")
    source_revision_resolved: bool = True
    contract_hash: str = Field(min_length=64, max_length=64)
    outcome: IntakePreflightOutcomeV1
    reason: str = Field(min_length=1)
    readme_path: str | None = None
    readme_sha256: str | None = None
    signals: ReadmeIntakeSignalsV1 | None = None
    target_remote_effects_allowed: Literal[False] = False
    target_local_effects_allowed: Literal[False] = False

    def canonical_hash(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def intake_contract_hash(entry: ProductEntry) -> str:
    """Invalidate only when inputs that decide the intake route change."""

    material = json.dumps(
        {
            "active": entry.active,
            "ecosystem": entry.ecosystem,
            "platform": entry.platform,
            "policy_profile": entry.policy_profile,
            "rules": INTAKE_PREFLIGHT_CONTRACT_HASH,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode()).hexdigest()


def classify_readonly_intake(
    entry: ProductEntry,
    snapshot: RepositorySnapshotV1,
) -> ReadOnlyIntakePreflightV1:
    """Select a fast/full/block route without accepting any README claim."""

    identity = entry.provider_identity
    if identity is None:
        raise ValueError(f"{entry.org_repo!r} has no stable provider identity")
    base: dict[str, Any] = {
        "org_repo": entry.org_repo,
        "provider_repository_id": identity.repository_id,
        "source_revision": snapshot.source_revision,
        "contract_hash": intake_contract_hash(entry),
    }
    if not entry.active:
        return ReadOnlyIntakePreflightV1(
            **base,
            outcome="NOT_APPLICABLE",
            reason="the provider reports this admitted repository as archived or inactive",
        )
    if (entry.ecosystem is not None and entry.ecosystem not in known_manifest_globs()) or (
        entry.ecosystem is None and entry.platform not in known_manifest_globs()
    ):
        return ReadOnlyIntakePreflightV1(
            **base,
            outcome="BLOCKED_UNSUPPORTED",
            reason="no registered ecosystem parser can classify this repository",
        )
    if entry.ecosystem is None or entry.policy_profile is None:
        return ReadOnlyIntakePreflightV1(
            **base,
            outcome="BLOCKED_CLASSIFICATION",
            reason="ecosystem or policy profile is not yet configured",
        )
    if snapshot.readme_path is None:
        return ReadOnlyIntakePreflightV1(
            **base,
            outcome="READY_FULL_PIPELINE",
            reason="no source README exists; full evidence-backed composition is required",
        )

    readme_path = snapshot.root_path / snapshot.readme_path
    try:
        readme_bytes = readme_path.read_bytes()
        readme_text = readme_bytes.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        return ReadOnlyIntakePreflightV1(
            **base,
            outcome="BLOCKED_EVIDENCE",
            reason=f"source README could not be read as UTF-8: {type(exc).__name__}",
            readme_path=snapshot.readme_path,
        )

    signals = _readme_signals(readme_text, len(readme_bytes))
    readme_sha256 = hashlib.sha256(readme_bytes).hexdigest()
    if _is_fast_path_eligible(signals):
        outcome: IntakePreflightOutcomeV1 = "READY_FAST_PATH"
        reason = (
            "the existing README is structurally substantial; preserve-first proof may attempt "
            "a byte-identical candidate, but facts and independent approval remain mandatory"
        )
    else:
        outcome = "READY_FULL_PIPELINE"
        reason = "the existing README needs the ordinary evidence-backed assessment pipeline"
    return ReadOnlyIntakePreflightV1(
        **base,
        outcome=outcome,
        reason=reason,
        readme_path=snapshot.readme_path,
        readme_sha256=readme_sha256,
        signals=signals,
    )


def blocked_access_intake(
    entry: ProductEntry,
    source_revision: str,
    reason: str,
) -> ReadOnlyIntakePreflightV1:
    """Represent a read-only access failure without guessing repository content."""

    identity = entry.provider_identity
    if identity is None:
        raise ValueError(f"{entry.org_repo!r} has no stable provider identity")
    return ReadOnlyIntakePreflightV1(
        org_repo=entry.org_repo,
        provider_repository_id=identity.repository_id,
        source_revision=source_revision,
        source_revision_resolved=False,
        contract_hash=intake_contract_hash(entry),
        outcome="BLOCKED_ACCESS",
        reason=reason,
    )


def system_failure_intake(
    entry: ProductEntry,
    source_revision: str,
    reason: str,
) -> ReadOnlyIntakePreflightV1:
    """Represent an agent-fixable intake failure without losing its boundary."""

    identity = entry.provider_identity
    if identity is None:
        raise ValueError(f"{entry.org_repo!r} has no stable provider identity")
    return ReadOnlyIntakePreflightV1(
        org_repo=entry.org_repo,
        provider_repository_id=identity.repository_id,
        source_revision=source_revision,
        contract_hash=intake_contract_hash(entry),
        outcome="SYSTEM_FAILURE",
        reason=reason,
    )


def _readme_signals(text: str, byte_count: int) -> ReadmeIntakeSignalsV1:
    tokens = MarkdownIt("commonmark").parse(text)
    headings = [token for token in tokens if token.type == "heading_open"]
    return ReadmeIntakeSignalsV1(
        byte_count=byte_count,
        heading_count=len(headings),
        h1_count=sum(token.tag == "h1" for token in headings),
        code_block_count=sum(token.type in {"fence", "code_block"} for token in tokens),
        link_count=sum(
            child.type == "link_open" for token in tokens for child in (token.children or [])
        ),
        reader_section_signal_count=len(
            {
                match.group(0).casefold()
                for match in _SECTION_SIGNAL.finditer(
                    "\n".join(token.content for token in tokens if token.type == "inline")
                )
            }
        ),
    )


def _is_fast_path_eligible(signals: ReadmeIntakeSignalsV1) -> bool:
    return (
        signals.byte_count >= 1_200
        and signals.h1_count >= 1
        and signals.heading_count >= 4
        and signals.code_block_count >= 1
        and signals.link_count >= 1
        and signals.reader_section_signal_count >= 3
    )
