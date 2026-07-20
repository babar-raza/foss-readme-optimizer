# `templates/` — fill-and-match templates

The categorical home for **every template this project fills in or matches against** — README
owned-span skeletons and anything else with the fill-and-match shape. Governed by
`plans/GOVERNANCE.md` ("Repository layout", table row + placement rule 9).

## What belongs here

- README owned-span skeletons: the `resources` block (end of file) — see
  `docs/architecture.md`, "One owned span, not two"
- Any other skeleton used to **fill** (render output from policy/facts placeholders) or
  **match** (recognize a prior render for gap detection / idempotency)

Format follows the artifact's nature (`.md` skeletons, YAML/JSON structural specs, …).

## Organization

```
templates/<surface>/<self-explanatory-name>.<ext>
```

One subdirectory per surface (e.g. `readme/`), named for what it templates (naming rules:
`plans/GOVERNANCE.md`, "Machinery artifacts"). No enumerated or vague names.

## Rules

1. **Only the owning `src/` module loads a template** (today that's
   `src/readme_agent/readme/renderer.py` / `markers.py` for README spans). No other module or
   script reads `templates/` directly.
2. **Fill and match must stay in sync.** A template is both what the renderer emits and what
   gap detection/idempotency recognizes — changing one side without the other breaks the
   "second run makes zero LLM calls" property. Template changes land with the renderer,
   marker, and idempotency tests that prove both sides.
3. **Templates join the hashed generation inputs on migration**, same regime as prompts
   (placement rule 9): a changed template file must change the generation hash.

## Current state

The span skeletons are still embedded in `src/readme_agent/readme/renderer.py` (structure) and
`src/readme_agent/readme/markers.py` (span markers); they migrate here on next substantive
touch. New template content starts here from day one.
