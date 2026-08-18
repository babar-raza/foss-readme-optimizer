# TL-01 — import licensing / authorization gate

**Status: BLOCKED (genuine external authority gap).**

## Facts established this session

- Source repository: `https://github.com/aspose/aspose.org` (org `aspose`), HEAD
  `7f72da4e1423546104b40fa8cebf5b9ae3ce9c91` (re-verified 2026-08-15, unchanged from the
  earlier measurement).
- No `LICENSE`, `COPYING`, or `NOTICE` file exists at the repository root.
- No SPDX identifiers or copyright headers found in the four core modules under
  `scripts/pipeline/commands/foss/`.
- Default posture for unlicensed first-party corporate code is **all rights reserved** —
  the copyright owner is the entity controlling the `aspose` GitHub org (Aspose Pty Ltd, per
  the org name and product branding), not this repository or its committers.
- This repository's own git identity (`babar.raza@aspose.com`) suggests an employment or
  contractor relationship with that entity, but per this plan's own binding rule (§9's TL-01
  card, carried into this evidence): **relatedness to the same company does NOT by itself
  establish authority to copy, modify, or redistribute that company's code** — an explicit
  authorization is required, not inferred.

## Why this is genuinely blocked, not a task I can complete myself

I am executing autonomously with no interactive human available to grant a legally
consequential authorization mid-run. Recording an authorization I have no actual grant for
would be fabricating provenance, which this plan explicitly prohibits ("do NOT infer
relicensing rights merely because the repositories are related to the same company").

## Exact unblock request

A person with actual authority over `github.com/aspose/aspose.org`'s licensing needs to
either:
1. Add a LICENSE file to that repository establishing terms this project can rely on, or
2. Provide an explicit, written authorization (e.g., recorded in this evidence file, in a
   commit message, or in `plans/master.md`'s Decision Ledger) naming: the copyright owner,
   the specific paths authorized for import (the lean set: `scripts/pipeline/commands/foss/`,
   `scripts/pipeline/lib/backlink_targets.py`, `data/*.json` minus workspace artifacts,
   `keywords/`, `knowledge/` minus `_vectors/`/`scout/`, `reports/repo-presenter/`), and the
   permitted uses (copy, modify, redistribute within `foss-readme-optimizer`).

## Downstream effect

`T1A`/`T1B` (import execution) remain `BLOCKED`. `T3` (vendored check battery) and `T4`
(merged factpack) depend on `T1B` and are therefore also blocked. `GC-02` (G2 close) cannot
complete while `T3`/`T4` are unresolved, which prevents `G3` onward from opening. This is a
genuine, plan-designed stopping point — not a workaround-around-able gap.
