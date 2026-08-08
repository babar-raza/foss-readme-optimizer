"""Build directional format facts from native-tool and isolated-consumer evidence."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlencode

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatExtractionV1
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.repository_format_extraction import RepositoryFormatExtractionV1
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id
from readme_agent.registry.models import EvidenceBackedProductFact

_DIRECTIONAL_FORMAT = re.compile(
    r"(?i)^(?:input|output|input/output|load|read|import|save|write|export)\s+formats?\s*:\s*\S"
)
_FORMAT_STOPWORDS = frozenset({"file", "files", "format", "formats", "microsoft"})
_FORMAT_TOKEN_ALIASES = {
    "microsoft3mf": "3mf",
    "threemf": "3mf",
}


def format_direction_failures(specifications: Sequence[EvidenceBackedProductFact]) -> list[str]:
    """Reject format labels that erase whether the repository consumes or emits them."""

    failures: list[str] = []
    for specification in specifications:
        if _DIRECTIONAL_FORMAT.match(" ".join(specification.value.split())) is None:
            failures.append(
                "format direction missing: prefix the claim with 'Input format:', "
                "'Output format:', or both as separate evidence-backed claims"
            )
    return failures


def block_directionless_format_fact(
    fact: FactRecordV2,
    specifications: Sequence[EvidenceBackedProductFact],
) -> FactRecordV2:
    """Fail a verified format fact closed when its accepted values lost direction."""

    failures = format_direction_failures(specifications)
    if not failures or fact.verification_state != "verified":
        return fact
    return fact.model_copy(
        update={
            "value": {
                "assertions": [specification.value for specification in specifications],
                "evidence_failures": failures,
            },
            "verification_state": "blocked",
            "confidence": 0.0,
        }
    )


def _format_tokens(value: str) -> set[str]:
    normalized = re.sub(
        r"(?i)^(?:input|output|input/output|load|read|import|save|write|export)\s+formats?\s*:\s*",
        "",
        value,
    )
    tokens = {
        token.casefold()
        for token in re.findall(r"[A-Za-z0-9]+", normalized)
        if len(token) >= 2 and token.casefold() not in _FORMAT_STOPWORDS
    }
    tokens.update(match.casefold() for match in re.findall(r"\.[A-Za-z0-9]+", normalized))
    return tokens


def _label_for_token(specifications: Sequence[EvidenceBackedProductFact], token: str) -> str:
    normalized_token = _canonical_format_token(token)
    for specification in specifications:
        tokens = {_canonical_format_token(item) for item in _format_tokens(specification.value)}
        if normalized_token in tokens:
            return (
                re.sub(
                    r"(?i)^(?:input|output|input/output|load|read|import|save|write|export)"
                    r"\s+formats?\s*:\s*",
                    "",
                    specification.value,
                )
                .strip()
                .rstrip(".")
            )
    return token.upper()


def _canonical_format_token(token: str) -> str:
    normalized = token.casefold().lstrip(".")
    return _FORMAT_TOKEN_ALIASES.get(normalized, normalized)


def _verified_input_extensions(example_fact: FactRecordV2) -> set[str]:
    if example_fact.verification_state != "verified" or not isinstance(example_fact.value, dict):
        return set()
    bindings = example_fact.value.get("input_fixture_bindings")
    if not isinstance(bindings, list):
        return set()
    extensions: set[str] = set()
    for binding in bindings:
        if not isinstance(binding, dict):
            continue
        source_path = binding.get("source_path")
        if not isinstance(source_path, str):
            continue
        suffix = Path(source_path).suffix.casefold()
        if suffix:
            extensions.add(suffix)
    return extensions


def _native_extraction_location(extraction: AsposeOrgFormatExtractionV1) -> str:
    revision = extraction.extractor_revision or "unavailable"
    if (
        extraction.extractor_sha256 is None
        or extraction.dependency_sha256 is None
        or not extraction.dependency_files
    ):
        return f"aspose-org-extractor://{revision}"
    query = urlencode(
        {
            "extractor_sha256": extraction.extractor_sha256,
            "dependency_sha256": extraction.dependency_sha256,
            "receipt_sha256": extraction.receipt_sha256(),
        }
    )
    return f"aspose-org-extractor://{revision}?{query}"


def directional_format_fact_from_verified_evidence(
    *,
    source_revision: str,
    specifications: Sequence[EvidenceBackedProductFact],
    example_fact: FactRecordV2,
    native_extraction: AsposeOrgFormatExtractionV1 | RepositoryFormatExtractionV1,
) -> FactRecordV2:
    """Combine consumer-proven inputs with battle-tested native format extraction."""

    values: list[str] = []
    locations: list[str] = []

    for extension in sorted(_verified_input_extensions(example_fact)):
        label = _label_for_token(specifications, extension)
        value = f"Input format: {label}"
        if value not in values:
            values.append(value)
            locations.append("local-verifier://example.minimal")

    if native_extraction.status == "available":
        for entry in native_extraction.formats:
            if entry.direction not in {"import", "export", "both"} or entry.functional is not True:
                continue
            label = _label_for_token(specifications, entry.format)
            directions = ("import", "export") if entry.direction == "both" else (entry.direction,)
            for direction in directions:
                prefix = "Input format" if direction == "import" else "Output format"
                value = f"{prefix}: {label}"
                if value in values:
                    continue
                values.append(value)
                locations.append(f"repository://{entry.file}#L{entry.line}")

    failures: list[str] = []
    if not values:
        failures.append(
            "no input/output format survived isolated-consumer and native-extractor verification"
        )
    provenance_locations = sorted(set(locations))
    if native_extraction.status == "available" and isinstance(
        native_extraction, AsposeOrgFormatExtractionV1
    ):
        provenance_locations.append(_native_extraction_location(native_extraction))
    location = ";".join(provenance_locations) or "local-verifier://format-direction-unresolved"
    return FactRecordV2(
        fact_id=descriptive_fact_id("product.formats", "native-direction-evidence"),
        field="product.formats",
        value=values if not failures else {"assertions": [], "evidence_failures": failures},
        source=FactSourceV2(
            source_type="mechanical_test",
            location=location,
            source_revision=source_revision,
        ),
        verification_state="verified" if not failures else "blocked",
        authoritative_owner="repository-owner",
        confidence=1.0 if not failures else 0.0,
        affected_surfaces=SURFACE_DEPENDENCIES["product.formats"],
    )
