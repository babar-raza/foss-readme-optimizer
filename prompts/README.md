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

Ten active manifests are registered:

| Category | Prompt IDs |
|---|---|
| `analysis` | `presentation_standard_compliance` |
| `generation` | `draft_product_truth`, `plan_readme_composition`, `relationship_explained` |
| `planning` | `repair_capability_selection`, `specialist_selection_turn`, `supervisor_turn` |
| `verification` | `independent_readme_review`, `prose_quality_check`, `visual_asset_accuracy` |

They are loaded and schema-validated by `src/readme_agent/llm/prompt_registry.py`. The registry
already rejects duplicate IDs and category/path disagreement and hashes every registered prompt.
The remaining production-hygiene work is tracked by `L8-028` and
`L8-TRUTH-01C-PROMPT-HYGIENE`: add owner/consumer/dependency metadata and a blocking inventory that
reconciles files, model routes, runtime call sites, documentation, and inline-prompt exclusions
before another paid portfolio campaign.
