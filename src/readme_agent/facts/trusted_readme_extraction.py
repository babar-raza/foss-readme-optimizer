"""Extract source-complete trusted evidence from one immutable README."""

from __future__ import annotations

import hashlib
import re

from markdown_it import MarkdownIt
from markdown_it.token import Token
from pydantic import TypeAdapter

from readme_agent.errors import RepositorySnapshotError
from readme_agent.facts.trusted_readme_schema import (
    ConfiguredStandardAdditionV1,
    ConfiguredStandardIdV1,
    InheritedReadmeFactV1,
    InstructionRiskV1,
    ReadmeMaterialKindV1,
    ReadmeSourceSpanV1,
    TrustedReadmeFactGraphV1,
)
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot

_MATERIAL_TOKEN_KINDS: dict[str, ReadmeMaterialKindV1] = {
    "heading_open": "heading",
    "paragraph_open": "paragraph",
    "bullet_list_open": "unordered_list",
    "ordered_list_open": "ordered_list",
    "blockquote_open": "blockquote",
    "fence": "code",
    "code_block": "code",
    "html_block": "html",
    "hr": "thematic_break",
    "table_open": "table",
}
_PROMPT_INJECTION = re.compile(
    r"(?is)\b(?:ignore|disregard|override)\s+(?:all\s+)?"
    r"(?:previous|prior|system|developer)\s+(?:instructions?|prompts?)\b|"
    r"\b(?:system|developer)\s+(?:message|prompt)\s*:|"
    r"\b(?:do not|never)\s+(?:follow|obey)\s+(?:the\s+)?(?:system|developer)\b"
)
_HTML_COMMENT = re.compile(r"(?s)<!--.*?-->")
_STANDARD_AUTHORITIES: dict[ConfiguredStandardIdV1, tuple[str, ...]] = {
    "readme.header": ("L8-021",),
    "readme.badges": ("L8-021",),
    "readme.navigation": ("L8-020",),
    "readme.at_a_glance_mermaid": ("L8-021",),
    "readme.enterprise_edition_terminology": ("L8-026",),
    "readme.contextual_links": ("L8-022", "L8-023", "L8-024"),
}
_STANDARD_ID_ADAPTER: TypeAdapter[ConfiguredStandardIdV1] = TypeAdapter(ConfiguredStandardIdV1)


def _line_character_offsets(source: str) -> list[int]:
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    if offsets[-1] < len(source):
        offsets.append(len(source))
    return offsets


def _byte_offset(source: str, character_offset: int) -> int:
    return len(source[:character_offset].encode("utf-8"))


def _heading_text(tokens: list[Token], index: int) -> str:
    if index + 1 < len(tokens) and tokens[index + 1].type == "inline":
        return tokens[index + 1].content.strip()
    return ""


def _update_heading_path(
    heading_path: list[str],
    token: Token,
    heading_text: str,
) -> list[str]:
    try:
        level = int(token.tag.removeprefix("h"))
    except ValueError:
        return heading_path
    retained = heading_path[: max(0, level - 1)]
    return [*retained, heading_text]


def _instruction_risks(value: str) -> tuple[InstructionRiskV1, ...]:
    risks: list[InstructionRiskV1] = []
    if _PROMPT_INJECTION.search(value):
        risks.append("prompt_injection")
    if _HTML_COMMENT.search(value):
        risks.append("hidden_content")
    return tuple(risks)


def _material_tokens(
    source: str,
) -> list[tuple[Token, ReadmeMaterialKindV1, tuple[str, ...]]]:
    tokens = MarkdownIt("commonmark", {"html": True}).parse(source)
    heading_path: list[str] = []
    selected: list[tuple[Token, ReadmeMaterialKindV1, tuple[str, ...]]] = []
    for index, token in enumerate(tokens):
        if token.level != 0 or token.map is None or token.type not in _MATERIAL_TOKEN_KINDS:
            continue
        if token.type == "heading_open":
            heading_path = _update_heading_path(heading_path, token, _heading_text(tokens, index))
        selected.append((token, _MATERIAL_TOKEN_KINDS[token.type], tuple(heading_path)))
    return selected


