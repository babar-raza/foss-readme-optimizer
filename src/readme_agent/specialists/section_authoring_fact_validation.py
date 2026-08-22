"""Reject section prose that contradicts deterministic fact coordinates."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable

from readme_agent.facts.format_vocabulary import canonical_document_format
from readme_agent.readme.presentation_similarity import semantic_content_words
from readme_agent.specialists.section_authoring_contracts import (
    OmittedFactV1,
    SectionAuthoringFactV1,
    SectionAuthoringPacketV1,
    SectionClusterAuthoringResultV1,
    SectionClusterUnitV1,
)

_REGISTRY_NAME = re.compile(
    r"(?i)\b(?:pypi|nuget|maven central|npm(?:js)?|crates\.io|go (?:module )?proxy|"
    r"(?:public )?(?:python )?package registr(?:y|ies))\b"
)
_CLOSED_WORLD_DENIAL = re.compile(
    r"(?i)\b(?:does not|doesn't|do not|don't|cannot|can't)\s+support\b[^.\n]{0,140}"
    r"\b(?:other|beyond|except|outside|only)\b|\bonly supports?\b"
)
_UNSUPPORTED_POSITIONING = re.compile(
    r"(?i)\b(?:complete|comprehensive|effortless|ensur(?:e|es|ing)|powerful|rapid|reliable|"
    r"robust|seamless|production[- ]ready|fully implemented|(?:smallest|simplest) possible|"
    r"only supported|"
    r"requiring only)\b|"
    r"\bwithout (?:any )?external [a-z][a-z-]*\b"
)
_SIBLING_GENERIC_WORDS = frozenset(
    {"3d", "and", "file", "format", "includ", "operation", "support", "system"}
)
_FORMAT_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9])(?P<token>\.?[A-Za-z0-9][A-Za-z0-9.+_-]{1,})(?![A-Za-z0-9])"
)
_DIRECTIONAL_FORMAT_VALUE = re.compile(
    r"(?i)^(?P<role>input|output)\s+formats?\s*:\s*(?P<format>\S+)"
)
_INPUT_FORMAT_CLAIM = re.compile(r"(?i)\b(?:input|import|load|open|read)(?:s|ed|ing)?\b")
_OUTPUT_FORMAT_CLAIM = re.compile(r"(?i)\b(?:export|output|save|write)(?:s|ed|ing)?\b")
_AMBIGUOUS_LOWERCASE_FORMAT_WORDS = frozenset({"one"})
_NON_EXECUTION_PREDICATES = frozenset(
    {"allow", "contain", "enable", "include", "provide", "support"}
)
_EXAMPLE_OPERATION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("access", re.compile(r"(?i)\baccess(?:es|ed|ing)?\b")),
    ("add", re.compile(r"(?i)\badd(?:s|ed|ing)?\b")),
    ("append", re.compile(r"(?i)\bappend(?:s|ed|ing)?\b")),
    ("allow", re.compile(r"(?i)\ballow(?:s|ed|ing)?\b")),
    ("automate", re.compile(r"(?i)\bautomat(?:e|es|ed|ing)\b")),
    ("apply", re.compile(r"(?i)\bappl(?:y|ies|ied|ying)\b")),
    ("build", re.compile(r"(?i)\bbuild(?:s|ing)?|\bbuilt\b")),
    ("compress", re.compile(r"(?i)\bcompress(?:es|ed|ing)?\b")),
    ("concatenate", re.compile(r"(?i)\bconcatenat(?:e|es|ed|ing)\b")),
    ("configure", re.compile(r"(?i)\bconfigur(?:e|es|ed|ing)\b")),
    ("contain", re.compile(r"(?i)\bcontain(?:s|ed|ing)?\b")),
    ("construct", re.compile(r"(?i)\bconstruct(?:s|ed|ing)?\b")),
    ("convert", re.compile(r"(?i)\bconvert(?:s|ed|ing)?\b")),
    ("create", re.compile(r"(?i)\bcreat(?:e|es|ed|ing)\b")),
    ("decode", re.compile(r"(?i)\bdecod(?:e|es|ed|ing)\b")),
    ("decrypt", re.compile(r"(?i)\bdecrypt(?:s|ed|ing)?\b")),
    ("define", re.compile(r"(?i)\bdefin(?:e|es|ed|ing)\b")),
    ("delete", re.compile(r"(?i)\bdelet(?:e|es|ed|ing)\b")),
    ("detect", re.compile(r"(?i)\bdetect(?:s|ed|ing)?\b")),
    ("edit", re.compile(r"(?i)\bedit(?:s|ed|ing)?\b")),
    ("enable", re.compile(r"(?i)\benabl(?:e|es|ed|ing)\b")),
    ("encode", re.compile(r"(?i)\bencod(?:e|es|ed|ing)\b")),
    ("encrypt", re.compile(r"(?i)\bencrypt(?:s|ed|ing)?\b")),
    ("export", re.compile(r"(?i)\bexport(?:s|ed|ing)?\b")),
    ("extract", re.compile(r"(?i)\bextract(?:s|ed|ing)?\b")),
    ("generate", re.compile(r"(?i)\bgenerat(?:e|es|ed|ing)\b")),
    ("import", re.compile(r"(?i)\bimport(?:s|ed|ing)?\b")),
    ("include", re.compile(r"(?i)\binclud(?:e|es|ed|ing)\b")),
    ("integrate", re.compile(r"(?i)\bintegrat(?:e|es|ed|ing)\b")),
    ("insert", re.compile(r"(?i)\binsert(?:s|ed|ing)?\b")),
    ("inspect", re.compile(r"(?i)\binspect(?:s|ed|ing)?\b")),
    ("instantiate", re.compile(r"(?i)\binstantiat(?:e|es|ed|ing)\b")),
    ("load", re.compile(r"(?i)\bload(?:s|ed|ing)?\b")),
    ("manipulate", re.compile(r"(?i)\bmanipulat(?:e|es|ed|ing)\b")),
    ("manage", re.compile(r"(?i)\bmanag(?:e|es|ed|ing)\b")),
    ("merge", re.compile(r"(?i)\bmerg(?:e|es|ed|ing)\b")),
    ("modify", re.compile(r"(?i)\bmodif(?:y|ies|ied|ying)\b")),
    ("navigate", re.compile(r"(?i)\bnavigat(?:e|es|ed|ing)\b")),
    ("open", re.compile(r"(?i)\bopen(?:s|ed|ing)?\b")),
    ("optimize", re.compile(r"(?i)\boptimi[sz](?:e|es|ed|ing)\b")),
    ("parse", re.compile(r"(?i)\bpars(?:e|es|ed|ing)\b")),
    ("process", re.compile(r"(?i)\bprocess(?:es|ed|ing)?\b")),
    ("provide", re.compile(r"(?i)\bprovid(?:e|es|ed|ing)\b")),
    ("read", re.compile(r"(?i)\bread(?:s|ing)?\b")),
    ("remove", re.compile(r"(?i)\bremov(?:e|es|ed|ing)\b")),
    ("render", re.compile(r"(?i)\brender(?:s|ed|ing)?\b")),
    ("replace", re.compile(r"(?i)\breplac(?:e|es|ed|ing)\b")),
    ("run", re.compile(r"(?i)\brun(?:s|ning)?|\bran\b")),
    ("save", re.compile(r"(?i)\bsav(?:e|es|ed|ing)\b")),
    ("search", re.compile(r"(?i)\bsearch(?:es|ed|ing)?\b")),
    ("sign", re.compile(r"(?i)\bsign(?:s|ed|ing)?\b")),
    ("support", re.compile(r"(?i)\bsupport(?:s|ed|ing)?\b")),
    ("transform", re.compile(r"(?i)\btransform(?:s|ed|ing)?\b")),
    ("traverse", re.compile(r"(?i)\btravers(?:e|es|ed|ing)\b")),
    ("update", re.compile(r"(?i)\bupdat(?:e|es|ed|ing)\b")),
    ("validate", re.compile(r"(?i)\bvalidat(?:e|es|ed|ing)\b")),
    ("verify", re.compile(r"(?i)\bverif(?:y|ies|ied|ying)\b")),
    ("write", re.compile(r"(?i)\bwrit(?:e|es|ing)|\bwrote\b|\bwritten\b")),
)


def _structured_values(value: object, keys: set[str]) -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys and isinstance(item, (str, int, float)):
                rendered = str(item).strip()
                if rendered:
                    yield key, rendered
            yield from _structured_values(item, keys)
    elif isinstance(value, list):
        for item in value:
            yield from _structured_values(item, keys)


def _contains_literal(text: str, literal: str) -> bool:
    if len(literal) < 2:
        return False
    if re.fullmatch(r"[A-Za-z0-9_.+-]+", literal):
        return (
            re.search(
                rf"(?<![A-Za-z0-9_.+-]){re.escape(literal)}(?![A-Za-z0-9_.+-])",
                text,
                flags=re.IGNORECASE,
            )
            is not None
        )
    return literal.casefold() in text.casefold()


def _deterministic_literal_errors(
    unit: SectionClusterUnitV1,
    cited_facts: Iterable[SectionAuthoringFactV1],
) -> list[str]:
    errors: list[str] = []
    owned_keys_by_field = {
        "installation.verified_acquisition": {"name", "version", "source_revision"},
        "installation.coordinates": {"name", "version", "manifest_path"},
        "example.minimal": {"code", "command", "module", "class", "function"},
        "api.public_surface": {"module", "name", "export", "signature"},
    }
    for fact in cited_facts:
        keys = owned_keys_by_field.get(fact.field)
        if keys is None:
            continue
        for key, literal in sorted(set(_structured_values(fact.value, keys))):
            if _contains_literal(unit.text, literal):
                errors.append(f"{fact.field} {key!r} literal belongs to deterministic rendering")
    return errors


def _known_operations(value: object) -> set[str]:
    operations: set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            operations.update(_known_operations(item))
    elif isinstance(value, list):
        for item in value:
            operations.update(_known_operations(item))
    elif isinstance(value, str):
        operations.update(
            operation for operation, pattern in _EXAMPLE_OPERATION_PATTERNS if pattern.search(value)
        )
    return operations


def _unsupported_operation_errors(
    unit: SectionClusterUnitV1,
    cited_facts: Iterable[SectionAuthoringFactV1],
    *,
    task_family: str,
) -> list[str]:
    prose = unit.text if task_family == "opening_summary" else unit.heading + "\n" + unit.text
    prose = re.sub(r"(?i)\bopen[- ]source\b", "", prose)
    cited_facts = list(cited_facts)
    authorized = set().union(*(_known_operations(fact.value) for fact in cited_facts))
    for fact in cited_facts:
        if fact.field != "example.minimal" or not isinstance(fact.value, dict):
            continue
        code = str(fact.value.get("code") or "").casefold()
        identifiers = " ".join(
            match.group(0).replace("_", " ")
            for match in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", code)
        )
        authorized.update(
            {
                operation
                for operation, pattern in _EXAMPLE_OPERATION_PATTERNS
                if pattern.search(identifiers)
            }
        )
        if "=" in code and re.search(r"\b[A-Za-z_][A-Za-z0-9_.]*\s*\(", code):
            authorized.update({"build", "create", "instantiate"})
    mentioned = {
        operation for operation, pattern in _EXAMPLE_OPERATION_PATTERNS if pattern.search(prose)
    }
    mentioned -= _NON_EXECUTION_PREDICATES
    unsupported = sorted(mentioned - authorized)
    if not unsupported:
        return []
    if task_family == "verified_example_framing":
        return [
            f"example.minimal does not execute the claimed {operation!r} operation"
            for operation in unsupported
        ]
    if task_family not in {"opening_summary", "scope_and_limitations"}:
        return []
    if task_family == "scope_and_limitations" and any(
        fact.field == "product.limitations" for fact in cited_facts
    ):
        # A verified limitation is interpretive by construction: it commonly describes an
        # unavailable operation through a source-derived error or stub. Exact closed-world,
        # format, and deterministic-literal claims remain governed by the other validators.
        return []
    if any(
        fact.field in {"product.capabilities", "product.problems_solved", "product.formats"}
        for fact in cited_facts
    ):
        # These accepted interpretive facts authorize conservative editorial paraphrase. Exact
        # names, formats, package coordinates, examples, denials, and guarantees remain governed
        # by the other deterministic checks in this module; PF-02's independent reviewer owns
        # broader natural-language entailment.
        return []
    return [f"cited accepted facts do not authorize operations: {unsupported}"]


def _known_format_tokens(value: object) -> set[str]:
    tokens: set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            tokens.update(_known_format_tokens(item))
    elif isinstance(value, list):
        for item in value:
            tokens.update(_known_format_tokens(item))
    elif isinstance(value, str):
        for match in _FORMAT_CANDIDATE.finditer(value):
            raw = match.group("token")
            if raw.casefold() in _AMBIGUOUS_LOWERCASE_FORMAT_WORDS and not raw.isupper():
                continue
            canonical = canonical_document_format(raw.lstrip("."))
            if canonical is not None:
                tokens.add(canonical)
    return tokens


def _unsupported_format_errors(
    unit: SectionClusterUnitV1,
    cited_facts: Iterable[SectionAuthoringFactV1],
    accepted_facts: Iterable[SectionAuthoringFactV1],
    do_not_claim_fact_ids: set[str],
) -> list[str]:
    cited_facts = list(cited_facts)
    accepted_facts = list(accepted_facts)
    authorized = set().union(*(_known_format_tokens(fact.value) for fact in cited_facts))
    mentioned = _known_format_tokens(unit.heading + "\n" + unit.text)
    unsupported = sorted(mentioned - authorized)
    errors = (
        [f"recognized file formats are absent from cited accepted facts: {unsupported}"]
        if unsupported
        else []
    )
    directional_facts = [fact for fact in accepted_facts if fact.field == "product.formats"]
    if not directional_facts:
        return errors
    cited_ids = {fact.fact_id for fact in cited_facts}
    roles: dict[str, set[str]] = {}
    for fact in directional_facts:
        values = fact.value if isinstance(fact.value, list) else [fact.value]
        for value in values:
            if (
                not isinstance(value, str)
                or (match := _DIRECTIONAL_FORMAT_VALUE.match(value)) is None
            ):
                continue
            canonical = canonical_document_format(match.group("format"))
            if canonical is not None:
                roles.setdefault(canonical, set()).add(match.group("role").casefold())
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", unit.heading + ". " + unit.text):
        sentence_formats = _known_format_tokens(sentence)
        if not sentence_formats:
            continue
        claimed_roles = set()
        if _INPUT_FORMAT_CLAIM.search(sentence):
            claimed_roles.add("input")
        if _OUTPUT_FORMAT_CLAIM.search(sentence):
            claimed_roles.add("output")
        if not claimed_roles:
            continue
        if all(fact.fact_id in do_not_claim_fact_ids for fact in directional_facts):
            errors.append(
                "directional format prose is reserved for deterministic rendering in this cluster"
            )
            continue
        if not any(fact.fact_id in cited_ids for fact in directional_facts):
            errors.append("directional format prose must cite the accepted product.formats fact")
            continue
        for format_name in sorted(sentence_formats):
            unsupported_roles = claimed_roles - roles.get(format_name, set())
            if unsupported_roles:
                errors.append(
                    f"{format_name} does not have cited direction support for "
                    f"{sorted(unsupported_roles)}"
                )
    return errors


def enrich_directional_format_fact_ids(
    packet: SectionAuthoringPacketV1,
    result: SectionClusterAuthoringResultV1,
) -> SectionClusterAuthoringResultV1:
    """Attach exact directional provenance where the authored prose makes a direction claim.

    Asking the provider to repeat a format fact alias in every relevant unit is brittle schema
    bookkeeping, not editorial judgment. Deterministic code can infer the required provenance
    without inferring a new product claim; the existing direction validator still rejects prose
    that exceeds the accepted input/output roles.
    """

    directional_ids = tuple(
        fact.fact_id for fact in packet.accepted_facts if fact.field == "product.formats"
    )
    if not directional_ids:
        return result
    units = []
    attached_ids: set[str] = set()
    for unit in result.units:
        prose = unit.heading + ". " + unit.text
        has_direction = bool(
            _known_format_tokens(prose)
            and (_INPUT_FORMAT_CLAIM.search(prose) or _OUTPUT_FORMAT_CLAIM.search(prose))
        )
        units.append(
            unit.model_copy(
                update={"fact_ids": tuple(dict.fromkeys((*unit.fact_ids, *directional_ids)))}
            )
            if has_direction
            else unit
        )
        if has_direction:
            attached_ids.update(directional_ids)
    omitted = tuple(item for item in result.omitted if item.fact_id not in attached_ids)
    return result.model_copy(update={"units": tuple(units), "omitted": omitted})


def remove_reserved_directional_units(
    packet: SectionAuthoringPacketV1,
    result: SectionClusterAuthoringResultV1,
) -> tuple[SectionClusterAuthoringResultV1, tuple[str, ...], tuple[str, ...]]:
    """Discard provider units that cross the deterministic format-rendering boundary.

    The model may infer familiar formats from the public product name even when the prompt hides
    those values. Retrying a whole cluster can repeat that defect and discard unrelated accepted
    prose. Keep the valid units, retain only hashes of rejected public units in the receipt, and
    let normal acceptance trigger recovery when removing a unit leaves a fact undisposed.
    """

    if not any(fact.field == "product.formats" for fact in packet.do_not_claim):
        return result, (), ()
    all_facts = (*packet.accepted_facts, *packet.do_not_claim)
    forbidden_ids = {fact.fact_id for fact in packet.do_not_claim}
    retained: list[SectionClusterUnitV1] = []
    rejected_hashes: list[str] = []
    rejected_fact_ids: set[str] = set()
    for unit in result.units:
        cited = [fact for fact in packet.accepted_facts if fact.fact_id in unit.fact_ids]
        errors = _unsupported_format_errors(unit, cited, all_facts, forbidden_ids)
        if any("reserved for deterministic rendering" in error for error in errors):
            payload = json.dumps(unit.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
            rejected_hashes.append(hashlib.sha256(payload.encode("utf-8")).hexdigest())
            rejected_fact_ids.update(unit.fact_ids)
            continue
        retained.append(unit)
    if not retained:
        return result, (), ()
    retained_fact_ids = {fact_id for unit in retained for fact_id in unit.fact_ids}
    existing_omitted_ids = {item.fact_id for item in result.omitted}
    omitted_fact_ids = tuple(sorted(rejected_fact_ids - retained_fact_ids - existing_omitted_ids))
    omitted = (
        *result.omitted,
        *(
            OmittedFactV1(
                fact_id=fact_id,
                reason="Authored unit crossed the deterministic format-rendering boundary.",
            )
            for fact_id in omitted_fact_ids
        ),
    )
    return (
        result.model_copy(update={"units": tuple(retained), "omitted": omitted}),
        tuple(rejected_hashes),
        omitted_fact_ids,
    )


def _sibling_item_conflation_errors(
    unit: SectionClusterUnitV1,
    cited_facts: Iterable[SectionAuthoringFactV1],
) -> list[str]:
    errors: list[str] = []
    unit_words = semantic_content_words(unit.heading + " " + unit.text)
    for fact in cited_facts:
        if not isinstance(fact.value, list):
            continue
        items = [item for item in fact.value if isinstance(item, str) and item.strip()]
        if len(items) < 2:
            continue
        word_sets = [semantic_content_words(item) - _SIBLING_GENERIC_WORDS for item in items]
        exclusive_sets = [
            words - set().union(*(other for index, other in enumerate(word_sets) if index != item))
            for item, words in enumerate(word_sets)
        ]
        matched_items = [words & unit_words for words in exclusive_sets if words & unit_words]
        if len(matched_items) > 1:
            errors.append(
                f"{fact.field} unit combines {len(matched_items)} independent sibling items"
            )
    return errors


def section_authoring_fact_errors(
    packet: SectionAuthoringPacketV1,
    unit: SectionClusterUnitV1,
) -> list[str]:
    """Return contradictions and deterministic-literal ownership violations.

    Fact IDs establish provenance, but they do not make arbitrary prose true. This validator
    handles the structured coordinates for which a false rewrite is both high-risk and
    mechanically decidable. Broader natural-language factuality remains independently checked
    after complete candidate assembly.
    """

    facts_by_id = {fact.fact_id: fact for fact in packet.accepted_facts}
    cited_facts = [facts_by_id[fact_id] for fact_id in unit.fact_ids if fact_id in facts_by_id]
    errors = _deterministic_literal_errors(unit, cited_facts)
    public_text = unit.heading + "\n" + unit.text
    if "\ufffd" in public_text or any(
        marker in public_text for marker in ("\u00c3", "\u00c2", "\u00e2\u20ac")
    ):
        errors.append("public prose contains replacement characters or UTF-8 mojibake")
    errors.extend(_unsupported_operation_errors(unit, cited_facts, task_family=packet.task_family))
    errors.extend(
        _unsupported_format_errors(
            unit,
            cited_facts,
            (*packet.accepted_facts, *packet.do_not_claim),
            {fact.fact_id for fact in packet.do_not_claim},
        )
    )
    if re.search(r"(?i)\baspose\b", public_text):
        if packet.public_product_name not in unit.text:
            errors.append(
                f"product identity must preserve exact public name {packet.public_product_name!r}"
            )
    if _CLOSED_WORLD_DENIAL.search(unit.text):
        errors.append("positive capability inventories cannot authorize closed-world denials")
    # Capability entries promise one scannable concept per unit, so fusing independent list
    # items changes their meaning (for example, animation becomes an export format). An opening
    # summary intentionally synthesizes several verified purposes/capabilities and must not be
    # forced into one sentence per list item.
    if packet.task_family == "capability_entry_cluster":
        errors.extend(_sibling_item_conflation_errors(unit, cited_facts))
    cited_values = json.dumps(
        [fact.value for fact in cited_facts],
        sort_keys=True,
        default=str,
    ).casefold()
    unsupported_positioning = sorted(
        {
            match.group(0).casefold()
            for match in _UNSUPPORTED_POSITIONING.finditer(unit.text)
            if match.group(0).casefold() not in cited_values
        }
    )
    if unsupported_positioning:
        errors.append(
            "unsupported quality, completeness, guarantee, or dependency wording: "
            f"{unsupported_positioning}"
        )
    acquisitions = [
        fact
        for fact in packet.accepted_facts
        if fact.field == "installation.verified_acquisition" and isinstance(fact.value, dict)
    ]
    for acquisition in acquisitions:
        value = acquisition.value
        assert isinstance(value, dict)
        source_only = value.get("method") == "source_build" or value.get("outcome") == (
            "SOURCE_BUILD_VERIFIED"
        )
        if not source_only:
            continue
        registry_publication = _REGISTRY_NAME.search(unit.text)
        if registry_publication:
            errors.append(
                "source-build acquisition cannot authorize a package-registry publication "
                "or installation claim"
            )
    return errors


__all__ = [
    "enrich_directional_format_fact_ids",
    "remove_reserved_directional_units",
    "section_authoring_fact_errors",
]
