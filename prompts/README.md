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
prompts/<task-or-flow>/<self-explanatory-name>.<ext>
```

One subdirectory per LLM task or flow, named for what it does (naming rules:
`plans/GOVERNANCE.md`, "Machinery artifacts"). No enumerated or vague names.

## Rules

1. **`prompts/` is the only place LLM prompt content is allowed to live.** No prompt text, few-
   shot block, or structured prompt artifact is ever written as a string literal inside an
   executable file — not `src/`, not `scripts/`, not a test, not anywhere code lives. If it's a
   prompt, it's a file under `prompts/`, loaded at runtime — never typed inline.
2. **Only `src/readme_agent/llm/` loads these files.** No other module (and no script) reads
   `prompts/` directly — prompt assembly stays in one place.
3. **Determinism contract.** Generation inputs are hash-coupled: today the prompt text is
   embedded in `src/readme_agent/llm/prompts.py`, where `build_prompt(facts, policy)` takes
   only two already-hashed objects and `tests/unit/test_prompt_hash_coupling.py` enforces it.
   When prompt content migrates into files here (on next substantive touch, per governance),
   the loaded file content **joins the hashed inputs** — a changed prompt file must change the
   generation hash, never silently reuse a stale generation.
4. **Prompt changes are behavior changes.** They land with the tests that cover them, like any
   `src/` change.

## Current state

The one live prompt (relationship-explanation paragraph) lives in
`prompts/relationship_explained/` (`system.txt`, `user.txt`), loaded by
`src/readme_agent/llm/prompts.py::build_prompt()`. `prompt_content_hash()` in the same module
hashes the loaded assets and joins `RepositoryFacts.prompt_content_hash` (rule 3's determinism
contract) — migrated 2026-07-19, `GOV-016`.
