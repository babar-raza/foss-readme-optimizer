# RDM-031 — LLM-authored code fences skip the normalization the deterministic path already has

## Status

Root-caused. Not repaired: the correct fix needs new markdown-fence-rewriting
logic (locate every CommonMark fence via `MarkdownIt` tokenization, replace
only its interior lines via the existing `normalize_code_snippet()`, leave
delimiter lines and all non-fence content byte-exact) -- a materially
different, higher-risk kind of change than this session's other additive-only
detection fixes (which only ever widen what an existing check authorizes,
never rewrite document text). Deferred rather than rushed.

## Symptom

`presentation.code_fence_spacing.<id>: Code fences must not contain trailing
whitespace or repeated blank lines.` blocks three repositories in the
`fleet-final2-20260826` portfolio pass: `aspose-cells-foss/Aspose.Cells-FOSS-
for-Go`, `aspose-cells-foss/Aspose.Cells-FOSS-for-Rust`, and `aspose-slides-
foss/Aspose.Slides-FOSS-for-.NET`. In all three cases it is one of several
concurrent blockers (alongside `claim_accountability`,
`semantic_duplicate`/`malformed_low_information_prose`, or `composition.
segment...lack exact candidate authority`), so fixing it alone would not by
itself fully unblock any of the three.

## Root cause

The check (`presentation_lint_structure.py:108`, via
`code_fence_presentation.py::inspect_code_fences()`) compares each fence's
raw content against `normalize_code_snippet()`'s cleaned version (strips
trailing whitespace per line, collapses repeated blank lines) and fails
whenever they differ.

`normalize_code_snippet()` is already called at every code-fence emission
site in the **deterministic** template renderer
(`presentation/verified_template_draft.py:367,380`;
`presentation/verified_template_sections.py:323,379,413,495,507`) -- so
deterministically-rendered fences never trip this check. The **agentic**
section-authoring path (`specialists/section_cluster_authoring.py` and
`section_authoring_fact_validation.py`, the same LLM-authored quick_start-
style content this session's other authoring fix touched) has no equivalent
call anywhere: an LLM-authored unit's code fence is accepted and inserted
into the candidate exactly as generated, trailing whitespace or doubled
blank lines included.

## Correct repair direction

Add a `normalize_all_code_fences(markdown: str) -> str` sibling to
`code_fence_presentation.py`, using the identical `MarkdownIt("commonmark")`
tokenization `inspect_code_fences()` already relies on: for each fence
token, keep its opening/closing delimiter lines (via `token.map`) byte-exact
and replace only the interior lines with `normalize_code_snippet(token.
content)`. Apply it once, deterministically, to the fully-assembled
candidate text right before the presentation-lint pass runs (or, more
narrowly, to each section-authoring unit's `.text` at acceptance) rather
than expecting every LLM-authoring call site to remember it. Iterate fence
replacements in reverse document order so earlier edits do not invalidate
later tokens' line-number ranges.

## Why it was not fixed here

Every other fix from this session's triage (the two quick_start authoring
patterns, RDM-029) was strictly additive: widen what an existing detector
recognizes as authorized, never touch the document text itself, which bounds
the blast radius to "fewer false blocks, never a new false accept." This fix
is structurally different -- it rewrites candidate text -- so a subtly wrong
line-range calculation (e.g. an unterminated fence at end-of-document, where
CommonMark's implicit close leaves no literal closing delimiter line) could
silently corrupt or duplicate content rather than merely fail to unblock a
repo. That risk profile warrants its own focused implementation and test
pass, not a rushed addition alongside this session's other work.
