"""Enforce inherited provenance for executable code in trusted README candidates."""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass

from markdown_it import MarkdownIt

from readme_agent.errors import LLMError
from readme_agent.facts.example_quality import strip_source_comments


@dataclass(frozen=True)
class TrustedCodeBlockFingerprint:
    """One normalized, language-bound inherited code-block identity."""

    language: str
    content: str

    @property
    def sha256(self) -> str:
        payload = f"{self.language}\0{self.content}".encode()
        return hashlib.sha256(payload).hexdigest()


def _code_block_fingerprints(markdown: str) -> Counter[TrustedCodeBlockFingerprint]:
    blocks: Counter[TrustedCodeBlockFingerprint] = Counter()
    for token in MarkdownIt("commonmark").parse(markdown):
        if token.type not in {"fence", "code_block"}:
            continue
        language = token.info.strip().split(maxsplit=1)[0].casefold()
        if language == "mermaid":
            continue
        stripped = strip_source_comments(language, token.content).replace("\r\n", "\n")
        content = "\n".join(line.rstrip() for line in stripped.splitlines() if line.strip())
        blocks[TrustedCodeBlockFingerprint(language=language, content=content)] += 1
    return blocks


def validate_trusted_code_block_provenance(source_text: str, candidate_text: str) -> None:
    """Reject executable candidate blocks absent from the inherited README."""

    source_blocks = _code_block_fingerprints(source_text)
    candidate_blocks = _code_block_fingerprints(candidate_text)
    introduced = candidate_blocks - source_blocks
    if not introduced:
        return
    identities = sorted(
        f"{block.language or 'plain'}:{block.sha256[:16]} x{count}"
        for block, count in introduced.items()
    )
    raise LLMError(
        "trusted composition candidate introduced executable code without inherited "
        f"README provenance: {identities}"
    )
