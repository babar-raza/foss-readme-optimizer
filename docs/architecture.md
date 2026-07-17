# Architecture

## What this tool does

`readme-agent` audits a GitHub repository's README for four specific, independently-checkable
promotional elements and closes only what's missing:

- `license_mentioned` — does the README state the repo's license?
- `products_org_link` — does it link to the FOSS catalog page (`products.*.org/...`)?
- `products_com_link` — does it link to the commercial edition (`products.*.com/...`)?
- `relationship_explained` — does it explain the FOSS-vs-commercial relationship, with that
  explanation actually co-located with a real commercial/FOSS link (not just prose)?

This was derived empirically: a live audit of 14 real Aspose FOSS READMEs (2026-07-17, see
`tests/fixtures/readmes/real_audit_2026-07-17/`) found repos in three distinct states — fully
compliant (hand-authored), fully blank, and partially compliant — and a binary "has our marker or
not" design can't represent that. See `readme_agent/readme/gap_detector.py`.

## Pipeline order

```
allow-list check (data/products.json)
  -> preflight (GitHub read + LLM /models, both fail-closed)
  -> git safety (clone baseline, clone/reuse work, neuter push, install pre-push hook, verify)
  -> inspect (git metadata, file inventory, ecosystem manifest parse)
  -> gap-detect (scan the *whole* README, not just our own marker span)
  -> facts + facts_hash (repo metadata + policy content hash -- NOT gap_report, see below)
  -> decide: skip (compliant or hash-matches-and-still-valid) vs regenerate
  -> LLM call *only* if relationship_explained is a gap (every other element is
     deterministically rendered from policy config -- no LLM needed to know a URL
     that's already in config/policies/*.yml)
  -> render missing elements into two owned spans (callout, resources)
  -> validate (8 deterministic rules, always run, even on the skip path)
  -> evidence (redacted, atomic writes)
  -> commit locally if mode=full and status=GENERATED (never pushed)
```

## Two owned spans, not one

- `callout`: immediately after the H1. Short, addresses *prominence* (a real finding: one repo's
  only commercial link was buried at line 1890 of a 1890-line file).
- `resources`: appended at the end of the file. Fuller, mirrors the one real repo that already had
  this fully hand-authored (`aspose-3d-foss/Aspose.3D-FOSS-for-Java`).

Each renders **only** the specific elements missing for that repo. A repo missing only the org
link (the real `pdf/java` case) gets a one-line callout addition and nothing else — no LLM call,
no redundant restatement of content that's already there.

## Why facts_hash excludes gap_report

`gap_report` is *derived from* README content this tool itself rewrites. Including it in the hash
used to decide "should I regenerate" is circular: rendering closes gaps, which changes gap_report,
which would make the hash unable to ever match itself again. `facts_hash` covers only genuinely
independent inputs (repo metadata, detected license, policy content, generation schema version).
See `readme_agent/readme/facts.py` and the orchestrator test that caught this
(`tests/unit/test_orchestrator.py::TestBlankSlateRepo::test_second_run_is_idempotent_zero_llm_calls`).

## Idempotency requires a persistent work clone

This tool never pushes. That means the *only* place "run twice, second run makes zero LLM calls"
can be real is a local work clone that persists across separate CLI invocations
(`paths.work_dir`, keyed by `org/repo`, not by run-id). A fresh work clone every run would make
idempotency fictional, since the real upstream repo never receives our changes to remember them.
Evidence (`paths.evidence_dir`) is the opposite: always run-id-scoped, since it's meant to
accumulate as a historical audit trail.

## Module map

| Module | Responsibility |
|---|---|
| `registry/` | `data/products.json` + `config/policies/*.yml` loading, the allow-list gate |
| `preflight/` | GitHub + LLM connectivity checks, fail-closed |
| `gitsafety/` | Clone, push-neuter, pre-push hook, independent verification |
| `inspection/`, `ecosystems/` | Git metadata, file inventory, per-ecosystem manifest parsing |
| `readme/` | `gap_detector.py`, `markers.py` (two spans), `facts.py`, `renderer.py` |
| `llm/` | Strict-schema client (live + fixture), `prompts.py` (facts+policy only) |
| `validation/` | 8-rule deterministic registry |
| `license/`, `links/` | License classification, link checks |
| `evidence/` | Redaction, atomic writes, run manifest |
| `orchestrator.py` | Wires everything into `generate`/`run`/`run-registry`/`inspect`/`report` |
