# T5 — deterministic pilot skeleton (cells/python)

**Status: SUBSTANTIAL PROGRESS, not COMPLETE.** Recorded honestly — the card's own closeout bar
("full battery green + byte-identical double run") is only half met: the double-run proof is
real and complete; the battery did **not** go green, for reasons genuinely outside this card's
scope (see below). `GC-03` (G3 close) correctly stays blocked until this is resolved.

## What is genuinely done and verified

- **Real target, real network access, real clone**: `aspose-cells-foss/Aspose.Cells-FOSS-for-
  Python` confirmed real and clonable (`git ls-remote`); resolved at `main` @
  `26c3bd1633e84b91c0f6fad1fd353662fd61fb54`. Run via `readme-agent poc --repo
  aspose-cells-foss/Aspose.Cells-FOSS-for-Python` — the sanctioned local-candidate-generation
  tool for this repo (per standing project convention: no contract edits, no new machinery).
- **Byte-identical double run — PROVEN, twice over**: two independent CLI invocations produced
  byte-identical `README.md` (`sha256
  2e6579ea89c1a06ede70928e564c1f352584a88467b56dd66a46d39bd618a6f3` both times); run 2's stdout
  ("reusing hash-bound composition plan") and `noop.json` (`new_provider_call_count: 0`,
  `llm_accounting_status: "EXACT"`, `verdict: "RENDER_REPRODUCIBLE"`) independently confirm zero
  new LLM calls on the second run. Full details + exact commands: `run-log.md`.
- **Docker isolation machinery proven live**: the diagnostic `poc` path does not reach it (its
  `verified_example_present` check is a static substring match, confirmed by reading
  `document_validation.py:411` before claiming otherwise — never assumed). The full canonical
  `supervise` transaction reaches it but did not complete in available session time (see below).
  In its place, `tests/security/test_isolated_execution_docker_live.py` (normally excluded,
  `@pytest.mark.live`) was run explicitly and **passed 2/2** against a real pinned Alpine image
  with real container start/cleanup — genuine, live proof the capability works in this
  environment, short of a cells/python-specific Docker-verified run.

## What is NOT done, and why (honest, not fabricated)

**"Full battery green" was not achieved.** The real `validation.json` from both runs reports
`deterministic_verdict: "reject"` with concrete, real reasons:

- **9 blocking claim-accountability gaps** (`claim_accountability_complete: false`).
- **9 unauthorized protected-content losses** (`technical_terminology:*` fragment IDs).
- **A structurally invalid disposition ledger**: 13 of the original README's units (its H1 and
  effectively every H2 section) are `VERIFIED_MERGED`/`SUPERSEDED` in `dispositions.json` but
  carry an empty `target` field, which the ledger validator correctly flags as "retained unit
  without candidate destination" for all 13.

These are **real defects in the existing (pre-T5), soon-to-be-retired LLM/agentic composer
path** (`readme/agentic_composition.py` and friends) — the "old composer path" this entire plan
already designates a fallback, explicitly scheduled to retire at `T12` once the new deterministic
+ gateway-DAG pipeline (`T6`-`T8`) replaces it. T5's own card scope is a **pilot skeleton**, not
a mandate to debug and fix the pre-existing composer's disposition-ledger/claim-accountability
wiring — that repair is out of proportion to "skeleton," touches shared, heavily-consumed
machinery no lane in this plan currently owns, and duplicates work that rightfully belongs to
later cards (`T7D` dispositions, `TP-11A` preservation core) once the new pipeline exists to
receive the fix. Recorded here as a genuine, disclosed finding — not fixed, not hidden, not
force-passed.

**Full canonical Docker-verified run not completed.** `supervise --repo ... --execution-profile
local_dry_run` did not finish within available session time (terminated, no output). `--execution
-profile local_poc` (the CLI's own named full-coverage profile) requires `--registry
data/products.json` — a whole-30+-product portfolio run, disproportionate for a single-repo
pilot and not attempted for that reason.

## Downstream effect

`GC-03` (Gate G3 close) requires **both** `T14` (COMPLETE) and `T5` COMPLETE — it stays blocked.
`T6` onward (G4, prereq'd on `GC-03`) cannot start until T5's genuine gap above is resolved: either
by debugging the old composer's disposition/claim-accountability wiring (a bounded, well-scoped
follow-up now that the exact defect is documented) or by reaching G4's new deterministic pipeline
by some other legitimate route this plan's own cards define.
