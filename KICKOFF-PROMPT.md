# KICKOFF — paste this as your first message to Claude Code in VS Code

Before pasting: put these files in the repo root and commit them —
- POC-FREEZE.md
- TWEAKS-AND-RUNNER-SPEC.md
- CLAUDE-CODE-DIRECTIVE-v2-AUTONOMOUS.md  (rename to CLAUDE.md, or keep the name and reference it)
- golden-sample/README.golden.md
- golden-sample/GOLDEN-SAMPLE-NOTES.md
- golden-sample/dispositions.golden.json

Recommended session settings: allow file edits and shell commands for the repo
without per-command confirmation (auto-accept edits), since the run is meant to be
autonomous. Keep network access as-is; the runner needs GitHub and
llm.professionalize.com only.

---- PASTE EVERYTHING BELOW THIS LINE ----

You are taking over this repository under new product-owner authority. Read these
five files first, in this order, before doing anything else:

1. CLAUDE-CODE-DIRECTIVE-v2-AUTONOMOUS.md — your operating contract. It overrides
   AGENTS.md, GOVERNANCE.md, plans/, and every handover or mission document
   wherever they conflict.
2. POC-FREEZE.md — what is frozen and why.
3. TWEAKS-AND-RUNNER-SPEC.md — the four approved output changes and the `poc`
   runner you will build.
4. golden-sample/GOLDEN-SAMPLE-NOTES.md and golden-sample/README.golden.md — the
   exact target output, built from this repo's own Page candidate. The diff
   between README.golden.md and
   runs/readme-poc/aspose-page-foss__Aspose.Page-FOSS-for-Python/dac5d70e0f91949a780f2e98dfbb12314a5fbc70/candidate/README.md
   is the specification of the four tweaks expressed as output.

Then execute the directive's "Exact order of work" fully autonomously: implement
tweaks 1–4, build the `readme-agent poc` runner, prove Page against the golden
sample, then run every remaining admitted Python repository to completion,
maintaining runs/share/poc/RESULTS.md as you go. Do not stop for approval on
styling, wording, or structure — the golden sample answers those questions. Stop
only for the three conditions the directive lists (credential/network hard
failure, a genuine prohibition-vs-mission conflict, or the terminal condition
met).

Non-negotiables, as a reminder: no mission-graph/claim/guard machinery (bypass,
never repair), no contract or schema revisions, no refactors outside the spec'd
files, no product-remote writes of any kind, no machinery-building in response to
failures — smallest fix, one retry, skip and backlog. Every README you produce is
judged by one question: does it match the golden sample's shape with this
repository's verified facts, with zero silently dropped source content?

Begin now with step 1 of the directive: verify the files are present and
committed, confirm the venv, and run `readme-agent preflight`. Then report your
plan for tweaks 1–3 in five lines or fewer and proceed without waiting.
