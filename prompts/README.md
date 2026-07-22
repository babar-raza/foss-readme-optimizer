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

## Current state

Two prompts are registered (Wave 8.5, `GOV-024`): `prompts/generation/relationship_explained.yaml`
(the relationship-explanation paragraph, migrated from the former `system.txt`/`user.txt` pair,
`GOV-016`) and `prompts/planning/supervisor_turn.yaml` (the autonomous supervisor's planner
prompt, migrated from a hardcoded string literal in `supervisor/loop.py`). Both are loaded and
schema-validated by `src/readme_agent/llm/prompt_registry.py`; `build_prompt()`
(`llm/prompts.py`) and the supervisor's dossier assembly (`supervisor/dossier.py`) both read
through this one registry — no other module reads `prompts/` directly.
