"""Bind compiled template spans to explicit evidence."""

from __future__ import annotations

import hashlib
import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.section_authoring_overlay import authored_unit_markdown
from readme_agent.presentation.template_schema import (
    BoundTemplateContentV1,
    PresentationTemplateInputV1,
    TemplateSlot,
    load_repository_presentation_template,
)
from readme_agent.presentation.verified_source_claim_resolutions import (
    build_source_claim_resolutions,
    probe_source_claim_resolutions_for_composition,
)
from readme_agent.presentation.verified_template_api_reference import api_reference_markdown
from readme_agent.presentation.verified_template_capabilities import (
    CapabilityPresentationPlanV1,
    capability_claim_fact_coordinates,
    capability_claim_fact_ids,
)
from readme_agent.presentation.verified_template_draft import (
    generated_minimal_example,
    source_tree_installation_fact_ids,
    source_tree_installation_text,
)
from readme_agent.presentation.verified_template_limitations import verified_limitation_groups
from readme_agent.presentation.verified_template_sections import (
    additional_examples_markdown,
    dependency_markdown,
    development_markdown,
    scenario_dependency_markdown,
)
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.claim_accountability_coordinates import structured_fact_coordinates
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.document_templates import example_text, installation_text
from readme_agent.readme.example_assurance_validation import (
    additional_examples_disclosure_fact_ids,
)
from readme_agent.readme.fact_grounding import literal_fact_ids
from readme_agent.readme.public_text import (
    canonical_abbreviations_from_facts,
    canonicalize_public_markdown,
)
from readme_agent.readme.source_claim_fact_binding import complete_source_claim_fact_binding
from readme_agent.readme.source_claim_repository_asset_binding import (
    repository_asset_source_claim_fact_ids,
)
from readme_agent.readme.source_claim_risk import classify_source_claim_risk
from readme_agent.specialists.section_authoring_contracts import SectionAuthoringDocumentV1

_CLAIM_LEVEL_SLOTS = {
    "additional_examples",
    "api_reference",
    "api_method_index",
    "contributing",
    "dependencies",
    "development_and_testing",
    "installation",
    "key_capabilities",
    "quick_start",
    "scope_and_limitations",
    "security",
    "third_party_notices",
}
_STRUCTURAL_SHELL = re.compile(
    r"(?is)^(?:optional dependency groups declared by the package:|"
    r"install the package published for this repository:|"
    r"the coordinate was verified against maven central\.|"
    r"the package was verified against nuget\.|"
    r"add the module published for this repository:|"
    r"the module was verified through the go module proxy\.|"
    r"build the verified repository revision from source:|"
    r"explore additional examples for common product workflows\.|"
    r"the repository registers these mcp tools:|"
    r"validate a proposed change with the checked-in repository scripts:|"
    r"<details>\s*<summary>[^<]+</summary>|</details>|"
    r"- \[browse all [^]]+\]\([^)]+\))\s*$"
)
_MECHANICAL_STRUCTURE_STANDARD = "readme.composition.mechanical-markdown-v1"


def _canonical_structural_section(
    slot: TemplateSlot,
    template_input: PresentationTemplateInputV1,
    facts: ProductFactsV2,
    source_text: str | None = None,
) -> str | None:
    """Re-render the only variable-heading sections from accepted typed facts."""

    if slot == "additional_examples":
        title = " ".join(template_input.title.markdown.split())
        markdown = additional_examples_markdown(
            facts, reserved_heading_titles=(title,), source_text=source_text
        )
    elif slot == "api_reference":
        markdown = api_reference_markdown(facts)
    elif slot == "development_and_testing":
        markdown = development_markdown(facts)
    elif slot == "dependencies":
        parts = []
        required = dependency_markdown(facts)
        if required:
            parts.append("### Required Package Dependencies\n\n" + required)
        optional = scenario_dependency_markdown(facts, source_text=source_text)
        if optional:
            parts.append("### Optional Dependencies\n\n" + optional)
        markdown = "\n\n".join(parts) or None
    else:
        return None
    return (
        canonicalize_public_markdown(markdown, canonical_abbreviations_from_facts(facts))
        if markdown is not None
        else None
    )


