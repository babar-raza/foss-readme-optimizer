# Working-Condition-Presentation Exceptions

This tree is **not** the finalized, fresh-transaction-no-op-proven cohort at
`plans/investigations/evidence/finalized-repository-readmes-v1/`. Every README
here is delivered through the `readme-agent poc` diagnostic path (Decision #100)
and promoted only because a human explicitly accepted it, per repository, as a
bounded exception (Decision #101) -- the strict `supervise` pipeline cannot
currently pass for these repositories because of a genuine, evidence-backed
*upstream* defect, not an agent-fixable gap. None of these count toward
`NO_OP_PROVEN`, Gate A/B, or full-registry closure.

The gate for what this script is even allowed to promote is
`data/working_condition_exceptions.json`, hand-maintained and never auto-populated.
Each promoted repository's directory also contains its poc `validation.json`,
`UPSTREAM-DEFECTS.md`, and an `ACCEPTANCE-RECORD.json` recording who accepted the
exception, the exact blocking defect, and the resume predicate that returns the
repository to the strict lane once upstream is fixed.

Current exception count: **1 / 1 registry entries**.

| Platform | Repository | Source revision | Accepted | README |
| --- | --- | --- | --- | --- |
| Python | `aspose-html-foss/Aspose.HTML-FOSS-for-Python` | `c2356ec872fd` | 2026-08-12 | [Review README](repositories/python/html--c2356ec872fd--5ee3042d2b09/README.md) |
