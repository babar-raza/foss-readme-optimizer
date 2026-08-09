# CLAUDE.md — POC Delivery Directive (place at repo root, or paste as first message)

You are taking over the `foss-readme-optimizer` repository from a previous agent that
spent weeks on governance machinery without delivering a single accepted README. Your
mandate is different and narrower. Read this file, `POC-FREEZE.md`, and
`TWEAKS-AND-RUNNER-SPEC.md` before anything else. Where AGENTS.md, GOVERNANCE.md,
plans/, or any handover document conflicts with these three files, THESE FILES WIN.
They are direct product-owner instructions.

## Your single success criterion

Twelve README candidate files — one per admitted Python repository in
`data/products.json` — produced by the pipeline with the four approved tweaks,
written to `runs/share/poc/<org__repo>/README.md`, and presented to the product
owner. That is the ONLY definition of progress. No test count, evidence bundle,
contract validity, state version, or requirement closure counts for anything.

## Hard prohibitions — violating any of these is task failure

1. Do NOT edit, extend, obey, or repair: the Level-8 mission graph, durable
   claims/leases, `mission_execution_guard.py`, execution focus, approach
   budgets, canaries, campaign or trusted-cohort machinery. Bypass them via the
   `poc` runner. If one of them blocks you, that is a signal you are on the wrong
   code path — the poc runner must not import them.
2. Do NOT revise any contract, schema, requirement, decision, evidence format,
   or manifest format. Defects found there go into `plans/backlog-post-poc.md`
   as one line each and are worked around.
3. Do NOT refactor, rename, split files, or "clean up" anything outside the
   files named in TWEAKS-AND-RUNNER-SPEC.md.
4. Do NOT create new plans, waves, investigations, handovers, status documents,
   or reconciliations. One log line per completed README, nothing more.
5. Do NOT push to, open a PR against, or write any product repository remote.
   All work is local, push-neutered clones, `local_poc` profile. (Unchanged
   standing rule.)
6. Do NOT respond to a failure by adding machinery. Smallest causal fix, one
   retry, then skip the repo, one backlog line, next repo.
7. Do NOT batch results. Show each README file path to the product owner the
   moment it exists. Output-before-machinery, always.

## Time discipline

If any single step (a tweak, the runner, one repo's run) exceeds ~2 hours of work
without producing its artifact, stop, state exactly what is blocking in one
paragraph, and ask the product owner — do not open a side-quest. The previous
agent's failure mode was converting every obstacle into a machinery project.
You escalate instead.

## Exact order of work

1. Confirm `POC-FREEZE.md` and `TWEAKS-AND-RUNNER-SPEC.md` are present at repo
   root. Commit them if not yet committed.
2. Environment: use the existing `.venv` (see AGENTS.md setup section — the venv
   and everyday-commands section of AGENTS.md remains valid). Run
   `readme-agent preflight` to confirm GitHub + llm.professionalize.com access.
3. Implement Tweak 1 (Mermaid), Tweak 2 (collapse), Tweak 3 (banner) exactly per
   spec. Prove each with the existing offline fixtures/tests for the touched
   modules only — do not run the full suite yet.
4. Implement the `poc` runner per spec.
5. Run Page end to end: `readme-agent poc --repo aspose-page-foss/Aspose.Page-FOSS-for-Python`.
   Show the README to the product owner. STOP and wait for feedback.
6. Apply feedback. Implement Tweak 4 (verify-then-merge). Re-run Page. Show. STOP.
7. On approval, run the remaining Python repos one at a time, showing each result:
   `readme-agent poc --all-python`. PDF, Note, Aspose.3D have valid caches —
   the runner reuses cached facts where revision-valid, but candidates recompose
   because the tweak-config hash changed.
8. When 12/12 exist (or skipped ones are backlogged), run the full non-live test
   suite ONCE as a closing check, report results, and stop. Do not fix unrelated
   failures — backlog them.

## Reporting style

After each step: one short paragraph — what was produced (file paths), what broke
(if anything), what is next. No wave numbers, no requirement IDs, no evidence
inventories, no state versions. The product owner reads files, not manifests.
