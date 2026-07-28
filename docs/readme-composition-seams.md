# README composition seams

This records the pre-extraction characterization for active mission task
`L8-COMPOSE-00-CHARACTERIZE` and the candidate responsibility extraction intended for
`L8-COMPOSE-01-DECOMPOSE`. The frozen public composition boundary proves the candidate extraction
is behavior-preserving; the later task still owns its independent acceptance and closure.

## Public pipeline

The public sequence and returned contracts are:

1. `assessment.assess_readme_document(...) -> ReadmeAssessmentV1`
2. `agentic_composition.plan_readme_composition(...) -> ReadmeAgenticCompositionPlanV1`
3. `agentic_composition.validate_readme_composition_plan(...) ->
   ReadmeAgenticCompositionPlanV1`
4. `document_renderer.build_readme_document_candidate(...) ->
   tuple[str, ReadmeDocumentPlanV1]`

`tests/unit/test_readme_composition_characterization.py` freezes the exact call signatures and,
using the committed three-Java ProductFactsV2 proof, the composition-plan, candidate-byte, and
document-plan hashes for three distinct source shapes. Structural extraction kept the original
values unchanged. `L8-COMPOSE-01B-HEADER-VISUAL-CONTRACT` deliberately revised the candidate and
document-plan hashes after extraction to establish the factual marker-free header and Mermaid
contract; those revised values are now the regression baseline.

## Before/after responsibility map

| Before | After | Preserved boundary |
|---|---|---|
| `agentic_composition.py`: schemas, grounding, validation, model orchestration, repair hints (527 lines) | `agentic_composition.py`: model orchestration and repair hints; `agentic_composition_models.py`: typed contracts; `agentic_composition_grounding.py`: accepted visitor facts and deterministic materialization; `agentic_composition_validation.py`: source/fact/prompt/schema validation | The existing `agentic_composition` imports and four public functions/contracts remain unchanged. |
| `document_renderer.py`: editorial operation selection and candidate assembly (513 lines) | `document_renderer.py`: thin operation ordering and candidate assembly; `document_render_context.py`: immutable source/fact view; `document_opening.py`, `document_acquisition.py`, `document_examples.py`, `document_limitations.py`, and `document_release.py`: one editorial responsibility each. | `build_readme_document_candidate`, operation order, candidate bytes, and document-plan hashes remain unchanged. |
| `assessment.py` | Unchanged; source parsing and section classification remain independent. | `ReadmeAssessmentV1` and its canonical hash remain unchanged. |
| `document_structure.py`, `document_templates.py`, `document_operations.py` | Unchanged shared parsing, deterministic fragment, and bounded-operation seams. | No authoring orchestration moves into deterministic helpers. |
| `document_validation.py` | Unchanged independent reconstruction and validation. | Authoring never accepts its own output. |

## Marker-free factual header contract

`L8-COMPOSE-01B-HEADER-VISUAL-CONTRACT` stores ownership, fact hashes, and idempotency metadata in
the durable `ReadmeDocumentPlanV1` rather than HTML comments in the visitor-facing README.
`markers.find_presentation_span()` remains a legacy migration parser only. Production candidates
are raw Markdown and are recognized for no-op purposes through their exact factual title, badge
row, and sanitized Mermaid structure.

Badges are not a universal template. A package or version badge exists only when the selected
acquisition fact is registry-verified and matches selected manifest/release facts; a license badge
exists only for the selected verified license. Build, status, download, and documentation badges
are removed unless a future accepted fact contract explicitly proves them. Every Mermaid node
cites a selected accepted identity, audience, problem, capability, or format fact, and unsafe
labels fail closed.

Both extractions are behavior-preserving and bring each responsibility module below the governed
roughly-300-line threshold. The active task still changes no editorial behavior: the frozen
contracts exist so later corrective tasks can distinguish intended improvements from accidental
extraction regressions.

## Frozen defect families

The next regression tasks own the desired corrections. This task only records their first failing
boundaries so decomposition cannot hide or accidentally reclassify them:

- `L8-COMPOSE-01A-SECTION-REGRESSIONS`: partial existing installation, limitations, overview,
  and example sections can require verified completion rather than a competing additive section.
- `L8-COMPOSE-02A-OPERATION-REGRESSIONS`: every actionable assessment must compile to an exact
  source-span operation; an advisory decision is not a candidate change.
- `L8-COMPOSE-03A-PRESENTATION-CORPUS`: raw taxonomy tokens, semantic duplicates, competing
  examples, weak identity/navigation, and promotional imbalance require visitor-facing controls.
- `L8-COMPOSE-04A-CANDIDATE-FIXTURES`: seven immutable representative inputs must be frozen in the
  configured order Python, .NET, Java, C++, TypeScript, Rust, Go.
- `L8-COMPOSE-01B-HEADER-VISUAL-CONTRACT`: visible ownership comments are prohibited; candidates
  need factual badge headers and repository-specific Mermaid at-a-glance visuals.
- `L8-COMPOSE-01C-CONTEXTUAL-LINKING`: contextual links require verified adjacent relevance,
  configured/adaptive budgets, products-domain priority, and the term "Enterprise Edition".

These are open governed tasks, not accepted limitations and not evidence that their target behavior
already works.
