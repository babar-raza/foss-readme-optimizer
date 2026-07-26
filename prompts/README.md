# `prompts/` — LLM prompt assets

The categorical home for **every prompt asset used with the LLM gateway**
(`llm.professionalize.com` — see `.env.example` for the endpoint/key variables). Governed by
`plans/GOVERNANCE.md` ("Repository layout", table row + placement rule 9).

## What belongs here

- System and user prompt text (`.md`, `.txt`)
- Few-shot example blocks
- Structured prompt artifacts: YAML/JSON state machines, conversation flows, multi-step
  prompt graphs

Format follows the artifact's nature — a prompt is not required to be `.md`/`.txt`.

## Organization

```
prompts/<category>/<prompt-id>.yaml
```

One subdirectory per prompt *category* (e.g. `generation/`, `planning/`), one schema-validated
YAML file per prompt job (`src/readme_agent/llm/prompt_schema.py::PromptManifest`), keyed by its
own declared `prompt_id`, not its filename — loaded and validated once, eagerly, at import time
by `src/readme_agent/llm/prompt_registry.py` (mirrors `capabilities/registry.py`'s own
eager-registration pattern). A manifest's declared `category` must match the subdirectory it's
found in — checked at build time, fails loud on mismatch.

## Rules

1. **`prompts/` is the only place LLM prompt content is allowed to live.** No prompt text, few-
   shot block, or structured prompt artifact is ever written as a string literal inside an
   executable file — not `src/`, not `scripts/`, not a test, not anywhere code lives. If it's a
   prompt, it's a file under `prompts/`, loaded at runtime — never typed inline.
2. **Only `src/readme_agent/llm/` loads these files.** No other module (and no script) reads
   `prompts/` directly — prompt assembly stays in one place.
3. **Determinism contract.** Generation inputs are hash-coupled: `build_prompt(facts, policy)`
   takes only two already-hashed objects and `tests/unit/test_prompt_hash_coupling.py` enforces
   it. `src/readme_agent/llm/prompts.py::prompt_content_hash()` reads
   `prompts/generation/relationship_explained.yaml` fresh on every call and joins
   `RepositoryFacts.prompt_content_hash` — narrowly scoped to that one job only, so an unrelated
   prompt edit (e.g. the supervisor planner's own prompt) never forces every README to look
   stale. `src/readme_agent/llm/prompt_registry.py::content_hash()` separately hashes *every*
   registered prompt file, consumed by `supervisor/convergence.py::
   compute_control_plane_fingerprint()` instead.
4. **Prompt changes are behavior changes.** They land with the tests that cover them, like any
   `src/` change.
5. **The active tree is not an archive.** Do not create timestamped, backup, draft, or superseded
   copies here. Inspect references and history before removing an obsolete prompt; Git history
   preserves it after its consumer and replacement are reconciled.

## Current state

Ten active manifests are registered. This table is part of the blocking inventory and must match
the manifest metadata exactly.

| Prompt ID | Category | Model route | Owner | Runtime consumer | Output contract | Invalidation scope |
|---|---|---|---|---|---|---|
| `presentation_standard_compliance` | `analysis` | `presentation_standard_compliance` | `readme_agent.capabilities.compare_against_presentation_standard` | `readme_agent.llm.analysis_prompts` | `presentation-standard-comparison-v1` | `README_ASSESSED` |
| `draft_product_truth` | `generation` | `draft_product_truth` | `readme_agent.capabilities.draft_product_truth` | `readme_agent.llm.generation_prompts` | `DraftProductTruthV1` | `FACTS_COLLECTING` |
| `plan_readme_composition` | `generation` | `plan_readme_composition` | `readme_agent.capabilities.plan_readme_composition` | `readme_agent.llm.generation_prompts` | `ReadmeAgenticCompositionPlanV1` | `PLAN_READY` |
| `relationship_explained` | `generation` | `relationship_explained` | `readme_agent.readme.candidate_pipeline` | `readme_agent.llm.prompts` | `LLMBlockResponse` | `CANDIDATE_GENERATED` |
| `repair_capability_selection` | `planning` | `repair_capability_selection` | `readme_agent.supervisor.repair` | `readme_agent.llm.planning_prompts` | `PlannerTurn-repair-capability-selection` | `REPAIRING` |
| `specialist_selection_turn` | `planning` | `specialist_selection` | `readme_agent.supervisor.specialist_selection` | `readme_agent.llm.planning_prompts` | `PlannerTurn-select-specialists-to-skip` | `SPECIALIST_SELECTION` |
| `supervisor_turn` | `planning` | `supervisor_planning` | `readme_agent.supervisor.planner_loop` | `readme_agent.llm.planning_prompts` | `PlannerTurn-capability-or-stop` | `SUPERVISOR_PLANNING` |
| `independent_readme_review` | `verification` | `independent_readme_review` | `readme_agent.specialists.independent_readme_review` | `readme_agent.llm.verification_prompts` | `IndependentReadmeReviewResultV1` | `AGENT_REVIEWING` |
| `prose_quality_check` | `verification` | `prose_quality_check` | `readme_agent.capabilities.verify_prose_quality` | `readme_agent.llm.verification_prompts` | `prose-quality-finding-v1` | `DETERMINISTIC_VALIDATED` |
| `visual_asset_accuracy` | `verification` | `visual_asset_accuracy` | `readme_agent.capabilities.review_visual_asset_accuracy` | `readme_agent.llm.analysis_prompts` | `visual-asset-accuracy-v1` | `AGENT_REVIEWING` |

`src/readme_agent/llm/prompt_hygiene.py` reconciles these rows with the files, schema, route table,
runtime content/hash/call references, and source-level inline-prompt exclusions. The same check is
required by the paid campaign entry points, unit suite, and official verification runner.