def _structural_heading_bindings(
    *,
    slot: TemplateSlot,
    content: BoundTemplateContentV1,
    section_text: str,
    section_base_byte: int,
    template_input: PresentationTemplateInputV1,
    facts: ProductFactsV2,
    source_text: str | None = None,
) -> list[CandidateContentProvenanceV1]:
    """Bind H3 bytes only when the complete section is the canonical fact renderer."""

    canonical = _canonical_structural_section(slot, template_input, facts, source_text)
    if (
        canonical is None
        or canonical.strip() != section_text
        or content.source_kind != "repository_fact_and_configured_standard"
        or not content.fact_ids
        or not content.standard_ids
    ):
        return []
    bindings = []
    for index, heading in enumerate(parse_headings(section_text)):
        if heading.level != 3:
            continue
        bindings.append(
            CandidateContentProvenanceV1(
                provenance_id=f"template.structure.h3.{slot}.{index:04d}",
                candidate_byte_start=section_base_byte
                + len(section_text[: heading.start].encode("utf-8")),
                candidate_byte_end=section_base_byte
                + len(section_text[: heading.heading_end].encode("utf-8")),
                fact_ids=content.fact_ids,
                configured_standard_ids=content.standard_ids,
                rationale=(
                    "Bind one exact canonical fact-renderer H3 to its accepted facts and "
                    "configured section standard."
                ),
            )
        )
    return bindings


def _scope_limitation_heading_bindings(
    *,
    slot: TemplateSlot,
    content: BoundTemplateContentV1,
    section_text: str,
    section_base_byte: int,
    facts: ProductFactsV2,
) -> list[CandidateContentProvenanceV1]:
    """Bind only exact deterministic limitation-group H3 bytes to their own facts."""

    if slot != "scope_and_limitations" or content.source_kind != (
        "repository_fact_and_configured_standard"
    ):
        return []
    bindings = []
    for index, group in enumerate(verified_limitation_groups(facts)):
        fact_id = facts.selected_fact_ids.get(group.fact_field)
        if (
            fact_id is None
            or fact_id not in content.fact_ids
            or section_text.count(group.markdown) != 1
        ):
            continue
        group_start = section_text.index(group.markdown)
        heading = next(
            (
                item
                for item in parse_headings(group.markdown)
                if item.level == 3 and item.title == group.heading
            ),
            None,
        )
        if heading is None:
            continue
        bindings.append(
            CandidateContentProvenanceV1(
                provenance_id=f"template.structure.h3.scope_and_limitations.{index:04d}",
                candidate_byte_start=section_base_byte
                + len(section_text[: group_start + heading.start].encode("utf-8")),
                candidate_byte_end=section_base_byte
                + len(section_text[: group_start + heading.heading_end].encode("utf-8")),
                fact_ids=[fact_id],
                configured_standard_ids=[_MECHANICAL_STRUCTURE_STANDARD],
                rationale=(
                    "Bind one exact deterministic limitation-group heading to its corresponding "
                    "accepted fact and mechanical presentation standard."
                ),
            )
        )
    return bindings


