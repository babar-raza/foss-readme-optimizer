# Prepared change: render the empty-dependency `## Dependencies` section (queued, post-pass)

## The find (2026-08-18, fully deterministic)

The recurring cross-repo blocking claim `source:claim:*:7ff54c1da64deecb` is byte-exactly
`"No required third-party package dependencies.\n"` — verified by direct hashing; it appears in
the note, page, and email source READMEs (all of which are aspose.org's own earlier refreshes,
per the fleet-parity finding). Our `dependency_markdown()`
(`presentation/verified_template_sections.py`) renders the Dependencies slot only when
dependency data exists, so for zero-dependency repos the section — and that sentence — vanish
from the candidate, and the inherited claim has nowhere to survive: it blocks. aspose.org's
contract renders the section in the empty case with exactly that standard sentence (its four
fixed H3s cover "Required Package Dependencies" with the no-deps statement).

## The fix (one renderer change + tests; runtime source ⇒ after the pass + worktree merges)

In the empty case (python.distribution present, `runtime_dependencies` verified empty — NOT the
unknown/unverified case), `dependency_markdown()` returns the standard section body containing
the exact sentence `No required third-party package dependencies.` instead of None. Fail-closed
nuance: only when emptiness is a VERIFIED fact (manifest present and parsed); an absent/
unverifiable manifest keeps returning None. Regression tests: verified-empty renders the
sentence; unverified stays omitted; the inherited claim then survives mechanically
(claim-accountability accepts without any LLM disposition) — use email/page fixtures.

## Expected effect

Clears the boilerplate claim class deterministically in email/page (+anywhere else it recurs),
converges note without its LLM-ratchet dependence, closes the "aspose has Dependencies, ours
doesn't" parity gap on zero-dep repos, and removes the class's provider calls entirely.