def extract_trusted_readme_fact_graph(
    snapshot: RepositorySnapshotV1,
    *,
    verify_snapshot: bool = True,
) -> TrustedReadmeFactGraphV1:
    """Inventory exact material blocks without consulting any external fact authority."""

    if verify_snapshot:
        verify_repository_snapshot(snapshot)
    if snapshot.readme_path is None or snapshot.readme_sha256 is None:
        raise RepositorySnapshotError(
            f"{snapshot.org_repo}@{snapshot.source_revision} has no README to transform"
        )
    readme_path = snapshot.root_path / snapshot.readme_path
    source_bytes = readme_path.read_bytes()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    if source_sha256 != snapshot.readme_sha256:
        raise RepositorySnapshotError("snapshot README checksum changed before trusted extraction")
    try:
        source = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RepositorySnapshotError("snapshot README is not valid UTF-8") from exc
    line_offsets = _line_character_offsets(source)
    inherited_facts: list[InheritedReadmeFactV1] = []
    seen_spans: set[tuple[int, int]] = set()
    covered_characters = [False] * len(source)
    for token, material_kind, heading_path in _material_tokens(source):
        start_line, end_line = token.map or (0, 0)
        character_start = line_offsets[start_line]
        character_end = line_offsets[end_line]
        byte_start = _byte_offset(source, character_start)
        byte_end = _byte_offset(source, character_end)
        span_key = (byte_start, byte_end)
        if span_key in seen_spans:
            continue
        seen_spans.add(span_key)
        value = source[character_start:character_end]
        if not value.strip():
            continue
        for character_index in range(character_start, character_end):
            covered_characters[character_index] = True
        content_sha256 = hashlib.sha256(value.encode("utf-8")).hexdigest()
        identity = hashlib.sha256(
            f"{snapshot.source_revision}:{byte_start}:{byte_end}:{content_sha256}".encode()
        ).hexdigest()
        inherited_facts.append(
            InheritedReadmeFactV1(
                fact_id=f"readme.inherited:{identity[:24]}",
                value=value,
                material_kind=material_kind,
                heading_path=heading_path,
                source_span=ReadmeSourceSpanV1(
                    source_path=snapshot.readme_path,
                    source_revision=snapshot.source_revision,
                    source_sha256=source_sha256,
                    byte_start=byte_start,
                    byte_end=byte_end,
                    start_line=start_line + 1,
                    end_line_exclusive=end_line + 1,
                    content_sha256=content_sha256,
                ),
                instruction_risks=_instruction_risks(value),
            )
        )
    if not inherited_facts:
        raise RepositorySnapshotError("snapshot README contains no material Markdown blocks")
    uncovered_material = "".join(
        character
        for character, covered in zip(source, covered_characters, strict=True)
        if not covered and not character.isspace()
    )
    if uncovered_material:
        raise RepositorySnapshotError(
            "Markdown inventory left non-whitespace README content without source accountability"
        )
    return TrustedReadmeFactGraphV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        readme_path=snapshot.readme_path,
        readme_sha256=source_sha256,
        source_byte_count=len(source_bytes),
        covered_material_byte_count=sum(
            fact.source_span.byte_end - fact.source_span.byte_start for fact in inherited_facts
        ),
        inherited_facts=tuple(inherited_facts),
    )


def configured_standard_addition(
    standard_id: str,
    *,
    configuration_source: str,
    configuration_bytes: bytes,
    parameters: dict | None = None,
) -> ConfiguredStandardAdditionV1:
    """Create only a catalogued addition with separate configured provenance."""

    validated_id = _STANDARD_ID_ADAPTER.validate_python(standard_id)
    return ConfiguredStandardAdditionV1(
        standard_id=validated_id,
        authority_requirement_ids=_STANDARD_AUTHORITIES[validated_id],
        configuration_source=configuration_source,
        configuration_sha256=hashlib.sha256(configuration_bytes).hexdigest(),
        parameters=parameters or {},
    )


def bind_configured_standards(
    graph: TrustedReadmeFactGraphV1,
    additions: list[ConfiguredStandardAdditionV1],
) -> TrustedReadmeFactGraphV1:
    """Return a graph whose non-inherited additions remain separately attributable."""

    payload = graph.model_dump(mode="python")
    payload["configured_standards"] = additions
    return TrustedReadmeFactGraphV1.model_validate(payload)