def build_template_provenance(
    candidate: str,
    template_input: PresentationTemplateInputV1,
    facts: ProductFactsV2,
    *,
    source_text: str | None = None,
    capability_plan: CapabilityPresentationPlanV1 | None = None,
    section_authoring_document: SectionAuthoringDocumentV1 | None = None,
) -> list[CandidateContentProvenanceV1]:
    """Bind each exact compiled span to its accepted facts and standards."""

    bindings: list[CandidateContentProvenanceV1] = []
    cursor = 0

    def bind(identifier: str, markdown: str, fact_ids: list[str], standard_ids: list[str]) -> None:
        nonlocal cursor
        text = markdown.strip()
        start_character = candidate.find(text, cursor)
        if start_character < 0:
            raise ValueError(f"compiled template content is absent: {identifier}")
        end_character = start_character + len(text)
        bindings.append(
            CandidateContentProvenanceV1(
                provenance_id=identifier,
                candidate_byte_start=len(candidate[:start_character].encode("utf-8")),
                candidate_byte_end=len(candidate[:end_character].encode("utf-8")),
                fact_ids=fact_ids,
                configured_standard_ids=standard_ids,
                rationale="Bind one exact compiled slot to its accepted inputs.",
            )
        )
        cursor = end_character

    def bind_claims(
        identifier: str,
        markdown: str,
        fact_ids: list[str],
        standard_ids: list[str],
    ) -> None:
        """Bind independent prose claims without widening one fact span across another."""

        nonlocal cursor
        text = markdown.strip()
        start_character = candidate.find(text, cursor)
        if start_character < 0:
            raise ValueError(f"compiled template content is absent: {identifier}")
        base_byte = len(candidate[:start_character].encode("utf-8"))
        claims = assess_material_claims(text)
        for claim in claims:
            claim_text = text.encode("utf-8")[
                claim.source_byte_start : claim.source_byte_end
            ].decode("utf-8")
            accepted_fact_ids = set(literal_fact_ids(claim_text, facts, fact_ids))
            coordinates = structured_fact_coordinates(
                text,
                claim,
                facts,
                list(accepted_fact_ids),
            )
            exact_binding = complete_source_claim_fact_binding(text, claim, facts)
            if exact_binding is not None:
                accepted_fact_ids.update(exact_binding.fact_ids)
                coordinates = sorted(
                    {*coordinates, *exact_binding.fact_coordinates},
                    key=lambda item: (item.fact_id, item.path, item.value_sha256),
                )
            if len(claims) == 1:
                # An atomic agentic summary was validated as one typed output
                # against all of its declared supporting facts. Partition only
                # multi-claim summaries, where widening one claim's authority
                # across its neighbours would be ambiguous.
                accepted_fact_ids.update(fact_ids)
            if not accepted_fact_ids and not standard_ids:
                continue
            bindings.append(
                CandidateContentProvenanceV1(
                    provenance_id=f"{identifier}.{claim.claim_id}",
                    candidate_byte_start=base_byte + claim.source_byte_start,
                    candidate_byte_end=base_byte + claim.source_byte_end,
                    fact_ids=sorted(accepted_fact_ids),
                    fact_coordinates=coordinates,
                    configured_standard_ids=standard_ids,
                    rationale="Bind one exact compiled prose claim to its accepted inputs.",
                )
            )
        cursor = start_character + len(text)

    bind(
        "template.title",
        template_input.title.markdown,
        template_input.title.fact_ids,
        template_input.title.standard_ids,
    )
    bind(
        "template.badges",
        template_input.badges.markdown,
        template_input.badges.fact_ids,
        template_input.badges.standard_ids,
    )
    bind_claims(
        "template.summary",
        template_input.summary.markdown,
        template_input.summary.fact_ids,
        template_input.summary.standard_ids,
    )
    if section_authoring_document is not None:
        summary_text = template_input.summary.markdown.strip()
        summary_start = candidate.find(summary_text)
        if summary_start < 0:
            raise ValueError("compiled authored summary is absent")
        for outcome_index, outcome in enumerate(section_authoring_document.outcomes):
            if outcome.target_section_id != "summary" and not outcome.target_section_id.startswith(
                "summary-"
            ):
                continue
            for unit_index, unit in enumerate(outcome.result.units):
                authored = canonicalize_public_markdown(
                    authored_unit_markdown("summary", unit),
                    canonical_abbreviations_from_facts(facts),
                ).strip()
                relative_start = summary_text.find(authored)
                if relative_start < 0:
                    raise ValueError("accepted authored summary unit is absent")
                absolute_start = summary_start + relative_start
                absolute_end = absolute_start + len(authored)
                if absolute_end < len(candidate) and candidate[absolute_end] == "\n":
                    absolute_end += 1
                bindings.append(
                    CandidateContentProvenanceV1(
                        provenance_id=(
                            f"template.section-authoring.summary."
                            f"{outcome_index:02d}.{unit_index:02d}"
                        ),
                        candidate_byte_start=len(candidate[:absolute_start].encode("utf-8")),
                        candidate_byte_end=len(candidate[:absolute_end].encode("utf-8")),
                        fact_ids=list(unit.fact_ids),
                        rationale=(
                            "Bind one deterministically accepted section-authoring summary unit "
                            "to its closed fact set."
                        ),
                    )
                )
    navigation = next(
        heading for heading in parse_headings(candidate) if heading.title.casefold() == "navigation"
    )
    bind("template.structure.h2.navigation", "## Navigation", [], ["readme.navigation"])
    navigation_body = candidate[navigation.heading_end : navigation.section_end].strip()
    bind("template.navigation", navigation_body, [], ["readme.navigation"])
    contract = load_repository_presentation_template()
    for slot, content in template_input.sections.items():
        if content.source_kind == "omitted":
            continue
        bind(
            f"template.structure.h2.{slot}",
            f"## {contract.headings[slot]}",
            [],
            [_MECHANICAL_STRUCTURE_STANDARD],
        )
        if slot in _CLAIM_LEVEL_SLOTS:
            text = content.markdown.strip()
            canonical_structural_section = _canonical_structural_section(
                slot, template_input, facts, source_text
            )
            canonical_structural_section_matches = (
                canonical_structural_section is not None
                and canonical_structural_section.strip() == text
            )
            start_character = candidate.find(text, cursor)
            if start_character < 0:
                raise ValueError(f"compiled template content is absent: template.section.{slot}")
            base_byte = len(candidate[:start_character].encode("utf-8"))
            if section_authoring_document is not None:
                for outcome_index, outcome in enumerate(section_authoring_document.outcomes):
                    if not (
                        outcome.target_section_id == slot
                        or outcome.target_section_id.startswith(f"{slot}-")
                    ):
                        continue
                    for unit_index, unit in enumerate(outcome.result.units):
                        authored = canonicalize_public_markdown(
                            authored_unit_markdown(slot, unit),
                            canonical_abbreviations_from_facts(facts),
                        ).strip()
                        relative_start = text.find(authored)
                        if relative_start < 0:
                            raise ValueError(
                                f"accepted authored unit is absent from template slot {slot!r}"
                            )
                        relative_end = relative_start + len(authored)
                        absolute_start = start_character + relative_start
                        absolute_end = start_character + relative_end
                        if candidate[absolute_end : absolute_end + 2] == "\r\n":
                            absolute_end += 2
                        elif candidate[absolute_end : absolute_end + 1] == "\n":
                            absolute_end += 1
                        bindings.append(
                            CandidateContentProvenanceV1(
                                provenance_id=(
                                    f"template.section-authoring.{slot}."
                                    f"{outcome_index:02d}.{unit_index:02d}"
                                ),
                                candidate_byte_start=len(
                                    candidate[:absolute_start].encode("utf-8")
                                ),
                                candidate_byte_end=len(candidate[:absolute_end].encode("utf-8")),
                                fact_ids=list(unit.fact_ids),
                                rationale=(
                                    "Bind one deterministically accepted section-authoring unit "
                                    "to its closed fact set."
                                ),
                            )
                        )
            bindings.extend(
                _structural_heading_bindings(
                    slot=slot,
                    content=content,
                    section_text=text,
                    section_base_byte=base_byte,
                    template_input=template_input,
                    facts=facts,
                    source_text=source_text,
                )
            )
            bindings.extend(
                _scope_limitation_heading_bindings(
                    slot=slot,
                    content=content,
                    section_text=text,
                    section_base_byte=base_byte,
                    facts=facts,
                )
            )
            verified_installation_range: tuple[int, int] | None = None
            verified_installation_fact_ids: list[str] = []
            source_tree_installation_range: tuple[int, int] | None = None
            source_tree_installation_fact_ids_value: list[str] = []
            installation_slot_canonical = False
            if slot == "installation":
                canonical_installation = installation_text(
                    facts,
                    template_input.org_repo,
                    template_input.source_revision,
                ) or source_tree_installation_text(facts)
                if canonical_installation is not None:
                    installation_slot_canonical = canonical_installation.strip() == text.strip()
                source_tree_installation = source_tree_installation_text(facts)
                if source_tree_installation is not None:
                    exact_source_tree = source_tree_installation.strip()
                    if text.count(exact_source_tree) == 1:
                        source_tree_character_start = text.index(exact_source_tree)
                        source_tree_character_end = source_tree_character_start + len(
                            exact_source_tree
                        )
                        # `assess_material_claims` is always called below as `text + "\n"`
                        # (the same terminator dependency this file's own claim loop
                        # already documents) -- a terminal code-fence claim's own boundary
                        # then consumes that trailing newline, one byte past a range
                        # computed strictly from `exact_source_tree`'s own (`.strip()`ed)
                        # length. Widen the range by that same one optional byte so the
                        # code-fence claim isn't excluded by the mismatch -- confirmed live
                        # via aspose-cells-foss/Aspose.Cells-FOSS-for-Rust, where the
                        # fallback clone block is always this slot's terminal content.
                        extended_text = text + "\n"
                        if (
                            extended_text[source_tree_character_end : source_tree_character_end + 1]
                            == "\n"
                        ):
                            source_tree_character_end += 1
                        source_tree_start = len(text[:source_tree_character_start].encode("utf-8"))
                        source_tree_installation_range = (
                            source_tree_start,
                            len(extended_text[:source_tree_character_end].encode("utf-8")),
                        )
                        source_tree_installation_fact_ids_value = source_tree_installation_fact_ids(
                            facts
                        )
                verified_installation = installation_text(
                    facts,
                    template_input.org_repo,
                    template_input.source_revision,
                )
                if verified_installation is not None:
                    exact = verified_installation.strip()
                    if text.count(exact) != 1:
                        raise ValueError(
                            "compiled installation does not contain exactly one verified "
                            "acquisition block"
                        )
                    relative_start = text.index(exact)
                    relative_end = relative_start + len(exact)
                    accepted_fact_ids = [
                        facts.selected_fact(field).fact_id
                        for field in (
                            "installation.coordinates",
                            "installation.verified_acquisition",
                        )
                        if facts.selected_fact(field).verification_state
                        in {"verified", "policy_approved"}
                        and not facts.selected_fact(field).has_unresolved_conflict
                    ]
                    verified_installation_range = (
                        len(text[:relative_start].encode("utf-8")),
                        len(text[:relative_end].encode("utf-8")),
                    )
                    verified_installation_fact_ids = accepted_fact_ids
            verified_example_range: tuple[int, int] | None = None
            verified_example_fact_ids: list[str] = []
            if slot == "quick_start":
                verified_example = example_text(facts, template_input.source_revision)
                if verified_example:
                    exact_example = verified_example.strip()
                    if text.count(exact_example) == 1:
                        example_character_start = text.index(exact_example)
                        example_character_end = example_character_start + len(exact_example)
                        # Mirrors `source_tree_installation_range`'s own documented fix
                        # (PWD-023-FOLLOWUP): `assess_material_claims` is always called
                        # below as `text + "\n"`, so a terminal code-fence claim's own
                        # boundary can consume that appended newline, landing one byte
                        # past a range computed strictly from the exact text's own
                        # length. Widen by that same one optional byte.
                        extended_text = text + "\n"
                        if extended_text[example_character_end : example_character_end + 1] == "\n":
                            example_character_end += 1
                        example_start = len(text[:example_character_start].encode("utf-8"))
                        verified_example_range = (
                            example_start,
                            len(extended_text[:example_character_end].encode("utf-8")),
                        )
                        example_fact_id = facts.selected_fact_ids.get("example.minimal")
                        if example_fact_id is not None:
                            example_fact = facts.fact_by_id(example_fact_id)
                            if (
                                example_fact.verification_state in {"verified", "policy_approved"}
                                and not example_fact.has_unresolved_conflict
                            ):
                                verified_example_fact_ids = [example_fact_id]
            # The material-claim parser treats a terminal Markdown list row as
            # complete only when it has its line terminator. Template slots are
            # stripped for stable lookup, while the compiler always restores a
            # separating newline. Parse that real boundary so the final factual
            # row cannot become the one unbound segment in an otherwise governed
            # deterministic section.
            for claim in assess_material_claims(text + "\n"):
                claim_text = text.encode("utf-8")[
                    claim.source_byte_start : claim.source_byte_end
                ].decode("utf-8")
                fact_ids = literal_fact_ids(claim_text, facts, content.fact_ids)
                fact_ids = sorted(
                    {
                        *fact_ids,
                        *(
                            coordinate.fact_id
                            for coordinate in structured_fact_coordinates(
                                text,
                                claim,
                                facts,
                                content.fact_ids,
                            )
                        ),
                    }
                )
                if slot == "key_capabilities":
                    fact_ids = sorted(
                        {
                            *fact_ids,
                            *capability_claim_fact_ids(
                                claim_text,
                                facts,
                                presentation_plan=capability_plan,
                            ),
                        }
                    )
                if slot == "api_reference" and canonical_structural_section_matches:
                    fact_ids = sorted({*fact_ids, *content.fact_ids})
                if (
                    not fact_ids
                    and "readme.contextual_links" in content.standard_ids
                    and "](https://" in claim_text
                ):
                    fact_ids = list(content.fact_ids)
                installation_claim = bool(
                    verified_installation_range is not None
                    and verified_installation_range[0] <= claim.source_byte_start
                    and claim.source_byte_end <= verified_installation_range[1]
                )
                if installation_claim:
                    fact_ids = sorted({*fact_ids, *verified_installation_fact_ids})
                source_tree_installation_claim = bool(
                    source_tree_installation_range is not None
                    and source_tree_installation_range[0] <= claim.source_byte_start
                    and claim.source_byte_end <= source_tree_installation_range[1]
                )
                if source_tree_installation_claim:
                    # `content.fact_ids` (the installation slot's generic accepted facts)
                    # is empty whenever this fallback clone-and-import block is the *only*
                    # installation content -- no other accepted installation fact exists to
                    # populate it. Cite the specific facts this block was actually rendered
                    # from instead, or it renders provably real content with no binding at
                    # all (observed live: composition-lineage validation rejected it as
                    # "substantive generated bytes lack exact candidate authority").
                    fact_ids = sorted(
                        {*fact_ids, *content.fact_ids, *source_tree_installation_fact_ids_value}
                    )
                if slot == "installation" and not fact_ids and installation_slot_canonical:
                    # The remaining installation prose is rendered verbatim by the
                    # deterministic installation builder from these accepted facts.
                    fact_ids = list(content.fact_ids)
                example_claim = bool(
                    verified_example_range is not None
                    and verified_example_range[0] <= claim.source_byte_start
                    and claim.source_byte_end <= verified_example_range[1]
                )
                if example_claim:
                    # The verified minimal example's own code fence is not material-claim
                    # prose, so the generic literal/structured-coordinate binding above
                    # never covers it -- cite `example.minimal` directly, mirroring the
                    # installation slot's own fallback-block fix (PWD-023/PWD-023-FOLLOWUP)
                    # for the identical "substantive generated bytes lack exact candidate
                    # authority" failure mode.
                    fact_ids = sorted({*fact_ids, *verified_example_fact_ids})
                if (
                    slot == "additional_examples"
                    and not fact_ids
                    and canonical_structural_section_matches
                ):
                    fact_ids = list(content.fact_ids)
                if slot == "dependencies" and not fact_ids and canonical_structural_section_matches:
                    fact_ids = list(content.fact_ids)
                if (
                    slot == "development_and_testing"
                    and not fact_ids
                    and canonical_structural_section_matches
                ):
                    fact_ids = list(content.fact_ids)
                if slot == "scope_and_limitations" and not fact_ids:
                    limitations_fact_id = facts.selected_fact_ids.get("product.limitations")
                    before_details = text.split("<details>", 1)[0]
                    if limitations_fact_id is not None and claim.source_byte_end <= len(
                        before_details.encode("utf-8")
                    ):
                        fact_ids = [limitations_fact_id]
                if slot == "scope_and_limitations":
                    relationship_risk = classify_source_claim_risk(text, claim)
                    if relationship_risk.obligation_id == "contextual_product_relationship":
                        relationship = facts.selected_fact("relationship.commercial_foss")
                        if (
                            relationship.verification_state in {"verified", "policy_approved"}
                            and not relationship.has_unresolved_conflict
                        ):
                            fact_ids = sorted({*fact_ids, relationship.fact_id})
                if slot == "quick_start" and not fact_ids:
                    generated = generated_minimal_example(facts)
                    if generated is not None and generated.strip() in text:
                        fact_ids = list(content.fact_ids)
                if slot == "additional_examples" and not fact_ids:
                    fact_ids = additional_examples_disclosure_fact_ids(claim_text, facts)
                if (
                    slot == "additional_examples"
                    and not fact_ids
                    and canonical_structural_section_matches
                    and claim_text.strip() == text.split("<details>", 1)[0].strip()
                ):
                    examples = facts.selected_fact("repository.examples")
                    if (
                        examples.fact_id in content.fact_ids
                        and examples.verification_state in {"verified", "policy_approved"}
                        and not examples.has_unresolved_conflict
                    ):
                        fact_ids = [examples.fact_id]
                if slot == "additional_examples":
                    fact_ids = sorted(
                        {
                            *fact_ids,
                            *repository_asset_source_claim_fact_ids(claim_text, facts),
                        }
                    )
                fact_coordinates = structured_fact_coordinates(
                    text,
                    claim,
                    facts,
                    fact_ids,
                )
                if slot == "key_capabilities":
                    fact_coordinates = sorted(
                        {
                            *fact_coordinates,
                            *capability_claim_fact_coordinates(
                                claim_text,
                                facts,
                                source_text=source_text,
                                presentation_plan=capability_plan,
                            ),
                        },
                        key=lambda item: (item.fact_id, item.path, item.value_sha256),
                    )
                fact_ids = sorted(
                    {*fact_ids, *(coordinate.fact_id for coordinate in fact_coordinates)}
                )
                if fact_ids:
                    standard_ids = content.standard_ids
                elif _STRUCTURAL_SHELL.fullmatch(claim_text.strip()):
                    standard_ids = list(content.standard_ids) or [_MECHANICAL_STRUCTURE_STANDARD]
                else:
                    standard_ids = []
                if installation_claim:
                    standard_ids = sorted({*standard_ids, "readme.verified_acquisition"})
                if not fact_ids and not standard_ids:
                    continue
                claim_end = base_byte + claim.source_byte_end
                provenance_id = f"template.section.{slot}.{claim.claim_id}"
                if claim_text.strip() == "</details>":
                    candidate_bytes = candidate.encode("utf-8")
                    if candidate_bytes[claim_end : claim_end + 2] == b"\r\n":
                        claim_end += 2
                    elif candidate_bytes[claim_end : claim_end + 1] == b"\n":
                        claim_end += 1
                    exact_bytes = candidate_bytes[base_byte + claim.source_byte_start : claim_end]
                    digest = hashlib.sha256(exact_bytes).hexdigest()[:16]
                    provenance_id = (
                        f"template.section.{slot}.claim:{claim.source_byte_start}:{digest}"
                    )
                bindings.append(
                    CandidateContentProvenanceV1(
                        provenance_id=provenance_id,
                        candidate_byte_start=base_byte + claim.source_byte_start,
                        candidate_byte_end=claim_end,
                        fact_ids=fact_ids,
                        fact_coordinates=fact_coordinates,
                        configured_standard_ids=standard_ids,
                        rationale="Bind one exact optional-section claim to accepted inputs.",
                    )
                )
            cursor = start_character + len(text)
            continue
        bind(f"template.section.{slot}", content.markdown, content.fact_ids, content.standard_ids)
    return bindings


__all__ = [
    "build_source_claim_resolutions",
    "build_template_provenance",
    "probe_source_claim_resolutions_for_composition",
]
