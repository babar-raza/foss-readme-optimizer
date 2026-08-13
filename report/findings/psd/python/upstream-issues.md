# Upstream issues — Aspose.PSD FOSS for Python

**Repository:** `aspose-psd-foss/Aspose.PSD-FOSS-for-Python`
**Registry entry:** `data/products.json`, `family: "psd"`, `platform: "python"`, `mode: "disabled"`
(private repository; read-only access only, no push authority implied or exercised)
**Status:** No implementation source exists at all. **Not currently reusable as a source for an
accurate README.**

This is a consolidation of an already-established finding into the canonical location Decision
#101 requires for a repository whose source itself is missing (`report/findings/<family>/
<platform>/upstream-issues.md`), not a new investigation. The repository's state was independently
observed twice, on different dates, with consistent results:

- **2026-08-09** (`plans/backlog-post-poc.md`): local candidate delivery was made to work
  (authenticated read-only cloning, local Git-ref state backend, explicit Python policy profile,
  `mode: disabled` preserved), but the visible candidate remained `VALIDATION_FAILED` on one
  preserved source claim because "the upstream repository contains only a two-line README and no
  license or implementation evidence."
- **2026-08-12** (`logs/2026-08-12.md`, `master mission cohort external-blocker` entry): reconfirmed
  "the upstream repository has no source code at all (single 'Initial commit,' `README.md` only)."

## Bottom line

There is no Python package to import, no example to run, and no public API surface to describe.
The repository contains exactly one commit ("Initial commit") adding only a `README.md`. There is
no `src/`, no `pyproject.toml`, no test suite, and no license file. This is categorically different
from Aspose.TeX FOSS for Python's defect (`report/findings/tex/python/upstream-issues.md`): TeX
*has* a full, corrupted source tree that fails to parse; PSD has never had a source tree published
at all. Both are excluded from the working-condition-exception lane for the same reason — Decision
#101 explicitly routes a repository "whose source itself is non-importable or missing" here instead
— but PSD's specific defect is absence, not corruption.

## Why this repository does not currently get a generated README

Per the project's working-condition-presentation policy, a repository with no verified working
content has nothing a documentation pipeline can honestly show as "this works." There is no
Quick Start to run, no installed package to import, and no license to summarize. Fabricating any
of these from the product family's general conventions (e.g. assuming PSD/Python will eventually
mirror Aspose.PSD's other-platform API shape) would be inventing a fact this repository's own
content does not support, which the project's factuality rules forbid.

## Owner, evidence, and resume predicate

- **Owner:** product team responsible for `aspose-psd-foss/Aspose.PSD-FOSS-for-Python` (private
  repository; publishing real source is a product action, not something a README-generation agent
  can perform or infer).
- **Evidence:** `plans/backlog-post-poc.md` (2026-08-09 entry) and `logs/2026-08-12.md` (`master
  mission cohort external-blocker` entry), both independently observing the same single-commit,
  README-only state on different dates.
- **Disposition:** deferred (governance decision 102's terminology) — distinct from TeX's excluded
  disposition and HTML's accepted working-condition exception, but identical in effect: this
  repository does not count toward `NO_OP_PROVEN`, Gate A/B, or full-registry closure while
  deferred.
- **Resume predicate:** the product team publishes real, importable Python source (and, ideally, a
  license) to the repository. Once that happens, this repository re-enters the standard verified
  pipeline from `INTAKE_READY`/`FACTS_READY` like any other registry entry — this is a source
  question, not a presentation-contract question, so no template or validator change is implied.

## What was not done

No fresh independent re-investigation was run for this report (unlike TeX, which received one at
the product owner's explicit request after they stated distrust of the original analysis). This
report only consolidates the two already-independent 2026-08-09 and 2026-08-12 observations into
the canonical location. If the product owner wants the same standard of fresh, deliberately
unbiased re-verification applied to PSD that TeX received, that is separate, not-yet-requested
work.
