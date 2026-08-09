# CLAUDE.md — Autonomous POC Delivery Directive (v2 — replaces v1)

**Change from v1: run AUTONOMOUSLY to completion. Do not stop and wait for human
feedback at checkpoints. The product owner reviews the finished set.**

You are taking over the `foss-readme-optimizer` repository from a previous agent that
spent weeks on governance machinery without delivering a single accepted README. Your
mandate is narrow and terminal. Read, in order: this file, `POC-FREEZE.md`,
`TWEAKS-AND-RUNNER-SPEC.md`, `golden-sample/GOLDEN-SAMPLE-NOTES.md`, and
`golden-sample/README.golden.md`. Where AGENTS.md, GOVERNANCE.md, plans/, or any
handover/mission document conflicts with these files, THESE FILES WIN. They are
direct product-owner instructions.

## Mission (terminal condition)

For every admitted Python repository in `data/products.json`: a README candidate
produced by the pipeline, matching the golden sample's shape, written to
`runs/share/poc/<org__repo>/README.md` with its `dispositions.json`,
`validation.json`, and `noop.json` beside it. When all Python repos have either a
delivered candidate or a one-line skip entry in `plans/backlog-post-poc.md`, write
`runs/share/poc/RESULTS.md` (table: repo, status, file path, open issues) and STOP.
That file is the POC. Nothing else counts as progress.

## The golden sample is the acceptance oracle

`golden-sample/README.golden.md` defines the target shape: banner placement,
Mermaid compactness, brief-then-collapse structure, source-content merge quality.
Before writing any code, diff the golden sample against
`runs/readme-poc/aspose-page-foss__Aspose.Page-FOSS-for-Python/dac5d70e.../candidate/README.md`
— that diff IS the specification of tweaks 1–4 expressed as output. Your Page
result must match the golden sample's shape (facts identical, prose equivalent).
Treat any shape divergence on Page as a bug in your implementation, not a
judgment call.

## Hard prohibitions — violating any is task failure

1. Do NOT edit, extend, obey, or repair: the Level-8 mission graph, durable
   claims/leases, `mission_execution_guard.py`, execution focus, approach budgets,
   canaries, campaign or trusted-cohort machinery. The `poc` runner must not
   import any of them. If one blocks you, you are on the wrong code path.
2. Do NOT revise any contract, schema, requirement, decision, evidence format, or
   manifest format. Defects there → one line in `plans/backlog-post-poc.md`,
   work around, continue.
3. Do NOT refactor, rename, split, or clean up anything outside the files named
   in TWEAKS-AND-RUNNER-SPEC.md plus the new `commands_poc.py`.
4. Do NOT create plans, waves, investigations, handovers, status regenerations,
   or reconciliations. One log line per delivered README.
5. Do NOT push to, PR against, or write any product repository remote. Local
   push-neutered clones, `local_poc` profile only. (Standing rule, unchanged.)
6. Do NOT respond to failure with machinery. Smallest causal fix, one retry,
   then skip the repo with a backlog line and continue. Never let one repo block
   the fleet.
7. Do NOT stop to ask for approval of styling/wording/structure decisions — the
   golden sample answers them. Choose the option closest to the sample and note
   it in RESULTS.md.

## When you MAY stop (only these)

- Credentials/network hard-fail (llm.professionalize.com or GitHub unreachable
  after retry) — report exactly what failed and stop.
- A prohibition and the mission genuinely conflict — state the conflict in one
  paragraph and stop.
- The terminal condition is met — write RESULTS.md and stop.
Everything else: decide per the golden sample and keep moving.

## Budget discipline

- Per step (a tweak, the runner, one repo run): ~2 hours. Over budget → smallest
  workaround or skip+backlog. Never a side-quest.
- LLM calls: composition + one review + at most one repair per repo. Cache-valid
  stages are reused; the no-op re-run must make ZERO calls. If a repo exceeds
  ~15 provider calls, something is looping — skip and backlog.

## Exact order of work

1. Verify POC-FREEZE.md, TWEAKS-AND-RUNNER-SPEC.md, and golden-sample/ are at
   repo root; commit if needed. Use the existing `.venv` (AGENTS.md setup section
   remains valid). `readme-agent preflight` to confirm GitHub + LLM access.
2. Study the golden-sample-vs-candidate diff (see above).
3. Implement Tweaks 1, 2, 3 per spec. Prove each against the golden sample using
   the touched modules' existing offline fixtures. Full suite NOT run here.
4. Implement Tweak 4 (verify-then-merge + disposition ledger) per spec, target
   shape `golden-sample/dispositions.golden.json`.
5. Implement `readme-agent poc` per spec.
6. Run Page first: `readme-agent poc --repo aspose-page-foss/Aspose.Page-FOSS-for-Python`.
   Compare the output against the golden sample; fix divergences; re-run until
   shape-matched (this replaces the human checkpoint).
7. Run every remaining Python repo one at a time (`--all-python`), appending each
   result to RESULTS.md as it lands. PDF, Note, Aspose.3D reuse revision-valid
   fact caches; candidates recompose because the tweak-config hash changed.
8. Write final RESULTS.md. Run the full non-live suite once, record pass/fail
   counts in RESULTS.md (do NOT fix unrelated failures — backlog them). Commit.
   Stop.

## Reporting style

Append to `runs/share/poc/RESULTS.md` as you go — one row per repo the moment it
completes, plus a short running notes section (what broke, what you skipped, what
needs the product owner's eye). No wave numbers, requirement IDs, state versions,
or evidence inventories anywhere. The product owner reads READMEs and RESULTS.md,
nothing else.
